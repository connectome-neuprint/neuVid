# Renders the animation created by addAnimation.py (run after importMeshes.py).

# Run in Blender, e.g.:
# blender --background --python render.py -- -ib movieWithAnimation.blend -o framesDirectory
# Assumes Blender 2.79.
# Requires an OTOY Octane license and special Blender installation for the --octane option.

import argparse
import bpy
import datetime
import json
import math
import mathutils
import os
import os.path
import platform
import shutil
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsGeneral import newObject
from utilsMaterials import getMaterialFcurve, getMaterialValue, setMaterialValue
from utilsJson import removeComments

USE_OPTIX1 = "--optix"
USE_OPTIX2 = "-optix"
USE_CUDA1 = "--cuda"
USE_CUDA2 = "-cuda"
USE_HIP1 = "--hip"
USE_HIP2 = "-hip"
USE_METAL1 = "--metal"
USE_METAL2 = "-metal"
USE_PERSISTENT_DATA1 = "--persist"
USE_PERSISTENT_DATA2 = "-p"

def suggest_optimizations(args):
    if args.useCycles:
        gpu = args.useOptix or args.useCuda or args.useHip or args.useMetal
        persist = args.usePersistentData
        if not gpu or not persist:
            print("--------------------------------------------------------------")
            print("Better performance may be possible with the following options:")
            if not gpu:
                print(". Use a GPU, if available: {} or {} or {} or {}".format(USE_OPTIX1, USE_CUDA1, USE_HIP1, USE_METAL1))
            if not persist:
                print(". Use persistent data (to avoid 'Synchronizing object'), if memory allows: {}".format(USE_PERSISTENT_DATA1))
            print("--------------------------------------------------------------")

timeStart = datetime.datetime.now()

argv = sys.argv
if "--" not in argv:
    argv = []
else:
    argv = argv[argv.index("--") + 1:]

parser = argparse.ArgumentParser()
parser.add_argument("--inputBlender", "-ib", dest="inputBlenderFile", help="path to the input .blend file")
parser.add_argument("--inputJson", "-ij", "-i", dest="inputJsonFile", help="path to the JSON file describing the input")
parser.add_argument("--frame-start", "-s", type=int, dest="start", help="first frame to render")
parser.add_argument("--frame-end", "-e", type=int, dest="end", help="last frame to render")
parser.add_argument("--frame-jump", "-j", type=int, dest="step", help="number of frames to step forward")
parser.add_argument("--output", "-o", dest="output", help="render output path")
parser.add_argument("--outputBlender", "-ob", dest="outputFile", help="path for the output .blend file instead of rendering")
parser.set_defaults(doRois=False)
parser.add_argument("--roi", "-r", dest="doRois", action="store_true", help="render only unlit content (ROIs, grayscales)")
parser.set_defaults(willComp=True)
parser.add_argument("--nocomp", "-nc", dest="willComp", action="store_false", help="create a final PNG, not a comp layer")
parser.set_defaults(useOctane=False)
parser.add_argument("--octane", "-oct", dest="useOctane", action="store_true", help="use the Octane renderer")
parser.set_defaults(useCycles=True)
# The Blender documentation claims that the double dashes (`--`) in the command line arguments "end option processing, 
# following arguments passed unchanged."  But in fact, Blender does look after the double dashes for some arguments
# that start with `--cycles`.  So this script cannot specify `--cycles` as its argument, and instead it must specify
# something more awkward like `--cycles-render`.  As a user, it is simplest to use the short form, `-cyc`.
parser.add_argument("--cycles-render", "-cyc", dest="useCycles", action="store_true", help="use the Cycles renderer")
parser.add_argument("--eevee", "-ee", dest="useCycles", action="store_false", help="use the Eevee renderer")
parser.set_defaults(transparentMaxBounces=32)
parser.add_argument("--transparent-max-bounces", "-tmb", type=int, dest="transparentMaxBounces", help="max ray bounces when alpha < 1")

parser.set_defaults(useOptix=False)
parser.add_argument(USE_OPTIX1, USE_OPTIX2, dest="useOptix", action="store_true", help="use the GPU and NVIDIA OptiX for Cycles")
parser.set_defaults(useCuda=False)
parser.add_argument(USE_CUDA1, USE_CUDA2, dest="useCuda", action="store_true", help="use the GPU and NVIDIA CUDA for Cycles")
parser.set_defaults(useHip=False)
parser.add_argument(USE_HIP1, USE_HIP2, dest="useHip", action="store_true", help="use the GPU and AMD HIP for Cycles")
parser.set_defaults(useMetal=False)
parser.add_argument(USE_METAL1, USE_METAL2, dest="useMetal", action="store_true", help="use the GPU and Apple Metal for Cycles")
parser.set_defaults(usePersistentData=False)
parser.add_argument(USE_PERSISTENT_DATA1, USE_PERSISTENT_DATA2, dest="usePersistentData", action="store_true", help="use the persistent data optimization")

parser.add_argument("--samples", "-sa", type=int, dest="numSamples", help="number of samples per pixel for the Octane renderer")
parser.set_defaults(denoise=True)
parser.add_argument("--nodenoise", "-ndn", dest="denoise", action="store_false", help="skip final denoising")
parser.set_defaults(filterSizeFactor=1.0)
parser.add_argument("--filter", "-f", type=float, dest="filterSizeFactor", help="filter size factor")
parser.set_defaults(onlyAmbient=False)
parser.add_argument("--ambient", "-amb", dest="onlyAmbient", action="store_true", help="use only ambient lighting")
parser.set_defaults(white=False)
parser.add_argument("--white", "-w", dest="white", action="store_true", help="use a white background")
parser.set_defaults(debug=False)
parser.set_defaults(resX=1920)
parser.add_argument("--resX", "-rx", type=int, dest="resX", help="output image X resolution (width)")
parser.set_defaults(resY=1080)
parser.add_argument("--resY", "-ry", type=int, dest="resY", help="output image Y resolution (height)")

# TODO: Improve on this temporary solution for data sets (e.g., FAFB) that have unit that are orders of magnitude different
# from the original FlyEM units.
parser.set_defaults(rescaleFactor=1.0)
parser.add_argument("--rescale", "-re", type=float, dest="rescaleFactor", help="rescale factor (for numerical precision)")

parser.add_argument("--debug", "-d", dest="debug", action="store_true", help="debug")

args = parser.parse_args(argv)

suggest_optimizations(args)

print("Rendering only ROIs and unlit content: {}".format(args.doRois))
if args.doRois:
    print("Compatibilty with Octane renderer: {}".format(args.useOctane))
else:
    print("Using Octane renderer: {}".format(args.useOctane))
print("Using Cycles renderer: {}".format(args.useCycles))
print("Using fps: {}".format(bpy.context.scene.render.fps))

if args.output != None:
    output = args.output
else:
    input = args.inputJsonFile
    if not input:
        input = args.inputBlenderFile
    output = os.path.splitext(input)[0] + "-frames"
# Ensure a final path separator, which is important for how Blender generates output file names
# from frame numbers.
output = os.path.join(output, "")
disableStandardOutput = False
print("Using output directory: {}".format(output))

willComp = False
if args.useOctane or args.doRois:
    willComp = True
if not args.willComp:
    willComp = False
print("Rendering for compositing: {}".format(willComp))

print("Input JSON file: {}".format(args.inputJsonFile))

