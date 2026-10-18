"""Procedural materials for the city."""
import bpy

# Palette: (name, base color, roughness, metallic, glass)
FACADE_PALETTES = [
    ("ConcreteLight", (0.38, 0.37, 0.35, 1.0), 0.8, 0.0, False),
    ("ConcreteDark", (0.14, 0.14, 0.16, 1.0), 0.85, 0.0, False),
    ("Beige", (0.42, 0.34, 0.25, 1.0), 0.8, 0.0, False),
    ("WhitePanel", (0.6, 0.6, 0.58, 1.0), 0.7, 0.0, False),
    ("Brick", (0.28, 0.12, 0.09, 1.0), 0.9, 0.0, False),
    ("GlassTower", (0.03, 0.06, 0.1, 1.0), 0.15, 0.9, True),
    ("GlassBlue", (0.04, 0.1, 0.18, 1.0), 0.12, 0.85, True),
]


def _principled(mat):
    return mat.node_tree.nodes["Principled BSDF"]


def simple_mat(name, color, roughness, metallic=0.0, emission=None, emission_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = _principled(mat)
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = emission
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


def _facade_mat(name, color, roughness, metallic, glass, night, windows=True):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = _principled(mat)
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic

    if not windows or glass:
        return mat

    # Window grid via brick texture on generated coordinates
    tex = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1.0, 1.0, 1.0)
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.0
    brick.inputs["Scale"].default_value = 10.0
    brick.inputs["Mortar Size"].default_value = 0.25
    brick.inputs["Color1"].default_value = (1, 1, 1, 1)
    brick.inputs["Color2"].default_value = (1, 1, 1, 1)
    brick.inputs["Mortar"].default_value = (0, 0, 0, 1)
    invert = nt.nodes.new("ShaderNodeMath")
    invert.operation = "SUBTRACT"
    invert.inputs[0].default_value = 1.0
    nt.links.new(brick.outputs["Fac"], invert.inputs[1])

    if night:
        emission = nt.nodes.new("ShaderNodeEmission")
        emission.inputs["Color"].default_value = (1.0, 0.75, 0.4, 1.0)
        emission.inputs["Strength"].default_value = 2.2
        mix = nt.nodes.new("ShaderNodeMixShader")
        out = nt.nodes["Material Output"]
        nt.links.new(tex.outputs["Generated"], mapping.inputs["Vector"])
        nt.links.new(mapping.outputs["Vector"], brick.inputs["Vector"])
        nt.links.new(invert.outputs["Value"], mix.inputs["Fac"])
        nt.links.new(bsdf.outputs["BSDF"], mix.inputs[1])
        nt.links.new(emission.outputs["Emission"], mix.inputs[2])
        nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat


def get_facade_materials(cfg):
    mats = []
    for name, color, rough, metal, glass in FACADE_PALETTES:
        mats.append(_facade_mat(name, color, rough, metal, glass,
                                night=cfg.night, windows=not glass))
    return mats


def lamp_material(cfg):
    strength = 40.0 if cfg.night else 0.0
    return simple_mat("LampHead", (0.9, 0.9, 0.85, 1), 0.3,
                      emission=(1.0, 0.8, 0.5, 1), emission_strength=strength)


def car_materials():
    colors = [
        (0.6, 0.05, 0.05, 1), (0.05, 0.1, 0.4, 1), (0.7, 0.7, 0.7, 1),
        (0.05, 0.05, 0.05, 1), (0.6, 0.5, 0.1, 1),
    ]
    return [simple_mat(f"Car{i}", c, 0.4, 0.6) for i, c in enumerate(colors)]


def glass_mat():
    return simple_mat("CarGlass", (0.02, 0.03, 0.04, 1), 0.1, 0.8)


def park_mat():
    return simple_mat("Park", (0.1, 0.22, 0.08, 1), 0.95)


def trunk_mat():
    return simple_mat("Trunk", (0.15, 0.09, 0.05, 1), 0.9)


def leaves_mat():
    return simple_mat("Leaves", (0.05, 0.18, 0.04, 1), 0.9)
