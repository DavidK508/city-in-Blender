# city-in-Blender
<<<<<<< HEAD
=======

Procedural modern-megapolis generator for Blender 5.x (headless, Python API).

## Requirements

- Blender 5.x (`blender` in PATH, override with `BLENDER=...`)

## Usage

```bash
make preview        # day preview render -> renders/preview.png
make preview-night  # night preview     -> renders/preview_night.png
make render         # final 1920x1080   -> renders/city.png
make anim           # fly-in animation  -> renders/city_anim.mp4
make save           # save .blend       -> renders/city.blend
```

Or call Blender directly:

```bash
blender --background --python run.py -- --preview --seed 7 --night
```

Flags: `--seed N`, `--night`, `--preview`, `--render`, `--anim`, `--frames N`,
`--save`, `--out PATH`.

## How it works

| Module | Role |
|---|---|
| `city/roads.py` | jittered street grid (arteries + local streets), sidewalks, ground |
| `city/buildings.py` | lot subdivision, buildings with podiums/taper/antennas, skyline falloff from downtown |
| `city/materials.py` | procedural facades; night window emission (brick-mask + noise) |
| `city/details.py` | street lamps, cars, trees (park blocks + sidewalks) |
| `city/lighting.py` | sky + sun (day) / moon + warm window lights (night), bloom compositor |
| `city/camera.py` | static beauty shot or keyframed fly-in over downtown |
| `city/main.py` | CLI, scene assembly, render |

All randomness is seeded (`--seed`), so the same seed reproduces the same city.
>>>>>>> dd9043f (Fix Blender 5 API compat, night windows, camera framing, video output)