inputBlenderFile = args.inputBlenderFile
if inputBlenderFile == None:
    if args.inputJsonFile != None:
        inputBlenderFile = os.path.splitext(args.inputJsonFile)[0] + "Anim.blend"
    else:
        parser.print_help()
        quit()
print("Opening input Blender file '{}'...".format(inputBlenderFile))

bpy.ops.wm.open_mainfile(filepath=inputBlenderFile)

timeEndOpen = datetime.datetime.now()
print("Done (elapsed time: {:.2f} sec)".format((timeEndOpen - timeStart).total_seconds()))

print("Using output width: {} px".format(args.resX))
print("Using output height: {} px".format(args.resY))

useSeparateNeuronFiles = False
if any(map(lambda x: x.name.startswith("Neuron"), bpy.data.objects)):
    useSeparateNeuronFiles = all(map(lambda x: not x.name.startswith("Neuron") or
        x.name.startswith("Neuron.proxy"), bpy.data.objects))

hasSynapses = any(map(lambda x: x.name.startswith("Synapses."), bpy.data.objects))

useOctane = args.useOctane

jsonLightPowerScale = [1.0, 1.0, 1.0]
jsonLightSizeScale = 1.0
jsonLightDistanceScale = 1.0
jsonLightColor = "default"
jsonUseShadows = True
jsonUseSpecular = True
jsonLightRotationZ = 0.0
jsonLightRotationY = 0.0
jsonLightRotationX = 0.0

if args.inputJsonFile:
    jsonData = json.loads(removeComments(args.inputJsonFile))
    if "lightPowerScale" in jsonData:
        jsonLightPowerScale = jsonData["lightPowerScale"]
        print("Using lightPowerScale: {}".format(jsonLightPowerScale))
    if "lightSizeScale" in jsonData:
        jsonLightSizeScale = jsonData["lightSizeScale"]
        print("Using lightSizeScale: {}".format(jsonLightSizeScale))
    if "lightDistanceScale" in jsonData:
        jsonLightDistanceScale = jsonData["lightDistanceScale"]
        print("Using lightDistanceScale: {}".format(jsonLightDistanceScale))
    if "lightColor" in jsonData:
        jsonLightColor = jsonData["lightColor"]
        print("Using lightColor: {}".format(jsonLightColor))
    if "useShadows" in jsonData:
        jsonUseShadows = jsonData["useShadows"]
        print("Using shadows: {}".format(jsonUseShadows))
    if "useSpecular" in jsonData:
        jsonUseSpecular = jsonData["useSpecular"]
        print("Using specular: {}".format(jsonUseSpecular))
    if "lightRotationZ" in jsonData:
        jsonLightRotationZ = jsonData["lightRotationZ"]
        print("Using lightRotationZ: {}".format(jsonLightRotationZ))
    if "lightRotationY" in jsonData:
        jsonLightRotationY = jsonData["lightRotationY"]
        print("Using lightRotationY: {}".format(jsonLightRotationY))
    if "lightRotationX" in jsonData:
        jsonLightRotationX = jsonData["lightRotationX"]
        print("Using lightRotationX: {}".format(jsonLightRotationX))

if args.white and not useOctane:
    print("Using white background")

#

print("Rescaling/recentering to improve numerical precision...")

timeStartRescale = datetime.datetime.now()

def rescaleRecenter(obj, overallCenter, overallScale):
    if obj.name.startswith("Neuron.") or obj.name.startswith("Roi.") or obj.name.startswith("Synapses."):
        # Meshes for neurons and ROIs have location at the origin and
        # world position in the vertex coordinates.
        for vert in obj.data.vertices:
            vert.co = (vert.co - overallCenter) * overallScale
        if obj.animation_data:
            for fc in obj.animation_data.action.fcurves:
                if fc.data_path.endswith("location"):
                    for key in fc.keyframe_points:
                        key.co[1] = key.co[1] * overallScale
                    fc.update()

    elif obj.name.startswith("Bound."):
        obj.location = (obj.location - overallCenter) * overallScale
        obj["Min"] = (mathutils.Vector(obj["Min"]) - overallCenter) * overallScale
        obj["Max"] = (mathutils.Vector(obj["Max"]) - overallCenter) * overallScale
        obj["Radius"] *= overallScale
    elif obj.name.startswith("ImagePlane."):
        if not obj.name.endswith(".Pivot"):
            obj.scale *= overallScale
        if not obj.name.endswith(".Pivot") and obj.animation_data == None:
            if not obj.parent:
                obj.location = (obj.location - overallCenter) * overallScale
        else:
            for fc in obj.animation_data.action.fcurves:
                if fc.data_path.endswith("location"):
                    for key in fc.keyframe_points:
                        key.co[1] = (key.co[1] - overallCenter[fc.array_index]) * overallScale
                    fc.update()
    elif obj.name.startswith("Orbiter"):
        obj.location = (obj.location - overallCenter) * overallScale
    elif obj.name == "Camera":
        if obj.animation_data:
            for fc in obj.animation_data.action.fcurves:
                if fc.data_path.endswith("location"):
                    for key in fc.keyframe_points:
                        key.co[1] = (key.co[1] - overallCenter[fc.array_index]) * overallScale
                    fc.update()
        for con in obj.constraints:
            if con.type == "CHILD_OF":
                oldMat = con.inverse_matrix.inverted()
                oldTrans, oldRot, oldScale = oldMat.decompose()
                newTrans = (oldTrans - overallCenter) * overallScale
                if bpy.app.version < (2, 80, 0):
                    newMat = mathutils.Matrix.Translation(newTrans) * oldRot.to_matrix().to_4x4()
                else:
                    newMat = mathutils.Matrix.Translation(newTrans) @ oldRot.to_matrix().to_4x4()
                con.inverse_matrix = newMat.inverted()

# If using Octane to render neurons, then ROIs should be rendered with "--roi --octane"
# to get the same `overallScale`.  Then `useOctane` is disabled so the ROIs will be rendered
# with Eevee (for Blender 2.80 and later) or Blender Render (for Blender 2.79).

overallScale = 0.00001
if useOctane:
    overallScale = 0.01
elif args.useCycles:
    overallScale = 0.01
print("Original overall scale: {}, factor: {}".format(overallScale, args.rescaleFactor))
overallScale *= args.rescaleFactor
print("Using overall scale: {}".format(overallScale))
if args.doRois:
    useOctane = False

if useOctane:
    # For a test cube, this change to `ray_epsilon` eliminated ringing.
    bpy.data.scenes["Scene"].octane.ray_epsilon *= 10
    print("Using ray_epsilon: {}".format(bpy.data.scenes["Scene"].octane.ray_epsilon))

overallCenter = bpy.data.objects["Bound.neurons"].location.copy()
print("Using overall center: {}".format(overallCenter))

for obj in bpy.data.objects:
    rescaleRecenter(obj, overallCenter, overallScale)

camera = bpy.data.cameras["Camera"]
camera.clip_start *= overallScale
camera.clip_end *= overallScale

print("Rescaled/recentered camera clip_start: {}".format(camera.clip_start))
print("Rescaled/recentered camera clip_end: {}".format(camera.clip_end))

timeEndRescale = datetime.datetime.now()
print("Done (elapsed time: {:.2f} sec)".format((timeEndRescale - timeStartRescale).total_seconds()))

#

