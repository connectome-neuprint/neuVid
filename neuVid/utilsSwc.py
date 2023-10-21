import bpy
import math
import mathutils
import os

def parse_swc(filepath):
    swc_json = {}
    with open(filepath, "r") as f:
        lines = f.readlines()
        swap = False
        for line in lines:
            if line.strip().startswith("#"):
                if "CCFv3.0" in line:
                    swap = True
                continue
            values = line.split()
            if len(values) == 7:
                id = int(values[0])
                swc_json[id] = {
                    "id": id,
                    "type": int(values[1]),
                    "x": float(values[2] if not swap else values[4]),
                    "y": float(values[3]),
                    "z": float(values[4] if not swap else values[2]),
                    "radius": float(values[5]),
                    "parent_id": int(values[6])
                }
    return swc_json

def build_disk_points(center, x_axis, y_axis, radius, count):
    result = []
    angle_step = 2 * math.pi / count
    angle = 0
    for i in range(count):
        x = math.cos(angle)
        y = math.sin(angle)
        p = center + x * radius * x_axis + y * radius * y_axis
        result.append(p)
        angle += angle_step
    return result

def build_cap_faces(offset, cap_vertex_count, flip):
    result = ""
    for i in range(1, cap_vertex_count - 1):
        if flip:
            result += f"f {offset} {offset + i} {offset + i + 1}\n"
        else:
            result += f"f {offset} {offset + i + 1} {offset + i}\n"
    return result

# depth is the full length along z_axis (i.e., ends are at location +/- z_axis * depth / 2)
def build_cone_obj(offset, location, depth, radius1, radius2, x_axis, y_axis, z_axis, cap_vertex_count, cap1, cap2):
    result = ""

    # Vertices.

    center1 = location - depth / 2 * z_axis
    disk_points1 = build_disk_points(center1, x_axis, y_axis, radius1, cap_vertex_count)
    for point in disk_points1:
        result += f"v {point[0]} {point[1]} {point[2]}\n"

    center2 = location + depth / 2 * z_axis
    disk_points2 = build_disk_points(center2, x_axis, y_axis, radius2, cap_vertex_count)
    for point in disk_points2:
        result += f"v {point[0]} {point[1]} {point[2]}\n"

    # Faces.

    for i in range(cap_vertex_count):
        i1 = offset + i
        i2 = i1 + cap_vertex_count
        i_next = (i + 1) % cap_vertex_count
        i1_next = offset + i_next
        i2_next = i1_next + cap_vertex_count
        result += f"f {i1} {i1_next} {i2}\n"
        result += f"f {i1_next} {i2_next} {i2}\n"

    if cap1:
        result += build_cap_faces(offset, cap_vertex_count, False)
    if cap2:
        result += build_cap_faces(offset + cap_vertex_count, cap_vertex_count, True)

    return result

def build_swc_obj(swc_json, cap_vertex_count=12, axon_radius_factor=2*5, dendrite_radius_factor=3*5):
    result = "# OBJ file converted from SWC by neuVid.\n"

    EPSILON = 1e-5
    # https://neuroinformatics.nl/swcPlus/
    # Type 2 is axon, type 3 is (basal) dendrite.
    radius_factor = {2: axon_radius_factor, 3: dendrite_radius_factor}

    # In OBJ files, the first vertex has index 1.
    offset = 1
    for item in swc_json.values():
        parent_id = item["parent_id"]
        if parent_id != -1:
            parent_item = swc_json[parent_id]
            p0 = mathutils.Vector((parent_item["x"], parent_item["y"], parent_item["z"]))
            p1 = mathutils.Vector((item["x"], item["y"], item["z"]))
            location = (p1 + p0) / 2

            # The cone has its spine along the Z axis, with radius1 at -Z and radius2 at +Z.
            z = (p1 - p0)
            depth = z.length
            if depth > EPSILON:
                z = z / depth

                x = mathutils.Vector((1, 0, 0))
                y = mathutils.Vector((0, 1, 0))
                if z.dot(x) < z.dot(y):
                    x_on_z = x.project(z)
                    x = (x - x_on_z).normalized()
                    y = z.cross(x)
                else:
                    y_on_z = y.project(z)
                    y = (y - y_on_z).normalized()
                    x = y.cross(z)

                radius1 = parent_item["radius"] * radius_factor[item["type"]]
                radius2 = item["radius"] * radius_factor[item["type"]]

                result += build_cone_obj(offset, location, depth, radius1, radius2, x, y, z, cap_vertex_count, True, True)
                offset += 2 * cap_vertex_count

    return result
