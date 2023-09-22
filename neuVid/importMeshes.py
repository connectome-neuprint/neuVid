# Imports meshes to set up the basic Blender file.
# Animation is added in the next step, with another script, which runs more quickly for
# iteration on the details of the animation.

# Run in Blender, e.g.:
# blender --background --python importMeshes.py -- -ij movieScript.json -o movieWithoutAnimation.blend
# Assumes Blender 2.79.

import argparse
import bpy
import datetime
import json
import math
import mathutils
import os
import sys

timeStart = datetime.datetime.now()

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsColors import colors, getColor, shuffledColorsForSmallDataSets
from utilsGeneral import newObject, report_version
from utilsJson import decode_id, guess_extraneous_comma, parseNeuronsIds, parseRoiNames, removeComments
from utilsMaterials import newBasicMaterial, newGlowingMaterial, newSilhouetteMaterial
from utilsMeshes import fileToImportForRoi, fileToImportForNeuron, fileToImportForSynapses

report_version()

argv = sys.argv
if "--" not in argv:
    argv = []
else:
    argv = argv[argv.index("--") + 1:]

parser = argparse.ArgumentParser()
parser.add_argument("--inputJson", "-ij", "-i", dest="inputJsonFile", help="path to the JSON file describing the input")
parser.add_argument("--output", "-o", dest="outputFile", help="path for the output .blend file")
# A limit of 0 means no limit.
parser.set_defaults(limit=0)
parser.add_argument("--limit", "-l", type=int, dest="limit", help="limit to the number of IDs from each separate neurons file")

args = parser.parse_args(argv)

if args.inputJsonFile == None:
    parser.print_help()
    quit()

outputFile = args.outputFile
if outputFile == None:
    outputFile = os.path.splitext(args.inputJsonFile)[0] + ".blend"
if not os.path.dirname(outputFile):
    outputFile = os.path.join(".", outputFile)
print("Using output Blender file: '{}'".format(outputFile))

inputJsonDir = os.path.dirname(os.path.realpath(args.inputJsonFile))

try:
    jsonData = json.loads(removeComments(args.inputJsonFile))
except json.JSONDecodeError as exc:
    print("Error reading JSON, line {}, column {}: {}".format(exc.lineno, exc.colno, exc.msg))
    guess_extraneous_comma(args.inputJsonFile)
    sys.exit()

if jsonData == None:
    print("Loading JSON file {} failed".format(args.inputJsonFile))
    quit()

#

def computeBbox(objs):
    limit = sys.float_info.max
    bboxMin = [ limit,  limit,  limit]
    bboxMax = [-limit, -limit, -limit]
    for obj in objs:
        if bpy.app.version < (2, 80, 0):
            verts = [(obj.matrix_world * vert.co).to_tuple() for vert in obj.data.vertices]
        else:
            verts = [(obj.matrix_world @ vert.co).to_tuple() for vert in obj.data.vertices]
        for vert in verts:
          for i in range(len(vert)):
              c = float(vert[i])
              bboxMin[i] = min(bboxMin[i], c)
              bboxMax[i] = max(bboxMax[i], c)

    bboxCenter = [(bboxMin[i] + bboxMax[i]) / 2 for i in range(3)]
    return (mathutils.Vector(bboxCenter), mathutils.Vector(bboxMin), mathutils.Vector(bboxMax))

def computeBsphere(objs, center):
    radius = 0
    c = mathutils.Vector(center)
    for obj in objs:
        if bpy.app.version < (2, 80, 0):
            verts = [obj.matrix_world * vert.co for vert in obj.data.vertices]
        else:
            verts = [obj.matrix_world @ vert.co for vert in obj.data.vertices]
        for vert in verts:
            radius = max((vert - c).length, radius)
    return radius

groupToBBox = {}
meshesSourceIndexToBBox = {}

#

print("Parsing neuron IDs...")

