"""
filter_builder.py — Sonia Intelligence
GenrePreset + AcousticSpace + ProfileParams → ffmpeg filter chain string

Dynamically generates the -af option string passed to Sonia's playback function.
Maintains compatibility with the existing Sonia filter chain (alimiter, acompressor, aecho, etc.).
"""

from dataclasses import dataclass, field
from typing import Optional

from acoustic_spaces import AcousticSpace, get_space, space_to_ffmpeg_params
from genre_presets import GenrePreset, get_preset


# EQ band definitions: band name → (centre frequency Hz, width Hz)
EQ_BAND_SPECS = {
    "sub_bass":   (40,    60),
    "bass":       (80,    100),
    "low_mid":    (200,   160),
    "mid":        (500,   300),
    "upper_mid":  (1000,  500),
    "presence":   (2000,  800),
    "high_mid":   (4000,  1500),
    "air_low":    (6000,  2000),
    "air":        (10000, 3000),
    "air_high":   (16000, 4000),
}


@dataclass
class PlayerParams:
    """
    Current player state parameters.
    Passed from CurrentParams in profile_db.py.
    """
    # EQ (gain in dB per band)
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

    # Acoustic space
    acoustic_space: str = "musikverein"
    # Space overrides (individual adjustments via feedback)
    rt60_override: Optional[float] = None
    wet_override: Optional[float] = None
    pre_delay_override: Optional[float] = None
    side_ratio_override: Optional[float] = None

    # Instrument focus
    instrument_focus_db: float = 0.0
    instrument_focus_band: str = "presence"
    instrument_focus_gain: float = 0.0

    # Musikverein hall simulation toggle (V key compatible)
    hall_simulation: bool = True

    # Echo (for jazz vocal)
    echo_enabled: bool = False


def build_filter_chain(params: PlayerParams, sample_rate: int = 44100) -> str:
    """
    Generate an ffmpeg -af filter chain string from PlayerParams.

    Returns:
        str: string passed to the -af option
             e.g.: "acompressor=...,equalizer=...,aecho=...,alimiter=..."
    """
    filters = []

    # ─── 1. EQ filters ──────────────────────────────
    eq_filters = _build_eq_filters(params.eq)
    if eq_filters:
        filters.extend(eq_filters)

    # ─── 2. Instrument focus EQ ─────────────────────
    if abs(params.instrument_focus_db) > 0.01 or abs(params.instrument_focus_gain) > 0.01:
        focus_filters = _build_instrument_focus(params)
        filters.extend(focus_filters)

    # ─── 3. Dynamics (acompressor) ──────────────────
    compressor = _build_compressor(params)
    filters.append(compressor)

    # ─── 4. Acoustic space (aecho) ──────────────────
    if params.hall_simulation:
        space_filters = _build_acoustic_space(params)
        filters.extend(space_filters)

    # ─── 5. Jazz vocal echo ─────────────────────────
    if params.echo_enabled:
        filters.append(_build_jazz_echo())

    # ─── 6. Limiter (final stage) ───────────────────
    limiter = _build_limiter(params)
    filters.append(limiter)

    return ",".join(filters)


def _build_eq_filters(eq: dict) -> list[str]:
    """Convert EQ bands to ffmpeg equalizer filters"""
    result = []
    for band_name, gain_db in eq.items():
        if abs(gain_db) < 0.1:  # Negligible change
            continue
        if band_name not in EQ_BAND_SPECS:
            continue
        freq, width = EQ_BAND_SPECS[band_name]
        result.append(f"equalizer=f={freq}:t=h:width={width}:g={gain_db:.1f}")
    return result


def _build_instrument_focus(params: PlayerParams) -> list[str]:
    """Instrument focus EQ (foregrounding)"""
    result = []

    # Foreground: boost the focus band
    if abs(params.instrument_focus_gain) > 0.01:
        band = params.instrument_focus_band
        if band in EQ_BAND_SPECS:
            freq, width = EQ_BAND_SPECS[band]
            result.append(
                f"equalizer=f={freq}:t=h:width={width}:g={params.instrument_focus_gain:.1f}"
            )

    # Focus dB approximates volume-based foregrounding
    # (mix balance adjustment would be ideal, but EQ is used here)
    if abs(params.instrument_focus_db) > 0.01:
        # Lift the overall presence band
        result.append(
            f"equalizer=f=2500:t=h:width=2000:g={params.instrument_focus_db * 0.5:.1f}"
        )

    return result


