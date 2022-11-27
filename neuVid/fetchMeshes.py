# Runs with standard Python (not through Blender), as in:
# $ python fetchMeshes.py -ij from-neuroglancer.json

# To fetch only meshes (e.g., synapses) from a neuPrint.janelia.org Neuroglancer session,
# no additional dependencies are required.

# To fetch meshes from other Neuroglancer sessions,
# the following dependencies may be required:
# $ conda create --name neuvid python=3.9
# $ conda activate neuvid
# $ pip install meshparty open3d

import argparse
import datetime
import json
import os
import requests
import struct
import sys
import traceback
import tempfile

# Additional imports (e.g., numpy, trimesh, DracoPy) occur in the specific functions that need them,
# to allow the simplest use with neuPrint (to get synapses) with no need for Conda.

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsJson import decode_id, parseNeuronsIds, removeComments
from utilsMeshesBasic import icosohedron
from utilsNg import dir_name_from_ng_source, is_ng_source, source_to_url

def get_mesh_info(source):
    url = source_to_url(source)
    if url:
        try:
            response = requests.get(url + "/info")
            response.raise_for_status()
            info = response.json()
            return info
        except requests.exceptions.RequestException as e:
            print(f"Error: get({url}) failed: {str(e)}")
    return None

def is_cloudvolume_accessible(mesh_info):
    return mesh_info and "scales" in mesh_info

def ensure_dir(input_json_dir, dir):
    download_dir = os.path.join(input_json_dir, dir)
    if not os.path.exists(download_dir):
        os.mkdir(download_dir)
    return download_dir

def already_fetched(id, download_dir):
    path = os.path.join(download_dir, str(id) + ".obj")
    return os.path.exists(path)

# Supports Neuroglancer precomputed with sharding, but fails when the "scales" metadata is on another source.

def fetch_with_cloudvolume(source, ids, decim_fraction, input_json_dir, force):
    print("Fetching with CloudVolume")
    from meshparty import trimesh_io
    import trimesh

    try:
        download_dir = ensure_dir(input_json_dir, dir_name_from_ng_source(source))
        tmp_dir = tempfile.TemporaryDirectory().name
        mesh_meta = trimesh_io.MeshMeta(cv_path=source, disk_cache_path=tmp_dir, map_gs_to_https=True)

        j = 0
        for id in ids:
            id = decode_id(id)
            id = int(id)
            percent = j / len(ids) * 100

            if not force and already_fetched(id, download_dir):
                j += 1
                continue

            print(f"[{percent:.1f}%] Fetching ID {id} ...")
            mesh = mesh_meta.mesh(seg_id=id)
            print("Done")

            face_count = mesh.faces.shape[0]
            print(f"[{percent:.1f}%] Smoothing ID {id} ...")
            mesh_smooth = trimesh.smoothing.filter_taubin(mesh)
            print("Done")

            face_count_decim = int(face_count * decim_fraction)
            print(f"[{percent:.1f}%] Decimating ID {id} from {face_count} to {face_count_decim} faces ...")
            mesh_smooth_decim = mesh_smooth.simplify_quadratic_decimation(face_count_decim)

            output = os.path.join(download_dir, str(id) + ".obj")
            print(f"[{percent:.1f}%] Exporting {output} ...")
            mesh_smooth_decim.export(output)
            print("Done")

            j += 1

    except Exception as e:
        print(f"Error: fetching from source '{source}' failed: {traceback.format_exc()}")

# Supports the approach used by OpenOrganelle, with an N5 volume source having the "scales" metadata
# and another source having the meshes in Neuroglancer precomputed format.
# Does not support sharding.
# Based on code from David Ackerman.

def unpack_and_remove(datatype, num_elements, file_content):
    import numpy as np

    datatype = datatype * num_elements
    output = struct.unpack(datatype, file_content[0:4 * num_elements])
    file_content = file_content[4 * num_elements:] 
    return np.array(output), file_content