neuronSources = []
groupToNeuronIds = {}
useSeparateNeuronFiles = False

if "neurons" in jsonData:
    jsonNeurons = jsonData["neurons"]

    if "source" in jsonNeurons:
        source = jsonNeurons["source"]
        if isinstance(source, str):
            neuronSources = [source]
        else:
            neuronSources = source

    # If "useSeparateNeuronFiles" is set, it means the JSON specification does not list explicit
    # neuron body IDs, but instead lists files containing neuron body IDs.  It also means that
    # each of those files will generate a separate Blender file, and only one of these files will be
    # appended at a time, to manage complexity.

    neuronIds, groupToNeuronIds, groupToMeshesSourceIndex, useSeparateNeuronFiles = parseNeuronsIds(jsonNeurons, args.limit)

print("Done")
print("Using separate .blend files for neurons: {}".format(useSeparateNeuronFiles))

#

print("Assigning colors...")

neuronToColorIndex = {}

# When iterating through the neurons to assign consecutive colors,
# iterate first through the smaller groups of neurons that are visible at the
# same time, to reduce the chance that colors will be reused in these groups.

groupSizes = [[k, len(groupToNeuronIds[k])] for k in groupToNeuronIds.keys()]
# Sort on size, and if there is a tie sort on group name.
groupSizes.sort(key=lambda x: (x[1], x[0]))

# Add more contrast for very small data sets.
colors = shuffledColorsForSmallDataSets(groupToNeuronIds)

iColor = 0
for groupSize in groupSizes:
    groupNeuronIds = groupToNeuronIds[groupSize[0]]

    # Some neurons in this group may have colors already due to being in other groups.
    # So make a list of the colors not assigned to such neurons.  These not-assigned
    # colors are the colors to use first in this group, to minimize color reuse
    # within the group.
    usedColorIndices = set()
    for neuronId in groupNeuronIds:
        objName = "Neuron." + neuronId
        if objName in neuronToColorIndex:
            usedColorIndices.add(neuronToColorIndex[objName])
    colorIndicesToUseFirst = []
    if len(usedColorIndices) > 0:
        colorIndicesToUseFirst = [i for i in range(len(colors)) if not i in usedColorIndices]

    for neuronId in groupNeuronIds:
        objName = "Neuron." + neuronId
        if not objName in neuronToColorIndex:
            if len(colorIndicesToUseFirst) > 0:
                neuronToColorIndex[objName] = colorIndicesToUseFirst.pop()
            else:
                neuronToColorIndex[objName] = iColor
                iColor = (iColor + 1) % len(colors)

print("Done")

#

separateNeuronFiles = []
missingNeuronObjs = []
missingRoiObjs = []
missingSynapseSetObjs = []