def addOctaneMaterial(obj, animMat=None):
    # Type 1 is "Scatter", meaning a static object, sent to Octane only once
    # at the beginning of all rendering?
    obj.data.octane.mesh_type = "1"

    matName = "Material." + obj.name
    mat = bpy.data.materials[matName]

    mat.use_nodes = True
    matNodes = mat.node_tree.nodes
    matLinks = mat.node_tree.links

    if "Material" in matNodes:
        # Make the `Material` node use the non-node material being used
        # to preview in the UI's 3D View, so its animated alpha can be
        # reused as an input to `alphaNode`, below.  Thus we can preview
        # the animation in the 3D View and also see it in the final render.

        matNode = matNodes["Material"]
        matNode.material = mat

    glossyNode = matNodes.new("ShaderNodeOctGlossyMat")
    # Diffuse color is `inputs[0]`.
    c = getMaterialValue(mat, "diffuse_color")
    glossyNode.inputs[0].default_value = (c[0], c[1], c[2], 1.0)

    if not animMat:
        animMat = mat
    # Opacity is `inputs[11]`.
    # To transfer the animation from the material's alpha to this opacity,
    # it does not work to just add a link like the following:
    # `matLinks.new(matNode.outputs["Alpha"], glossyNode.inputs[11])`
    # Instead, it seems to be necessary to copy the keys.
    fcurvesAlpha = getMaterialFcurve(animMat, "alpha")
    if fcurvesAlpha:
        keyframes = fcurvesAlpha.keyframe_points
        for i in range(len(keyframes)):
            glossyNode.inputs[11].default_value = keyframes[i].co[1]
            glossyNode.inputs[11].keyframe_insert("default_value", frame=keyframes[i].co[0])

    # Roughness
    glossyNode.inputs[2].default_value = 0.0

    # Smooth is inputs[12]
    # http://www.aoktar.com/octane/OCTANE%20HELP%20MANUAL.html?DiffuseMaterial.html
    # "The Smooth parameter is a Boolean (meaning that it is a toggle that turns the feature on or off)
    # which smooths the transition between surface normals. If this option is disabled the edges between
    # the polygons of the surface will be sharp giving the surface a faceted look."
    glossyNode.inputs[12].default_value = True

    if bpy.app.version < (2, 80, 0):
        outputNode = matNodes.new("ShaderNodeOutputMaterial")
    else:
        outputNode = matNodes["Material Output"]

    # Connect the glossy node's "OutMat" output to the output node's "surface" input.
    matLinks.new(glossyNode.outputs[0], outputNode.inputs[0])

if args.doRois:
    for obj in bpy.data.objects:
        if obj.name.startswith("Neuron."):
            if bpy.app.version < (2, 80, 0):
                    obj.hide = True
            obj.hide_render = True

        # A current limitation of Blender's Eevee renderer is that "BLEND" (alpha blend)
        # materials are ignored in all passes other than the basic "combined" pass.
        # So for depth compositing, which needs a depth pass (i.e., "Mist"), change these 
        # materials to "HASHED".
        elif obj.name.startswith("Roi.") and willComp:
            matName = "Material." + obj.name
            if matName in bpy.data.materials:
                mat = bpy.data.materials[matName]
                mat.blend_method = "HASHED"

    if bpy.app.version < (2, 80, 0):
        bpy.data.scenes["Scene"].render.use_shadows = False
        bpy.data.scenes["Scene"].render.use_textures = True
        bpy.data.scenes["Scene"].render.use_sss = False
        bpy.data.scenes["Scene"].render.use_raytrace = False
        bpy.data.scenes["Scene"].render.use_envmaps = False
    else:
        bpy.data.scenes["Scene"].eevee.use_soft_shadows = False
        bpy.data.scenes["Scene"].eevee.use_shadow_high_bitdepth = False
else:
    if useOctane:
        print("Adding Octane materials...")
        for obj in bpy.data.objects:
            if obj.name.startswith("Roi.") or obj.name.startswith("ImagePlane.") or obj.name.startswith("Synapses."):
                matName = "Material." + obj.name
                if matName in bpy.data.materials:
                    mat = bpy.data.materials[matName]
                    bpy.data.materials.remove(mat, do_unlink=True)
                bpy.data.objects.remove(obj, do_unlink=True)
            elif obj.name.startswith("Neuron.") and not useSeparateNeuronFiles:
                addOctaneMaterial(obj)
        print("Done")
    else:
        if args.useCycles:
            for obj in bpy.data.objects:
                matName = "Material." + obj.name
                if matName in bpy.data.materials:
                    mat = bpy.data.materials[matName]
                    mat.cycles.use_transparent_shadow = True
            # With the default transparent_max_bounces (8), some complex scenes with many bodies having alpha below one
            # max have black patches, when the maximum is reached too soon.  So raise the maximum.
            bpy.data.scenes["Scene"].cycles.transparent_max_bounces = args.transparentMaxBounces
            print("Using transparent_max_bounces {}".format(bpy.data.scenes["Scene"].cycles.transparent_max_bounces))
        else:
            if bpy.app.version < (2, 80, 0):
                bpy.data.scenes["Scene"].render.use_shadows = jsonUseShadows
                bpy.data.scenes["Scene"].render.use_textures = True
                bpy.data.scenes["Scene"].render.use_sss = False
                bpy.data.scenes["Scene"].render.use_raytrace = False
                bpy.data.scenes["Scene"].render.use_envmaps = False
            else:
                bpy.data.scenes["Scene"].eevee.use_soft_shadows = jsonUseShadows
                bpy.data.scenes["Scene"].eevee.use_shadow_high_bitdepth = True
        print("Updating Blender materials...")
        for obj in bpy.data.objects:
            if obj.name.startswith("Neuron.") and not useSeparateNeuronFiles:
                matName = "Material." + obj.name
                if matName in bpy.data.materials:
                    mat = bpy.data.materials[matName]

                    if not jsonUseSpecular:
                        setMaterialValue(mat, "specular_intensity", 0)

                    if bpy.app.version < (2, 80, 0):
                        if mat.animation_data:
                            fcurvesAlpha = mat.animation_data.action.fcurves.find(data_path="alpha")
                            if fcurvesAlpha:
                                # To make an object transparent it is not sufficient to set just its material's alpha.
                                # The material's `specular_alpha` must be set, too.  Using a driver to tie the `specular_alpha`
                                # to the alpha seems difficult to do, so just copy the alpha animation.
                                # (For 2.80+, there is no `specular_alpha` and this problem is solved in the material, by
                                # by setting up node links to scale the specular with the alpha.)
                                keyframes = fcurvesAlpha.keyframe_points
                                for i in range(len(keyframes)):
                                    mat.specular_alpha = keyframes[i].co[1]
                                    mat.keyframe_insert("specular_alpha", frame=keyframes[i].co[0])
        print("Done")

print("Adding lamps...")

lampSpecs = [
    {
        "direction": (-0.892, 0.3, 0.9),
        "color": (0.8, 0.8, 0.8, 1.0)
    },
    {
        "direction": (0.588, 0.46, 0.248),
        "color": (0.498, 0.5, 0.6, 1.0)
    },
    {
        "direction": (0.216, -0.392, -0.216),
        "color": (0.798, 0.838, 1.0, 1.0)
    }
]

lamps = []

