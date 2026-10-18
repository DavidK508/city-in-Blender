"""City generation parameters."""
import random
from dataclasses import dataclass


@dataclass
class Config:
    seed: int = 42
    night: bool = False
    anim: bool = False

    # City extent (meters)
    extent: float = 800.0
    grid_n: int = 12           # cells per axis
    jitter: float = 14.0       # street grid distortion

    # Roads
    artery_every: int = 3
    artery_width: float = 20.0
    street_width: float = 12.0
    sidewalk_width: float = 4.0
    sidewalk_height: float = 0.18

    # Blocks / lots
    min_lot: float = 160.0     # m^2
    max_lot: float = 650.0     # m^2, larger lots get split
    park_chance: float = 0.08

    # Buildings
    max_height: float = 190.0
    mid_height: float = 30.0
    downtown_radius: float = 280.0
    glass_chance: float = 0.55  # chance for glass facade downtown

    # Details
    lamp_every: float = 35.0
    car_count: int = 200
    tree_count: int = 400

    # Render
    resolution_x: int = 1920
    resolution_y: int = 1080
    preview_scale: float = 0.35
    samples: int = 64
    preview_samples: int = 16
    anim_frames: int = 250
    fps: int = 24

    out_dir: str = "renders"

    def __post_init__(self):
        self._rng = random.Random(self.seed)


CONFIG = Config()
