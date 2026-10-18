"""Street details: lamps, cars, trees."""
import bpy
import math

from .config import Config
from . import materials
from .roads import ROAD_Z, SIDEWALK_Z


def _link_copy(prototype, location, rotation_z=0.0, scale=1.0, name=None):
    obj = prototype.copy()
    obj.location = location
    obj.rotation_euler = (0, 0, rotation_z)
    obj.scale = (scale, scale, scale)
    if name:
        obj.name = name
    bpy.context.collection.objects.link(obj)
    return obj


def _make_lamp_prototype(cfg):
    mat_pole = materials.simple_mat("Pole", (0.1, 0.1, 0.1, 1), 0.6, 0.8)
    head_mat = materials.lamp_material(cfg)

    bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=7.0, location=(0, 0, 3.5))
    pole = bpy.context.active_object
    pole.name = "LampProtoPole"
    pole.data.materials.append(mat_pole)

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.35, location=(0.5, 0, 7.0))
    head = bpy.context.active_object
    head.name = "LampProtoHead"
    head.data.materials.append(head_mat)

    head.select_set(True)
    pole.select_set(True)
    bpy.context.view_layer.objects.active = pole
    bpy.ops.object.join()
    proto = bpy.context.active_object
    proto.name = "LampProto"
    return proto


def _make_car_prototypes(cfg):
    glass = materials.glass_mat()
    tire = materials.simple_mat("Tire", (0.02, 0.02, 0.02, 1), 0.9)
    headlight = materials.simple_mat(
        "Headlight", (0.9, 0.9, 0.85, 1), 0.2,
        emission=(1.0, 0.95, 0.8, 1), emission_strength=8.0 if cfg.night else 0.0)
    taillight = materials.simple_mat(
        "Taillight", (0.8, 0.05, 0.05, 1), 0.3,
        emission=(1.0, 0.05, 0.05, 1), emission_strength=6.0 if cfg.night else 0.0)
    protos = []
    for i, mat in enumerate(materials.car_materials()):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.55))
        body = bpy.context.active_object
        body.scale = (4.4, 1.9, 0.7)
        body.data.materials.append(mat)

        bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.3, 0, 1.15))
        cabin = bpy.context.active_object
        cabin.scale = (2.2, 1.7, 0.55)
        cabin.data.materials.append(glass)

        parts = [body, cabin]
        # wheels
        for wx in (1.4, -1.4):
            for wy in (0.95, -0.95):
                bpy.ops.mesh.primitive_cylinder_add(
                    radius=0.35, depth=0.25,
                    location=(wx, wy, 0.35),
                    rotation=(math.pi / 2, 0, 0))
                wheel = bpy.context.active_object
                wheel.data.materials.append(tire)
                parts.append(wheel)
        # lights
        for ly in (0.6, -0.6):
            bpy.ops.mesh.primitive_cube_add(size=1, location=(2.2, ly, 0.6))
            hl = bpy.context.active_object
            hl.scale = (0.08, 0.35, 0.15)
            hl.data.materials.append(headlight)
            parts.append(hl)
            bpy.ops.mesh.primitive_cube_add(size=1, location=(-2.2, ly, 0.6))
            tl = bpy.context.active_object
            tl.scale = (0.08, 0.35, 0.15)
            tl.data.materials.append(taillight)
            parts.append(tl)

        for p in parts:
            p.select_set(True)
        bpy.context.view_layer.objects.active = body
        bpy.ops.object.join()
        car = bpy.context.active_object
        car.name = f"CarProto{i}"
        protos.append(car)
    return protos


def _make_tree_prototype():
    trunk_mat = materials.trunk_mat()
    leaves_mat = materials.leaves_mat()
    bpy.ops.mesh.primitive_cylinder_add(radius=0.25, depth=2.5, location=(0, 0, 1.25))
    trunk = bpy.context.active_object
    trunk.data.materials.append(trunk_mat)
    bpy.ops.mesh.primitive_ico_sphere_add(radius=1.6, subdivisions=1, location=(0, 0, 3.2))
    crown = bpy.context.active_object
    crown.data.materials.append(leaves_mat)
    crown.select_set(True)
    trunk.select_set(True)
    bpy.context.view_layer.objects.active = trunk
    bpy.ops.object.join()
    tree = bpy.context.active_object
    tree.name = "TreeProto"
    return tree