if not args.onlyAmbient:
    lightRotationX = math.radians(jsonLightRotationX)
    lightRotationY = math.radians(jsonLightRotationY)
    lightRotationZ = math.radians(jsonLightRotationZ)
    lightRotationE = mathutils.Euler((jsonLightRotationX, jsonLightRotationY, lightRotationZ))

    neuronsBound = bpy.data.objects["Bound.neurons"]
    neuronsBoundRadius = neuronsBound["Radius"]
    for i in range(len(lampSpecs)):
        spec = lampSpecs[i]
        lampName = "Lamp." + str(i)

        # Use area lights for Octane, and for Octane-compatible ROIs, but not for synapses.
        if useOctane and not (args.doRois and hasSynapses):
            if bpy.app.version < (2, 80, 0):
                lampData = bpy.data.lamps.new(name=lampName, type="AREA")
            else:
                lampData = bpy.data.lights.new(name=lampName, type="AREA")
            lampData.use_nodes = True

            lampData.size = neuronsBoundRadius
            if "sizeFactor" in spec:
                sizeFactor = spec["sizeFactor"]
                lampData.size *= sizeFactor
            lampData.size *= jsonLightSizeScale
        elif args.useCycles:
            lampData = bpy.data.lights.new(name=lampName, type="AREA")
            lampData.size = neuronsBoundRadius
            if "sizeFactor" in spec:
                sizeFactor = spec["sizeFactor"]
                lampData.size *= sizeFactor
            lampData.size *= jsonLightSizeScale
            lampData.cycles.cast_shadow = True
            lampData.cycles.use_multiple_importance_sampling = True
        else:
            if bpy.app.version < (2, 80, 0):
                lampData = bpy.data.lamps.new(name = "Lamp.Key", type = "SPOT")
                lampData.shadow_method = "BUFFER_SHADOW"
                lampData.use_auto_clip_start = True
                lampData.use_auto_clip_end = True
                lampData.energy = 1.5
            else:
                lampData = bpy.data.lights.new(name = "Lamp.Key", type = "SPOT")
                # The newer Blender seems less bright somehow.
                lampData.energy = 1.5 * 3.75
                lampData.use_shadow = jsonUseShadows
            lampData.energy *= jsonLightPowerScale[i]
            lampData.spot_size = 1.4
            if jsonLightColor != "uniform":
                lampData.color = spec["color"][0:3]
            lampData.falloff_type = "CONSTANT"
        lamp = newObject(lampName, lampData)
        lamps.append(lamp)

        direction = mathutils.Vector(spec["direction"])
        direction.rotate(lightRotationE)
        direction.normalize()
        lampDistance = neuronsBoundRadius * 2.5
        lampDistance *= jsonLightDistanceScale
        lamp.location = direction * lampDistance

        lampTrackTo = lamp.constraints.new(type="TRACK_TO")
        lampTrackTo.target = neuronsBound
        lampTrackTo.track_axis = "TRACK_NEGATIVE_Z"
        lampTrackTo.up_axis = "UP_X"

        if useOctane:
            if bpy.app.version < (2, 80, 0):
                lampLamp = bpy.data.lamps[lampData.name]
            else:
                lampLamp = bpy.data.lights[lampData.name]
            lampNodes = lampLamp.node_tree.nodes
            lampLinks = lampLamp.node_tree.links
            lampDiffuse = lampNodes.new("ShaderNodeOctDiffuseMat")
            # Diffuse color is inputs[0]
            lampDiffuse.inputs[0].default_value = spec["color"]
            lampEmit = lampNodes.new("ShaderNodeOctBlackBodyEmission")
            # Connect the emitter's "OutTex" output to the material's "Emission" input.
            lampLinks.new(lampEmit.outputs[0], lampDiffuse.inputs[10])

            # Power 2400000 works well for lamp distance 425 with the "visual-E-PG-new" data, so scale relative to it.
            # Emission power: lampEmit.inputs[1].default_value
            lampEmit.inputs[1].default_value = 2400000
            powerScale = (lampDistance / 425.1282)**2
            powerScale *= jsonLightPowerScale[i]
            lampEmit.inputs[1].default_value *= powerScale

            if bpy.app.version >= (2, 80, 0):
                # The newer Blender seems less bright somehow.
                lampEmit.inputs[1].default_value *= 2.5

            print("lamp {} power {} after scaling by {}".format(i, lampEmit.inputs[1].default_value, powerScale))

            if "powerFactor" in spec:
                powerFactor = spec["powerFactor"]
                lampEmit.inputs[1].default_value *= powerFactor
            if bpy.app.version < (2, 80, 0):
                lampOutputName = "Lamp Output"
            else:
                lampOutputName = "Light Output"
            lampOutput = lampNodes[lampOutputName]
            lampLinks.new(lampDiffuse.outputs[0], lampOutput.inputs[0])

            lamp.octane.camera_visibility = False
        elif args.useCycles:
            # Power 2400000 works well for lamp distance 425 with the "visual-E-PG-new" data, so scale relative to it.
            # Emission power: lampEmit.inputs[1].default_value
            lampData.energy = 2400000
            powerScale = (lampDistance / 425.1282)**2
            powerScale *= jsonLightPowerScale[i]
            lampData.energy *= powerScale

            if bpy.app.version < (3, 0, 0):
                lamp.cycles_visibility.camera = False
            else:
                lamp.visible_camera = False

    # Put the lights in the correct orientation for the "standard" view,
    # with positive X right, positive Y out, positive Z down.
    lampRotator = newObject("Lamps")
    lampRotator.location = neuronsBound.location
    for lamp in lamps:
        lamp.parent = lampRotator
    lampRotator.rotation_euler = mathutils.Euler((0, math.radians(180), 0), "XYZ")

    print("Done")

# Environment and ambient light
if useOctane:
    # Environment texture, i.e., background color
    ambient = 0.0
    if args.onlyAmbient:
        ambient = 0.25

    if bpy.app.version < (2, 80, 0):
        texEnv = bpy.data.textures.new("Texture.Env", type="IMAGE")
        texEnv.use_nodes = True
        texEnvNodes = texEnv.node_tree.nodes
        texEnvLinks = texEnv.node_tree.links
        texEnvOut = texEnvNodes["Output"]
        texEnvRGB = texEnvNodes.new("ShaderNodeOctRGBSpectrumTex")
        texEnvRGB.inputs[0].default_value = (ambient, ambient, ambient, 1)
        texEnvLinks.new(texEnvRGB.outputs[0], texEnvOut.inputs[0])
        bpy.context.scene.world.octane.env_texture_ptr = texEnv
    else:
        color = (ambient, ambient, ambient, 1)
        nodes = bpy.data.worlds["World"].node_tree.nodes
        links = bpy.data.worlds["World"].node_tree.links
        texEnvNode = nodes.new("ShaderNodeOctTextureEnvironment")
        texEnvNode.inputs["Texture"].default_value = color
        worldOutputNode = nodes["World Output"]
        links.new(texEnvNode.outputs["OutEnv"], worldOutputNode.inputs["Octane Environment"])
else:
    # Rendering background color
    background = (1, 1, 1, 1) if args.white else (0, 0, 0, 1)
    if bpy.app.version < (2, 80, 0):
        bpy.data.worlds["World"].horizon_color = background[0:3]
    else:
        bpy.data.worlds["World"].use_nodes = True
        bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = background
        bpy.data.worlds["World"].cycles_visibility.diffuse = False
        if args.white:
            bpy.context.scene.view_settings.view_transform = "Standard"

        numSamples = 256
        if args.useCycles:
            numSamples = 128
        if args.numSamples:
            numSamples = args.numSamples
        print("Samples per pixel: {}".format(numSamples))
        bpy.data.scenes["Scene"].eevee.taa_render_samples = numSamples
        if args.useCycles:
            bpy.data.scenes["Scene"].cycles.samples = numSamples