def _build_compressor(params: PlayerParams) -> str:
    """Generate acompressor filter string"""
    makeup = params.compressor_makeup_db
    return (
        f"acompressor="
        f"threshold={params.compressor_threshold_db:.0f}dB:"
        f"ratio={params.compressor_ratio:.1f}:"
        f"attack={params.compressor_attack_ms:.0f}:"
        f"release={params.compressor_release_ms:.0f}:"
        f"makeup={makeup:.1f}dB"
    )


def _build_acoustic_space(params: PlayerParams) -> list[str]:
    """
    Convert AcousticSpace to aecho filter group.
    Two-stage structure: Early Reflections + Late Reverb.
    """
    space = get_space(params.acoustic_space)
    if space is None:
        space = get_space("musikverein")

    # Apply parameter overrides
    if params.rt60_override is not None:
        space = space.clone_with(**{"reverb.rt60_sec": params.rt60_override})
    if params.pre_delay_override is not None:
        space = space.clone_with(**{"reverb.pre_delay_ms": params.pre_delay_override})
    if params.side_ratio_override is not None:
        space = space.clone_with(**{"early.side_ratio": params.side_ratio_override})

    p = space_to_ffmpeg_params(space)

    result = []

    # Room EQ (frequency response specific to space materials)
    room_eq_filters = _build_eq_filters(p.get("room_eq", {}))
    result.extend(room_eq_filters)

    # Early Reflections (aecho)
    wet = p["early_out_gain"]
    if wet > 0.01:
        result.append(
            f"aecho="
            f"in_gain={p['early_in_gain']:.2f}:"
            f"out_gain={wet:.2f}:"
            f"delays={p['early_delays']}:"
            f"decays={p['early_decays']}"
        )

    # Late Reverb (aecho 2nd stage)
    late_wet = p["late_out_gain"]
    if late_wet > 0.01:
        late_delay = p["late_delay"]
        late_decay = p["late_decay"]
        result.append(
            f"aecho="
            f"in_gain={p['late_in_gain']:.2f}:"
            f"out_gain={late_wet:.2f}:"
            f"delays={late_delay}:"
            f"decays={late_decay}"
        )

    # Air absorption (high-freq attenuation: sense of distance)
    air_gain = p.get("air_absorption_gain", 0)
    if abs(air_gain) > 0.1:
        air_freq = p.get("air_absorption_freq", 8000)
        result.append(
            f"equalizer=f={air_freq}:t=h:width=4000:g={air_gain:.1f}"
        )

    return result


def _build_jazz_echo() -> str:
    """Jazz vocal echo (compatible with existing Sonia)"""
    return "aecho=0.8:0.7:60|100:0.3|0.2"


def _build_limiter(params: PlayerParams) -> str:
    """alimiter filter string (final stage)"""
    return (
        f"alimiter="
        f"limit={params.limiter_limit_db:.1f}dB:"
        f"attack={params.limiter_attack_ms:.0f}:"
        f"release={params.limiter_release_ms:.0f}:"
        f"level=disabled"
    )


# ══════════════════════════════════════════════════════
# Helper: generate PlayerParams from a preset
# ══════════════════════════════════════════════════════

def params_from_preset(preset_name: str) -> PlayerParams:
    """Generate PlayerParams from a GenrePreset name"""
    preset = get_preset(preset_name)
    focus = preset.instrument_focus

    return PlayerParams(
        eq=preset.eq.copy(),
        compressor_threshold_db=preset.compressor_threshold_db,
        compressor_ratio=preset.compressor_ratio,
        compressor_attack_ms=preset.compressor_attack_ms,
        compressor_release_ms=preset.compressor_release_ms,
        acoustic_space=preset.acoustic_space,
        instrument_focus_db=focus.foreground_db,
        instrument_focus_band=focus.focus_eq_band,
        instrument_focus_gain=focus.focus_eq_gain,
    )