for i in range(len(neuronSources)):
    if len(neuronSources) == 1:
        print("Importing {} neuron meshes".format(len(neuronIds[i])))
    else:
        print("Importing {} neuron meshes for index {} ({})".format(len(neuronIds[i]), i, neuronSources[i]))

    if useSeparateNeuronFiles or i == 0:
        for obj in bpy.data.objects:
            if obj.name != "Camera":
                matName = "Material." + obj.name
                if matName in bpy.data.materials:
                    mat = bpy.data.materials[matName]
                    bpy.data.materials.remove(mat, do_unlink=True)
                bpy.data.objects.remove(obj, do_unlink=True)

    j = 0
    for neuronId in neuronIds[i]:
        id = decode_id(neuronId)
        objPath = fileToImportForNeuron(neuronSources[i], id, inputJsonDir)

        timeNow = datetime.datetime.now()
        elapsedSecs = (timeNow - timeStart).total_seconds()
        print("{}: {} / {} ({:.2f} secs)".format(i, j, len(neuronIds[i]), elapsedSecs))
        j += 1

        if not os.path.isfile(objPath):
            print("Skipping missing file {}".format(objPath))
            missingNeuronObjs.append(neuronId)
            continue

        try:
            objs0 = bpy.data.objects.keys()

            # Follow the conventions of NeuTu/Neu3:
            # positive X points right, positive Y points out, positive Z points down.
            # Note that this is different from the convention in the first FlyEM movies:
            # positive X pointed down, positive Y pointed right, positive Z pointed out,
            # implemented with a call like the following:
            # bpy.ops.import_scene.obj(filepath=objPath, axis_up="Y", axis_forward="X")
            bpy.ops.import_scene.obj(filepath=objPath, axis_up="Z", axis_forward="Y")

            obj = bpy.context.selected_objects[0]
            obj.name = "Neuron." + neuronId

            print("Added object '{}'".format(obj.name))

            # Is there a bug in Blender that sometimes adds an extra object when importing?
            objs1 = bpy.data.objects.keys()
            extra = [o for o in objs1 if not o in objs0 and o != obj.name]
            for name in extra:
                o = bpy.data.objects[name]
                print("Removing extra object '{}'".format(o.name))
                bpy.data.objects.remove(o, do_unlink=True)

            matName = "Material." + obj.name
            color = getColor(neuronToColorIndex[obj.name], colors)
            mat = newBasicMaterial(matName, color)
            obj.data.materials.clear()
            obj.data.materials.append(mat)

            # Make the object appear transparent in the interactive viewport rendering.
            obj.show_transparent = True

            print("Added material '{}'".format(matName))

        except Exception as e:
            print("Error: cannot import '{}': '{}'".format(objPath, str(e)))

    if useSeparateNeuronFiles:
        j = outputFile.rfind(".")
        outputFile = outputFile[:j] + "_neurons_" + str(i) + outputFile[j:]
        separateNeuronFiles.append(outputFile)
        bpy.ops.wm.save_mainfile(filepath=outputFile)

    print("Done")

    if len(neuronSources) == 1:
        print("Computing bounding boxes for neuron meshes...")
    else:
        print("Computing bounding boxes for neuron meshes for index {}...".format(i))

    for groupName in groupToNeuronIds.keys():
        if groupToMeshesSourceIndex[groupName] == i:
            groupNeuronIds = groupToNeuronIds[groupName]
            objs = [bpy.data.objects["Neuron." + id] for id in groupNeuronIds]
            bboxCenter, bboxMin, bboxMax = computeBbox(objs)
            radius = computeBsphere(objs, bboxCenter)
            groupToBBox[groupName] = { "center" : bboxCenter, "min" : bboxMin, "max" : bboxMax, "radius" : radius }

    objs = [bpy.data.objects["Neuron." + id] for id in neuronIds[i]]
    bboxCenter, bboxMin, bboxMax = computeBbox(objs)
    radius = computeBsphere(objs, bboxCenter)
    meshesSourceIndexToBBox[i] = { "center" : bboxCenter, "min" : bboxMin, "max" : bboxMax, "radius" : radius }

    print("Done")

if useSeparateNeuronFiles:
    for obj in bpy.data.objects:
        if obj.name != "Camera":
            matName = "Material." + obj.name
            if matName in bpy.data.materials:
                mat = bpy.data.materials[matName]
                bpy.data.materials.remove(mat, do_unlink=True)
            bpy.data.objects.remove(obj, do_unlink=True)

#

roiExponents = {}
roiThresholds = {}