if useOctane:
    # Seems to causes some errors?
    #bpy.ops.wm.addon_enable(module="octane")

    # Switch to the Octane renderer after creating the materials above,
    # to avoid getting a default Octane material that deletes the standard
    # material with its animated alpha.
    bpy.context.scene.render.engine = "octane"
    # Path tracing
    bpy.context.scene.octane.kernel_type = "2"

    # "Render" tab, "Animation mode" "Camera only"
    # This setting does give some speedup on animated frames after the
    # initial frame, and gives correct results even if there is animation on
    # the opacity in the objects' materials.
    bpy.context.scene.octane.anim_mode = "2"

    # Switch from the sky environment to a solid texture.
    bpy.context.scene.world.octane.env_type = "0"

    if args.denoise:

        # Eliminate flickering during animation, at least in theory.
        bpy.context.scene.octane.static_noise = True

        # Denoising requires turning on the "Octane Camera Imager (Render Mode)"
        bpy.context.scene.octane.hdr_tonemap_render_enable = True

        # The denoised result will be in a special beauty pass, called "OctDenoiserBeauty".
        bpy.context.scene.octane.use_passes = True
        
        if bpy.app.version < (2, 80, 0):
            bpy.context.scene.render.layers["RenderLayer"].use_pass_denoise_beauty = True
        else:
            bpy.data.scenes["Scene"].view_layers["View Layer"].use_pass_oct_denoise_beauty = True
            if not platform.platform().startswith("macOS"):
                # Turn on the Octane Spectral AI denoiser.
                bpy.context.scene.camera.data.octane.enable_denoising = True
                bpy.context.scene.camera.data.octane.denoise_on_completion = True
            else:
                # The Octane Spectral AI denoiser does not work well with Octane X on a M1 Mac:
                # it is extremely slow and produces very dark results).  As a work-around,
                # use the built-in Blender denoiser.
                bpy.context.scene.use_nodes = True
                bpy.context.scene.render.use_compositing = True
                compNodes = bpy.context.scene.node_tree.nodes
                compLinks = bpy.context.scene.node_tree.links
                layersNode = compNodes["Render Layers"]

                denoiseNode = compNodes.new("CompositorNodeDenoise")
                compLinks.new(layersNode.outputs["Image"], denoiseNode.inputs["Image"])

                bpy.data.scenes["Scene"].view_layers["View Layer"].use_pass_oct_info_geo_normal = True
                compLinks.new(layersNode.outputs["OctGeoNormal"], denoiseNode.inputs["Normal"])

                compNode = compNodes["Composite"]
                if willComp:
                    # Set up a new file output feeding output from denoising to the layer.channel names
                    # expected by compFrames.py
                    fileNode = compNodes.new("CompositorNodeOutputFile")
                    fileNode.format.file_format = "OPEN_EXR_MULTILAYER"
                    # The file path will be the same as the standard animation output file. 
                    fileNode.base_path = output
                    #  Blender currently offers no way to disable the writing of that standard file, so enable
                    # code (later) that redirects that standard file to a temporary directory and deletes it.
                    disableStandardOutput = True
                    fileNode.file_slots.remove(fileNode.inputs[0])

                    fileNode.file_slots.new("View Layer.OctDenoiserBeauty")
                    compLinks.new(denoiseNode.outputs["Image"], fileNode.inputs["View Layer.OctDenoiserBeauty"])

                    # Enable the "OctZDepth" pass, and map the depth at `camera.clip_end` to 1.0.
                    bpy.data.scenes["Scene"].view_layers["View Layer"].use_pass_oct_info_z_depth = True
                    bpy.context.view_layer.octane.info_pass_z_depth_max = camera.clip_end
                    fileNode.file_slots.new("View Layer.Depth")
                    sepNode = compNodes.new("CompositorNodeSepRGBA")
                    # The "OctZDepth" pass produces a RGBA value with Z depth duplicated in the R, G and B
                    # channels.  The compFrames.py nodes could handle this format, but it saves space in the
                    # .exr files to extract just on copy of Z depth, from the R channel.
                    compLinks.new(layersNode.outputs["OctZDepth"], sepNode.inputs["Image"])
                    # Leave "View Layer.Depth" in [0, 1] range, so compFrames.py can compare it to "Mist".
                    compLinks.new(sepNode.outputs["R"], fileNode.inputs["View Layer.Depth"])
                else:
                    compLinks.new(denoiseNode.outputs["Image"], compNode.inputs["Image"])

    bpy.context.scene.octane.filter_size *= args.filterSizeFactor
    print("Using filter size: {}".format(bpy.context.scene.octane.filter_size))
elif args.useCycles:
    bpy.context.scene.render.engine = "CYCLES"

    if args.denoise:
        bpy.context.scene.cycles.use_denoising = True
        bpy.context.view_layer.cycles.denoising_store_passes = True

        bpy.context.scene.use_nodes = True
        bpy.context.scene.render.use_compositing = True
        compNodes = bpy.context.scene.node_tree.nodes
        compLinks = bpy.context.scene.node_tree.links
        layersNode = compNodes["Render Layers"]

        denoiseNode = compNodes.new("CompositorNodeDenoise")
        compLinks.new(layersNode.outputs["Noisy Image"], denoiseNode.inputs["Image"])
        compLinks.new(layersNode.outputs["Denoising Normal"], denoiseNode.inputs["Normal"])
        compLinks.new(layersNode.outputs["Denoising Albedo"], denoiseNode.inputs["Albedo"])

        compNode = compNodes["Composite"]
        compLinks.new(denoiseNode.outputs["Image"], compNode.inputs["Image"])

if willComp:
    # Save depth with the output image
    bpy.context.scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"

    # Use a transparent background, for compositing with other renderings (e.g., ROI)
    if useOctane:
        bpy.context.scene.octane.alpha_channel = True
    elif bpy.app.version < (2, 80, 0):
        bpy.context.scene.render.alpha_mode = "TRANSPARENT"
    else:
        bpy.context.scene.render.film_transparent = True
        # Remove the "Z" pass, because it has only a single sample per pixel and thus 
        # does not capture "HASHED" transparency accurately.
        bpy.data.scenes["Scene"].view_layers["View Layer"].use_pass_z = False
        bpy.context.scene.display_settings.display_device = "None"

        # Use "Mist" as depth (z), normalized with 1 at `camera.clip_end`.
        bpy.data.scenes["Scene"].view_layers["View Layer"].use_pass_mist = True
        bpy.context.scene.world.mist_settings.falloff = "LINEAR"
        bpy.context.scene.world.mist_settings.start = 0
        bpy.context.scene.world.mist_settings.depth = camera.clip_end
        bpy.context.scene.render.image_settings.color_depth = '32'
else:
    bpy.context.scene.render.image_settings.file_format = "PNG"

#

if args.outputFile != None:
    bpy.ops.wm.save_as_mainfile(filepath=args.outputFile)
    quit()

#

# "Rest intervals" are periods in time where nothing is being animated.
# Ideally, rendering can be avoided during such an interval, being replaced
# with copying of the last frame before the start of the interval.

