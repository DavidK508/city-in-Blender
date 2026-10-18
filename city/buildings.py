"""Buildings: lots, towers, skyline."""
import bmesh
import bpy
import math

from .config import Config
from . import materials
from .roads import SIDEWALK_Z

FLOOR_H = 3.2


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


def _add_tower(bm, quad, height, taper, top_scale, z0, facade_idx):
    """Extrude a quad footprint with optional taper; return top center, base+top verts."""
    base_verts = [bm.verts.new((x, y, z0)) for x, y in quad]
    face = bm.faces.new(base_verts)
    result = bmesh.ops.extrude_face_region(bm, geom=[face])
    new_verts = [g for g in result["geom"] if isinstance(g, bmesh.types.BMVert)]
    new_faces = [g for g in result["geom"] if isinstance(g, bmesh.types.BMFace)]
    bmesh.ops.translate(bm, vec=(0, 0, height), verts=new_verts)
    if taper < 0.999:
        cx = sum(v.co.x for v in new_verts) / len(new_verts)
        cy = sum(v.co.y for v in new_verts) / len(new_verts)
        for v in new_verts:
            v.co.x = cx + (v.co.x - cx) * top_scale
            v.co.y = cy + (v.co.y - cy) * top_scale
    else:
        cx = sum(v.co.x for v in new_verts) / len(new_verts)
        cy = sum(v.co.y for v in new_verts) / len(new_verts)
    for f in new_faces:
        f.material_index = facade_idx
    return (cx, cy, z0 + height), base_verts, new_verts


def _lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


class _Geom:
    """Plain vertex/face lists for windows and balconies (fast from_pydata)."""

    def __init__(self):
        self.verts = []
        self.faces = []
        self.face_mats = []

    def quad(self, corners, mat=0):
        base = len(self.verts)
        self.verts.extend(corners)
        self.faces.append((base, base + 1, base + 2, base + 3))
        self.face_mats.append(mat)

    def box(self, bot4, h, mat=0):
        top4 = [(p[0], p[1], p[2] + h) for p in bot4]
        base = len(self.verts)
        self.verts.extend(bot4)
        self.verts.extend(top4)
        b = [base + i for i in range(4)]
        t = [base + 4 + i for i in range(4)]
        self.faces.append(tuple(t[::-1]))
        self.faces.append(tuple(b))
        for i in range(4):
            self.faces.append((b[i], b[(i + 1) % 4], t[(i + 1) % 4], t[i]))
        self.face_mats.extend([mat] * 6)


def _add_windows_balconies(win, balc, base_pts, top_pts, z0, height, rng,
                           with_balconies):
    """Windows grid + balconies on the four side walls of a prism."""
    n_floors = max(1, int(height / FLOOR_H))
    for i in range(4):
        a0 = base_pts[i]
        b0 = base_pts[(i + 1) % 4]
        a1 = top_pts[i]
        b1 = top_pts[(i + 1) % 4]
        wall_len = ((b0[0] - a0[0]) ** 2 + (b0[1] - a0[1]) ** 2) ** 0.5
        if wall_len < 2.5:
            continue
        cols = max(1, int(wall_len / 2.6))
        # outward normal at wall base
        dx, dy = b0[0] - a0[0], b0[1] - a0[1]
        nx, ny = dy / wall_len, -dx / wall_len
        cx = (a0[0] + b0[0]) / 2.0
        cy = (a0[1] + b0[1]) / 2.0
        if nx * cx + ny * cy < 0:
            nx, ny = -nx, -ny

        win_w, win_h = 1.4, 1.7
        for f in range(n_floors):
            z = z0 + f * FLOOR_H + FLOOR_H * 0.55
            if z + win_h / 2.0 > z0 + height - 0.3:
                break
            t = (z - z0) / height if height > 1e-6 else 0.0
            left = _lerp(a0, a1, t)
            right = _lerp(b0, b1, t)
            wdx, wdy = right[0] - left[0], right[1] - left[1]
            wlen = (wdx * wdx + wdy * wdy) ** 0.5
            if wlen < 1e-6:
                continue
            ux, uy = wdx / wlen, wdy / wlen
            for c in range(cols):
                tt = (c + 0.5) / cols
                px = left[0] + wdx * tt + nx * 0.06
                py = left[1] + wdy * tt + ny * 0.06
                hw = min(win_w, wlen / cols * 0.7) / 2.0
                hh = win_h / 2.0
                win.quad([
                    (px - ux * hw, py - uy * hw, z - hh),
                    (px + ux * hw, py + uy * hw, z - hh),
                    (px + ux * hw, py + uy * hw, z + hh),
                    (px - ux * hw, py - uy * hw, z + hh),
                ])

        if not with_balconies:
            continue
        # balconies: protruding slab + railing on random floors
        for f in range(2, n_floors):
            if rng.random() > 0.4:
                continue
            z = z0 + f * FLOOR_H
            if z + 1.2 > z0 + height - 0.3:
                break
            t = (z - z0) / height if height > 1e-6 else 0.0
            left = _lerp(a0, a1, t)
            right = _lerp(b0, b1, t)
            wdx, wdy = right[0] - left[0], right[1] - left[1]
            wlen = (wdx * wdx + wdy * wdy) ** 0.5
            if wlen < 1e-6:
                continue
            ux, uy = wdx / wlen, wdy / wlen
            bw = min(3.2, wlen * 0.8) / 2.0
            depth = 1.1
            mx = left[0] + wdx * 0.5
            my = left[1] + wdy * 0.5
            c0 = (mx - ux * bw, my - uy * bw)
            c1 = (mx + ux * bw, my + uy * bw)
            # slab
            balc.box([
                (c0[0], c0[1], z),
                (c1[0], c1[1], z),
                (c1[0] + nx * depth, c1[1] + ny * depth, z),
                (c0[0] + nx * depth, c0[1] + ny * depth, z),
            ], 0.15)
            # railing: 3 quads around outer edge
            rz0, rz1 = z + 0.15, z + 1.15
            ro0 = (c0[0] + nx * depth, c0[1] + ny * depth)
            ro1 = (c1[0] + nx * depth, c1[1] + ny * depth)
            for p, q in ((c0, ro0), (ro0, ro1), (ro1, c1)):
                balc.quad([
                    (p[0], p[1], rz0),
                    (q[0], q[1], rz0),
                    (q[0], q[1], rz1),
                    (p[0], p[1], rz1),
                ], mat=1)