if "rois" in jsonData:
    jsonRois = jsonData["rois"]

    roiSources = ["."]
    if "source" in jsonRois:
        source = jsonRois["source"]
        if isinstance(source, str):
            roiSources = [source]
        else:
            roiSources = source

    roiNames, groupToRoiNames, groupToRoiMeshesSourceIndex = parseRoiNames(jsonRois)

    if "exponents" in jsonRois:
        groupToExponent = jsonRois["exponents"]

        # The exponent for the "*" key applies to all ROI groups that are not
        # mentioned by other keys.  So apply "*" first, then the others.
        if "*" in groupToExponent.keys():
            for groupName in groupToRoiNames.keys():
                for roiName in groupToRoiNames[groupName]:
                    roiExponents["Roi." + roiName] = groupToExponent["*"]

        for groupName in groupToExponent.keys():
            if groupName in groupToRoiNames:
                for roiName in groupToRoiNames[groupName]:
                    roiExponents["Roi." + roiName] = groupToExponent[groupName]

        if "thresholds" in jsonRois:
            groupToThreshold = jsonRois["thresholds"]

            # The threshold for the "*" key applies to all ROI groups that are not
            # mentioned by other keys.  So apply "*" first, then the others.
            if "*" in groupToThreshold.keys():
                for groupName in groupToRoiNames.keys():
                    for roiName in groupToRoiNames[groupName]:
                        roiThresholds["Roi." + roiName] = groupToThreshold["*"]

            for groupName in groupToThreshold.keys():
                if groupName in groupToRoiNames:
                    for roiName in groupToRoiNames[groupName]:
                        roiThresholds["Roi." + roiName] = groupToThreshold[groupName]

    for i in range(len(roiSources)):
        if len(roiSources) == 1:
            print("Importing {} ROI meshes".format(len(roiNames[i])))
        else:
            print("Importing {} ROI meshes for index {}".format(len(roiNames[i]), i))

        for roiName in roiNames[i]:
            objPath = fileToImportForRoi(roiSources[i], roiName, inputJsonDir)
            if not os.path.isfile(objPath):
                print("Skipping missing file {}".format(objPath))
                missingRoiObjs.append(roiName)
                continue

            try:
                # Follow the conventions of NeuTu/Neu3:
                # positive X points right, positive Y points out, positive Z points down.
                # Note that this is different from the convention in the first FlyEM movies:
                # positive X pointed down, positive Y pointed right, positive Z pointed out,
                # implemented with a call like the following:
                # bpy.ops.import_scene.obj(filepath=objPath, axis_up="Y", axis_forward="X")
                bpy.ops.import_scene.obj(filepath=objPath, axis_up="Z", axis_forward="Y")

                obj = bpy.context.selected_objects[0]
                obj.name = "Roi." + roiName

                print("Added object '{}'".format(obj.name))
            except Exception as e:
                print("Error: cannot import '{}': '{}'".format(objPath, str(e)))

#

print("Assigning ROI materials...")

rois = [o for o in bpy.data.objects.keys() if o.startswith("Roi.")]
for roi in rois:
    obj = bpy.data.objects[roi]
    matName = "Material." + obj.name

    exp = 5
    if roi in roiExponents:
        exp = roiExponents[roi]

    threshold = 100
    if roi in roiThresholds:
        threshold = roiThresholds[roi]

    mat = newSilhouetteMaterial(matName, exp, threshold)
    obj.data.materials.clear()
    obj.data.materials.append(mat)

    # Make that transparency appear in the interactive viewport rendering.
    obj.show_transparent = True
    
    # Prevent shadows from these objects in renderers like Cycles.
    if bpy.app.version >= (3, 0, 0):
        obj.visible_shadow = False
    elif bpy.app.version >= (2, 80, 0):
        obj.cycles_visibility.shadows = False

#

print("Importing synapse meshes...")

