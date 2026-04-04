"""
Animation sequence definitions for the 2D RTS unit pipeline.

Animations are defined as per-frame transforms applied to specific part groups
(turret, barrel, mobility) before the directional rotation render. The game
engine plays back these frames from the sprite sheet at runtime.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class AnimationKeyframe:
    """Transform to apply to a part group on a specific frame."""
    frame_index: int
    part_group: str                                     # "turret_parts", "barrel_parts", "mobility_parts"
    translation: Tuple[float, float, float] = (0, 0, 0)
    rotation_axis: Tuple[float, float, float] = (0, 0, 1)
    rotation_angle: float = 0.0                         # radians


@dataclass
class AnimationSequence:
    """A named animation consisting of N frames with keyframes."""
    name: str
    n_frames: int
    looping: bool = False
    keyframes: List[AnimationKeyframe] = field(default_factory=list)

    def get_keyframes_for_frame(self, frame_index: int) -> List[AnimationKeyframe]:
        return [kf for kf in self.keyframes if kf.frame_index == frame_index]


@dataclass
class AnimationSet:
    """Collection of animation sequences for a vehicle."""
    sequences: Dict[str, AnimationSequence] = field(default_factory=dict)

    def get_sequence(self, name: str) -> AnimationSequence:
        return self.sequences.get(name)

    def get_ordered_sequences(self) -> List[AnimationSequence]:
        """Return sequences in a stable order: idle first, then alphabetical."""
        order = []
        if "idle" in self.sequences:
            order.append(self.sequences["idle"])
        for name in sorted(self.sequences):
            if name != "idle":
                order.append(self.sequences[name])
        return order


# ---------------------------------------------------------------------------
# Default animation factories
# ---------------------------------------------------------------------------

def _make_idle() -> AnimationSequence:
    """Single static frame – no transforms."""
    return AnimationSequence(name="idle", n_frames=1, looping=False)


def _make_firing(vehicle_type: str, scale_factor: float = 4.0) -> AnimationSequence:
    """Barrel recoil animation (6 frames).

    Frame 0 : rest
    Frame 1 : barrel snaps backward  (peak recoil)
    Frame 2 : barrel at ~60 % recoil
    Frame 3 : barrel at ~30 % recoil
    Frame 4 : barrel at ~10 % recoil
    Frame 5 : rest (returned)
    """
    n_frames = 6

    # Recoil distance varies by vehicle
    recoil_distances = {
        "tank": 0.6 * scale_factor,
        "apc": 0.25 * scale_factor,
        "artillery": 1.0 * scale_factor,
    }
    max_recoil = recoil_distances.get(vehicle_type, 0.5 * scale_factor)

    # Recoil curve: sharp snap back, slow recovery
    recoil_curve = [0.0, 1.0, 0.6, 0.3, 0.1, 0.0]

    keyframes = []
    for i, t in enumerate(recoil_curve):
        if t != 0.0:
            keyframes.append(AnimationKeyframe(
                frame_index=i,
                part_group="barrel_parts",
                translation=(-max_recoil * t, 0, 0),
            ))

    return AnimationSequence(
        name="firing", n_frames=n_frames, looping=False, keyframes=keyframes,
    )


def _make_moving(vehicle_type: str, scale_factor: float = 4.0) -> AnimationSequence:
    """Movement animation (4 frames).

    APC  : wheels rotate incrementally around Y.
    Tank / Artillery : treads get a small vertical bounce to suggest motion.
    """
    n_frames = 4
    keyframes: List[AnimationKeyframe] = []

    if vehicle_type == "apc":
        # Wheels spin – quarter turn per frame
        for i in range(n_frames):
            angle = (math.pi / 2) * (i + 1)   # 90° per frame
            keyframes.append(AnimationKeyframe(
                frame_index=i,
                part_group="mobility_parts",
                rotation_axis=(0, 1, 0),
                rotation_angle=angle,
            ))
    else:
        # Treads: subtle vertical oscillation
        amplitude = 0.05 * scale_factor
        for i in range(n_frames):
            phase = math.sin(2 * math.pi * i / n_frames)
            if abs(phase) > 1e-6:
                keyframes.append(AnimationKeyframe(
                    frame_index=i,
                    part_group="mobility_parts",
                    translation=(0, 0, amplitude * phase),
                ))

    return AnimationSequence(
        name="moving", n_frames=n_frames, looping=True, keyframes=keyframes,
    )


def get_default_animations(vehicle_type: str,
                           scale_factor: float = 4.0) -> AnimationSet:
    """Return the full set of default animations for *vehicle_type*."""
    return AnimationSet(sequences={
        "idle": _make_idle(),
        "firing": _make_firing(vehicle_type, scale_factor),
        "moving": _make_moving(vehicle_type, scale_factor),
    })
