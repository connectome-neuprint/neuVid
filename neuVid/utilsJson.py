# Utility functions related to JSON and parsing.

import json
import math

def guess_extraneous_comma(json_input_file):
    i = 1
    found_comma = False
    line_with_comma = ""
    line_number_with_comma = 0
    with open(json_input_file, "r") as f:
        for line in f:
            line_stripped = line.lstrip()
            if line_stripped.startswith("#") or line_stripped.startswith("//"):
                i +=1
                continue
            for c in line:
                if found_comma and (c == "]" or c == "}"):
                    print("Possible extraneous comma in line {}:\n{}".format(line_number_with_comma, line_with_comma))
                    return
                elif c == ",":
                    found_comma = True
                    line_with_comma = line
                    line_number_with_comma = i
                elif c != " " and c != "\t" and c != "\n":
                    found_comma = False
                    line_with_comma = ""
                    line_number_with_comma = 0
            i += 1

def parseFov(jsonData, width, height):
    fovx = None
    fovy = None
    for key, value in jsonData.items():
        if key.lower().startswith("fovhoriz"):
            fovx = math.radians(value)
            fovy = 2 * math.atan((0.5 * height) / (0.5 * width / math.tan(0.5 * fovx)))
        if key.lower().startswith("fovvert"):
            fovy = math.radians(value)
            fovx = 2 * math.atan((0.5 * width) / (0.5 * height / math.tan(0.5 * fovy)))
    if fovx:
        fovx = math.degrees(fovx)
    if fovy:
        fovy = math.degrees(fovy)
    return fovx, fovy

def encode_id(id, source_index):
    return "{}_{}".format(id, source_index)

def decode_id(id):
    if type(id) == str and "_" in id:
        return id.split("_")[0]
    return id

def get_ids_from_file(path):
    with open(path, "r") as f:
        ids0 = f.read()
    ids1 = ids0.replace("\n", " ")
    ids2 = ids1.replace(",", " ")
    return ids2.split()

def parseNeuronsIds(jsonNeurons, limit=0):
    # neuronIds[i] is the set of neuron IDs for source i.
    neuronIds = [set()]
    # The mapping from group name to neuron IDs in that group does not need to be
    # split up by source, as each group can have only one source.
    groupToNeuronIds = {}
    # The mapping from group name to the index in the array of directories
    # for mesh files; using an array supports mutiples source for meshes.
    groupToMeshesSourceIndex = {}

    # True indicates that each group's body IDs are not only loaded from separate files,
    # but that each group should have its own .blend file, to be loaded only when that
    # groups is visible and being rendered, to support bigger sets of neurons.
    useSeparateNeuronFiles = False

    # Needed only for the case of entries that are dictionaries.
    idsPath = "./"
    if "idsSource" in jsonNeurons:
        idsPath = jsonNeurons["idsSource"]
        if idsPath[-1] != "/":
            idsPath += "/"

    for key in jsonNeurons.keys():
        if key == "source" or key == "idsSource":
            continue
        value = jsonNeurons[key]

        # A key for a group name has a value that is just a list of body IDs.
        # E.g., "step4" here:
        # "neurons" : { "source" : "./meshesDir", "step4" : [ 819828986, 5813050767, 1169898618 ] }
        if isinstance(value, list):
            jsonList = value
            groupToNeuronIds[key] = []
            iMeshesPath = 0
            groupToMeshesSourceIndex[key] = iMeshesPath

            for id in jsonList:
                neuronIds[iMeshesPath].add(str(id))
                groupToNeuronIds[key].append(str(id))

        # A key for a group name has a value that is a dictionary, with information
        # about how to load the body IDs from a file.
        # E.g., "LALEtc" here:
        # "neurons" : { "source" : [ "./meshesDirRes0", "./meshesDirRes1" ],
        #               "idsSource" : "./bodyIDsDir",
        #               "LALEtc" : { "ids" : [ "LAL", "CRE" ], "sourceIndex" : 1 } }
        elif isinstance(value, dict):
            # Check whether the JSON indicates that each group should have its own
            # .blend file.
            if "separate" in jsonNeurons and jsonNeurons["separate"]:
                useSeparateNeuronFiles = True

            jsonDict = value
            groupToNeuronIds[key] = []
            iMeshesPath = 0
            if "sourceIndex" in jsonDict:
                iMeshesPath = jsonDict["sourceIndex"]
                while len(neuronIds) <= iMeshesPath:
                    neuronIds.append(set())
            groupToMeshesSourceIndex[key] = iMeshesPath

            if "ids" in jsonDict:
                idsItemList = jsonDict["ids"]
                if isinstance(idsItemList, str):
                    idsItemList = [idsItemList]
                for idsItem in idsItemList:
                    if isinstance(idsItem, int):
                        id = encode_id(idsItem, iMeshesPath)
                        neuronIds[iMeshesPath].add(id)
                        groupToNeuronIds[key].append(id)
                    else:
                        idsFile = idsPath + idsItem
                        try:
                            ids = get_ids_from_file(idsFile)
                            i = 0
                            for id in ids:
                                id = encode_id(id, iMeshesPath)
                                neuronIds[iMeshesPath].add(id)
                                groupToNeuronIds[key].append(id)

                                i += 1
                                if i == limit:
                                    break
                        except Exception as e:
                            print("Error: cannot read neuron IDs file '{}': '{}'".format(idsFile, str(e)))

    # Sort `neuronIds` to improve the peformance when importing large numbers (Blender 3.3+):
    # https://developer.blender.org/D15506
    # Match: `int BLI_strcasecmp(const char *s1, const char *s2)`
    neuronIdsSorted = []
    for ids in neuronIds:
        neuronIdsSorted.append(sorted(ids))
    return neuronIdsSorted, groupToNeuronIds, groupToMeshesSourceIndex, useSeparateNeuronFiles

