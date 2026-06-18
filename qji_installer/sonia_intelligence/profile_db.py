"""
profile_db.py — Sonia Intelligence
Profile database management

A database that accumulates Yasuhito's musical aesthetics.
The core of the "learning" loop:
feedback history → trend analysis → automatic application to similar tracks.
"""

import json
import os
import copy
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

from genre_presets import GenrePreset, get_preset, detect_preset
from filter_builder import PlayerParams, params_from_preset, apply_delta_to_params


PROFILE_DB_PATH = os.path.expanduser("~/.config/sonia/profile_db.json")


@dataclass
class TuningRecord:
    """Single adjustment record from a feedback event"""
    timestamp: str
    feedback_text: str
    preset_name: str
    delta_summary: dict
    confidence: float


@dataclass
class SoniaProfile:
    """
    A complete profile for one musical context.
    Deepens through repeated use and feedback.
    """
    profile_id: str
    display_name: str
    description: str

    # マッチングタグ
    tags: list = field(default_factory=list)

    # 対応するジャンルプリセット名
    base_preset: str = "default"

    # 音響空間
    acoustic_space: str = "musikverein"

    # 現在のパラメータ（最新の調整済み値）
    current_params: dict = field(default_factory=dict)

    # フィードバック調整履歴
    tuning_history: list = field(default_factory=list)

    # 使用統計
    listen_count: int = 0
    last_used: str = ""

    # 満足度スコア（将来: 👍/👎で蓄積）
    satisfaction_score: float = 0.5

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SoniaProfile":
        obj = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        return obj


