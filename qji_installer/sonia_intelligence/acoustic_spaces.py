"""
acoustic_spaces.py — Sonia Intelligence
Physical models of concert halls and acoustic spaces

Each space is defined as a parameter set convertible to ffmpeg filters.
Three-layer structure: Early Reflections + Late Reverberation + Air Absorption.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import copy


@dataclass
class EarlyReflections:
    """Early reflection model (5–30ms) — defines the "size" and "shape" of the space"""
    delay_ms: float = 15.0        # Arrival delay of early reflections
    side_ratio: float = 0.6       # Side wall reflection strength (0–1)
    ceiling_ratio: float = 0.5    # Ceiling reflection strength (0–1)
    rear_ratio: float = 0.3       # Rear reflection strength (0–1)
    clarity: float = 0.7          # Separation from direct sound (0=blend, 1=clear)


@dataclass
class LateReverb:
    """Late reverb model — defines the "depth" and "material feel" of the space"""
    rt60_sec: float = 1.8         # Reverberation time (RT60)
    pre_delay_ms: float = 25.0    # Pre-delay (separation between direct sound and reverb)
    decay_curve: str = "exp"      # "linear" / "exp" / "convex"
    diffusion: float = 0.7        # Diffusion (0=simple echo, 1=dense reverb)
    air_absorption: float = 0.3   # High-frequency distance attenuation (0–1)


@dataclass
class AcousticSpace:
    """
    Full definition of an acoustic space.
    Converted to ffmpeg aecho/areverb/equalizer filters.
    """
    name: str
    display_name: str
    description: str
    early: EarlyReflections = field(default_factory=EarlyReflections)
    reverb: LateReverb = field(default_factory=LateReverb)

    # Space-specific EQ signature (frequency response due to materials and shape)
    room_eq: dict = field(default_factory=dict)

    # Mix ratio of direct sound to reverb
    dry_wet_ratio: float = 0.82   # 0.82 = dry 82% / wet 18%

    def to_dict(self) -> dict:
        return asdict(self)

    def clone_with(self, **overrides) -> "AcousticSpace":
        """Return a deep copy with specified parameters overridden (for fine-tuning)"""
        obj = copy.deepcopy(self)
        for key, val in overrides.items():
            if "." in key:
                # Dot notation like "early.delay_ms"
                parts = key.split(".", 1)
                sub = getattr(obj, parts[0])
                setattr(sub, parts[1], val)
            elif hasattr(obj, key):
                setattr(obj, key, val)
        return obj


# ══════════════════════════════════════════════════════
# Acoustic Space Preset Definitions
# ══════════════════════════════════════════════════════

ACOUSTIC_SPACES: dict[str, AcousticSpace] = {

    # ─── Concert Halls ────────────────────────────────

    "musikverein": AcousticSpace(
        name="musikverein",
        display_name="Musikverein Großer Saal (Vienna)",
        description="Shoebox hall of wood and stucco. Warm mids and rich lows. RT60≈2.0s",
        early=EarlyReflections(
            delay_ms=18, side_ratio=0.75, ceiling_ratio=0.60,
            rear_ratio=0.35, clarity=0.65
        ),
        reverb=LateReverb(
            rt60_sec=2.05, pre_delay_ms=28, decay_curve="exp",
            diffusion=0.82, air_absorption=0.25
        ),
        room_eq={
            "low_mid": +1.5,   # Warmth of wood
            "mid": +1.0,       # Body resonance
            "presence": -0.5,  # Gentle upper mids
        },
        dry_wet_ratio=0.80
    ),

    "concertgebouw": AcousticSpace(
        name="concertgebouw",
        display_name="Concertgebouw (Amsterdam)",
        description="The pinnacle of shoebox halls. Rich bass and 360-degree envelopment. RT60≈2.2s",
        early=EarlyReflections(
            delay_ms=20, side_ratio=0.80, ceiling_ratio=0.65,
            rear_ratio=0.45, clarity=0.60
        ),
        reverb=LateReverb(
            rt60_sec=2.25, pre_delay_ms=30, decay_curve="exp",
            diffusion=0.88, air_absorption=0.20
        ),
        room_eq={
            "bass": +2.0,      # Rich bass
            "low_mid": +1.0,
            "air": +0.5,       # Delicate high-frequency extension
        },
        dry_wet_ratio=0.78
    ),

    "carnegie_hall": AcousticSpace(
        name="carnegie_hall",
        display_name="Carnegie Hall (New York)",
        description="Balances clarity and richness. Three-dimensional soundstage. RT60≈1.8s",
        early=EarlyReflections(
            delay_ms=14, side_ratio=0.65, ceiling_ratio=0.70,
            rear_ratio=0.30, clarity=0.75
        ),
        reverb=LateReverb(
            rt60_sec=1.85, pre_delay_ms=22, decay_curve="exp",
            diffusion=0.75, air_absorption=0.30
        ),
        room_eq={
            "presence": +0.5,  # Clear upper mids
            "air": +1.0,       # Open, extended highs
        },
        dry_wet_ratio=0.82
    ),

    "berliner_philharmonie": AcousticSpace(
        name="berliner_philharmonie",
        display_name="Berliner Philharmonie",
        description="Vineyard-style hall. Uniform, transparent soundfield. Even volume throughout. RT60≈2.0s",
        early=EarlyReflections(
            delay_ms=16, side_ratio=0.55, ceiling_ratio=0.75,
            rear_ratio=0.50, clarity=0.78
        ),
        reverb=LateReverb(
            rt60_sec=2.00, pre_delay_ms=24, decay_curve="convex",
            diffusion=0.85, air_absorption=0.28
        ),
        room_eq={
            "mid": -0.5,       # Transparency
            "presence": +0.5,
            "air": +1.5,       # Open, extended highs
        },
        dry_wet_ratio=0.81
    ),

    "salle_pleyel": AcousticSpace(
        name="salle_pleyel",
        display_name="Salle Pleyel (Paris)",
        description="The scent of French recordings. Delicate, brilliant highs. RT60≈1.7s",
        early=EarlyReflections(
            delay_ms=12, side_ratio=0.60, ceiling_ratio=0.55,
            rear_ratio=0.25, clarity=0.80
        ),
        reverb=LateReverb(
            rt60_sec=1.72, pre_delay_ms=20, decay_curve="exp",
            diffusion=0.70, air_absorption=0.35
        ),
        room_eq={
            "presence": +1.0,  # Brilliance of French recordings
            "air": +2.0,
            "bass": -1.0,      # Tight, controlled bass
        },
        dry_wet_ratio=0.83
    ),

    # ─── Chamber Music / Small Halls ──────────────────

    "small_chamber": AcousticSpace(
        name="small_chamber",
        display_name="Small Hall / Chamber Space",
        description="Intimate and delicate space. Close enough to hear the breath of the instruments. RT60≈0.9s",
        early=EarlyReflections(
            delay_ms=8, side_ratio=0.50, ceiling_ratio=0.45,
            rear_ratio=0.20, clarity=0.85
        ),
        reverb=LateReverb(
            rt60_sec=0.90, pre_delay_ms=12, decay_curve="exp",
            diffusion=0.60, air_absorption=0.40
        ),
        room_eq={
            "upper_mid": +1.0,  # Clarity for chamber music
            "presence": +0.5,
        },
        dry_wet_ratio=0.87
    ),

    "church": AcousticSpace(
        name="church",
        display_name="Stone Church",
        description="Long reverb and solemn sense of space. Ideal for sacred music and organ. RT60≈3.5s",
        early=EarlyReflections(
            delay_ms=25, side_ratio=0.70, ceiling_ratio=0.80,
            rear_ratio=0.60, clarity=0.45
        ),
        reverb=LateReverb(
            rt60_sec=3.50, pre_delay_ms=40, decay_curve="linear",
            diffusion=0.90, air_absorption=0.15
        ),
        room_eq={
            "sub_bass": +2.0,  # Stone resonance
            "bass": +1.5,
            "mid": -0.5,       # Absorption by stone walls
        },
        dry_wet_ratio=0.72
    ),

    # ─── Jazz / Contemporary ───────────────────────────

    "jazz_club": AcousticSpace(
        name="jazz_club",
        display_name="Jazz Club",
        description="Intimacy and warmth. Close proximity to the performers. RT60≈0.5s",
        early=EarlyReflections(
            delay_ms=6, side_ratio=0.40, ceiling_ratio=0.35,
            rear_ratio=0.15, clarity=0.90
        ),
        reverb=LateReverb(
            rt60_sec=0.52, pre_delay_ms=8, decay_curve="exp",
            diffusion=0.50, air_absorption=0.50
        ),
        room_eq={
            "bass": +1.5,      # Warmth of the upright bass
            "low_mid": +1.0,
            "air": -1.0,       # Reduce highs for close-mic intimacy
        },
        dry_wet_ratio=0.90
    ),

    "studio_dry": AcousticSpace(
        name="studio_dry",
        display_name="Studio (Dry)",
        description="Minimal reverb. Preserves the original character of the recording. RT60≈0.3s",
        early=EarlyReflections(
            delay_ms=4, side_ratio=0.20, ceiling_ratio=0.20,
            rear_ratio=0.10, clarity=0.95
        ),
        reverb=LateReverb(
            rt60_sec=0.30, pre_delay_ms=5, decay_curve="exp",
            diffusion=0.40, air_absorption=0.60
        ),
        room_eq={},
        dry_wet_ratio=0.95
    ),
}


def get_space(name: str) -> Optional[AcousticSpace]:
    """Retrieve an acoustic space by name. Returns None if not found."""
    return ACOUSTIC_SPACES.get(name)


def list_spaces() -> list[dict]:
    """Return a list of available acoustic spaces (for UI display)."""
    return [
        {
            "name": s.name,
            "display_name": s.display_name,
            "rt60": s.reverb.rt60_sec,
            "description": s.description,
        }
        for s in ACOUSTIC_SPACES.values()
    ]


def space_to_ffmpeg_params(space: AcousticSpace) -> dict:
    """
    Convert an AcousticSpace to ffmpeg filter parameters.
    Used by filter_builder.py.
    """
    e = space.early
    r = space.reverb
    wet = 1.0 - space.dry_wet_ratio

    # Parameters for aecho filter (Early Reflections)
    # aecho=in_gain:out_gain:delays:decays
    early_delays = f"{int(e.delay_ms)}|{int(e.delay_ms * 1.6)}|{int(e.delay_ms * 2.3)}"
    early_decays = (
        f"{e.side_ratio:.2f}|"
        f"{e.ceiling_ratio * 0.8:.2f}|"
        f"{e.rear_ratio * 0.6:.2f}"
    )

    # Reverb approximation via aecho
    late_delay = int(r.pre_delay_ms + e.delay_ms * 3)
    late_decay = min(0.95, r.rt60_sec / 4.5)  # Convert RT60 to decay coefficient

    return {
        # Early Reflections
        "early_delays": early_delays,
        "early_decays": early_decays,
        "early_in_gain": 0.8,
        "early_out_gain": wet * 0.6,

        # Late Reverb
        "late_delay": late_delay,
        "late_decay": f"{late_decay:.2f}",
        "late_in_gain": 0.6,
        "late_out_gain": wet * 0.4,

        # Air absorption (high-frequency attenuation)
        "air_absorption_freq": 8000,
        "air_absorption_gain": -r.air_absorption * 3.0,

        # Room EQ
        "room_eq": space.room_eq,

        # Dry/Wet
        "dry": space.dry_wet_ratio,
        "wet": wet,
    }


if __name__ == "__main__":
    # Diagnostic check
    print("=== Sonia Intelligence — Acoustic Spaces ===\n")
    for info in list_spaces():
        print(f"  [{info['name']:25s}] RT60={info['rt60']:.1f}s  {info['display_name']}")

    print("\n--- Musikverein ffmpeg params ---")
    import json
    space = get_space("musikverein")
    params = space_to_ffmpeg_params(space)
    print(json.dumps(params, indent=2, ensure_ascii=False))