if "synapses" in jsonData:
    jsonSynapses = jsonData["synapses"]

    source = "."
    if "source" in jsonSynapses:
        source = jsonSynapses["source"]

    for synapseSetName, synapseSetSpec in jsonSynapses.items():
        if synapseSetName == "source":
            continue

        objPath = fileToImportForSynapses(source, synapseSetName, synapseSetSpec, inputJsonDir)
        if not os.path.isfile(objPath):
            print("Skipping missing file {}".format(objPath))
            missingSynapseSetObjs.append(synapseSetName)
            continue

        try:
            # Follow the conventions of NeuTu/Neu3:
            # positive X points right, positive Y points out, positive Z points down.
            # Note that this is different from the convention in the first FlyEM movies:
            # positive X pointed down, positive Y pointed right, positive Z pointed out,
            # implemented with a call like the following:
            # bpy.ops.import_scene.obj(filepath=objPath, axis_up="Y", axis_forward="X")
            bpy.ops.import_scene.obj(filepath=objPath, axis_up="Z", axis_forward="Y")

            obj = bpy.context.selected_objects[0]
            obj.name = "Synapses." + synapseSetName

            print("Added object '{}'".format(obj.name))
        except Exception as e:
            print("Error: cannot import '{}': '{}'".format(objPath, str(e)))

print("Done")

print("Assigning synapse materials...")

synapseSets = [o for o in bpy.data.objects.keys() if o.startswith("Synapses.")]
for synapseSet in synapseSets:
    obj = bpy.data.objects[synapseSet]

    if "pre" in obj.name.lower():
        color = (1, 1, 0, 1)
    elif "post" in obj.name.lower():
        color = (0.19, 0.19, 0.19, 1)
    else:
        color = (1, 1, 1, 1)

    matName = "Material." + obj.name
    mat = newGlowingMaterial(matName, color)
    obj.data.materials.clear()
    obj.data.materials.append(mat)

    # Make the transparency appear in the interactive viewport rendering.
    obj.show_transparent = True

print("Done")

#

print("Adding bounds...")

def addBoundObj(name, boundData):
    boundName = "Bound." + name
    bound = newObject(boundName)
    bound.location = boundData["center"]

    bound["Min"] = boundData["min"]
    bound["Max"] = boundData["max"]
    bound["Radius"] = boundData["radius"]

for groupName in groupToNeuronIds.keys():
    addBoundObj("neurons." + groupName, groupToBBox[groupName])

if "rois" in jsonData:
    for groupName in groupToRoiNames.keys():
        roiNames = groupToRoiNames[groupName]
        objs = [bpy.data.objects["Roi." + name] for name in roiNames]
        bboxCenter, bboxMin, bboxMax = computeBbox(objs)
        radius = computeBsphere(objs, bboxCenter)
        data = { "center" : bboxCenter, "min" : bboxMin, "max" : bboxMax, "radius" : radius }
        addBoundObj("rois." + groupName, data)

if "synapses" in jsonData:
    jsonSynapses = jsonData["synapses"]
    for synapseSetName in jsonSynapses:
        if synapseSetName == "source":
            continue
        key = "Synapses." + synapseSetName
        if not key in bpy.data.objects:
            print("Missing '{}': run fetchMeshes.py or buildSynapses.py".format(key))
            exit()
        objs = [bpy.data.objects[key]]
        bboxCenter, bboxMin, bboxMax = computeBbox(objs)
        radius = computeBsphere(objs, bboxCenter)
        data = { "center" : bboxCenter, "min" : bboxMin, "max" : bboxMax, "radius" : radius }
        addBoundObj("synapses." + synapseSetName, data)

# Some overall bounds, useful for placing lights.

def unionBounds(boundDataMap):
    limit = sys.float_info.max
    bboxMin = [ limit,  limit,  limit]
    bboxMax = [-limit, -limit, -limit]
    for (key, data) in boundDataMap.items():
        for i in range(3):
            bboxMin[i] = min(bboxMin[i], data["min"][i])
            bboxMax[i] = max(bboxMax[i], data["max"][i])
    bboxCenter = [(bboxMin[i] + bboxMax[i]) / 2 for i in range(3)]

    # Approximate the sphere, since the individual vertices are no longer available.
    radius = 0
    for (key, data) in boundDataMap.items():
        offset = (data["center"] - mathutils.Vector(bboxCenter)).length
        approxRadius = offset + data["radius"]
        radius = max(radius, approxRadius)

    return { "center" : bboxCenter, "min" : bboxMin, "max" : bboxMax, "radius" : radius }