restIntervals = []
numCurves = 0

def getObjectFcurves():
    result = []
    for obj in bpy.data.objects:
        if obj.animation_data:
            for fc in obj.animation_data.action.fcurves:
                if fc.data_path.endswith(("location", "rotation_euler")):
                    if (obj.name == "Orbiter" or obj.name.endswith(".Pivot")) and fc.data_path.endswith("location"):
                        continue
                    result.append((obj.name, fc))
    return result

def getMaterialFcurves():
    result = []
    for mat in bpy.data.materials:
        fc = getMaterialFcurve(mat, "alpha")
        if fc:
            result.append((mat.name, fc))
        fc = getMaterialFcurve(mat, "diffuse_color")
        if fc:
            result.append((mat.name, fc))

    return result

def addRestIntervals(namesAndFcurves):
    global restIntervals, numCurves
    for name, fc in namesAndFcurves:
        numCurves += 1
        id = name + "." + fc.data_path + "." + str(fc.array_index)
        fStart = 1
        # The value for the first resting interval is not known until the first key,
        # with its value.
        vStart = None
        fEnd = None
        for key in fc.keyframe_points:
            f = int(key.co[0])
            v = key.co[1]
            if (vStart == None or v == vStart) and f != fStart:
                # The first key define the value of the first resting interval.
                vStart = v
                fEnd = f
            else:
                if fEnd:
                    restIntervals.append((fStart, "s", id))
                    restIntervals.append((fEnd, "e", id))
                vStart = v
                fStart = f
                fEnd = None
        fEnd = bpy.data.scenes["Scene"].frame_end
        if fStart != fEnd:
            restIntervals.append((fStart, "s", id))
            restIntervals.append((fEnd, "e", id))

def addTextureRestIntervals():
    global restIntervals, numCurves
    idIus = []
    if bpy.app.version < (2, 80, 0):
        for tex in bpy.data.textures:
            if isinstance(tex, bpy.types.ImageTexture):
                if tex.image.source == "MOVIE":
                    id = tex.name
                    iu = tex.image_user
                    idIus.append((id, iu))
    else:
        for mat in bpy.data.materials:
            if mat.name.startswith("Material.ImagePlane."):
                texImageNode = mat.node_tree.nodes["texImage"]
                if texImageNode.image.source == "MOVIE":
                    id = texImageNode.image.name
                    iu = texImageNode.image_user
                    idIus.append((id, iu))
    for id, iu in idIus:
        numCurves += 1
        restIntervals.append((1, "s", id))
        restIntervals.append((iu.frame_start, "e", id))
        restIntervals.append((iu.frame_start + iu.frame_duration, "s", id))
        restIntervals.append((bpy.data.scenes["Scene"].frame_end, "e", id))

addRestIntervals(getObjectFcurves())
addRestIntervals(getMaterialFcurves())
addTextureRestIntervals()
restIntervals.sort()

restingCurves = set()
renderIntervals = []
fStartRendering = bpy.data.scenes["Scene"].frame_start
allResting = False

for pt in restIntervals:
    if pt[1] == "s":
        restingCurves.add(pt[2])
    else:
        restingCurves.remove(pt[2])
    if len(restingCurves) == numCurves:
        allResting = True
        fEndRendering = pt[0] + 1
        renderIntervals.append((fStartRendering, fEndRendering))
    elif allResting:
        allResting = False
        fStartRendering = pt[0] - 1

if fStartRendering < bpy.data.scenes["Scene"].frame_end:
    fEndRendering = bpy.data.scenes["Scene"].frame_end
    renderIntervals.append((fStartRendering, fEndRendering))

# If there is no animation, add an interval anyway, or nothing will render.
if len(renderIntervals) == 0:
    renderIntervals.append((1, 1))

fStartOverall = bpy.data.scenes["Scene"].frame_start
if args.start != None:
    fStartOverall = args.start

fEndOverall = bpy.data.scenes["Scene"].frame_end
if args.end != None:
    fEndOverall = args.end

if args.step != None:
    bpy.context.scene.frame_step = args.step

renderIntervalsClipped = []
for ri in renderIntervals:
    fStart = int(ri[0])
    fEnd = int(ri[1])

    if fEnd < fStartOverall:
        continue
    if fEndOverall < fStart:
        break
    if fStart < fStartOverall and fStartOverall < fEnd:
        fStart = fStartOverall
    if fStart <= fEndOverall and fEndOverall < fEnd:
        fEnd = fEndOverall

    renderIntervalsClipped.append((fStart, fEnd))

# TODO: There is a problem if fStartOverall is bewteen render intervals:
# we need to render one frame at the end of the preceding render interval,
# then copy.  The following is only a partial fix.
if len(renderIntervalsClipped) == 0:
    renderIntervalsClipped.append((fStartOverall, fEndOverall))

def findHideRenderFrames(materials):
    hideRenderAtFrame = {}
    for mat in materials:
        name = mat.name[mat.name.find(".")+1:]
        fc = getMaterialFcurve(mat, "alpha")
        if fc:
            # Go through the keys, looking for keys i and i+1 both setting alpha to 0
            # and i+2 setting alpha > 0.  Then hideRenderAtFrame is True for the
            # key i's frame (fStartHidden), and  False for key i+1's frame (fAlpha0).
            fAlpha0 = None
            fStartHidden = None
            firstKey = True
            for key in fc.keyframe_points:
                f = int(key.co[0])
                v = key.co[1]
                if v == 0.0:
                    if not fStartHidden:
                        if firstKey:
                            fStartHidden = 1
                        else:
                            fStartHidden = f
                    fAlpha0 = f
                else:
                    if fStartHidden and fAlpha0 and fStartHidden < fAlpha0:
                        if not fStartHidden in hideRenderAtFrame:
                            hideRenderAtFrame[fStartHidden] = []
                        hideRenderAtFrame[fStartHidden].append((name, True))
                        if not fAlpha0 in hideRenderAtFrame:
                            hideRenderAtFrame[fAlpha0] = []
                        hideRenderAtFrame[fAlpha0].append((name, False))
                    elif firstKey:
                        if not 1 in hideRenderAtFrame:
                            hideRenderAtFrame[1] = []
                        hideRenderAtFrame[1].append((name, False))
                    fAlpha0 = None
                    fStartHidden = None
                firstKey = False
            if fStartHidden != None:
                if not fStartHidden in hideRenderAtFrame:
                    hideRenderAtFrame[fStartHidden] = []
                hideRenderAtFrame[fStartHidden].append((name, True))
    return hideRenderAtFrame

def hideRenderTrueAtFrame(f, hideRenderTrueFrames):
    hrtfPrev = None
    for hrtf in hideRenderTrueFrames:
        if f == hrtf[0]:
            return hrtf[1]
        elif f < hrtf[0] and hrtfPrev:
            return hrtfPrev[1]
        hrtfPrev = hrtf
    return []

hideRenderTrueFrames = []