def fetch_directly(source, mesh_info, ids, lod, decim_fraction, input_json_dir, force):
    print("Fetching directly")
    import DracoPy
    import numpy as np
    import trimesh

    url_base = source_to_url(source)
    if not url_base:
        return

    # Get quantization and transform, for computing voxel size.
    if not "vertex_quantization_bits" in mesh_info:
        return
    vertex_quantization_bits = mesh_info["vertex_quantization_bits"]
    if not "transform" in mesh_info:
        return
    meshes_transform = mesh_info["transform"]
    meshes_transform += [0, 0, 0, 1]
    meshes_transform = np.reshape(meshes_transform, (4, 4))

    download_dir = ensure_dir(input_json_dir, dir_name_from_ng_source(source))
    failed = []

    j = 0
    for id in ids:
        id = decode_id(id)
        percent = j / len(ids) * 100

        if not force and already_fetched(id, download_dir):
            j += 1
            continue

        print(f"[{percent:.1f}%] Fetching ID {id} ...")

        # Get index file info.
        # Doing so may require several tries if there is "500 Server Error: Internal Server Error".
        success = False
        tries = 0
        while tries < 5:
            try:
                url = f"{url_base}/{id}.index"
                response = requests.get(url)
                response.raise_for_status()
                index_file_content = response.content

                chunk_shape, index_file_content = unpack_and_remove("f", 3, index_file_content)
                grid_origin, index_file_content = unpack_and_remove("f", 3, index_file_content)
                num_lods, index_file_content = unpack_and_remove("I", 1, index_file_content)
                lod_scales, index_file_content = unpack_and_remove("f", num_lods[0], index_file_content)
                vertex_offsets, index_file_content = unpack_and_remove("f", num_lods[0] * 3, index_file_content)
                num_fragments_per_lod, index_file_content = unpack_and_remove("I", num_lods[0], index_file_content)

                previous_lod_byte_offset = 0
                for current_lod in range(lod + 1):
                    fragment_positions, index_file_content = unpack_and_remove("I", num_fragments_per_lod[current_lod] * 3, index_file_content)
                    fragment_positions = fragment_positions.reshape((3, -1)).T
                    fragment_offsets, index_file_content = unpack_and_remove("I", num_fragments_per_lod[current_lod], index_file_content)

                    lod_byte_offset = np.cumsum(np.array(fragment_offsets)) + previous_lod_byte_offset
                    lod_byte_offset = np.insert(lod_byte_offset, 0, previous_lod_byte_offset)
                    # End of previous LOD.
                    previous_lod_byte_offset = lod_byte_offset[-1]

                mesh_fragments = []
                for idx,fragment_offset in enumerate(fragment_offsets):
                    if (lod_byte_offset[idx] != lod_byte_offset[idx + 1]): 
                        # Nonempty chunk.
                        chunk_name = f"{id}_{fragment_positions[idx][0]}_{fragment_positions[idx][1]}_{fragment_positions[idx][2]}"
                        response = requests.get(f'{url_base}/{id}', headers={"range": f"bytes={lod_byte_offset[idx]}-{lod_byte_offset[idx+1]}"})
                        drc_mesh = DracoPy.decode(response.content)
                        trimesh_mesh = trimesh.Trimesh(vertices=drc_mesh.points, faces=drc_mesh.faces)
                        n = chunk_shape * (2**lod) * (fragment_positions[idx] + trimesh_mesh.vertices / (2**vertex_quantization_bits - 1))
                        trimesh_mesh.vertices = grid_origin + vertex_offsets[lod] + n
                        mesh_fragments.append(trimesh_mesh)

                mesh = trimesh.util.concatenate(mesh_fragments)
                mesh.merge_vertices()
                mesh.apply_transform(meshes_transform)
                print("Done")

                face_count = mesh.faces.shape[0]
                print(f"[{percent:.1f}%] Smoothing ID {id} ...")
                mesh_smooth = trimesh.smoothing.filter_taubin(mesh)
                print("Done")

                face_count_decim = int(face_count * decim_fraction)
                print(f"[{percent:.1f}%] Decimating ID {id} from {face_count} to {face_count_decim} faces ...")
                mesh_smooth_decim = mesh_smooth.simplify_quadratic_decimation(face_count_decim)
                print("Done")

                output = os.path.join(download_dir, str(id) + ".obj")
                mesh_smooth_decim.export(output)

                j += 1

                success = True
                break
            except Exception as e:
                print(f"Error: fetching from source '{source}' failed: {traceback.format_exc()}")
                tries += 1

        if not success:
            failed.append(url)
            continue

    if len(failed) > 0:
        print(f"Failed: {failed}")

