# Builds OBJ mesh files for synapse sets in the JSON file.
# Must be run before importMeshes.py when synapse sets are present.

# Depends on neuprint-python, which is most easily installed using Miniconda.
# After installing Miniconda, create an enviroment (if necessary) and install
# neuprint-python:
# $ conda create --name neuVid-example
# $ conda activate neuVid-example
# Make sure flyem-forge is in your ~/.condarc, which could look like this:
#  channels:
#  - flyem-forge
#  - conda-forge
#  - defaults
# $ conda install neuprint-python

# Unfortunately, Blender comes with its own version of Python, so it is not
# easy or reliably to use Conda packages from within Blender.  Hence, the
# functionality in this script cannot easily be invoked from within
# importMeshes.py, even after the Conda environment is activated.
# So run it manually:
# $ python buildSynapses.py -ij example.json


import argparse
import json
import neuprint
import os
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsJson import removeComments
from utilsMeshesBasic import icosohedron

parser = argparse.ArgumentParser()
parser.add_argument("--inputJson", "-ij", dest="inputJsonFile", help="path to the JSON file describing the input")
args = parser.parse_args()

def matchingKey(key, json):
    # Make our "xmin" match json "xmin", "xMin", "x-min", "minX", "minx", "min-x", etc.
    for jsonKey in json:
        jsonKey1 = jsonKey.replace("-", "").lower()
        if key == jsonKey1 or key[1:] + key[0] == jsonKey1:
            return jsonKey
    return None

if args.inputJsonFile == None:
    parser.print_help()
    quit()

inputJsonDir = os.path.dirname(os.path.realpath(args.inputJsonFile))

jsonData = json.loads(removeComments(args.inputJsonFile))

if jsonData == None:
    print("Loading JSON file {} failed\n".format(args.inputJsonFile))
    quit()

if not "synapses" in jsonData:
    print("JSON contains no 'synapses' key, whose value is synapse sets to load")
    quit()
jsonSynapses = jsonData["synapses"]

if not "source" in jsonSynapses:
    print("JSON 'synapses' contains no 'source' key")
    quit()
