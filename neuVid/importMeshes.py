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
from utilsColors import colors, getColor
from utilsJson import parseNeuronsIds, parseRoiNames, removeComments
from utilsMeshes import fileToImportForRoi, fileToImportForNeuron, fileToImportForSynapses

argv = sys.argv
if "--" not in argv:
    argv = []
else:
    argv = argv[argv.index("--") + 1:]

parser = argparse.ArgumentParser()
parser.add_argument("--inputJson", "-ij", dest="inputJsonFile", help="path to the JSON file describing the input")
parser.add_argument("--output", "-o", dest="outputFile", help="path for the output .blend file")
# A limit of 0 means no limit.
parser.set_defaults(limit=0)
parser.add_argument("--limit", "-l", type=int, dest="limit", help="limit to the number of IDs from each separate neurons file")

args = parser.parse_args(argv)

if args.inputJsonFile == None:
    parser.print_help()
    quit()

inputJsonDir = os.path.dirname(os.path.realpath(args.inputJsonFile))

jsonData = json.loads(removeComments(args.inputJsonFile))

if jsonData == None:
    print("Loading JSON file {} failed".format(args.inputJsonFile))
    quit()

#

def computeBbox(objs):
    limit = sys.float_info.max
    bboxMin = [ limit,  limit,  limit]
    bboxMax = [-limit, -limit, -limit]
    for obj in objs:
        verts = [(obj.matrix_world * vert.co).to_tuple() for vert in obj.data.vertices]
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
        verts = [obj.matrix_world * vert.co for vert in obj.data.vertices]
        for vert in verts:
            radius = max((vert - c).length, radius)
    return radius

groupToBBox = {}
meshesSourceIndexToBBox = {}

#

print("Parsing neuron IDs...")

if not "neurons" in jsonData:
    print("JSON contains no 'neurons' key, whose value is lists of neuron meshes to load")
    quit()
jsonNeurons = jsonData["neurons"]

neuronSources = ["."]
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

#

print("Assigning colors...")

neuronToColorIndex = {}

# When iterating through the neurons to assign consecutive colors,
# iterate first through the smaller groups of neurons that are visible at the
# same time, to reduce the chance that colors will be reused in these groups.

groupSizes = [[k, len(groupToNeuronIds[k])] for k in groupToNeuronIds.keys()]
# Sort on size, and if there is a tie sort on group name.
groupSizes.sort(key=lambda x: (x[1], x[0]))

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
missingSynapseSetObjs = []

for i in range(len(neuronSources)):
    if len(neuronSources) == 1:
        print("Importing {} neuron meshes".format(len(neuronIds[i])))
    else:
        print("Importing {} neuron meshes for index {}".format(len(neuronIds[i]), i))

    for obj in bpy.data.objects:
        if obj.name != "Camera":
            matName = "Material." + obj.name
            if matName in bpy.data.materials:
                mat = bpy.data.materials[matName]
                bpy.data.materials.remove(mat, True)
            bpy.data.objects.remove(obj, True)

    for neuronId in neuronIds[i]:
        objPath = fileToImportForNeuron(neuronSources[i], neuronId, inputJsonDir)

        if not os.path.isfile(objPath):
            print("Skipping missing file {}".format(objPath))
            missingNeuronObjs.append(neuronId)
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
            obj.name = "Neuron." + neuronId

            print("Added object '{}'".format(obj.name))

            matName = "Material." + obj.name
            mat = bpy.data.materials.new(name=matName)
            obj.data.materials.append(mat)

            color = getColor(neuronToColorIndex[obj.name], colors)
            mat.diffuse_color = color[0:3]

            mat.use_transparency = True
            # Make the object appear transparent in the interactive viewport rendering.
            obj.show_transparent = True

            print("Added material '{}'".format(matName))

        except Exception as e:
            print("Error: cannot import '{}': '{}'".format(objPath, str(e)))

    if useSeparateNeuronFiles:
        j = args.outputFile.rfind(".")
        outputFile = args.outputFile[:j] + "_neurons_" + str(i) + args.outputFile[j:]
        separateNeuronFiles.append(outputFile)
        bpy.ops.wm.save_as_mainfile(filepath=outputFile)

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
                bpy.data.materials.remove(mat, True)
            bpy.data.objects.remove(obj, True)

#

roiExponents = {}

print("Importing ROI meshes...")

if "rois" in jsonData:
    jsonRois = jsonData["rois"]

    source = "."
    if "source" in jsonRois:
        source = jsonRois["source"]

    roiNames, groupToRoiNames = parseRoiNames(jsonRois)

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

    missingRoiObjs = []
    for roiName in roiNames:
        objPath = fileToImportForRoi(source, roiName, inputJsonDir)
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

print("Done")

#

print("Assigning ROI materials...")

