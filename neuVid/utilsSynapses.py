import os
import requests
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsMeshesBasic import icosohedron

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

def download_synapses(source, synapse_set_spec, output_path):
    if isinstance(synapse_set_spec, dict):
        positions = []
        if "neurons" in synapse_set_spec:
            neuron_ids = synapse_set_spec["neurons"]
            for id in neuron_ids:
                # TODO: The following works for a DVID source.  Support more general sources per this spec:
                # https://github.com/google/neuroglancer/blob/master/src/neuroglancer/datasource/precomputed/annotations.md

                url = f"{source}/label/{id}"
                print(f"Fetching synapses from {url}")

                response = requests.get(url)
                response.raise_for_status()
                for synapse in response.json():
                    if "Pos" in synapse:
                        pos = synapse["Pos"]
                        if synapse_type_matches(synapse, synapse_set_spec):
                            if synapse_confidence_matches(synapse, synapse_set_spec):
                                positions.append(pos)

            radius = synapse_radius(synapse_set_spec)
            try:
                print("Writing {} ...".format(output_path))
                with open(output_path, "w") as f:
                    for i in range(len(positions)):
                        f.write(icosohedron(positions[i], radius, i))
                print("Done")
            except OSError as e:
                print("Error: writing synapses to '{}' failed: {}\n".format(output_path, str(e)))