synapseSource = jsonSynapses["source"]
if synapseSource.startswith("http"):
    i1 = synapseSource.find("://")
    i2 = synapseSource.find("/?dataset=")
    if i2 == -1:
        server = synapseSource[i1:]
        dataset = None
    else:
        server = synapseSource[i1 + len("://"):i2]
        dataset = synapseSource[i2 + len("/?dataset="):]
        dataset = dataset.replace("%3A", ":")

    client = neuprint.Client(server, dataset=dataset)
    client.fetch_version()

    for synapseSetName, synapseSetSpec in jsonSynapses.items():
        if synapseSetName == "source":
            continue

        if "neuron" in synapseSetSpec:
            body = synapseSetSpec["neuron"]
        elif "neurons" in synapseSetSpec:
            bodies = synapseSetSpec["neurons"]
            if len(bodies) > 1:
                print("Using only the first body from 'neurons' list {}".format(bodies))
            body = bodies[0]
        else:
            print("Error: synapse set '{}' is missing 'neuron'\n".format(synapseSetName))
            continue

        if not "type" in synapseSetSpec:
            print("Error: synapse set '{}' is missing 'type'\n".format(synapseSetName))
            continue
        type = synapseSetSpec["type"]

        roi = None
        if "roi" in synapseSetSpec:
            roi = synapseSetSpec["roi"]
            roi1 = roi.split()
            # TODO: add support for grouping parantheses to the support for boolean operators.
            roi2 = ["exists(s.`{}`)".format(x) if x.lower() not in ["and", "or", "not"] \
                    else x.upper() for x in roi1]
            roi3 = " ".join(roi2)
            roi = "({})".format(roi3)

        radius = 40
        if "radius" in synapseSetSpec:
            radius = synapseSetSpec["radius"]
            if radius < 0:
                print("Skipping synapse set '{}' with negative radius {}".format(synapseSetName, radius))
                continue

        weight = 1
        if "weight" in synapseSetSpec:
            weight = synapseSetSpec["weight"]
            if weight < 0:
                print("Skipping synapse set '{}' with negative weight {}".format(synapseSetName, weight))
                continue

        boxToIncludeKeys = [["xmin", "ymin", "zmin"], ["xmax", "ymax", "zmax"]]
        limit = sys.float_info.max
        boxToInclude = [[-limit, -limit, -limit], [limit, limit, limit]]
        if "includeWithin" in synapseSetSpec:
            includeWithin = synapseSetSpec["includeWithin"]
            for i in range(len(boxToInclude)):
                for j in range(len(boxToInclude[i])):
                    jsonKey = matchingKey(boxToIncludeKeys[i][j], includeWithin)
                    if jsonKey:
                        x = includeWithin[jsonKey]
                        boxToInclude[i][j] = int(x)

        partner = None
        query = None
        if "partner" in synapseSetSpec:
            partner = synapseSetSpec["partner"]

            if "weight" in synapseSetSpec:
                print("Note: synapse set '{}' weight {} ignored".format(synapseSetName, weight))

            # Neo4j Cypher queries for neuprint-python.

            if type == "pre":
                query = "MATCH (a:Neuron{{bodyId:{}}})-[:Contains]->(ss:SynapseSet)-[:ConnectsTo]->(:SynapseSet)<-[:Contains]-(b{{bodyId:{}}}) " \
                        "WITH ss " \
                        "MATCH (ss)-[:Contains]->(s:Synapse) " \
                        "WHERE s.type = \"{}\" " \
                        "RETURN s.location.x, s.location.y, s.location.z\n".format(body, partner, type)
            elif type == "post":
                query = "MATCH (a:Neuron{{bodyId:{}}})-[:Contains]->(:SynapseSet)-[:ConnectsTo]->(ss:SynapseSet)<-[:Contains]-(b{{bodyId:{}}}) " \
                        "WITH ss " \
                        "MATCH (ss)-[:Contains]->(s:Synapse) " \
                        "WHERE s.type = \"{}\" " \
                        "RETURN s.location.x, s.location.y, s.location.z\n".format(partner, body, type)
            else:
                print("Error: synapse set '{}' unkown 'type' {}\n".format(synapseSetName, type))
            if roi:
                query = query.replace("RETURN", "AND {} RETURN".format(roi))

        else:
            if "weight" not in synapseSetSpec:
                print("Synapse set '{}' default weight {}".format(synapseSetName, weight))

            if type == "pre":
                query = "MATCH (a:Neuron{{bodyId:{}}})-[:Contains]->(ss:SynapseSet)-[:ConnectsTo]->(SynapseSet)<-[:Contains]-(b) " \
                        "WITH ss, b " \
                        "MATCH (ss)-[:Contains]->(s:Synapse) " \
                        "WHERE s.type = \"{}\" " \
                        "WITH b, count(s) as cnt, collect([s.location.x, s.location.y, s.location.z]) AS ses " \
                        "WHERE cnt >= {} " \
                        "UNWIND ses AS sesu " \
                        "RETURN sesu[0], sesu[1], sesu[2]\n".format(body, type, weight)
                if roi:
                    query = query.replace("WITH b", "AND {} WITH b".format(roi))
            elif type == "post":
                query = "MATCH (a)-[:Contains]->(SynapseSet)-[:ConnectsTo]->(ss:SynapseSet)<-[:Contains]-(b:Neuron{{bodyId:{}}}) " \
                        "WITH ss, a " \
                        "MATCH (ss)-[:Contains]->(s:Synapse) " \
                        "WHERE s.type = \"{}\" " \
                        "WITH a, count(s) as cnt, collect([s.location.x, s.location.y, s.location.z]) AS ses " \
                        "WHERE cnt >= {} " \
                        "UNWIND ses AS sesu " \
                        "RETURN sesu[0], sesu[1], sesu[2]\n".format(body, type, weight)
                if roi:
                    query = query.replace("WITH a", "AND {} WITH a".format(roi))
            else:
                print("Error: synapse set '{}' unkown 'type' {}\n".format(synapseSetName, type))

        if query:
            print("Querying '{}'...".format(synapseSetName))
            results = client.fetch_custom(query)
            print("Done, with {} value(s)".format(len(results.values)))
            positions = []
            numFiltered = 0
            for x in results.values:
                include = True
                for j in range(len(boxToInclude[0])):
                    if x[j] < boxToInclude[0][j] or boxToInclude[1][j] < x[j]:
                        include = False
                        numFiltered += 1
                        break
                if include:
                    positions.append((x[0], x[1], x[2]))
            print("Then filtered out {} value(s)".format(numFiltered))

            dirName = "neuVidSynapseMeshes/"
            downloadDir = inputJsonDir
            if downloadDir[-1] != "/":
                downloadDir += "/"
            downloadDir += dirName

            try:
                if not os.path.exists(downloadDir):
                    os.mkdir(downloadDir)
                fileName = downloadDir + synapseSetName + ".obj"
                print("Writing {} ...".format(fileName))
                with open(fileName, "w") as f:
                    for i in range(len(positions)):
                        f.write(icosohedron(positions[i], radius, i))
                print("Done")
            except OSError as e:
                print("Error: writing synapses '{}' failed: {}\n".format(synapseSetName, str(e)))