rois = [o for o in bpy.data.objects.keys() if o.startswith("Roi.")]
for roi in rois:
    obj = bpy.data.objects[roi]

    matName = "Material." + obj.name
    mat = bpy.data.materials.new(name=matName)
    obj.data.materials.append(mat)

    # Enable the transparency of the ROI away from its silhouette.
    mat.use_transparency = True
    # Make that transparency appear in the interactive viewport rendering.
    obj.show_transparent = True

    # Do not apply lighting to the ROI; just use the silhouette calculation.
    mat.use_shadeless = True
    # Do not involve the ROI in any aspect of shadows.
    mat.use_shadows = False
    mat.use_cast_shadows = False
    mat.use_transparent_shadows = False

    mat.alpha = 0.5

    # Set up the silhouette material for ROIs.

    mat.use_nodes = True
    matNodes = mat.node_tree.nodes
    matLinks = mat.node_tree.links

    matNode = matNodes["Material"]
    outputNode = matNodes["Output"]

    # Make the "Material" node use the non-node material being used
    # to preview in the UI's 3D View, so its animated alpha can be
    # reused as an input to alphaNode, below.  Thus we can preview
    # the animation in the 3D View and also see it in the final render.

    matNode.material = mat

    geomNode = matNodes.new("ShaderNodeGeometry")
    geomNode.name = "geom"

    dotNode = matNodes.new("ShaderNodeVectorMath")
    dotNode.name = "dot"
    dotNode.operation = "DOT_PRODUCT"
    matLinks.new(geomNode.outputs["View"], dotNode.inputs[0])
    matLinks.new(geomNode.outputs["Normal"], dotNode.inputs[1])

    absNode = matNodes.new("ShaderNodeMath")
    absNode.name = "abs"
    absNode.operation = "ABSOLUTE"
    matLinks.new(dotNode.outputs["Value"],absNode.inputs[0])

    negNode = matNodes.new("ShaderNodeMath")
    negNode.name = "neg"
    negNode.operation = "SUBTRACT"
    negNode.inputs[0].default_value = 1
    matLinks.new(absNode.outputs["Value"], negNode.inputs[1])

    powNode = matNodes.new("ShaderNodeMath")
    powNode.name = "pow"
    powNode.operation = "POWER"
    matLinks.new(negNode.outputs["Value"], powNode.inputs[0])
    exp = 5
    if roi in roiExponents:
        exp = roiExponents[roi]
    powNode.inputs[1].default_value = exp

    # Multiply in the animated alpha from the non-node material, above.
    # But note that alpha is the value needed for "SOLID" mode viewport
    # rendering, which is lower.  So scale it up before multiplying with
    # the silhouette alpha.

    alphaGainNode = matNodes.new("ShaderNodeMath")
    alphaGainNode.name = "alphaShift"
    alphaGainNode.operation = "MULTIPLY"
    alphaGainNode.inputs[0].default_value = 6 # 4
    matLinks.new(matNode.outputs["Alpha"], alphaGainNode.inputs[1])

    alphaCombineNode = matNodes.new("ShaderNodeMath")
    alphaCombineNode.name = "alphaCombine"
    alphaCombineNode.operation = "MULTIPLY"
    matLinks.new(alphaGainNode.outputs["Value"], alphaCombineNode.inputs[0])
    matLinks.new(powNode.outputs["Value"], alphaCombineNode.inputs[1])

    matLinks.new(alphaCombineNode.outputs["Value"], outputNode.inputs["Alpha"])

#

print("Importing synapse meshes...")

synapseSetToNeuron = {}
if "synapses" in jsonData:
    jsonSynapses = jsonData["synapses"]

    source = "."
    if "source" in jsonSynapses:
        source = jsonSynapses["source"]

    for synapseSetName, synapseSetSpec in jsonSynapses.items():
        if synapseSetName == "source":
            continue

        if not "neuron" in synapseSetSpec:
            print("Error: synapse set '{}' is missing 'neuron'\n".format(synapseSetName))
            continue
        neuron = synapseSetSpec["neuron"]

        objPath = fileToImportForSynapses(source, synapseSetName, inputJsonDir)
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

            synapseSetToNeuron[obj.name] = neuron

            print("Added object '{}'".format(obj.name))
        except Exception as e:
            print("Error: cannot import '{}': '{}'".format(objPath, str(e)))

print("Done")

print("Assigning synapse materials...")

synapseSets = [o for o in bpy.data.objects.keys() if o.startswith("Synapses.")]
for synapseSet in synapseSets:
    obj = bpy.data.objects[synapseSet]

    matName = "Material." + obj.name
    mat = bpy.data.materials.new(name=matName)
    obj.data.materials.append(mat)

    mat.use_transparency = True
    # Make that transparency appear in the interactive viewport rendering.
    obj.show_transparent = True

    # Give each synapse ball the color of its neuron body.
    neuron = synapseSetToNeuron[obj.name]
    neuronMatName = "Material.Neuron." + str(neuron)
    neuronMat = bpy.data.materials[neuronMatName]
    mat.diffuse_color = neuronMat.diffuse_color

    # And then make it "glow" like it is emitting light, which really just gives it
    # a brighter version of its neuron's color.
    mat.emit = 1
    mat.specular_intensity = 0

print("Done")

#

print("Adding bounds...")

def addBoundObj(name, boundData):
    boundName = "Bound." + name
    bound = bpy.data.objects.new(boundName, None)
    bpy.context.scene.objects.link(bound)
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
        mat = bpy.data.materials.new(name=matName)
        proxy.data.materials.append(mat)
        mat.use_transparency = True
        proxy.show_transparent = True

    print("Done")

#

# Maybe useful when previewing with viewport rendering set to "Material"?

bpy.context.scene.world.light_settings.use_environment_light = True

#

camera = bpy.data.cameras["Camera"]
camera.clip_end = 100000

# HDTV 1080P
# The X and Y resolution must be set before animation is applied, because
# this resolution defines the camera aspect ratio, which affects framing.
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080
bpy.context.scene.render.resolution_percentage = 100
bpy.context.scene.render.pixel_aspect_x = 1
bpy.context.scene.render.pixel_aspect_y = 1

bpy.ops.wm.save_as_mainfile(filepath=args.outputFile)

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
