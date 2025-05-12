# $ conda create --name neuvid
# $ conda activate neuvid
# $ conda install h5py requests
# $ python fetchVvd.py -i example.json
# $ python animateVvd -i example.json
# $ VVDViewer example.vrp
# In VVDViewer's "Record/Export" panel, change to the "Advanced" tab.
# Close other VVDViewer panels to make the 3D view bigger.
# Press the "Save..." button to save the video (with the size of the 3D view).

# Avoid playing the animation (with the play button on the "Advanced" tab, as opposed to the
# "Save..." button) because doing so, then rewinding and pressing "Save..." may produce
# glitches in the saved video.

import argparse
import json
import os
import re
import requests
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsGeneral import report_version
from utilsJson import formatted

def remove_comments(file):
    output = ""
    with open(file) as f:
        for line in f:
            line_stripped = line.lstrip()
            if line_stripped.startswith("#") or line_stripped.startswith("//"):
                # Replace a comment line with a blank line, so the line count stays the same
                # in error messages.
                output += "\n"
            else:
                output += line
    return output

def parse_json(json_input_file):
    try:
        json_data = json.loads(remove_comments(json_input_file))
        return json_data
    except json.JSONDecodeError as exc:
        print("Error reading JSON, line {}, column {}: {}".format(exc.lineno, exc.colno, exc.msg))
        # TODO: guess_extraneous_comma(json_input_file)
        sys.exit()

def fetch_s3_bucket_prefixes(source):
    url = "{}?delimiter=/".format(source)
    try:
        response = requests.get(url)
        response.raise_for_status()
        r = re.compile("<Prefix>[^<>]*/</Prefix>")
        prefixes_raw = r.findall(response.text)
        prefixes = [prefix[len("<Prefix>"):-len("/</Prefix>")] for prefix in prefixes_raw]
        return prefixes
    except requests.exceptions.RequestException as e:
        print("Error fetching S3 bucket prefixes {}: {}".format(url, str(e)))
        sys.exit()

def fetch_s3_bucket_keys(source, release, name):
    # Don't replace spaces with "+".
    url = "{}?prefix={}/{}/&delimiter=/".format(source, release, name)
    try:
        response = requests.get(url)
        response.raise_for_status()
        r = re.compile("<Key>[^<>]*h5j</Key>")
        keys_raw = r.findall(response.text)
        keys = [key[len("<Key>"):-len("</Key>")] for key in keys_raw]
        keys.sort()
        return keys
    except requests.exceptions.RequestException as e:
        print("Error fetching S3 bucket keys {}: {}".format(url, str(e)))
        sys.exit()

def find_in_keys(pattern_elements, keys):
    pattern = ".*({}).*({}).*({}).*(aligned).*".format(pattern_elements["line"], pattern_elements["region"], pattern_elements["sex"])
    pattern = pattern.lower()
    r = re.compile(pattern)
    for key in keys:
        if r.match(key.lower()):
            return key
    return None

