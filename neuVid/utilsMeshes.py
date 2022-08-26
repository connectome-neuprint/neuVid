# Utility functions related to loading meshes.

from io import BytesIO
import numpy as np
import os
import os.path
from pathlib import Path
import requests
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsNg import dir_name_from_ng_source, is_ng_source

def fileToImportForNeuron(source, bodyId, parentForDownloadDir):
    if source.startswith("http"):
        meshBin = downloadMesh(source, bodyId + ".ngmesh")
        if meshBin:
            with BytesIO(meshBin) as meshBinStream:
                verticesXYZ, faces = read_ngmesh(meshBinStream)
                # Per the comment in
                # https://github.com/janelia-flyem/vol2mesh/blob/master/vol2mesh/ngmesh.py,
                # divide by 8 to convert to DVID coordinates.
                verticesXYZ = verticesXYZ / 8

            dirName = "neuVidNeuronMeshes/"
            downloadDir = parentForDownloadDir
            if downloadDir[-1] != "/":
                downloadDir += "/"
            downloadDir += dirName

            try:
                if not os.path.exists(downloadDir):
                    os.mkdir(downloadDir)
                fileName = downloadDir + bodyId + ".obj"
                with open(fileName, "w") as f:
                    write_obj(verticesXYZ, faces,  None, f)
                return fileName
            except OSError as e:
                print("Error: writing neuron '{}' from source URL '{}' failed: {}".format(bodyId, source, str(e)))
                return None

    elif is_ng_source(source):
        # Try to use OBJ files downloaded by fetchMeshes.py.
        download_dir = dir_name_from_ng_source(source)
        path = os.path.join(parentForDownloadDir, download_dir)
        return os.path.join(path, bodyId + ".obj")

    else:
        dir = source
        if dir[-1] != "/":
            dir += "/"
        return dir + bodyId + ".obj"

def fileToImportForRoi(source, roiName, parentForDownloadDir):
    if source.startswith("http"):
        mesh = downloadMesh(source, roiName)
        if mesh:
            dirName = "neuVidRoiMeshes/"
            downloadDir = parentForDownloadDir
            if downloadDir[-1] != "/":
                downloadDir += "/"
            downloadDir += dirName

            try:
                if not os.path.exists(downloadDir):
                    os.mkdir(downloadDir)
                if roiName.endswith(".ngmesh"):
                    fileName = roiName.replace(".ngmesh", "")
                    fileName = downloadDir + roiNameClean(fileName) + ".obj"
                    with BytesIO(mesh) as meshBinStream:
                        verticesXYZ, faces = read_ngmesh(meshBinStream)
                        # Per the comment in
                        # https://github.com/janelia-flyem/vol2mesh/blob/master/vol2mesh/ngmesh.py,
                        # divide by 8 to convert to DVID coordinates.
                        verticesXYZ = verticesXYZ / 8
                    with open(fileName, "w") as f:
                        write_obj(verticesXYZ, faces,  None, f)
                else:
                    fileName = downloadDir + roiNameClean(roiName) + ".obj"
                    with open(fileName, "w") as f:
                        f.write(mesh.decode("utf-8"))
                return fileName
            except OSError as e:
                print("Error: writing roi '{}' from source URL '{}' failed: {}".format(roiName, source, str(e)))
                return None
    else:
        dir = source
        if dir[-1] != "/":
            dir += "/"
        return dir + roiName + ".obj"

def fileToImportForSynapses(source, synapseSetName, parentForDownloadDir):
    if source.startswith("http"):
        # Assume buildSynapses.py has been run already.  It is not run directly here,
        # for now, because it depends on neuprint-python, obtained from Conda, and
        # making Blender work with Conda is a topic for future work.

        dirName = "neuVidSynapseMeshes/"
        downloadDir = parentForDownloadDir
        if downloadDir[-1] != "/":
            downloadDir += "/"
        downloadDir += dirName

        fileName = downloadDir + synapseSetName + ".obj"
        return fileName
    else:
        dir = source
        if dir[-1] != "/":
            dir += "/"
        return dir + synapseSetName + ".obj"