def parseRoiNames(jsonRois):
    n = 1
    if "source" in jsonRois:
        sources = jsonRois["source"]
        if isinstance(sources, list):
            n = len(sources)
    roiNames = [set() for i in range(n)]

    groupToRoiNames = {}
    # The mapping from group name to the index in the array of directories
    # for mesh files; using an array supports mutiple mesh sources.
    groupToMeshesSourceIndex = {}

    for key in jsonRois.keys():
        if key == "source":
            continue
        value = jsonRois[key]
        if isinstance(value, list):
            jsonList = value
            groupToRoiNames[key] = []
            iMeshesPath = 0
            groupToMeshesSourceIndex[key] = iMeshesPath

            for x in jsonList:
                roiNames[iMeshesPath].add(x)
                groupToRoiNames[key].append(x)

        # A key for a group name has a value that is a dictionary.
        # E.g., "nerveRois" here:
        # "rois" : { "source" : [ "./meshesDirRois", "./meshesDirNerveRois" ],
        #            "nerveRois" : { "ids" : [ "n1", "n2" ], "sourceIndex" : 1 } }
        elif isinstance(value, dict):
            jsonDict = value
            groupToRoiNames[key] = []
            iMeshesPath = 0
            if "sourceIndex" in jsonDict:
                iMeshesPath = jsonDict["sourceIndex"]
            groupToMeshesSourceIndex[key] = iMeshesPath

            if "ids" in jsonDict:
                idsItemList = jsonDict["ids"]
                for idsItem in idsItemList:
                    if isinstance(idsItem, str):
                        roiNames[iMeshesPath].add(idsItem)
                        groupToRoiNames[key].append(idsItem)

    return roiNames, groupToRoiNames, groupToMeshesSourceIndex

def parseSynapsesSetNames(jsonSynapses):
    groupToSynapseSetNames = {}
    for key in jsonSynapses.keys():
        if isinstance(jsonSynapses[key], dict):
            groupToSynapseSetNames[key] = [key]
        elif isinstance(jsonSynapses[key], list):
            # TODO: Support lists of synapseSets, analogous to keys in
            # "neurons" supporting lists of body IDs.
            pass
    return groupToSynapseSetNames

def removeComments(file):
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

def fix_end(line):
    if line.endswith(",\n"):
        return line[:-2] + "\n"
    return line

def formatted(json_data):
    result_str = "{\n"

    indent = "  "
    for (key0, val0) in json_data.items():
        if isinstance(val0, dict):
            result_str += indent + "{}: {{\n".format(json.dumps(key0))
            indent += "  "

            for (key1, val1) in val0.items():
                result_str += indent + "{}: {},\n".format(json.dumps(key1), json.dumps(val1))

            indent = indent[:-2]
            result_str = fix_end(result_str)
            result_str += indent + "},\n"
        elif isinstance(val0, list):
            result_str += indent + "{}: [\n".format(json.dumps(key0))
            indent += "  "

            for item in val0:
                result_str += indent + json.dumps(item) + ",\n"

            indent = indent[:-2]
            result_str = fix_end(result_str)
            result_str += indent + "],\n"
        else:
            result_str += indent + "{}: {},\n".format(json.dumps(key0), json.dumps(val0))

    result_str = result_str = fix_end(result_str)
    result_str += "}\n"
    return result_str
