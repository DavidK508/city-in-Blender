"""Street network: jittered grid of arteries and local streets."""
import bpy

from .config import Config

ROAD_Z = 0.0
SIDEWALK_Z = 0.05


def _mat(name: str, color, roughness: float, metallic: float = 0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def asphalt_material() -> bpy.data.materials:
    return _mat("Asphalt", (0.03, 0.03, 0.035, 1.0), 0.9)


def sidewalk_material() -> bpy.data.materials:
    return _mat("Sidewalk", (0.35, 0.34, 0.32, 1.0), 0.85)


def build_grid(cfg: Config):
    """Jittered lattice points and road segments between neighbors."""
    n = cfg.grid_n
    step = cfg.extent / n
    half = cfg.extent / 2.0
    rng = cfg._rng

    points = [[None] * (n + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        for j in range(n + 1):
            x = -half + i * step
            y = -half + j * step
            if 0 < i < n:
                x += rng.uniform(-cfg.jitter, cfg.jitter)
            if 0 < j < n:
                y += rng.uniform(-cfg.jitter, cfg.jitter)
            points[i][j] = (x, y)

    segments = []  # (p1, p2, is_artery)
    for i in range(n + 1):
        for j in range(n + 1):
            if i < n:
                artery = (j % cfg.artery_every == 0)
                segments.append((points[i][j], points[i + 1][j], artery))
            if j < n:
                artery = (i % cfg.artery_every == 0)
                segments.append((points[i][j], points[i][j + 1], artery))
    return points, segments, step


def _strip(p1, p2, width, z):
    """Quad strip from p1 to p2 extended slightly past both ends."""
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = (dx * dx + dy * dy) ** 0.5
    if length < 1e-6:
        return None
    ux, uy = dx / length, dy / length
    ox, oy = -uy * width / 2.0, ux * width / 2.0
    ext = 3.0  # cover intersections
    a = (p1[0] - ux * ext + ox, p1[1] - uy * ext + oy, z)
    b = (p2[0] + ux * ext + ox, p2[1] + uy * ext + oy, z)
    c = (p2[0] + ux * ext - ox, p2[1] + uy * ext - oy, z)
    d = (p1[0] - ux * ext - ox, p1[1] - uy * ext - oy, z)
    return (a, b, c, d)


def build_roads(cfg: Config, segments) -> None:
    verts, faces = [], []
    z_art, z_str = ROAD_Z, ROAD_Z + 0.004
    for p1, p2, artery in segments:
        width = cfg.artery_width if artery else cfg.street_width
        quad = _strip(p1, p2, width, z_art if artery else z_str)
        if quad is None:
            continue
        base = len(verts)
        verts.extend(quad)
        faces.append((base, base + 1, base + 2, base + 3))

    mesh = bpy.data.meshes.new("Roads")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(asphalt_material())
    obj = bpy.data.objects.new("Roads", mesh)
    bpy.context.collection.objects.link(obj)


def block_quads(cfg: Config, points, step):
    """Inner quad of each grid cell, inset from road centerlines."""
    n = cfg.grid_n
    inset = cfg.artery_width / 2.0 + cfg.sidewalk_width + 1.5
    quads = []
    for i in range(n):
        for j in range(n):
            corners = [points[i][j], points[i + 1][j],
                       points[i + 1][j + 1], points[i][j + 1]]
            cx = sum(p[0] for p in corners) / 4.0
            cy = sum(p[1] for p in corners) / 4.0
            quad = []
            ok = True
            for x, y in corners:
                dx, dy = x - cx, y - cy
                dist = (dx * dx + dy * dy) ** 0.5
                target = dist - inset
                if target < step * 0.15:
                    ok = False
                    break
                quad.append((cx + dx * target / dist, cy + dy * target / dist))
            if ok:
                quads.append(quad)
    return quads


def build_sidewalks(cfg: Config, quads) -> None:
    verts, faces = [], []
    z = SIDEWALK_Z
    for quad in quads:
        base = len(verts)
        verts.extend((x, y, z) for x, y in quad)
        faces.append((base, base + 1, base + 2, base + 3))

    mesh = bpy.data.meshes.new("Sidewalks")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(sidewalk_material())
    obj = bpy.data.objects.new("Sidewalks", mesh)
    bpy.context.collection.objects.link(obj)


def build_ground(cfg: Config) -> None:
    size = cfg.extent * 3.0
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, -0.02))
    ground = bpy.context.active_object
    ground.name = "Ground"
    ground.data.materials.append(_mat("Ground", (0.08, 0.09, 0.07, 1.0), 0.95))


def generate(cfg: Config) -> None:
    build_ground(cfg)
    points, segments, step = build_grid(cfg)
    cfg._segments = segments
    build_roads(cfg, segments)
    quads = block_quads(cfg, points, step)
    build_sidewalks(cfg, quads)
    cfg._block_quads = quads