def downloadMesh(source, key):
    url = source
    if url[-1] != "/":
        url += "/"
    if "dvid" in url or "janelia.org" in url:
        url += "key/"
    url += key
    try:
        r = requests.get(url)
        r.raise_for_status()
        return r.content
    except requests.exceptions.RequestException as e:
        print("Error: downloading '{}' from source URL '{}' failed: {}".format(key, source, str(e)))
        return None

def roiNameClean(roiName):
    roiClean = roiName.replace("(", "").replace(")", "").replace("'", "Prime")
    # Another problem is that OS X treats filenames "aL" and "AL" as identical.
    roiClean = roiClean.replace("a", "aa")
    return roiClean

# Returns a string with the OBJ mesh for an icoshedron of radius r centered at c.

def icosohedron(c, r, i):
    # A Blender icoshedron sphere, with "subdivisions 2", output to OBJ.
    j = i * 42
    s = "v {} {} {}\n".format(c[0] + r * 0.000000, c[1] + r * -1.000000, c[2] + r * 0.000000)
    s += "v {} {} {}\n".format(c[0] + r * 0.723607, c[1] + r * -0.447220, c[2] + r * 0.525725)
    s += "v {} {} {}\n".format(c[0] + r * -0.276388, c[1] + r * -0.447220, c[2] + r * 0.850649)
    s += "v {} {} {}\n".format(c[0] + r * -0.894426, c[1] + r * -0.447216, c[2] + r * 0.000000)
    s += "v {} {} {}\n".format(c[0] + r * -0.276388, c[1] + r * -0.447220, c[2] + r * -0.850649)
    s += "v {} {} {}\n".format(c[0] + r * 0.723607, c[1] + r * -0.447220, c[2] + r * -0.525725)
    s += "v {} {} {}\n".format(c[0] + r * 0.276388, c[1] + r * 0.447220, c[2] + r * 0.850649)
    s += "v {} {} {}\n".format(c[0] + r * -0.723607, c[1] + r * 0.447220, c[2] + r * 0.525725)
    s += "v {} {} {}\n".format(c[0] + r * -0.723607, c[1] + r * 0.447220, c[2] + r * -0.525725)
    s += "v {} {} {}\n".format(c[0] + r * 0.276388, c[1] + r * 0.447220, c[2] + r * -0.850649)
    s += "v {} {} {}\n".format(c[0] + r * 0.894426, c[1] + r * 0.447216, c[2] + r * 0.000000)
    s += "v {} {} {}\n".format(c[0] + r * 0.000000, c[1] + r * 1.000000, c[2] + r * 0.000000)
    s += "v {} {} {}\n".format(c[0] + r * -0.162456, c[1] + r * -0.850654, c[2] + r * 0.499995)
    s += "v {} {} {}\n".format(c[0] + r * 0.425323, c[1] + r * -0.850654, c[2] + r * 0.309011)
    s += "v {} {} {}\n".format(c[0] + r * 0.262869, c[1] + r * -0.525738, c[2] + r * 0.809012)
    s += "v {} {} {}\n".format(c[0] + r * 0.850648, c[1] + r * -0.525736, c[2] + r * 0.000000)
    s += "v {} {} {}\n".format(c[0] + r * 0.425323, c[1] + r * -0.850654, c[2] + r * -0.309011)
    s += "v {} {} {}\n".format(c[0] + r * -0.525730, c[1] + r * -0.850652, c[2] + r * 0.000000)
    s += "v {} {} {}\n".format(c[0] + r * -0.688189, c[1] + r * -0.525736, c[2] + r * 0.499997)
    s += "v {} {} {}\n".format(c[0] + r * -0.162456, c[1] + r * -0.850654, c[2] + r * -0.499995)
    s += "v {} {} {}\n".format(c[0] + r * -0.688189, c[1] + r * -0.525736, c[2] + r * -0.499997)
    s += "v {} {} {}\n".format(c[0] + r * 0.262869, c[1] + r * -0.525738, c[2] + r * -0.809012)
    s += "v {} {} {}\n".format(c[0] + r * 0.951058, c[1] + r * 0.000000, c[2] + r * 0.309013)
    s += "v {} {} {}\n".format(c[0] + r * 0.951058, c[1] + r * 0.000000, c[2] + r * -0.309013)
    s += "v {} {} {}\n".format(c[0] + r * 0.000000, c[1] + r * 0.000000, c[2] + r * 1.000000)
    s += "v {} {} {}\n".format(c[0] + r * 0.587786, c[1] + r * 0.000000, c[2] + r * 0.809017)
    s += "v {} {} {}\n".format(c[0] + r * -0.951058, c[1] + r * 0.000000, c[2] + r * 0.309013)
    s += "v {} {} {}\n".format(c[0] + r * -0.587786, c[1] + r * 0.000000, c[2] + r * 0.809017)
    s += "v {} {} {}\n".format(c[0] + r * -0.587786, c[1] + r * 0.000000, c[2] + r * -0.809017)
    s += "v {} {} {}\n".format(c[0] + r * -0.951058, c[1] + r * 0.000000, c[2] + r * -0.309013)
    s += "v {} {} {}\n".format(c[0] + r * 0.587786, c[1] + r * 0.000000, c[2] + r * -0.809017)
    s += "v {} {} {}\n".format(c[0] + r * 0.000000, c[1] + r * 0.000000, c[2] + r * -1.000000)
    s += "v {} {} {}\n".format(c[0] + r * 0.688189, c[1] + r * 0.525736, c[2] + r * 0.499997)
    s += "v {} {} {}\n".format(c[0] + r * -0.262869, c[1] + r * 0.525738, c[2] + r * 0.809012)
    s += "v {} {} {}\n".format(c[0] + r * -0.850648, c[1] + r * 0.525736, c[2] + r * 0.000000)
    s += "v {} {} {}\n".format(c[0] + r * -0.262869, c[1] + r * 0.525738, c[2] + r * -0.809012)
    s += "v {} {} {}\n".format(c[0] + r * 0.688189, c[1] + r * 0.525736, c[2] + r * -0.499997)
    s += "v {} {} {}\n".format(c[0] + r * 0.162456, c[1] + r * 0.850654, c[2] + r * 0.499995)
    s += "v {} {} {}\n".format(c[0] + r * 0.525730, c[1] + r * 0.850652, c[2] + r * 0.000000)
    s += "v {} {} {}\n".format(c[0] + r * -0.425323, c[1] + r * 0.850654, c[2] + r * 0.309011)
    s += "v {} {} {}\n".format(c[0] + r * -0.425323, c[1] + r * 0.850654, c[2] + r * -0.309011)
    s += "v {} {} {}\n".format(c[0] + r * 0.162456, c[1] + r * 0.850654, c[2] + r * -0.499995)
    s += "f {} {} {}\n".format(j + 1, j + 14, j + 13)
    s += "f {} {} {}\n".format(j + 2, j + 14, j + 16)
    s += "f {} {} {}\n".format(j + 1, j + 13, j + 18)
    s += "f {} {} {}\n".format(j + 1, j + 18, j + 20)
    s += "f {} {} {}\n".format(j + 1, j + 20, j + 17)
    s += "f {} {} {}\n".format(j + 2, j + 16, j + 23)
    s += "f {} {} {}\n".format(j + 3, j + 15, j + 25)
    s += "f {} {} {}\n".format(j + 4, j + 19, j + 27)
    s += "f {} {} {}\n".format(j + 5, j + 21, j + 29)
    s += "f {} {} {}\n".format(j + 6, j + 22, j + 31)
    s += "f {} {} {}\n".format(j + 2, j + 23, j + 26)
    s += "f {} {} {}\n".format(j + 3, j + 25, j + 28)
    s += "f {} {} {}\n".format(j + 4, j + 27, j + 30)
    s += "f {} {} {}\n".format(j + 5, j + 29, j + 32)
    s += "f {} {} {}\n".format(j + 6, j + 31, j + 24)
    s += "f {} {} {}\n".format(j + 7, j + 33, j + 38)
    s += "f {} {} {}\n".format(j + 8, j + 34, j + 40)
    s += "f {} {} {}\n".format(j + 9, j + 35, j + 41)
    s += "f {} {} {}\n".format(j + 10, j + 36, j + 42)
    s += "f {} {} {}\n".format(j + 11, j + 37, j + 39)
    s += "f {} {} {}\n".format(j + 39, j + 42, j + 12)
    s += "f {} {} {}\n".format(j + 39, j + 37, j + 42)
    s += "f {} {} {}\n".format(j + 37, j + 10, j + 42)
    s += "f {} {} {}\n".format(j + 42, j + 41, j + 12)
    s += "f {} {} {}\n".format(j + 42, j + 36, j + 41)
    s += "f {} {} {}\n".format(j + 36, j + 9, j + 41)
    s += "f {} {} {}\n".format(j + 41, j + 40, j + 12)
    s += "f {} {} {}\n".format(j + 41, j + 35, j + 40)
    s += "f {} {} {}\n".format(j + 35, j + 8, j + 40)
    s += "f {} {} {}\n".format(j + 40, j + 38, j + 12)
    s += "f {} {} {}\n".format(j + 40, j + 34, j + 38)
    s += "f {} {} {}\n".format(j + 34, j + 7, j + 38)
    s += "f {} {} {}\n".format(j + 38, j + 39, j + 12)
    s += "f {} {} {}\n".format(j + 38, j + 33, j + 39)
    s += "f {} {} {}\n".format(j + 33, j + 11, j + 39)
    s += "f {} {} {}\n".format(j + 24, j + 37, j + 11)
    s += "f {} {} {}\n".format(j + 24, j + 31, j + 37)
    s += "f {} {} {}\n".format(j + 31, j + 10, j + 37)
    s += "f {} {} {}\n".format(j + 32, j + 36, j + 10)
    s += "f {} {} {}\n".format(j + 32, j + 29, j + 36)
    s += "f {} {} {}\n".format(j + 29, j + 9, j + 36)
    s += "f {} {} {}\n".format(j + 30, j + 35, j + 9)
    s += "f {} {} {}\n".format(j + 30, j + 27, j + 35)
    s += "f {} {} {}\n".format(j + 27, j + 8, j + 35)
    s += "f {} {} {}\n".format(j + 28, j + 34, j + 8)
    s += "f {} {} {}\n".format(j + 28, j + 25, j + 34)
    s += "f {} {} {}\n".format(j + 25, j + 7, j + 34)
    s += "f {} {} {}\n".format(j + 26, j + 33, j + 7)
    s += "f {} {} {}\n".format(j + 26, j + 23, j + 33)
    s += "f {} {} {}\n".format(j + 23, j + 11, j + 33)
    s += "f {} {} {}\n".format(j + 31, j + 32, j + 10)
    s += "f {} {} {}\n".format(j + 31, j + 22, j + 32)
    s += "f {} {} {}\n".format(j + 22, j + 5, j + 32)
    s += "f {} {} {}\n".format(j + 29, j + 30, j + 9)
    s += "f {} {} {}\n".format(j + 29, j + 21, j + 30)
    s += "f {} {} {}\n".format(j + 21, j + 4, j + 30)
    s += "f {} {} {}\n".format(j + 27, j + 28, j + 8)
    s += "f {} {} {}\n".format(j + 27, j + 19, j + 28)
    s += "f {} {} {}\n".format(j + 19, j + 3, j + 28)
    s += "f {} {} {}\n".format(j + 25, j + 26, j + 7)
    s += "f {} {} {}\n".format(j + 25, j + 15, j + 26)
    s += "f {} {} {}\n".format(j + 15, j + 2, j + 26)
    s += "f {} {} {}\n".format(j + 23, j + 24, j + 11)
    s += "f {} {} {}\n".format(j + 23, j + 16, j + 24)
    s += "f {} {} {}\n".format(j + 16, j + 6, j + 24)
    s += "f {} {} {}\n".format(j + 17, j + 22, j + 6)
    s += "f {} {} {}\n".format(j + 17, j + 20, j + 22)
    s += "f {} {} {}\n".format(j + 20, j + 5, j + 22)
    s += "f {} {} {}\n".format(j + 20, j + 21, j + 5)
    s += "f {} {} {}\n".format(j + 20, j + 18, j + 21)
    s += "f {} {} {}\n".format(j + 18, j + 4, j + 21)
    s += "f {} {} {}\n".format(j + 18, j + 19, j + 4)
    s += "f {} {} {}\n".format(j + 18, j + 13, j + 19)
    s += "f {} {} {}\n".format(j + 13, j + 3, j + 19)
    s += "f {} {} {}\n".format(j + 16, j + 17, j + 6)
    s += "f {} {} {}\n".format(j + 16, j + 14, j + 17)
    s += "f {} {} {}\n".format(j + 14, j + 1, j + 17)
    s += "f {} {} {}\n".format(j + 13, j + 15, j + 3)
    s += "f {} {} {}\n".format(j + 13, j + 14, j + 15)
    s += "f {} {} {}\n".format(j + 14, j + 2, j + 15)
    return s