def _place_on_roads(cfg, count, offset, place):
    """Place items along road segments at a lateral offset from centerline."""
    rng = cfg._rng
    placed = 0
    segments = cfg._segments
    while placed < count:
        p1, p2, artery = rng.choice(segments)
        width = cfg.artery_width if artery else cfg.street_width
        side = rng.choice((-1, 1))
        lat = side * (width / 2.0 - 1.5)
        t = rng.uniform(0.05, 0.95)
        x = p1[0] + (p2[0] - p1[0]) * t
        y = p1[1] + (p2[1] - p1[1]) * t
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1e-6:
            continue
        nx, ny = -dy / length * lat, dx / length * lat
        rot = math.atan2(dy, dx)
        place((x + nx, y + ny, 0), rot, artery)
        placed += 1


def generate(cfg: Config) -> None:
    rng = cfg._rng

    # Lamps on sidewalks
    lamp_proto = _make_lamp_prototype(cfg)
    n_lamps = int(cfg.extent * 4 * cfg.grid_n / cfg.lamp_every)
    lamp_positions = []

    def place_lamp(pos, rot, artery):
        if not artery and rng.random() < 0.4:
            return
        p = (pos[0], pos[1], SIDEWALK_Z)
        lamp_positions.append(p)
        _link_copy(lamp_proto, p, rot + math.pi / 2)

    _place_on_roads(cfg, n_lamps, 0.0, place_lamp)

    # Night point lights (limited count for Eevee)
    if cfg.night:
        step = max(1, len(lamp_positions) // 40)
        light_mat = None
        for i, p in enumerate(lamp_positions[::step]):
            light_data = bpy.data.lights.new(f"LampLight{i}", type="POINT")
            light_data.energy = 500.0
            light_data.color = (1.0, 0.75, 0.45)
            light_data.shadow_soft_size = 1.0
            lo = bpy.data.objects.new(f"LampLight{i}", light_data)
            lo.location = (p[0], p[1], 7.2)
            bpy.context.collection.objects.link(lo)

    # Cars on roads
    car_protos = _make_car_prototypes(cfg)

    def place_car(pos, rot, artery):
        proto = rng.choice(car_protos)
        lane = rng.choice((-1, 1)) * (3.5 if artery else 2.2)
        dx, dy = math.cos(rot), math.sin(rot)
        x = pos[0] - dy * lane
        y = pos[1] + dx * lane
        direction = rot if lane > 0 else rot + math.pi
        _link_copy(proto, (x, y, ROAD_Z + 0.02), direction)

    _place_on_roads(cfg, cfg.car_count, 0.0, place_car)

    # Trees: in parks + some sidewalk spots
    tree_proto = _make_tree_prototype()
    parks = getattr(cfg, "_park_quads", [])
    placed = 0
    target = cfg.tree_count
    for quad in parks:
        cx = sum(p[0] for p in quad) / 4.0
        cy = sum(p[1] for p in quad) / 4.0
        xs = [p[0] for p in quad]
        ys = [p[1] for p in quad]
        rx = (max(xs) - min(xs)) / 2.0 - 3.0
        ry = (max(ys) - min(ys)) / 2.0 - 3.0
        n = max(4, int(rx * ry / 40.0))
        for _ in range(n):
            a = rng.uniform(0, math.tau)
            r = rng.uniform(0, 1) ** 0.5
            x = cx + math.cos(a) * rx * r
            y = cy + math.sin(a) * ry * r
            _link_copy(tree_proto, (x, y, SIDEWALK_Z + 0.02),
                       rng.uniform(0, math.tau), rng.uniform(0.7, 1.3))
            placed += 1

    while placed < target:
        p1, p2, artery = rng.choice(cfg._segments)
        width = cfg.artery_width if artery else cfg.street_width
        side = rng.choice((-1, 1))
        lat = side * (width / 2.0 + 1.2)
        t = rng.uniform(0.1, 0.9)
        dxs, dys = p2[0] - p1[0], p2[1] - p1[1]
        length = (dxs * dxs + dys * dys) ** 0.5
        if length < 1e-6:
            continue
        x = p1[0] + dxs * t
        y = p1[1] + dys * t
        nx, ny = -dys / length * lat, dxs / length * lat
        _link_copy(tree_proto, (x + nx, y + ny, SIDEWALK_Z),
                   rng.uniform(0, math.tau), rng.uniform(0.6, 1.0))
        placed += 1

    # Hide prototypes
    for proto in [lamp_proto, tree_proto, *car_protos]:
        proto.hide_render = True
        proto.hide_viewport = True
