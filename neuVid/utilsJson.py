# Utility functions related to JSON and parsing.

def encode_id(id, source_index):
    return "{}_{}".format(id, source_index)

def decode_id(id):
    return id.split("_")[0]

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
        # A key for a group name has a value that is just a list of body IDs.
        # E.g., "step4" here:
        # "neurons" : { "source" : "./meshesDir", "step4" : [ 819828986, 5813050767, 1169898618 ] }
        value = jsonNeurons[key]
        if isinstance(value, list) and all(map(lambda x: isinstance(x, int), value)):
            jsonList = value
            groupToNeuronIds[key] = []
            iMeshesPath = 0
            groupToMeshesSourceIndex[key] = iMeshesPath

            for id in jsonList:
                if isinstance(id, int):
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
                            with open(idsFile) as f:
                                i = 0
                                for line in f:
                                    id = line[0:-1]
                                    id = encode_id(id, iMeshesPath)
                                    neuronIds[iMeshesPath].add(id)
                                    groupToNeuronIds[key].append(id)

                                    i += 1
                                    if i == limit:
                                        break
                        except Exception as e:
                            print("Error: cannot read neuron IDs file '{}': '{}'".format(idsFile, str(e)))

    if "source" in jsonNeurons:
        value = jsonNeurons["source"]
        if isinstance(value, list):
            while len(neuronIds) <= len(value):
                neuronIds.append(set())

    # Sort `neuronIds` to improve the peformance when importing large numbers (Blender 3.3+):
    # https://developer.blender.org/D15506
    # Match: `int BLI_strcasecmp(const char *s1, const char *s2)`
    neuronIdsSorted = []
    for ids in neuronIds:
        neuronIdsSorted.append(sorted(ids))
    return neuronIdsSorted, groupToNeuronIds, groupToMeshesSourceIndex, useSeparateNeuronFiles

def parseRoiNames(jsonRois):
    roiNames = [set()]
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
                if isinstance(x, str):
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
                while len(roiNames) <= iMeshesPath:
                    roiNames.append(set())
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