# The following functions are copied from https://github.com/janelia-flyem/vol2mesh
# (with Python 3.6 "f-strings" replaced by "format" calls).
# TODO: Try to find a way to use Conda with Blender's Python so the vol2mesh package
# can be used directly and such copying can be eliminated.

def read_ngmesh(f):
    """
    Read vertices and faces from the given binary file object,
    which is in ngmesh format as described above.

    Args:
        f:
            An open binary file object

    Returns:
        (vertices_xyz, faces)
        where vertices_xyz is a 2D array (N,3), in XYZ order.
    """
    num_vertices = np.frombuffer(f.read(4), np.uint32)[0]
    vertices_xyz = np.frombuffer(f.read(int(3*4*num_vertices)), np.float32).reshape(-1, 3)
    faces = np.frombuffer(f.read(), np.uint32).reshape(-1, 3)
    return vertices_xyz, faces

def write_obj(vertices_xyz, faces, normals_xyz=None, output_file=None):
    """
    Generate an OBJ file from the given (binary) data and write it to the given byte stream or file path.

    If no output stream/path is given, return a bytes object containing the OBJ data.

    vertices_xyz: np.ndarray, shape=(N,3), dtype=float
    faces: np.ndarray, shape=(N,3), dtype=int
    normals_xyz: np.ndarray, shape=(N,3), dtype=float (Optional.)

    Note: Each 'face' consists of 3 indexes, which correspond to indexes in the vertices_xyz.
          The indexes should be 0-based. (They will be converted to 1-based in the OBJ)
    """
    if normals_xyz is None:
        normals_xyz = np.zeros((0,3), np.float32)

    need_close = True

    if output_file is None:
        mesh_bytestream = BytesIO()
    elif isinstance(output_file, (str, Path)):
        mesh_bytestream = open(output_file, 'wb')
    else:
        assert hasattr(output_file, 'write')
        mesh_bytestream = output_file
        need_close = False

    try:
        _write_obj(vertices_xyz, faces, normals_xyz, mesh_bytestream)
        if output_file is None:
            return mesh_bytestream.getvalue()
    finally:
        if need_close:
            mesh_bytestream.close()

