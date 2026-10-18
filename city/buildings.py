"""Buildings: lots, towers, skyline."""
import bmesh
import bpy
import math

from .config import Config
from . import materials
from .roads import SIDEWALK_Z


def _quad_center(q):
    return (sum(p[0] for p in q) / 4.0, sum(p[1] for p in q) / 4.0)


def _quad_area(q):
    area = 0.0
    for i in range(4):
        x1, y1 = q[i]
        x2, y2 = q[(i + 1) % 4]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def _split_quad(q, rng):
    """Split quad along its longer axis at a random point."""
    edges = [(q[i], q[(i + 1) % 4]) for i in range(4)]
    lengths = [((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
               for a, b in edges]
    axis = 0 if lengths[0] >= lengths[2] else 1
    # edges 0 and 2 are parallel; split connecting edges 1 and 3
    t = rng.uniform(0.35, 0.65)
    e1a, e1b = edges[1]
    e3a, e3b = edges[3]
    m1 = (e1a[0] + (e1b[0] - e1a[0]) * t, e1a[1] + (e1b[1] - e1a[1]) * t)
    m2 = (e3a[0] + (e3b[0] - e3a[0]) * t, e3a[1] + (e3b[1] - e3a[1]) * t)
    q1 = [q[0], m1, m2, q[3]]
    q2 = [m1, q[1], q[2], m2]
    return q1, q2


def split_lots(quad, cfg, rng, out):
    """Recursively split quad into building lots."""
    if _quad_area(quad) <= cfg.max_lot:
        if _quad_area(quad) >= cfg.min_lot:
            out.append(quad)
        return
    if rng.random() < 0.15:
        out.append(quad)
        return
    try:
        q1, q2 = _split_quad(quad, rng)
    except Exception:
        out.append(quad)
        return
    split_lots(q1, cfg, rng, out)
    split_lots(q2, cfg, rng, out)


def _inset_quad(quad, amount):
    cx, cy = _quad_center(quad)
    result = []
    for x, y in quad:
        dx, dy = x - cx, y - cy
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 1e-6 or dist < amount:
            return None
        result.append((cx + dx * (dist - amount) / dist,
                       cy + dy * (dist - amount) / dist))
    return result


def height_at(cfg, x, y, rng):
    """Skyline height: tall downtown, low outskirts."""
    dist = (x * x + y * y) ** 0.5
    falloff = math.exp(-(dist / cfg.downtown_radius) ** 2)
    base = cfg.mid_height + cfg.max_height * falloff
    h = base * rng.uniform(0.45, 1.15)
    if falloff > 0.5 and rng.random() < 0.08:
        h *= 1.6  # landmark spikes
    return max(8.0, min(h, cfg.max_height * 1.35))


def _add_tower(bm, quad, height, taper, top_scale, z0):
    """Extrude a quad footprint with optional taper; return top face center."""
    verts = [bm.verts.new((x, y, z0)) for x, y in quad]
    face = bm.faces.new(verts)
    result = bmesh.ops.extrude_face_region(bm, geom=[face])
    new_verts = [g for g in result["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, height), verts=new_verts)
    if taper < 0.999:
        cx = sum(v.co.x for v in new_verts) / len(new_verts)
        cy = sum(v.co.y for v in new_verts) / len(new_verts)
        for v in new_verts:
            v.co.x = cx + (v.co.x - cx) * top_scale
            v.co.y = cy + (v.co.y - cy) * top_scale
        return (cx, cy, z0 + height), new_verts
    cx = sum(v.co.x for v in new_verts) / len(new_verts)
    cy = sum(v.co.y for v in new_verts) / len(new_verts)
    return (cx, cy, z0 + height), new_verts


def build_building(bm, quad, height, rng, facade_idx):
    """One building: optional podium, tapered tower, antenna."""
    z0 = SIDEWALK_Z
    faces_before = len(bm.faces)

    is_tower = height > 60.0
    if is_tower:
        # podium
        podium_h = rng.uniform(8.0, 14.0)
        podium_quad = _inset_quad(quad, -3.0) or quad
        _add_tower(bm, podium_quad, podium_h, False, 1.0, z0)
        z0 += podium_h

    taper = rng.uniform(0.8, 1.0) if is_tower else 1.0
    top_scale = rng.uniform(0.75, 0.95) if is_tower else 1.0
    top, _ = _add_tower(bm, quad, height - (z0 - SIDEWALK_Z), taper, top_scale, z0)

    if is_tower and rng.random() < 0.5:
        # antenna
        ax, ay, az = top
        r = 0.4
        ant_h = rng.uniform(8.0, 20.0)
        ring = [bm.verts.new((ax + r * math.cos(a), ay + r * math.sin(a), az))
                for a in (i * math.pi / 4 for i in range(8))]
        top_ring = [bm.verts.new((v.co.x * 0.5 + ax * 0.5, v.co.y * 0.5 + ay * 0.5, az + ant_h))
                    for v in ring]
        # fix top ring: center at ax, ay
        for v in top_ring:
            v.co.x = ax + (v.co.x - ax) * 0.15
            v.co.y = ay + (v.co.y - ay) * 0.15
        bm.faces.new(ring[::-1])
        bm.faces.new(top_ring)
        for i in range(8):
            bm.faces.new((ring[i], ring[(i + 1) % 8], top_ring[(i + 1) % 8], top_ring[i]))

    for f in bm.faces[faces_before:]:
        f.material_index = facade_idx


def pick_facade(cfg, height, glass_count, rng):
    glass_start = len(materials.FACADE_PALETTES) - glass_count
    if height > 50.0 and rng.random() < cfg.glass_chance:
        return rng.randrange(glass_start, len(materials.FACADE_PALETTES))
    return rng.randrange(0, glass_start)


def generate(cfg: Config) -> None:
    rng = cfg._rng
    facades = materials.get_facade_materials(cfg)
    glass_count = sum(1 for p in materials.FACADE_PALETTES if p[4])

    bm = bmesh.new()
    park_quads = []
    for quad in cfg._block_quads:
        if rng.random() < cfg.park_chance:
            park_quads.append(quad)
            continue
        lots = []
        block = _inset_quad(quad, 2.0)
        if block is None:
            continue
        split_lots(block, cfg, rng, lots)
        for lot in lots:
            inset = _inset_quad(lot, rng.uniform(0.8, 1.8))
            if inset is None:
                continue
            h = height_at(cfg, *_quad_center(inset), rng)
            idx = pick_facade(cfg, h, glass_count, rng)
            build_building(bm, inset, h, rng, idx)

    mesh = bpy.data.meshes.new("Buildings")
    bm.to_mesh(mesh)
    for mat in facades:
        mesh.materials.append(mat)
    bm.free()
    obj = bpy.data.objects.new("Buildings", mesh)
    bpy.context.collection.objects.link(obj)

    # parks
    if park_quads:
        verts, faces = [], []
        for quad in park_quads:
            base = len(verts)
            verts.extend((x, y, SIDEWALK_Z + 0.02) for x, y in quad)
            faces.append((base, base + 1, base + 2, base + 3))
        pmesh = bpy.data.meshes.new("Parks")
        pmesh.from_pydata(verts, [], faces)
        pmesh.materials.append(materials.park_mat())
        pobj = bpy.data.objects.new("Parks", pmesh)
        bpy.context.collection.objects.link(pobj)

    cfg._park_quads = park_quads
