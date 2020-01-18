# Utility functions related to JSON and parsing.

def parseNeuronsIds(jsonNeurons, limit=0):
    # neuronIds[i] is the set of neuron IDs for resolution i.
    neuronIds = [set()]
    # The mapping from group name to neuron IDs in that group does not need to be
    # split up by resolution, as each group can have only one resolution.
    groupToNeuronIds = {}
    # The mapping from group name to the index in the array of directories
    # for mesh files; using an array supports mutiples resolutions of meshes.
    groupToMeshesSourceIndex = {}

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
        # "neurons" : { "path-meshes" : "./meshesDir", "step4" : [ 819828986, 5813050767, 1169898618 ] }
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
        # "neurons" : { "path-meshes" : [ "./meshesDirRes0", "./meshesDirRes1" ],
        #               "idsSource" : "./bodyIDsDir",
        #               "LALEtc" : { "ids" : [ "LAL", "CRE" ], "sourceIndex" : 1 } }
        elif isinstance(value, dict):
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
                idsFileNameList = jsonDict["ids"]
                if isinstance(idsFileNameList, str):
                    idsFileNameList = [idsFileNameList]
                for idsFileName in idsFileNameList:
                    idsFile = idsPath + idsFileName
                    try:
                        with open(idsFile) as f:
                            i = 0
                            for line in f:
                                id = line[0:-1]
                                neuronIds[iMeshesPath].add(str(id))
                                groupToNeuronIds[key].append(str(id))
                                i += 1
                                if i == limit:
                                    break
                    except Exception as e:
                        print("Error: cannot read neuron IDs file '{}': '{}'".format(idsFile, str(e)))

    return neuronIds, groupToNeuronIds, groupToMeshesSourceIndex, useSeparateNeuronFiles

def parseRoiNames(jsonRois):
    roiNames = set()
    groupToRoiNames = {}

    for key in jsonRois.keys():
        if isinstance(jsonRois[key], list):
            jsonList = jsonRois[key]
            groupToRoiNames[key] = []

            for x in jsonList:
                if isinstance(x, str):
                    roiNames.add(x)
                    groupToRoiNames[key].append(x)

    return roiNames, groupToRoiNames

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
            if not (line.startswith("#") or line.startswith("//")):
                output += line
    return output
