"""
genre_presets.py — Sonia Intelligence
Initial parameter presets by genre and instrumentation

Each preset serves as the "skeleton" for AI profile generation,
nurtured into personal aesthetics through the feedback loop.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class InstrumentFocus:
    """Instrument focus settings — brings a specific instrument to the foreground"""
    instrument: str = "none"          # piano / violin / cello / voice / brass / ...
    foreground_db: float = 0.0        # Amount to foreground (0–+6dB)
    focus_eq_band: str = "presence"   # EQ band used for focus
    focus_eq_gain: float = 0.0        # Focus EQ gain
    blend_mode: str = "ensemble"      # "solo_focus" / "ensemble_blend"


@dataclass
class GenrePreset:
    """
    Full parameter preset by genre and instrumentation.
    acoustic_space names refer to keys in acoustic_spaces.py.
    """
    name: str
    display_name: str
    description: str

    # Acoustic space
    acoustic_space: str = "musikverein"

    # EQ (gain in dB per band, default 0)
    eq: dict = field(default_factory=dict)

    # Dynamics
    compressor_threshold_db: float = -20.0
    compressor_ratio: float = 2.0
    compressor_attack_ms: float = 100.0
    compressor_release_ms: float = 400.0
    compressor_makeup_db: float = 0.0

    # Limiter
    limiter_limit_db: float = -1.5
    limiter_attack_ms: float = 8.0
    limiter_release_ms: float = 80.0

    # Instrument focus
    instrument_focus: InstrumentFocus = field(default_factory=InstrumentFocus)

    # Matching rules (for cross-referencing track metadata)
    match_tags: list = field(default_factory=list)
    match_period: list = field(default_factory=list)
    match_instrumentation: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ══════════════════════════════════════════════════════
# Genre Preset Definitions
# ══════════════════════════════════════════════════════

GENRE_PRESETS: dict[str, GenrePreset] = {

    # ─── Classical — Piano ────────────────────────────

    "piano_concerto_romantic": GenrePreset(
        name="piano_concerto_romantic",
        display_name="Romantic Piano Concerto",
        description="Chopin, Liszt, Rachmaninoff, etc. Piano in the foreground, rich dialogue with orchestra.",
        acoustic_space="musikverein",
        eq={
            "sub_bass": -1.0,
            "bass": 0.0,
            "low_mid": +1.0,    # Warmth in the piano's low range
            "presence": +2.0,   # Brilliance of the piano keystroke
            "air": +1.0,
        },
        compressor_threshold_db=-22, compressor_ratio=2.0,
        compressor_attack_ms=200, compressor_release_ms=600,
        instrument_focus=InstrumentFocus(
            instrument="piano", foreground_db=2.5,
            focus_eq_band="presence", focus_eq_gain=1.5,
            blend_mode="solo_focus"
        ),
        match_tags=["piano concerto", "ピアノ協奏曲"],
        match_period=["romantic", "late_romantic"],
        match_instrumentation=["piano", "orchestra"],
    ),

    "piano_concerto_modern": GenrePreset(
        name="piano_concerto_modern",
        display_name="Modern Piano Concerto",
        description="Ravel, Prokofiev, Bartók, etc. Emphasis on clarity and sharp rhythm.",
        acoustic_space="carnegie_hall",
        eq={
            "bass": -0.5,
            "upper_mid": +1.5,  # Clarity of modern works
            "presence": +2.5,   # Sharpness of the piano keystroke
            "air": +1.5,
        },
        compressor_threshold_db=-20, compressor_ratio=2.2,
        compressor_attack_ms=80, compressor_release_ms=350,
        instrument_focus=InstrumentFocus(
            instrument="piano", foreground_db=3.0,
            focus_eq_band="presence", focus_eq_gain=2.0,
            blend_mode="solo_focus"
        ),
        match_tags=["piano concerto"],
        match_period=["modern", "20th_century", "contemporary"],
        match_instrumentation=["piano", "orchestra"],
    ),

    "piano_solo_intimate": GenrePreset(
        name="piano_solo_intimate",
        display_name="Piano Solo (Intimate)",
        description="Chopin nocturnes, Schubert sonatas, etc. Emphasis on intimacy and delicate tone.",
        acoustic_space="small_chamber",
        eq={
            "sub_bass": -1.5,
            "low_mid": +1.5,    # Sustain pedal resonance
            "mid": +1.0,
            "presence": +1.5,
            "air": +2.0,        # Air around the keys
        },
        compressor_threshold_db=-24, compressor_ratio=1.6,
        compressor_attack_ms=300, compressor_release_ms=800,
        instrument_focus=InstrumentFocus(
            instrument="piano", foreground_db=0.0,
            blend_mode="ensemble"
        ),
        match_tags=["piano solo", "nocturne", "sonata"],
        match_instrumentation=["piano"],
    ),

    # ─── Classical — Strings ──────────────────────────

    "string_quartet": GenrePreset(
        name="string_quartet",
        display_name="String Quartet",
        description="Haydn, Beethoven, Schubert, etc. Blend of four voices and intimacy.",
        acoustic_space="small_chamber",
        eq={
            "bass": -1.0,
            "low_mid": +1.5,    # Cello body resonance
            "mid": +1.0,        # Viola midrange
            "upper_mid": +1.5,  # Violin brilliance
            "presence": +1.0,
        },
        compressor_threshold_db=-20, compressor_ratio=1.8,
        compressor_attack_ms=150, compressor_release_ms=500,
        instrument_focus=InstrumentFocus(blend_mode="ensemble"),
        match_tags=["string quartet", "弦楽四重奏"],
        match_instrumentation=["violin", "viola", "cello"],
    ),

    "symphony_full": GenrePreset(
        name="symphony_full",
        display_name="Symphony (Full Orchestra)",
        description="Brahms, Bruckner, Mahler, etc. Vast soundfield and rich dynamics.",
        acoustic_space="concertgebouw",
        eq={
            "sub_bass": +0.5,
            "bass": +1.0,       # Low strings and timpani
            "low_mid": +0.5,
            "mid": 0.0,
            "air": +1.0,        # Woodwind highs
        },
        compressor_threshold_db=-26, compressor_ratio=1.8,
        compressor_attack_ms=400, compressor_release_ms=1000,
        instrument_focus=InstrumentFocus(blend_mode="ensemble"),
        match_tags=["symphony", "交響曲"],
        match_instrumentation=["orchestra"],
    ),

    "violin_concerto": GenrePreset(
        name="violin_concerto",
        display_name="Violin Concerto",
        description="Beethoven, Brahms, Tchaikovsky, etc. Violin in the foreground.",
        acoustic_space="berliner_philharmonie",
        eq={
            "bass": -0.5,
            "upper_mid": +2.0,  # Violin frequency range
            "presence": +2.5,   # String sheen
            "air": +2.0,
        },
        compressor_threshold_db=-20, compressor_ratio=2.0,
        compressor_attack_ms=150, compressor_release_ms=500,
        instrument_focus=InstrumentFocus(
            instrument="violin", foreground_db=2.5,
            focus_eq_band="upper_mid", focus_eq_gain=2.0,
            blend_mode="solo_focus"
        ),
        match_tags=["violin concerto", "ヴァイオリン協奏曲"],
        match_instrumentation=["violin", "orchestra"],
    ),

    # ─── Classical — Vocal ────────────────────────────

    "opera_aria": GenrePreset(
        name="opera_aria",
        display_name="Opera Aria",
        description="Voice in the foreground with rich hall reverb. Lyric clarity with vocal sheen.",
        acoustic_space="carnegie_hall",
        eq={
            "low_mid": +1.0,    # Vocal warmth
            "mid": +1.5,        # Vocal clarity
            "upper_mid": +1.0,
            "presence": +1.5,   # Sibilance clarity
            "air": +1.0,
        },
        compressor_threshold_db=-18, compressor_ratio=2.2,
        compressor_attack_ms=40, compressor_release_ms=250,
        instrument_focus=InstrumentFocus(
            instrument="voice", foreground_db=2.0,
            focus_eq_band="mid", focus_eq_gain=1.5,
            blend_mode="solo_focus"
        ),
        match_tags=["opera", "aria", "soprano", "tenor"],
        match_instrumentation=["voice", "orchestra"],
    ),

    # ─── Jazz ─────────────────────────────────────────

    "jazz_trio": GenrePreset(
        name="jazz_trio",
        display_name="Jazz Trio (Piano / Bass / Drums)",
        description="Intimacy and warmth. Emphasis on upright bass presence and piano sheen.",
        acoustic_space="jazz_club",
        eq={
            "sub_bass": -1.0,
            "bass": +2.0,       # Upright bass fundamental
            "low_mid": +1.5,    # Piano warmth
            "mid": +0.5,
            "upper_mid": +1.0,
            "air": -1.0,        # Reduce highs for close-mic intimacy
        },
        compressor_threshold_db=-16, compressor_ratio=2.5,
        compressor_attack_ms=30, compressor_release_ms=300,
        match_tags=["jazz", "jazz trio", "piano trio"],
        match_instrumentation=["piano", "bass", "drums"],
    ),

    "jazz_vocal": GenrePreset(
        name="jazz_vocal",
        display_name="Jazz Vocal",
        description="Samara Joy, Diana Krall style. Exploits vocal sheen, mic texture, and proximity effect.",
        acoustic_space="jazz_club",
        eq={
            "bass": +1.0,       # Proximity effect (mic low-end boost)
            "low_mid": +1.5,    # Vocal warmth
            "mid": +2.0,        # Vocal presence
            "presence": +1.5,   # Consonant clarity
            "air": +0.5,
        },
        compressor_threshold_db=-14, compressor_ratio=2.0,
        compressor_attack_ms=20, compressor_release_ms=200,
        instrument_focus=InstrumentFocus(
            instrument="voice", foreground_db=2.5,
            focus_eq_band="mid", focus_eq_gain=2.0,
            blend_mode="solo_focus"
        ),
        match_tags=["jazz vocal", "vocal jazz"],
        match_instrumentation=["voice"],
    ),

    # ─── General / Default ────────────────────────────

    "default": GenrePreset(
        name="default",
        display_name="General Preset",
        description="Default settings when genre is undetermined. Sonia's baseline sound.",
        acoustic_space="musikverein",
        eq={},
        compressor_threshold_db=-20, compressor_ratio=2.0,
        compressor_attack_ms=100, compressor_release_ms=400,
        match_tags=[],
    ),
}


# ══════════════════════════════════════════════════════
# Automatic Genre Detection Logic
# ══════════════════════════════════════════════════════

def detect_preset(
    genre: str = "",
    title: str = "",
    artist: str = "",
    album: str = "",
    instrumentation: list[str] | None = None,
    period: str = "",
    composer: str = "",
    performer: str = "",
    si_preset: str = "",   # Manually registered value read from music_mood_db.json
) -> str:
    """
    Auto-detect preset name from metadata (multilingual, performer-aware).
    Detection priority:
      0. si_preset field (manually registered — top priority)
      1. Title / album name keywords
      2. Instrument inference from performer name
      3. Genre name (multilingual)
    """
    # ── 0. Manually registered preset takes top priority ────────
    if si_preset and si_preset in GENRE_PRESETS:
        return si_preset

    text = f"{genre} {title} {artist} {album} {composer} {performer}".lower()
    title_l = title.lower()
    album_l = album.lower()
    instr = [i.lower() for i in (instrumentation or [])]

    # ── Classical genre detection (multilingual) ────────────────
    CLASSICAL_GENRES = [
        "classical", "classique", "klassik", "classica",
        "クラシック", "古典", "classic"
    ]
    JAZZ_GENRES = ["jazz", "ジャズ", "bossa", "blues", "swing", "bebop"]
    is_classical = any(g in genre.lower() for g in CLASSICAL_GENRES)
    # Jazz detection: also checks title and album name, not just genre
    is_jazz = (any(g in genre.lower() for g in JAZZ_GENRES)
               or any(g in title_l for g in JAZZ_GENRES)
               or any(g in album_l for g in JAZZ_GENRES))

    # ── Jazz (detected first) ──────────────────────────────────
    if is_jazz:
        VOCAL_WORDS = ["vocal", "voice", "singer", "chant", "chanson",
                       "ヴォーカル", "ボーカル", "歌"]
        if any(w in text for w in VOCAL_WORDS):
            return "jazz_vocal"
        return "jazz_trio"

    # ── Piano Concerto ─────────────────────────────────────────
    PIANO_CONCERTO_WORDS = [
        "piano concerto", "ピアノ協奏曲", "klavierkonzert",
        "concerto pour piano", "concerto per pianoforte",
        "concerto no", "piano con",
    ]
    if any(w in text for w in PIANO_CONCERTO_WORDS):
        # Concerto with orchestra — also check orchestra keywords
        MODERN_COMPOSERS = [
            "ravel", "bartók", "bartok", "prokofiev", "shostakovich",
            "shostakovitch", "stravinsky", "britten", "hindemith",
            "ラヴェル", "バルトーク", "プロコフィエフ"
        ]
        if (any(p in period.lower() for p in ["modern", "20th", "contemporary"])
                or any(c in text for c in MODERN_COMPOSERS)):
            return "piano_concerto_modern"
        return "piano_concerto_romantic"

    # ── Violin Concerto ────────────────────────────────────────
    if any(w in text for w in ["violin concerto", "ヴァイオリン協奏曲",
                                "violinkonzert", "concerto pour violon"]):
        return "violin_concerto"

    # ── String Quartet ─────────────────────────────────────────
    if any(w in text for w in ["string quartet", "弦楽四重奏", "streichquartett",
                                "quatuor", "quartet", "quartett"]):
        return "string_quartet"

    # ── Chamber music in general (piano trio, quintet, etc.) ───
    CHAMBER_WORDS = [
        "piano trio", "ピアノ三重奏", "klaviertrio",
        "piano quartet", "ピアノ四重奏",
        "piano quintet", "ピアノ五重奏",
        "string trio", "弦楽三重奏",
        "string quintet", "弦楽五重奏", "streichquintett",
        "clarinet trio", "clarinet quintet",
        "horn trio", "horn quintet",
        "chamber", "kammermusik", "musique de chambre",
        "trio", "quintet", "sextet", "octet",
        "室内楽",
    ]
    if any(w in text for w in CHAMBER_WORDS):
        return "string_quartet"  # Chamber music best suits the string quartet preset (small hall)

    # ── Symphony / Orchestral ──────────────────────────────────
    SYMPHONY_WORDS = [
        "symphony", "symphonie", "sinfonie", "sinfonia",
        "交響曲", "orchestral", "philharmonic", "philharmonique",
        "overture", "ouverture", "tone poem", "poème",
    ]
    if any(w in text for w in SYMPHONY_WORDS):
        return "symphony_full"

    # ── Opera / Vocal ──────────────────────────────────────────
    VOCAL_CLASSICAL = [
        "opera", "aria", "soprano", "tenor", "mezzo", "baritone",
        "lied", "lieder", "mélodie", "cantata", "oratorio",
        "mass", "messe", "requiem", "missa",
        "声楽", "歌曲", "カンタータ", "レクイエム"
    ]
    if any(w in text for w in VOCAL_CLASSICAL):
        return "opera_aria"

    # ── Piano solo (title/album keywords) ─────────────────────
    PIANO_SOLO_TITLE_WORDS = [
        "nocturne", "nocturnes",
        "prélude", "préludes", "prelude", "preludes",
        "étude", "etude", "études", "etudes",
        "ballade", "ballades",
        "sonata", "sonate", "sonatine",
        "impromptu", "impromptus",
        "mazurka", "mazurkas",
        "waltz", "waltzes", "valse", "valses",
        "scherzo",
        "intermezzo", "intermezzi",
        "berceuse", "barcarolle",
        "fantasy", "fantaisie", "fantasie",
        "variation", "variations",
        "suite", "partita",
        "moment musical", "moments musicaux",
        "klavierstück", "klavierwerke",
        "piano works", "piano music", "piano pieces",
        "ピアノ曲", "ピアノ作品", "ピアノ小品",
    ]
    if any(w in title_l for w in PIANO_SOLO_TITLE_WORDS) or \
       any(w in album_l for w in PIANO_SOLO_TITLE_WORDS):
        # If no orchestra-related words in title → classify as piano solo
        ORCH_WORDS = ["orchestra", "philharmonic", "symphon", "concerto"]
        if not any(w in text for w in ORCH_WORDS):
            return "piano_solo_intimate"

    # ── Infer piano solo from performer name ───────────────────
    # If a known pianist appears in the performer field → treat as piano solo
    KNOWN_PIANISTS = [
        "zimerman", "argerich", "pollini", "brendel", "ashkenazy",
        "rubinstein", "horowitz", "gould", "richter", "kissin",
        "pogorelich", "perahia", "lupu", "sokolov", "uchida",
        "radu lupu", "barenboim", "ax", "andsnes", "hewitt",
        "buniatishvili", "trifonov", "feinberg", "yuja wang",
        "内田光子", "ツィメルマン", "アルゲリッチ", "ポリーニ",
    ]
    performer_l = performer.lower()
    artist_l    = artist.lower()
    if any(p in performer_l or p in artist_l for p in KNOWN_PIANISTS):
        # Pianist + no orchestra words → piano solo
        ORCH_WORDS = ["orchestra", "philharmonic", "symphon", "concerto",
                      "conducted", "conductor", "dirigent"]
        if not any(w in text for w in ORCH_WORDS):
            return "piano_solo_intimate"
        # Orchestra words present → concerto
        MODERN_COMPOSERS = ["ravel", "bartók", "bartok", "prokofiev",
                            "shostakovich", "ラヴェル", "バルトーク"]
        if any(c in text for c in MODERN_COMPOSERS):
            return "piano_concerto_modern"
        return "piano_concerto_romantic"

    # ── Classical general fallback ─────────────────────────────
    if is_classical:
        # If album contains orchestra keywords → symphony category
        ORCH_WORDS = ["orchestra", "philharmonic", "symphon", "chamber"]
        if any(w in album_l for w in ORCH_WORDS):
            return "symphony_full"
        return "default"

    return "default"


def get_preset(name: str) -> GenrePreset:
    """Retrieve a preset by name. Returns "default" if not found."""
    return GENRE_PRESETS.get(name, GENRE_PRESETS["default"])


def list_presets() -> list[dict]:
    """List available presets (for UI display)."""
    return [
        {
            "name": p.name,
            "display_name": p.display_name,
            "acoustic_space": p.acoustic_space,
            "description": p.description,
        }
        for p in GENRE_PRESETS.values()
    ]


if __name__ == "__main__":
    print("=== Sonia Intelligence — Genre Presets ===\n")
    for info in list_presets():
        print(f"  [{info['name']:35s}] space={info['acoustic_space']}")

    print("\n--- Auto-detection test ---")
    tests = [
        dict(genre="Classical", title="Piano Concerto No.2", artist="Rachmaninoff"),
        dict(genre="Classical", title="Piano Concerto in G", artist="Ravel", period="modern"),
        dict(genre="Jazz", artist="Samara Joy", instrumentation=["voice"]),
        dict(genre="Classical", title="String Quartet No.14", artist="Schubert"),
    ]
    for t in tests:
        result = detect_preset(**t)
        print(f"  {t.get('title', t.get('artist', ''))} → [{result}]")
