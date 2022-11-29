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
from utilsSynapses import download_synapses;

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

def fileToImportForSynapses(source, synapseSetName, synapseSetSpec, parentForDownloadDir):
    if source.startswith("http"):
        dirName = "neuVidSynapseMeshes/"
        downloadDir = parentForDownloadDir
        if downloadDir[-1] != "/":
            downloadDir += "/"
        downloadDir += dirName

        try:
            if not os.path.exists(downloadDir):
                os.mkdir(downloadDir)
            fileName = downloadDir + synapseSetName + ".obj"
            download_synapses(source, synapseSetSpec, fileName)
            return fileName
        except OSError as e:
            print("Error: writing synapses '{}' from source URL '{}' failed: {}".format(synapseSetName, source, str(e)))
            return None
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