class ProfileDatabase:
    """
    CRUD and matching for the profile DB.
    JSON file-based (can be migrated to SQLite in the future).
    """

    def __init__(self, db_path: str = PROFILE_DB_PATH):
        self.db_path = db_path
        self.profiles: dict[str, SoniaProfile] = {}
        # アルバム名/フォルダ名 → プリセット名 の手動登録マップ
        self.album_presets: dict[str, str] = {}
        self._load()

    def _load(self):
        """Load from DB file"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for pid, pdata in data.get("profiles", {}).items():
                    self.profiles[pid] = SoniaProfile.from_dict(pdata)
                # アルバムプリセットマップを読み込む
                self.album_presets = data.get("album_presets", {})
            except Exception as e:
                print(f"[ProfileDB] Load error: {e}")

    def save(self):
        """Save to DB file"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        data = {
            "version": "1.0",
            "updated": datetime.now().isoformat(),
            "profiles": {pid: p.to_dict() for pid, p in self.profiles.items()},
            "album_presets": self.album_presets,
        }
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_album_preset(self, album: str, folder: str = "") -> Optional[str]:
        """
        Search for a manually registered preset by album or folder name.
        Returns: preset name or None
        """
        if album and album in self.album_presets:
            return self.album_presets[album]
        if folder:
            folder_name = os.path.basename(folder.rstrip("/"))
            if folder_name in self.album_presets:
                return self.album_presets[folder_name]
        return None

    def save_album_preset(self, album: str, folder: str, preset_name: str):
        """
        Register and save a preset for both album name and folder name.
        """
        if album:
            self.album_presets[album] = preset_name
        if folder:
            folder_name = os.path.basename(folder.rstrip("/"))
            if folder_name:
                self.album_presets[folder_name] = preset_name
        self.save()
        print(f"[ProfileDB] Album preset saved: '{album}' → {preset_name}")

    # ── CRUD ────────────────────────────────────────

    def get(self, profile_id: str) -> Optional[SoniaProfile]:
        return self.profiles.get(profile_id)

    def list_profiles(self) -> list[SoniaProfile]:
        return sorted(self.profiles.values(), key=lambda p: p.last_used, reverse=True)

    def create_from_preset(
        self,
        preset_name: str,
        profile_id: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> SoniaProfile:
        """Create a new profile from a genre preset"""
        preset = get_preset(preset_name)
        pid = profile_id or preset_name
        params = params_from_preset(preset_name)

        profile = SoniaProfile(
            profile_id=pid,
            display_name=display_name or preset.display_name,
            description=preset.description,
            tags=preset.match_tags.copy(),
            base_preset=preset_name,
            acoustic_space=preset.acoustic_space,
            current_params=self._params_to_dict(params),
            last_used=datetime.now().isoformat(),
        )
        self.profiles[pid] = profile
        return profile

    def delete(self, profile_id: str) -> bool:
        if profile_id in self.profiles:
            del self.profiles[profile_id]
            return True
        return False

    # ── フィードバック適用 ─────────────────────────

    def apply_feedback(
        self,
        profile_id: str,
        feedback_text: str,
        delta,  # ParamDelta from feedback_interpreter
    ) -> Optional[SoniaProfile]:
        """
        Apply feedback to a profile and record history.
        Returns: updated SoniaProfile
        """
        profile = self.get(profile_id)
        if profile is None:
            return None

        # 現在のParamDeltaをPlayerParamsに変換して適用
        current = self._dict_to_params(profile.current_params, profile.base_preset)
        updated = apply_delta_to_params(current, delta)

        # プロファイル更新
        profile.current_params = self._params_to_dict(updated)
        profile.tuning_history.append(asdict(TuningRecord(
            timestamp=datetime.now().isoformat(),
            feedback_text=feedback_text,
            preset_name=profile.base_preset,
            delta_summary=self._delta_to_summary(delta),
            confidence=delta.confidence,
        )))
        profile.last_used = datetime.now().isoformat()
        self.save()
        return profile

    def record_listen(self, profile_id: str):
        """Update play count"""
        profile = self.get(profile_id)
        if profile:
            profile.listen_count += 1
            profile.last_used = datetime.now().isoformat()
            self.save()

    # ── マッチング ────────────────────────────────

    def find_matching_profile(
        self,
        genre: str = "",
        title: str = "",
        artist: str = "",
        album: str = "",
        instrumentation: list = None,
        period: str = "",
    ) -> tuple[Optional[SoniaProfile], float]:
        """
        Search for the best matching profile from track metadata.
        Returns: (profile, score) — if score < threshold, creating a new profile is recommended
        """
        text = f"{genre} {title} {artist} {album}".lower()
        best_profile = None
        best_score = 0.0

        for profile in self.profiles.values():
            score = self._match_score(profile, text, instrumentation or [], period)
            if score > best_score:
                best_score = score
                best_profile = profile

        return best_profile, best_score

    def _match_score(
        self,
        profile: SoniaProfile,
        text: str,
        instrumentation: list,
        period: str,
    ) -> float:
        """Calculate match score with profile (0–1)"""
        score = 0.0
        max_score = 0.0

        for tag in profile.tags:
            max_score += 1.0
            if tag.lower() in text:
                score += 1.0

        if max_score == 0:
            return 0.0

        return score / max_score

    # ── ヘルパー ──────────────────────────────────

    def _params_to_dict(self, params: PlayerParams) -> dict:
        """Convert PlayerParams to dict (for JSON serialization)"""
        return {
            "eq": params.eq,
            "compressor_threshold_db": params.compressor_threshold_db,
            "compressor_ratio": params.compressor_ratio,
            "compressor_attack_ms": params.compressor_attack_ms,
            "compressor_release_ms": params.compressor_release_ms,
            "compressor_makeup_db": params.compressor_makeup_db,
            "limiter_limit_db": params.limiter_limit_db,
            "acoustic_space": params.acoustic_space,
            "rt60_override": params.rt60_override,
            "wet_override": params.wet_override,
            "pre_delay_override": params.pre_delay_override,
            "side_ratio_override": params.side_ratio_override,
            "instrument_focus_db": params.instrument_focus_db,
            "instrument_focus_band": params.instrument_focus_band,
            "instrument_focus_gain": params.instrument_focus_gain,
            "hall_simulation": params.hall_simulation,
            "echo_enabled": params.echo_enabled,
        }

    def _dict_to_params(self, d: dict, preset_name: str = "default") -> PlayerParams:
        """Restore PlayerParams from dict"""
        base = params_from_preset(preset_name)
        for key, val in d.items():
            if hasattr(base, key):
                setattr(base, key, val)
        return base

    def _delta_to_summary(self, delta) -> dict:
        """Convert ParamDelta to dict for storage (omit zero values)"""
        result = {}
        float_fields = [f for f in delta.__dataclass_fields__
                        if isinstance(getattr(delta, f), float)
                        and f not in ("confidence",)]
        for f in float_fields:
            v = getattr(delta, f)
            if abs(v) > 0.01:
                result[f] = round(v, 3)
        return result

    # ── 傾向分析（Stage 4への布石）────────────────

    def analyze_preferences(self) -> dict:
        """
        Analyse listening preference trends from all feedback history.
        Used in Stage 4 for automatic application to similar tracks.
        """
        all_deltas = {}
        total_records = 0

        for profile in self.profiles.values():
            for record in profile.tuning_history:
                total_records += 1
                for param, val in record.get("delta_summary", {}).items():
                    all_deltas[param] = all_deltas.get(param, 0.0) + val

        if total_records == 0:
            return {"message": "No feedback history yet"}

        # 平均を計算
        averages = {k: v / total_records for k, v in all_deltas.items()}
        sorted_prefs = sorted(averages.items(), key=lambda x: abs(x[1]), reverse=True)

        return {
            "total_feedback_records": total_records,
            "top_preferences": sorted_prefs[:10],
            "summary": _describe_preferences(sorted_prefs[:5]),
        }


def _describe_preferences(prefs: list) -> str:
    """Describe trends in plain language"""
    if not prefs:
        return "No trend data"
    lines = []
    param_desc = {
        "eq_presence": "2kHz band (piano brilliance / string sheen)",
        "rt60_delta": "Reverb time",
        "foreground_db_delta": "Instrument focus (foreground)",
        "eq_bass": "Bass",
        "eq_air": "High-frequency air",
        "eq_low_mid": "200Hz band (warmth)",
    }
    for param, avg in prefs:
        direction = "increase" if avg > 0 else "decrease"
        desc = param_desc.get(param, param)
        lines.append(f"  tendency to {direction} {desc} (avg {avg:+.2f})")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════
# Sonia本体との統合インターフェース
# ══════════════════════════════════════════════════════

class SoniaIntelligence:
    """
    Main interface called from the Sonia player.
    Manages playback start, feedback handling, and filter chain generation.
    """

    def __init__(self):
        self.db = ProfileDatabase()
        self.current_profile_id: Optional[str] = None
        self.current_params: Optional[PlayerParams] = None
        self._last_was_default: bool = False   # True if general preset was used
        self._pending_album: str = ""          # Album name currently playing
        self._pending_folder: str = ""         # Folder path currently playing

    def on_track_start(
        self,
        genre: str = "",
        title: str = "",
        artist: str = "",
        album: str = "",
        instrumentation: list = None,
        period: str = "",
        composer: str = "",
        performer: str = "",
        folder: str = "",
        si_preset: str = "",   # Manually registered value from music_mood_db.json
    ) -> str:
        """
        Called at track start.
        Selects the appropriate profile and returns an ffmpeg filter chain.
        Priority:
          1. Manually registered album/folder preset (top priority)
          2. Existing profile DB (score ≥ 0.5)
          3. Auto-detection from metadata
        """
        from filter_builder import build_filter_chain

        # ── 1. アルバム手動登録プリセットを最優先で確認 ──────────
        album_preset_name = self.db.get_album_preset(album, folder)
        if album_preset_name:
            self.current_params = params_from_preset(album_preset_name)
            # プロファイルDBにも登録（なければ作成）
            pid = f"album__{album_preset_name}"
            if not self.db.get(pid):
                self.db.create_from_preset(album_preset_name, profile_id=pid,
                                           display_name=f"{album or folder} [{get_preset(album_preset_name).display_name}]")
            self.current_profile_id = pid
            self.db.record_listen(pid)
            preset = get_preset(album_preset_name)
            status = f"Album preset: {preset.display_name}"
            self._last_was_default = False
            print(f"[Sonia Intelligence] {status}")
            return build_filter_chain(self.current_params)

        # ── 2. プロファイルDB検索 ─────────────────────────────────
        profile, score = self.db.find_matching_profile(
            genre, title, artist, album, instrumentation, period
        )

        if profile and score >= 0.5:
            preset_name = profile.base_preset
            self.current_profile_id = profile.profile_id
            self.current_params = self.db._dict_to_params(
                profile.current_params, preset_name
            )
            self.db.record_listen(profile.profile_id)
            self._last_was_default = (preset_name == "default")
            status = f"Profile applied: {profile.display_name}"
        else:
            # ── 3. メタデータから自動判定 ────────────────────────
            preset_name = detect_preset(
                genre=genre, title=title, artist=artist, album=album,
                instrumentation=instrumentation, period=period,
                composer=composer, performer=performer,
                si_preset=si_preset,
            )
            profile = self.db.create_from_preset(preset_name)
            self.current_profile_id = profile.profile_id
            self.current_params = params_from_preset(preset_name)
            self.db.save()
            self._last_was_default = (preset_name == "default")
            status = f"New profile created: {profile.display_name}"

        # 汎用フォールバックになった場合は手動選択を促すフラグを立てる
        self._pending_album = album
        self._pending_folder = folder

        print(f"[Sonia Intelligence] {status}")
        chain = build_filter_chain(self.current_params)
        return chain

    def on_feedback(self, feedback_text: str) -> tuple[str, str]:
        """
        Called when user feedback is received.
        Returns: (new filter chain, interpretation description)
        """
        from feedback_interpreter import interpret_feedback, describe_delta
        from filter_builder import build_filter_chain

        if self.current_profile_id is None:
            return "", "No profile selected"

        delta = interpret_feedback(feedback_text)
        if delta is None:
            return "", "Could not interpret feedback (querying Claude API)"

        # プロファイルに適用・保存
        updated_profile = self.db.apply_feedback(
            self.current_profile_id, feedback_text, delta
        )
        if updated_profile:
            self.current_params = self.db._dict_to_params(
                updated_profile.current_params, updated_profile.base_preset
            )

        chain = build_filter_chain(self.current_params)
        explanation = f"Interpretation: {delta.interpretation}\nChanges:\n{describe_delta(delta)}"
        return chain, explanation

    def get_current_filter_chain(self) -> str:
        """Get the current filter chain"""
        if self.current_params is None:
            from filter_builder import params_from_preset
            self.current_params = params_from_preset("default")
        from filter_builder import build_filter_chain
        return build_filter_chain(self.current_params)

    def apply_album_preset(self, preset_name: str) -> str:
        """
        Manually register and apply a preset for the current album.
        Saved to album_presets in profile_db.json.
        Returns: new filter chain
        """
        from filter_builder import build_filter_chain, params_from_preset
        from genre_presets import get_preset

        # パラメータ適用
        self.current_params = params_from_preset(preset_name)

        # プロファイルDB更新
        pid = f"album__{preset_name}__{self._pending_album or 'unknown'}"
        if not self.db.get(pid):
            preset = get_preset(preset_name)
            self.db.create_from_preset(
                preset_name,
                profile_id=pid,
                display_name=f"{self._pending_album or self._pending_folder} [{preset.display_name}]"
            )
        self.current_profile_id = pid

        # アルバム→プリセットのマッピングを永続保存
        self.db.save_album_preset(
            self._pending_album,
            self._pending_folder,
            preset_name
        )
        self._last_was_default = False

        return build_filter_chain(self.current_params)


if __name__ == "__main__":
    print("=== Sonia Intelligence — Profile Database ===\n")

    # 動作テスト（一時的なテストDB）
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        test_db_path = f.name

    si = SoniaIntelligence()
    si.db.db_path = test_db_path

    print("1. Ravel Piano Concerto — track start")
    chain = si.on_track_start(
        genre="Classical",
        title="Piano Concerto in G",
        artist="Ravel",
        period="modern"
    )
    print(f"   Filter chain generated ({len(chain)} chars)")

    print("\n2. Feedback: 'More piano presence'")
    new_chain, explanation = si.on_feedback("more piano presence")
    print(f"   {explanation}")

    print("\n3. Feedback: 'More hall depth'")
    new_chain, explanation = si.on_feedback("more hall depth")
    print(f"   {explanation}")

    print("\n4. Preference analysis")
    prefs = si.db.analyze_preferences()
    print(f"   Feedback records: {prefs.get('total_feedback_records', 0)}")

    os.unlink(test_db_path)
    print("\nDone")
