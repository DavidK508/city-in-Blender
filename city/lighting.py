"""Sky, sun, world lighting; day/night setup."""
import bpy
import math

from .config import Config


def setup(cfg: Config) -> None:
    scene = bpy.context.scene
    world = bpy.data.worlds.new("CityWorld")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")

    if cfg.night:
        bg.inputs["Color"].default_value = (0.01, 0.015, 0.04, 1.0)
        bg.inputs["Strength"].default_value = 0.4
        sun_energy = 0.05
        sun_color = (0.4, 0.5, 0.8, 1.0)
        sun_rot = (math.radians(70), 0, math.radians(35))
    else:
        sky = nt.nodes.new("ShaderNodeTexSky")
        try:
            sky.sky_type = "MULTIPLE_SCATTERING"
        except TypeError:
            pass
        if hasattr(sky, "sun_elevation"):
            sky.sun_elevation = math.radians(30)
            sky.sun_rotation = math.radians(135)
        nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = 0.45
        sun_energy = 1.5
        sun_color = (1.0, 0.95, 0.85, 1.0)
        sun_rot = (math.radians(50), 0, math.radians(-45))

    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    sun_data = bpy.data.lights.new("Sun", type="SUN")
    sun_data.energy = sun_energy
    sun_data.color = sun_color[:3]
    sun_data.angle = math.radians(1.0 if not cfg.night else 5.0)
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.rotation_euler = sun_rot
    bpy.context.collection.objects.link(sun)

    # gentle fill for night so silhouettes read
    if cfg.night:
        moon_data = bpy.data.lights.new("Moon", type="SUN")
        moon_data.energy = 1.5
        moon_data.color = (0.5, 0.6, 0.9)
        moon = bpy.data.objects.new("Moon", moon_data)
        moon.rotation_euler = (math.radians(60), 0, math.radians(140))
        bpy.context.collection.objects.link(moon)


def setup_compositor(cfg: Config) -> None:
    """Glare bloom for night lights (Blender 5 compositor node group)."""
    if not cfg.night:
        return
    scene = bpy.context.scene
    ng = bpy.data.node_groups.new("CityComp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = ng.nodes.new("CompositorNodeRLayers")
    glare = ng.nodes.new("CompositorNodeGlare")
    try:
        glare.inputs["Type"].default_value = "Bloom"
    except (TypeError, KeyError):
        pass
    for name, value in (("Threshold", 3.0), ("Strength", 0.35), ("Size", 5)):
        if name in glare.inputs:
            try:
                glare.inputs[name].default_value = value
            except (TypeError, ValueError):
                pass
    out = ng.nodes.new("NodeGroupOutput")
    ng.links.new(rl.outputs["Image"], glare.inputs["Image"])
    ng.links.new(glare.outputs["Image"], out.inputs[0])
    scene.compositing_node_group = ng
    scene.use_nodes = True