if not args.doRois:
    hideRenderChangesAtFrame = findHideRenderFrames(bpy.data.materials)

    # Sorted list of keys, i.e., the frame numbers at which hide_render must change.
    hideRenderFramesSorted = sorted(hideRenderChangesAtFrame)

    # Make sure that renderIntervalsClipped has a new interval starting at each
    # frame where hide_render must change.
    i = 0
    while i < len(renderIntervalsClipped):
        ri = renderIntervalsClipped[i]
        fStart = int(ri[0])
        fEnd = int(ri[1])
        for f in hideRenderFramesSorted:
            if fStart < f and f < fEnd:
                renderIntervalsClipped[i] = (fStart, f - 1)
                renderIntervalsClipped.insert(i + 1, (f, fEnd))
                break
        i += 1

    # Make hideRenderTrueFrames[(f, s)] be the set of objects, s, to be given hide_render = True
    # at frame f.
    hideRenderTrueFrames = []
    hideRenderTrue = set()
    for f in hideRenderFramesSorted:
        pairs = hideRenderChangesAtFrame[f]
        for pair in pairs:
            if pair[1]:
                hideRenderTrue.add(pair[0])
            elif pair[0] in hideRenderTrue:
                hideRenderTrue.remove(pair[0])
        hideRenderTrueFrames.append((f, hideRenderTrue.copy()))

    # Put a sentinel at the last frame of the animation, to simplfy the rendering
    # of intervals.
    hideRenderTrueFrames.append((bpy.context.scene.frame_end, hideRenderTrue.copy()))

    hideRenderTrueFrames.sort()

def findFadingIntervals(hideRenderTrueFrames):
    fadingIntervalsRaw = []
    for mat in bpy.data.materials:
        fc = getMaterialFcurve(mat, "alpha")
        if fc:
            fPrev = None
            vPrev = None
            for key in fc.keyframe_points:
                f = int(key.co[0])
                v = key.co[1]
                if vPrev != None:
                    if (vPrev == 0 and v > 0) or (vPrev > 0 and v == 0):
                        fadingIntervalsRaw.append((fPrev, f))
                fPrev = f
                vPrev = v
    fadingIntervalsRaw.sort()
    fadingIntervals = []
    fStart = None
    fEnd = None
    n = 0
    for i in range(len(fadingIntervalsRaw)):
        fi = fadingIntervalsRaw[i]
        if not fStart:
            fStart = fi[0]
            fEnd = fi[1]
        else:
            if fi[0] == fStart:
                fEnd = max(fEnd, fi[1])
                n += 1
            if (fi[0] != fStart) or (i == len(fadingIntervalsRaw) - 1):
                hidden = hideRenderTrueAtFrame(fStart, hideRenderTrueFrames)
                p = n / (len(bpy.data.materials) - len(hidden))

                if args.debug:
                    print("fading from {} to {}; {} / {} or p {}".
                        format(fStart, fEnd, n, (len(bpy.data.materials) - len(hidden)), p))

                if p > 0.5:
                    fadingIntervals.append((fStart, fEnd))
                    print("significant fading {} from {} to {}".format(p, fStart, fEnd))
                fStart = None
                n = 0
    return fadingIntervals

def findDollyIntervals():
    frames = []
    camera = bpy.data.objects["Camera"]
    if camera.animation_data:
        for fc in camera.animation_data.action.fcurves:
            if fc.data_path.endswith(("location")):
                for key in fc.keyframe_points:
                    frames.append(int(key.co[0]))
                break
    dollyIntervals = []
    for i in range(len(frames) - 1):
        fStart = frames[i]
        bpy.context.scene.frame_set(fStart)
        pStart = camera.matrix_world.translation.copy()
        fEnd = frames[i + 1]
        bpy.context.scene.frame_set(fEnd)
        pEnd = camera.matrix_world.translation.copy()

        # The distance form the camera to the position of "Bound.neurons" is an
        # approximation to the distance for the camera to the subject.  And
        # scaling moved the position of "Bound.neurons" to the origin.
        p = pEnd.magnitude / pStart.magnitude
        dt = (fEnd - fStart) / bpy.context.scene.render.fps

        if args.debug:
            print("dollying from {} to {}; start {} end {} or p {}".
                format(fStart, fEnd, pStart.magnitude, pEnd.magnitude, p))

        if (p < 5/6 or p > 6/5) and dt > 1:
            dollyIntervals.append((fStart, fEnd))
            print("significant dollying {} from {} to {}".format(p, fStart, fEnd))

    return dollyIntervals

def combineRenderIntervals(renderIntervalsA, renderIntervalsB):
    # Priority given to renderIntervalsA.
    # Both should be sorted on the first element of the interval tuple.
    result = []
    renderIntervalsA2 = [x for x in renderIntervalsA]
    renderIntervalsB2 = [x for x in renderIntervalsB]
    iA = 0
    iB = 0
    while iA < len(renderIntervalsA2) or iB < len(renderIntervalsB2):
        if iB >= len(renderIntervalsB2):
            result.append(renderIntervalsA2[iA])
            iA += 1
        elif iA >= len(renderIntervalsA2):
            result.append(renderIntervalsB2[iB])
            iB += 1
        else:
            riA = renderIntervalsA2[iA]
            riB = renderIntervalsB2[iB]
            if riA[0] < riB[0] and riA[1] <= riB[0]:
                result.append(riA)
                iA += 1
            elif riB[0] < riA[1] and riB[1] <= riA[0]:
                result.append(riB)
                iB += 1
            else:
                if riA[0] <= riB[0]:
                    if riB[1] <= riA[1]:
                        if riA[0] < riB[0] - 1:
                            result.append((riA[0], riB[0] - 1, riA[2]))
                        result.append((riB[0], riB[1], riA[2]))
                        if riB[1] + 1 < riA[1]:
                            renderIntervalsA2[iA] = (riB[1] + 1, riA[1], riA[2])
                        else:
                            iA += 1
                        iB += 1
                    else: # riA[1] < riB[1]
                        result.append(riA)
                        iA += 1
                        if riA[1] + 1 < riB[1]:
                            renderIntervalsB2[iB] = (riA[1] + 1, riB[1], riB[2])
                        else:
                            iB += 1
                else: # riB[0] < riA[0]
                    result.append((riB[0], riA[0] - 1, riB[2]))
                    if riB[1] <= riA[1]:
                        if riA[0] < riB[1]:
                            renderIntervalsB2[iB] = (riA[0], riB[1], riB[2])
                        else:
                            iB += 1
                    else: # riA[1] < riB[1]
                        result.append(riA)
                        iA += 1
                        if riA[1] + 1 < riB[1]:
                            renderIntervalsB2[iB] = (riA[1] + 1, riB[1], riB[2])
                        else:
                            iB += 1
    return result

DefaultNumSamples = 100
if useSeparateNeuronFiles:
    DefaultNumSamples = 150

def addSamplesPerInterval(renderIntervals, fadingIntervals, dollyIntervals):
    renderIntervals2 = [ri + (DefaultNumSamples, ) for ri in renderIntervals]
    fadingIntervals2 = [fi + (int(DefaultNumSamples / 2), ) for fi in fadingIntervals]

    # Using 5x samples here seems like overkill, but as of Octane Blender 2019/11/06,
    # it seems to be the only way to be sure there is no flicker from the denoiser.
    dollyIntervals2 = [di + (int(5 * DefaultNumSamples), ) for di in dollyIntervals]

    # Increases due to dollying have the highest priority.  Then decreases due to fading.
    renderIntervals3 = combineRenderIntervals(dollyIntervals2, fadingIntervals2)

    # Both of those changes have priority over the normal sampling rate.
    renderIntervals4 = combineRenderIntervals(renderIntervals3, renderIntervals2)

    # Then clip renderIntervals4 so there is nothing before the start of
    # renderIntervals or after its end.
    start = renderIntervals[0][0]
    end = renderIntervals[-1][1]
    renderIntervals5 = []
    for ri in renderIntervals4:
        if start <= ri[0] and ri[1] <= end:
            renderIntervals5.append(ri)

    return renderIntervals5