if useSeparateNeuronFiles:
    allNeuronsData = unionBounds(meshesSourceIndexToBBox)
else:
    allNeurons = [o for o in bpy.data.objects if o.name.startswith("Neuron.")]
    bboxCenter, bboxMin, bboxMax = computeBbox(allNeurons)
    radius = computeBsphere(allNeurons, bboxCenter)
    allNeuronsData = { "center" : bboxCenter, "min" : bboxMin, "max" : bboxMax, "radius" : radius }
addBoundObj("neurons", allNeuronsData)

if "rois" in jsonData:
    allRois = [o for o in bpy.data.objects if o.name.startswith("Roi.")]
    bboxCenter, bboxMin, bboxMax = computeBbox(allRois)
    radius = computeBsphere(allRois, bboxCenter)
    allRoisData = { "center" : bboxCenter, "min" : bboxMin, "max" : bboxMax, "radius" : radius }
    addBoundObj("rois", allRoisData)

print("Done")

#

if useSeparateNeuronFiles:
    print("Adding proxies...")

    for (group, boundData) in groupToBBox.items():
        r = boundData["radius"] / 8
        bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=r, depth=2*r)
        proxy = bpy.context.object
        proxy.name = "Neuron.proxy." + group
        proxy.location = boundData["center"]

        proxy["ids"] = groupToNeuronIds[group]
        proxy["neuronFile"] = separateNeuronFiles[groupToMeshesSourceIndex[group]]

        matName = "Material." + proxy.name
        mat = newBasicMaterial(matName)
        proxy.data.materials.clear()
        proxy.data.materials.append(mat)
        proxy.show_transparent = True

    print("Done")

#

# Maybe useful when previewing with viewport rendering set to "Material"?
if bpy.app.version < (2, 80, 0):
    bpy.context.scene.world.light_settings.use_environment_light = True

#

camera = bpy.data.cameras["Camera"]
# Frustum clipping planes appropriate for FlyEM data, with 1 unit being 8 nm.
# A lower clip_start causes Z-buffer artifacts with the Blender internal renderer.
# A lower clip_end can make many neurons invisibile.
camera.clip_start = 100
camera.clip_end = 100000

camera.lens_unit = "FOV"
camera.angle = math.radians(50)

# HDTV 1080P
# The X and Y resolution must be set before animation is applied, because
# this resolution defines the camera aspect ratio, which affects framing.
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080
bpy.context.scene.render.resolution_percentage = 100
bpy.context.scene.render.pixel_aspect_x = 1
bpy.context.scene.render.pixel_aspect_y = 1

if bpy.app.version < (3, 1, 0):
    print("Writing {}".format(outputFile))
    bpy.ops.wm.save_as_mainfile(filepath=outputFile)
else:
    outputAbsPath = os.path.join(os.getcwd(), outputFile)
    print("Writing {}".format(outputAbsPath))
    bpy.ops.wm.save_as_mainfile(filepath=outputAbsPath)

timeEnd = datetime.datetime.now()
print()
print("Importing started at {}".format(timeStart))
print("Importing ended at {}".format(timeEnd))

if len(missingNeuronObjs) > 0:
    print()
    print("ERROR: could not find mesh .obj files for the following neurons:")
    for x in missingNeuronObjs:
        print(x)
if len(missingRoiObjs) > 0:
    print()
    print("ERROR: could not find mesh .obj files for the following rois:")
    for x in missingRoiObjs:
        print(x)
if len(missingSynapseSetObjs) > 0:
    print()
    print("ERROR: could not find mesh .obj files for the following synapses:")
    for x in missingSynapseSetObjs:
        print(x)
    print("NOTE: run buildSynapses.py to generate synapse mesh .obj files")
