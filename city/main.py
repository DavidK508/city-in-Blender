"""Assemble the whole city scene and render."""
import argparse
import os
import sys
import time

import bpy

from .config import CONFIG
from .clear import clear_scene
from . import roads, buildings, details, lighting, camera


def _set_render(cfg, preview: bool) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    if preview:
        scene.render.resolution_x = int(cfg.resolution_x * cfg.preview_scale)
        scene.render.resolution_y = int(cfg.resolution_y * cfg.preview_scale)
        try:
            scene.cycles.samples = cfg.preview_samples
        except AttributeError:
            pass
    else:
        scene.render.resolution_x = cfg.resolution_x
        scene.render.resolution_y = cfg.resolution_y
    scene.render.fps = cfg.fps
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = cfg.preview_samples if preview else cfg.samples
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.exposure = -0.3
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            scene.view_settings.look = look
            break
        except TypeError:
            continue


def build(cfg) -> None:
    clear_scene()
    lighting.setup(cfg)
    roads.generate(cfg)
    buildings.generate(cfg)
    details.generate(cfg)
    lighting.setup_compositor(cfg)
    camera.setup(cfg)


def cli() -> None:
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []

    parser = argparse.ArgumentParser(description="Generate a procedural city")
    parser.add_argument("--seed", type=int, default=CONFIG.seed)
    parser.add_argument("--night", action="store_true")
    parser.add_argument("--preview", action="store_true", help="low-res render")
    parser.add_argument("--render", action="store_true", help="final still")
    parser.add_argument("--anim", action="store_true", help="fly-in animation")
    parser.add_argument("--save", action="store_true", help="save .blend")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    cfg = CONFIG
    cfg.seed = args.seed
    cfg.night = args.night
    cfg.anim = args.anim
    cfg.__post_init__()  # re-seed rng

    t0 = time.time()
    build(cfg)
    print(f"[city] built in {time.time() - t0:.1f}s")

    os.makedirs(cfg.out_dir, exist_ok=True)
    suffix = "_night" if cfg.night else ""

    if args.save or not (args.preview or args.render or args.anim):
        blend = os.path.join(cfg.out_dir, f"city{suffix}.blend")
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(blend))
        print(f"[city] saved {blend}")

    if args.preview:
        _set_render(cfg, preview=True)
        path = os.path.join(cfg.out_dir, f"preview{suffix}.png")
        scene = bpy.context.scene
        scene.render.filepath = os.path.abspath(path)
        bpy.ops.render.render(write_still=True)
        print(f"[city] preview -> {path}")

    if args.render:
        _set_render(cfg, preview=False)
        path = args.out or os.path.join(cfg.out_dir, f"city{suffix}.png")
        scene = bpy.context.scene
        scene.render.filepath = os.path.abspath(path)
        bpy.ops.render.render(write_still=True)
        print(f"[city] render -> {path}")

    if args.anim:
        _set_render(cfg, preview=False)
        scene = bpy.context.scene
        scene.frame_start = 1
        scene.frame_end = cfg.anim_frames
        scene.render.image_settings.file_format = "FFMPEG"
        scene.render.ffmpeg.format = "MPEG4"
        scene.render.ffmpeg.codec = "H264"
        path = args.out or os.path.join(cfg.out_dir, f"city_anim{suffix}.mp4")
        scene.render.filepath = os.path.abspath(path)
        bpy.ops.render.render(animation=True)
        print(f"[city] anim -> {path}")