# Formats to support:
# Using default channel:
# "volumes": {
#   "a": "a.h5j",
#   "b": {"line": "b"},
#   "c": {"line": "c", "sex": "male"}
# }
# Using channel a specific channel (e.g., 2):
# "volumes": {
#   "a": ["a.h5j", 2]
#   "b": [{"line": "b"}, 2],
#   "c": [{"line": "c", "sex": "male"}, 2]
# }
def fetch_volumes(json_data, output, debug=False):
    if not "volumes" in json_data:
        return {}
    json_volumes = json_data["volumes"]
    for val in json_volumes.values():
        # Don't fetch if any of the values are fetched already.
        if type(val) == str and val.endswith(".h5j"):
            return {}
        
    if not "source" in json_volumes:
        return {}
    json_source = json_volumes["source"]

    if debug:
        print(f"Fetching volumes: source {json_source}")

    if json_source.startswith("https://s3.amazonaws.com"):
        result = {}

        prefixes = fetch_s3_bucket_prefixes(json_source)

        if debug:
            print(f"Fetching volumes: AWS bucket prefixes {prefixes}")

        dir = os.path.dirname(output)
        vols_path = os.path.join(dir, "neuVidVolumes")
        if not os.path.exists(vols_path):
            os.mkdir(vols_path)
        # Even on Windows, forward slashes work better as path separators for
        # paths to be stored as JSON strings.
        vols_path_output = "./neuVidVolumes"

        for key, val in json_volumes.items():
            if key == "source":
                result[key] = vols_path_output
                continue

            if debug:
                print(f"Fetching volumes: {val}")

            if type(val) == list:
                val = val[0]
            if type(val) != dict:
                continue
            if not "line" in val:
                print("Invalid volume spec '{}: {}': missing 'line'".format(key, val))
                sys.exit()
            line = val["line"]
            if not "region" in val:
                val["region"] = "brain|central"
            if not "sex" in val:
                val["sex"] = "unisex"

            candidate_keys = []
            for release in prefixes:
                keys = fetch_s3_bucket_keys(json_source, release, line)
                if len(keys) > 0:
                    print("Preparing to check {} in release '{}'".format(val, release))
                    candidate_keys.append(keys)

            if debug:
                print(f"Fetching volumes: candidate keys {candidate_keys}")

            vol_name = None
            for keys in candidate_keys:
                vol_name = find_in_keys(val, keys)
                if vol_name:
                    break
            if vol_name == None:
                print("Cannot find volume matching '{}' at source '{}'".format(str(val), json_source))
                print("Choices:")
                for key in keys:
                    print(key)
                sys.exit()

            vol_name = vol_name.replace(" ", "+")
            url = json_source + "/" + vol_name
            print("Fetching {}.".format(url))
            try:
                response = requests.get(url)
                response.raise_for_status()
                filename = vol_name.replace("/", "-")
                vol_path = os.path.join(vols_path, filename)
                print("Writing {}".format(vol_path))
                with open(vol_path, "wb") as f:
                    f.write(response.content)
                result[key] = filename
            except requests.exceptions.RequestException as e:
                print("Error fetching volume {}: {}".format(url, str(e)))
    
        return result
    return {}

def fetch_meshes(json_data, output):
    if not "meshes" in json_data:
        return {}
    json_meshes = json_data["meshes"]

    if not "source" in json_meshes:
        return {}
    json_source = json_meshes["source"]
    if json_source.startswith("https://s3.amazonaws.com"):
        result = {}

        dir = os.path.dirname(output)
        meshes_path = os.path.join(dir, "neuVidMeshes")
        if not os.path.exists(meshes_path):
            os.mkdir(meshes_path)
        # Even on Windows, forward slashes work better as path separators for
        # paths to be stored as JSON strings.
        meshes_path_output = "./neuVidMeshes"

        for key, val in json_meshes.items():
            if key == "source":
                result[key] = meshes_path_output
                continue

            if type(val) == list:
                ids = []
                for id in val:
                    filename = f"{id}.swc"
                    url = f"{json_source}/{filename}"
                    print("Fetching {}.".format(url))
                    try:
                        response = requests.get(url)
                        response.raise_for_status()
                        vol_path = os.path.join(meshes_path, filename)
                        print("Writing {}".format(vol_path))
                        with open(vol_path, "wb") as f:
                            f.write(response.content)
                        ids.append(id)
                    except requests.exceptions.RequestException as e:
                        print("Error fetching mesh {}: {}".format(url, str(e)))
                result[key] = ids

        return result
    return {}

def update_input(input, volume_updates):
    updated_lines = []
    with open(input, "r") as f:
        lines = f.readlines()
        in_volumes = False
        in_meshes = False
        for line in lines:
            updated_line = line.rstrip()
            if "volumes" in line:
                in_volumes = True
                in_meshes = False
            elif "meshes" in line:
                in_volumes = False
                in_meshes = True
            elif in_volumes:
                for key, val in volume_updates.items():
                    if line.strip().startswith(f"\"{key}\""):
                        splits = line.split(":")
                        updated_line = f"{splits[0]} : \"{val}\""
            elif in_meshes:
                if line.strip().startswith("\"source\""):
                    splits = line.split(":")
                    updated_line = f"{splits[0]} : \"./neuVidMeshes\""
            updated_lines.append(updated_line)
    return "\n".join(updated_lines)

if __name__ == "__main__":
    report_version()
    
    parser = argparse.ArgumentParser()
    parser.set_defaults(input="")
    parser.add_argument("--input", "-i", dest="input", help="path to input (H5J file directory, or JSON file")
    parser.add_argument("--output", "-o", dest="output", help="path to output VVDViewer project file (.vrp)")
    args = parser.parse_args()

    output = args.output
    if not output:
        print("Updating {} in place".format(args.input))
        output = args.input

    json_data = parse_json(args.input)
    volume_updates = fetch_volumes(json_data, output)
    fetch_meshes(json_data, output)
    updated = update_input(args.input, volume_updates)

    with open(output, "w") as f:
        f.write(updated)
