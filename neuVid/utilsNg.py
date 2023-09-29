import os
import requests
import sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsMath import Vector

def source_to_url(s):
    precomputed_prefix = "precomputed://"
    if s.startswith(precomputed_prefix):
        s1 = s.split(precomputed_prefix)[1]
        gs_prefix = "gs://"
        s3_prefix = "s3://"
        plain1_prefix = "http://"
        plain2_prefix = "https://"
        if s1.startswith(gs_prefix):
            s2 = s1.split(gs_prefix)
            return "https://storage.googleapis.com/" + s2[1]
        elif s1.startswith(s3_prefix):
            s2 = s1.split(s3_prefix)
            s3 = s2[1].split("/", 1)
            return "https://" + s3[0] + ".s3.amazonaws.com/" + s3[1]
        elif s1.startswith(plain1_prefix) or s1.startswith(plain2_prefix):
            return s1
    return ""

def is_ng_source(source):
    if source.startswith("precomputed://"):
        return True
    return False

def dir_name_from_ng_source(source):
    return source.replace("/", "_").replace(":", "_")

# TODO: Update importNg.py to use these functions.

def quat_ng_to_blender(quat_ng):
    # In Neuroglancer, an identity quaternion is (0, 0, 0, 1), because in
    # src/neuroglancer/navigateion_state.ts` the "projectionOrientation" is omitted from
    # the view state if `quaternionIsIdentity(orientation)` returns true, which happens when
    # the orientation is (0, 0, 0, 1).  So Neuroglancer quaterions have the form (x, y, z, w).
    # In Neuroglancer, when the orientation is an identity quaternion, the camera is
    # looking down the +Z axis, with +X pointing right and +Y pointing down.
    # In Blender, when the orientation is an identity quaternion, the camera is
    # looking down the -Z axis, with +X pointing right and +Y pointing up.
    # So Blender's identity quaternion differs from Neuroglancers by a 180 degree rotation about X.

    # Convert (x, y, z, w) to (w, x, y, z).
    quat_blender = (quat_ng[3], quat_ng[0], quat_ng[1], quat_ng[2])

    # Right-multiple a quaternion that rotates 180 degrees around X.
    quat_blender_rot_x_180 = (quat_blender[1], -quat_blender[0], -quat_blender[3], quat_blender[2])
    return quat_blender_rot_x_180

def ng_camera_look_from(position, distance, quaternion_blender_format):
    # Neuroglancer state uses the term `position` for the point the camera is looking at.

    # Empirically, this increase of the distance seems about right, with `"fovVertical": 45`.
    distance = distance * 1.3

    v = Vector((0, 0, 1)) * distance
    v.rotate(quaternion_blender_format)
    v = Vector(position) + v
    return (v.x, v.y, v.z)