def synapse_type_matches(response_synapse, spec):
    type = spec["type"] if "type" in spec else None
    if not type:
        return True
    if "Kind" in response_synapse:
        kind = response_synapse["Kind"].lower()
        return kind.startswith(type)
    return True

def synapse_confidence_matches(response_synapse, spec):
    spec_conf = spec["confidence"] if "confidence" in spec else None
    if not spec_conf:
        return True
    if "Prop" in response_synapse:
        prop = response_synapse["Prop"]
        if "conf" in prop:
            conf = float(prop["conf"])  
            return conf >= spec_conf
    return True

def synapse_radius(spec):
    if "radius" in spec:
        return spec["radius"]
    return 60

def fetch_synapses(json_synapses):
    if not "source" in json_synapses:
        return
    source = json_synapses["source"]
    if not source.startswith("http"):
        return
    output_dir = ensure_dir(input_json_dir, "neuVidSynapseMeshes")
    for (group_name, group_spec) in json_synapses.items():
        if isinstance(group_spec, dict):
            positions = []
            if "neurons" in group_spec:
                neuron_ids = group_spec["neurons"]
                for id in neuron_ids:
                    url = f"{source}/label/{id}"

                    print(f"Fetching synapses from {url}")

                    response = requests.get(url)
                    response.raise_for_status()
                    for synapse in response.json():
                        if "Pos" in synapse:
                            pos = synapse["Pos"]
                            if synapse_type_matches(synapse, group_spec):
                                if synapse_confidence_matches(synapse, group_spec):
                                    positions.append(pos)

                radius = synapse_radius(group_spec)
                output_path = os.path.join(output_dir, group_name) + ".obj"
                try:
                    print("Writing {} ...".format(output_path))
                    with open(output_path, "w") as f:
                        for i in range(len(positions)):
                            f.write(icosohedron(positions[i], radius, i))
                    print("Done")
                except OSError as e:
                    print("Error: writing synapses '{}' failed: {}\n".format(group_name, str(e)))

#

if __name__ == "__main__":
    time_start = datetime.datetime.now()

    parser = argparse.ArgumentParser()
    parser.add_argument("--inputJson", "-ij", "-i", dest="input_json_file", help="path to the JSON file describing the input")
    parser.set_defaults(decim_fraction=0.5)
    parser.add_argument("--decim", "-d", type=float, dest="decim_fraction", help="mesh decimation fraction")
    parser.set_defaults(lod=3)
    parser.add_argument("--lod", "-l", type=int, dest="lod", help="mesh LOD (level of detail), 1 is highest resolution")
    parser.set_defaults(force=False)
    parser.add_argument("--force", "-fo", dest="force", action="store_true", help="force downloading of already-present OBJs")
    args = parser.parse_args()

    print(f"Using input file: {args.input_json_file}")
    print(f"Using decimation fraction: {args.decim_fraction}")

    input_json_dir = os.path.dirname(os.path.realpath(args.input_json_file))
    json_data = json.loads(removeComments(args.input_json_file))
    if json_data == None:
        print(f"Loading JSON file {args.input_json_file} failed")
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
                source = neuron_sources[i]

                if is_ng_source(source):
                    if len(neuron_sources) == 1:
                        print(f"Fetching {len(neuron_ids[i])} neuron meshes from source {source}")
                    else:
                        print(f"Fetching {len(neuron_ids[i])} neuron meshes for source index {i}: {source}")

                    mesh_info = get_mesh_info(source)
                    if is_cloudvolume_accessible(mesh_info):
                        fetch_with_cloudvolume(source, neuron_ids[i], args.decim_fraction, input_json_dir, args.force)
                    else:
                        fetch_directly(source, mesh_info, neuron_ids[i], args.lod, args.decim_fraction, input_json_dir, args.force)

    if "synapses" in json_data:
        json_synapses = json_data["synapses"]
        fetch_synapses(json_synapses)


    time_end = datetime.datetime.now()
    print()
    print("Fetching started at {}".format(time_start))
    print("Fetching ended at {}".format(time_end))