def _write_obj(vertices_xyz, faces, normals_xyz, mesh_bytestream):
    """
    Given lists of vertices and faces, write them to the given stream in .obj format.

    vertices_xyz: np.ndarray, shape=(N,3), dtype=float
    faces: np.ndarray, shape=(N,3), dtype=int
    normals_xyz: np.ndarray, shape=(N,3), dtype=float

    Note: Each 'face' consists of 3 indexes, which correspond to indexes in the vertices_xyz.
          The indexes should be 0-based. (They will be converted to 1-based in the OBJ)

    Returns:
        BytesIO
    """
    if len(vertices_xyz) == 0:
        # Empty meshes result in no bytes
        return

    mesh_bytestream.write("# OBJ file\n")

    for (x,y,z) in vertices_xyz:
        mesh_bytestream.write("v {:.7g} {:.7g} {:.7g}\n".format(x, y, z))

    for (x,y,z) in normals_xyz:
        mesh_bytestream.write("vn {:.7g} {:.7g} {:.7g}\n".format(x, y, z))

    # OBJ format: Faces start at index 1 (not 0)
    for (v1, v2, v3) in faces+1:
        if len(normals_xyz) > 0:
            mesh_bytestream.write("f {}//{} {}//{} {}//{}\n".format(v1, v1, v2, v2, v3, v3))
        else:
            mesh_bytestream.write("f {} {} {}\n".format(v1, v2, v3))