def build_building(bm, win, balc, quad, height, rng, facade_idx,
                   is_glass=False):
    """One building: optional podium, tapered tower, antenna + windows/balconies."""
    z0 = SIDEWALK_Z

    is_tower = height > 60.0
    if is_tower:
        # podium
        podium_h = rng.uniform(8.0, 14.0)
        podium_quad = _inset_quad(quad, -3.0) or quad
        _, pod_base, pod_top = _add_tower(bm, podium_quad, podium_h, False, 1.0, z0, facade_idx)
        _add_windows_balconies(
            win, balc,
            [(v.co.x, v.co.y) for v in pod_base],
            [(v.co.x, v.co.y) for v in pod_top],
            z0, podium_h, rng, False)
        z0 += podium_h

    taper = rng.uniform(0.8, 1.0) if is_tower else 1.0
    top_scale = rng.uniform(0.75, 0.95) if is_tower else 1.0
    shaft_h = height - (z0 - SIDEWALK_Z)
    top, base_verts, top_verts = _add_tower(bm, quad, shaft_h, taper, top_scale, z0, facade_idx)

    with_balconies = (not is_glass) and height < 60.0
    _add_windows_balconies(
        win, balc,
        [(v.co.x, v.co.y) for v in base_verts],
        [(v.co.x, v.co.y) for v in top_verts],
        z0, shaft_h, rng, with_balconies)

    if is_tower and rng.random() < 0.5:
        # antenna
        ax, ay, az = top
        r = 0.4
        ant_h = rng.uniform(8.0, 20.0)
        ring = [bm.verts.new((ax + r * math.cos(a), ay + r * math.sin(a), az))
                for a in (i * math.pi / 4 for i in range(8))]
        top_ring = [bm.verts.new((ax + r * 0.15 * math.cos(a), ay + r * 0.15 * math.sin(a),
                                  az + ant_h))
                    for a in (i * math.pi / 4 for i in range(8))]
        ant_faces = [bm.faces.new(ring[::-1]), bm.faces.new(top_ring)]
        for i in range(8):
            ant_faces.append(
                bm.faces.new((ring[i], ring[(i + 1) % 8], top_ring[(i + 1) % 8], top_ring[i])))
        for f in ant_faces:
            f.material_index = facade_idx


def pick_facade(cfg, height, glass_count, rng):
    glass_start = len(materials.FACADE_PALETTES) - glass_count
    if height > 50.0 and rng.random() < cfg.glass_chance:
        return rng.randrange(glass_start, len(materials.FACADE_PALETTES))
    return rng.randrange(0, glass_start)


def _make_mesh(name, verts, faces, mats, face_mats=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    for mat in mats:
        mesh.materials.append(mat)
    if face_mats:
        for poly, mi in zip(mesh.polygons, face_mats):
            poly.material_index = mi
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def generate(cfg: Config) -> None:
    rng = cfg._rng
    facades = materials.get_facade_materials(cfg)
    glass_count = sum(1 for p in materials.FACADE_PALETTES if p[4])
    glass_start = len(materials.FACADE_PALETTES) - glass_count

    bm = bmesh.new()
    win = _Geom()
    balc = _Geom()
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
            build_building(bm, win, balc, inset, h, rng, idx, is_glass=idx >= glass_start)

    mesh = bpy.data.meshes.new("Buildings")
    bm.to_mesh(mesh)
    for mat in facades:
        mesh.materials.append(mat)
    bm.free()
    obj = bpy.data.objects.new("Buildings", mesh)
    bpy.context.collection.objects.link(obj)

    if win.faces:
        _make_mesh("Windows", win.verts, win.faces, [materials.window_mat(cfg)])
    if balc.faces:
        _make_mesh("Balconies", balc.verts, balc.faces,
                   [materials.balcony_mat(), materials.railing_mat()],
                   face_mats=balc.face_mats)

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
