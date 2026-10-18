"""Camera: static beauty shot and fly-in animation."""
import bpy
import math

from .config import Config


def setup(cfg: Config) -> None:
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 40.0
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    target = bpy.data.objects.new("CamTarget", None)
    target.location = (0, 0, 60)
    bpy.context.collection.objects.link(target)

    constraint = cam.constraints.new(type="TRACK_TO")
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"

    if cfg.anim:
        # fly-in from outskirts to downtown
        keys = [
            (1, (1400, -1100, 90)),
            (80, (900, -700, 140)),
            (160, (450, -350, 220)),
            (cfg.anim_frames, (80, -120, 300)),
        ]
        for frame, loc in keys:
            cam.location = loc
            cam.keyframe_insert(data_path="location", frame=frame)
        target.location = (0, 0, 60)
        target.keyframe_insert(data_path="location", frame=1)
        target.location = (0, 0, 90)
        target.keyframe_insert(data_path="location", frame=cfg.anim_frames)

        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.easing = "EASE_IN_OUT"
    else:
        cam.location = (720, -560, 240)