def separateNeuronFilesHideRender(obj, hideRenderTrue, useOctane):
    matName = "Material." + obj.name
    if not matName in bpy.data.materials:
        return
    mat = bpy.data.materials[matName]
    if obj.name.startswith("Neuron.proxy"):
        if not obj.name in hideRenderTrue:
            # Append and render the real neurons referenced by the proxy
            neuronFile = obj["neuronFile"]
            objsDir = neuronFile + "/Object"
            matsDir = neuronFile + "/Material"
            for id in obj["ids"]:
                referencedObjName = "Neuron." + str(id)
                bpy.ops.wm.append(filename=referencedObjName, directory=objsDir)
                referencedMatName = "Material." + referencedObjName
                bpy.ops.wm.append(filename=referencedMatName, directory=matsDir)

                referencedObj = bpy.data.objects[referencedObjName]
                rescaleRecenter(referencedObj, overallCenter, overallScale)
                if useOctane:
                    addOctaneMaterial(referencedObj, mat)

            # But do not render the proxy itself.
            obj.hide_render = True

    else:
        # Remove all neurons appended previously.
        try:
            bpy.data.materials.remove(mat, do_unlink=True)
            bpy.data.objects.remove(obj, do_unlink=True)
        except:
            pass

def render(renderIntervalsClipped, hideRenderTrueFrames, justPrint=False):
    global args

    renderIntervals = renderIntervalsClipped
    if args.useOctane and not args.doRois:
        fadingIntervals = findFadingIntervals(hideRenderTrueFrames)
        dollyIntervals = findDollyIntervals()
        renderIntervals = addSamplesPerInterval(renderIntervalsClipped, fadingIntervals, dollyIntervals)

    numFramesCopied = 0
    j = 0
    for i in range(len(renderIntervals)):
        ri = renderIntervals[i]
        fStart = int(ri[0])
        fEnd = int(ri[1])

        # TODO: Improve on this say to handle the short render intervals generated by
        # the "stagger" option to the "fade" command.
        if bpy.context.scene.frame_step > 1 and fEnd - fStart < 2:
            continue

        if args.useOctane and not args.doRois:
            numSamples = DefaultNumSamples
            if len(ri) == 3:
                numSamples = int(ri[2])
            if args.numSamples:
                numSamples = args.numSamples
            bpy.context.scene.octane.max_samples = numSamples

        hideRenderTrue = hideRenderTrueAtFrame(fStart, hideRenderTrueFrames)

        if justPrint:
            if args.useOctane and not args.doRois:
                print("rendering from frame {} to {}, with {} objects hidden, {} samples".
                    format(fStart, fEnd, len(hideRenderTrue), bpy.context.scene.octane.max_samples))
            else:
                print("rendering from frame {} to {}".format(fStart, fEnd))
        else:
            if not args.doRois:
                for obj in bpy.data.objects:
                    if args.useCycles or obj.name.startswith("Neuron"):
                        if useSeparateNeuronFiles:
                            separateNeuronFilesHideRender(obj, hideRenderTrue, args.useOctane)
                        else:
                            # Path-traced renderers (e.g., Octane or Cycles) produce dark artifacts for
                            # fully transparent objects (alpha == 0), so such objects must be explicitly
                            # excluded from the rendering.
                            obj.hide_render = (obj.name in hideRenderTrue)
            bpy.context.scene.frame_start = fStart
            bpy.context.scene.frame_end = fEnd
            bpy.ops.render.render(animation=True)
        ext = ".png"
        if willComp:
            ext = ".exr"
        if i < len(renderIntervals) - 1:
            # TODO: Instead of skipping over the resting intervals when frame_step > 1,
            # add a way to do the stepping within those intervals.
            if bpy.context.scene.frame_step == 1:
                riNext = renderIntervals[i + 1]
                fStartCopy = fEnd + 1
                fEndCopy = int(riNext[0])
                if fStartCopy < fEndCopy:
                    if justPrint:
                        print("copying from frame {} to frame {}".format(fStartCopy, fEndCopy))
                    else:
                        src = output + str(fEnd).zfill(4) + ext
                        for j in range(fStartCopy, fEndCopy):
                            dst = output + str(j).zfill(4) + ext
                            shutil.copy(src, dst)
                            numFramesCopied += 1
    return numFramesCopied

bpy.context.scene.render.resolution_x = args.resX
bpy.context.scene.render.resolution_y = args.resY

if not disableStandardOutput:
    bpy.context.scene.render.filepath = output
else:
    tmpDir = tempfile.TemporaryDirectory().name
    tmpDir = os.path.join(tmpDir, "")
    bpy.context.scene.render.filepath = tmpDir
    print("Non-compositing output redirected to '{}'".format(tmpDir))

print(bpy.context.scene.render.engine)

if args.useCycles:
    cyclesPrefs = bpy.context.preferences.addons["cycles"].preferences
    if bpy.app.version >= (2, 93, 0):
        # Eliminates the "Synchronizing object" steps, but uses more memory.
        bpy.data.scenes["Scene"].render.use_persistent_data = args.usePersistentData
        print("Cycles using persistent data: {}".format(bpy.data.scenes["Scene"].render.use_persistent_data))

    bpy.context.scene.cycles.device = "CPU"
    cyclesPrefs.compute_device_type = "NONE"    
    if platform.system == "Darwin":
        # https://docs.blender.org/manual/en/latest/render/cycles/gpu_rendering.html#metal-apple-macos
        # "macOS 12.2 is required to use Metal with Apple Silicon"
        if args.useMetal:
            bpy.context.scene.cycles.device = "GPU"
            cyclesPrefs.compute_device_type = "METAL"
    else:
        if args.useOptix:
            bpy.context.scene.cycles.device = "GPU"
            cyclesPrefs.compute_device_type = "OPTIX"
        elif args.useCuda:
            bpy.context.scene.cycles.device = "GPU"
            cyclesPrefs.compute_device_type = "CUDA"
        elif args.useHip:
            bpy.context.scene.cycles.device = "GPU"
            cyclesPrefs.compute_device_type = "HIP"
    if bpy.context.scene.cycles.device == "GPU":
        cyclesPrefs.get_devices()
        for device in cyclesPrefs.devices:
            device["use"] = True
    print("Cycles device: {} {}".format(bpy.context.scene.cycles.device, cyclesPrefs.compute_device_type))


render(renderIntervalsClipped, hideRenderTrueFrames, justPrint=True)

if args.debug:
    print("Debugging, so quitting")
    quit()

numFramesTotal = fEndOverall - fStartOverall + 1
numFramesCopied = render(renderIntervalsClipped, hideRenderTrueFrames)

#

timeEnd = datetime.datetime.now()
print("Rendering started at {}".format(timeStart))
print("Copied {} frames of {} total".format(numFramesCopied, numFramesTotal))
print("Rendering ended at {}".format(timeEnd))

if disableStandardOutput:
    try:
        shutil.rmtree(tmpDir)
    except OSError as e:
        print("Error: %s : %s" % (tmpDir, e.strerror))
