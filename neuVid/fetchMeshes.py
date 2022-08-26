# Requires MeshParty, Open3D:
# $ conda create --name neuvid python=3.9
# $ conda activate neuvid
# $ pip install meshparty open3d

# Runs with standard Python (not through Blender), as in:
# $ python fetchMeshes.py -ij video.json

import argparse
import json
import os
import sys
import tempfile
import trimesh
from meshparty import trimesh_io

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsJson import parseNeuronsIds, removeComments
from utilsNg import dir_name_from_ng_source, is_ng_source

def fetch_ng_source(source, decim_fraction):
    dir = dir_name_from_ng_source(source)

    try:
        download_dir = os.path.join(input_json_dir, dir)
        if not os.path.exists(download_dir):
            os.mkdir(download_dir)
        tmp_dir = tempfile.TemporaryDirectory().name
        mesh_meta = trimesh_io.MeshMeta(cv_path=source, disk_cache_path=tmp_dir, map_gs_to_https=True)

        j = 0
        for neuron_id in neuron_ids[i]:
            neuron_id = int(neuron_id)
            percent = j / len(neuron_ids[i]) * 100

            print("[{:.1f}%] Fetching ID {} ...".format(percent, neuron_id))
            mesh = mesh_meta.mesh(seg_id=neuron_id)
            print("Done")

            face_count = mesh.faces.shape[0]
            print("[{:.1f}%] Smoothing ID {} ...".format(percent, neuron_id))
            mesh_smooth = trimesh.smoothing.filter_taubin(mesh)
            print("Done")

            print("[{:.1f}%] Decimating ID {} ...".format(percent, neuron_id))
            mesh_smooth_decim = mesh_smooth.simplify_quadratic_decimation(face_count * decim_fraction)
            print("Done")

            output = os.path.join(download_dir, str(neuron_id) + ".obj")
            print("[{:.1f}%] Exporting {} ...".format(percent, output))
            mesh_smooth_decim.export(output)
            print("Done")

            j += 1

    except OSError as e:
        print("Error: fetching from source '{}' failed: {}".format(source, str(e)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputJson", "-ij", dest="input_json_file", help="path to the JSON file describing the input")
    parser.set_defaults(decim_fraction=0.25)
    parser.add_argument("--decim", "-d", type=float, dest="decim_fraction", help="mesh decimation fraction")
    args = parser.parse_args()

    print("Using input file: {}".format(args.input_json_file))
    print("Using decimation fraction: {}".format(args.decim_fraction))

    input_json_dir = os.path.dirname(os.path.realpath(args.input_json_file))
    json_data = json.loads(removeComments(args.input_json_file))
    if json_data == None:
        print("Loading JSON file {} failed".format(args.input_json_file))
        quit()

    if "neurons" in json_data:
        json_neurons = json_data["neurons"]
        if "source" in json_neurons:
            source = json_neurons["source"]
            if isinstance(source, str):
                neuron_sources = [source]
            else:
                neuron_sources = source

            neuron_ids, _, _, _ = parseNeuronsIds(json_neurons)

            for i in range(len(neuron_sources)):
                if len(neuron_sources) == 1:
                    print("Fetching {} neuron meshes".format(len(neuron_ids[i])))
                else:
                    print("Fetching {} neuron meshes for index {}".format(len(neuron_ids[i]), i))

                source = neuron_sources[i]
                if is_ng_source(source):
                    fetch_ng_source(source, args.decim_fraction)