def apply_delta_to_params(params: PlayerParams, delta) -> PlayerParams:
    """
    Apply a ParamDelta (from feedback_interpreter.py) to PlayerParams
    and return new PlayerParams.
    """
    import copy
    p = copy.deepcopy(params)

    # EQ
    eq_delta_map = {
        "sub_bass": delta.eq_sub_bass,
        "bass": delta.eq_bass,
        "low_mid": delta.eq_low_mid,
        "mid": delta.eq_mid,
        "upper_mid": delta.eq_upper_mid,
        "presence": delta.eq_presence,
        "high_mid": delta.eq_high_mid,
        "air_low": delta.eq_air_low,
        "air": delta.eq_air,
        "air_high": delta.eq_air_high,
    }
    for band, gain in eq_delta_map.items():
        if abs(gain) > 0.01:
            p.eq[band] = p.eq.get(band, 0.0) + gain

    # Acoustic space
    if abs(delta.rt60_delta) > 0.01:
        space = get_space(p.acoustic_space)
        base_rt60 = space.reverb.rt60_sec if space else 2.0
        current = p.rt60_override if p.rt60_override is not None else base_rt60
        p.rt60_override = max(0.3, min(5.0, current + delta.rt60_delta))

    if abs(delta.wet_delta) > 0.001:
        space = get_space(p.acoustic_space)
        base_wet = (1.0 - space.dry_wet_ratio) if space else 0.18
        current = p.wet_override if p.wet_override is not None else base_wet
        p.wet_override = max(0.0, min(0.6, current + delta.wet_delta))

    if abs(delta.pre_delay_delta) > 0.01:
        space = get_space(p.acoustic_space)
        base_pd = space.reverb.pre_delay_ms if space else 25.0
        current = p.pre_delay_override if p.pre_delay_override is not None else base_pd
        p.pre_delay_override = max(0.0, min(80.0, current + delta.pre_delay_delta))

    if abs(delta.side_ratio_delta) > 0.01:
        space = get_space(p.acoustic_space)
        base_sr = space.early.side_ratio if space else 0.6
        current = p.side_ratio_override if p.side_ratio_override is not None else base_sr
        p.side_ratio_override = max(0.0, min(1.0, current + delta.side_ratio_delta))

    # Dynamics
    if abs(delta.compressor_threshold_delta) > 0.01:
        p.compressor_threshold_db += delta.compressor_threshold_delta
    if abs(delta.compressor_ratio_delta) > 0.01:
        p.compressor_ratio = max(1.0, p.compressor_ratio + delta.compressor_ratio_delta)
    if abs(delta.compressor_release_delta) > 0.01:
        p.compressor_release_ms = max(50, p.compressor_release_ms + delta.compressor_release_delta)
    if abs(delta.compressor_makeup_delta) > 0.01:
        p.compressor_makeup_db += delta.compressor_makeup_delta

    # Instrument focus
    if abs(delta.foreground_db_delta) > 0.01:
        p.instrument_focus_db += delta.foreground_db_delta

    return p


if __name__ == "__main__":
    print("=== Sonia Intelligence — Filter Builder ===\n")

    # Generate filter chain using the Ravel piano concerto preset
    params = params_from_preset("piano_concerto_modern")
    print("Preset: piano_concerto_modern (Ravel style)")
    print("Acoustic space:", params.acoustic_space)
    chain = build_filter_chain(params)
    print("\nffmpeg -af filter chain:")
    print()
    for f in chain.split(","):
        print(f"  {f.strip()}")

    print("\n--- Feedback application test ---")
    from feedback_interpreter import interpret_feedback
    feedback = "more piano presence please"
    delta = interpret_feedback(feedback)
    if delta:
        new_params = apply_delta_to_params(params, delta)
        new_chain = build_filter_chain(new_params)
        print(f"Feedback: {feedback!r}")
        print("Chain after applying feedback:")
        for f in new_chain.split(","):
            print(f"  {f.strip()}")
