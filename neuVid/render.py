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
import shutil
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsJson import removeComments

timeStart = datetime.datetime.now()

argv = sys.argv
if "--" not in argv:
    argv = []
else:
    argv = argv[argv.index("--") + 1:]

parser = argparse.ArgumentParser()
parser.add_argument("--inputBlender", "-ib", dest="inputBlenderFile", help="path to the input .blend file")
parser.add_argument("--inputJson", "-ij", dest="inputJsonFile", help="path to the JSON file describing the input")
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
parser.add_argument("--samples", "-sa", type=int, dest="numSamples", help="number of samples per pixel for the Octane renderer")
parser.set_defaults(denoise=True)
parser.add_argument("--nodenoise", "-ndn", dest="denoise", action="store_false", help="skip final denoising")
parser.set_defaults(filterSizeFactor=1.0)
parser.add_argument("--filter", "-f", type=float, dest="filterSizeFactor", help="filter size factor")
parser.set_defaults(onlyAmbient=False)
parser.add_argument("--ambient", "-amb", dest="onlyAmbient", action="store_true", help="use only ambient lighting")
parser.set_defaults(debug=False)
parser.add_argument("--debug", "-d", dest="debug", action="store_true", help="debug")

args = parser.parse_args(argv)

print("Rendering ROIs and unlit content: {}".format(args.doRois))
if args.doRois:
    print("Compatibilty with Octane renderer: {}".format(args.useOctane))
else:
    print("Using Octane renderer: {}".format(args.useOctane))
print("Using fps: {}".format(bpy.context.scene.render.fps))

if args.output != None:
    output = args.output
else:
    output = "."
if output[-1] != "/":
    output += "/"
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
print("Using input Blender file: '{}'".format(inputBlenderFile))

bpy.ops.wm.open_mainfile(filepath=inputBlenderFile)

useSeparateNeuronFiles = all(map(lambda x: not x.name.startswith("Neuron") or
    x.name.startswith("Neuron.proxy"), bpy.data.objects))

hasSynapses = any(map(lambda x: x.name.startswith("Synapses."), bpy.data.objects))

useOctane = args.useOctane

jsonLightPowerScale = [1.0, 1.0, 1.0]
jsonLightSizeScale = 1.0
jsonLightColor = "default"
if args.inputJsonFile:
    jsonData = json.loads(removeComments(args.inputJsonFile))
    if "lightPowerScale" in jsonData:
        jsonLightPowerScale = jsonData["lightPowerScale"]
        print("Using lightPowerScale: {}".format(jsonLightPowerScale))
    if "lightSizeScale" in jsonData:
        jsonLightSizeScale = jsonData["lightSizeScale"]
        print("Using lightSizeScale: {}".format(jsonLightSizeScale))
    if "lightColor" in jsonData:
        jsonLightColor = jsonData["lightColor"]
        print("Using lightColor: {}".format(jsonLightColor))

#

print("Rescaling/recentering to improve numerical precision...")

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
                newMat = mathutils.Matrix.Translation(newTrans) * oldRot.to_matrix().to_4x4()
                con.inverse_matrix = newMat.inverted()

# If using Octane to render neurons, then ROIs should be rendered with "--roi --octane"
# to get the same overallScale.  Then useOctane is disabled so the ROIs will be rendered
# with the standard Blender Render.

overallScale = 0.00001
if useOctane:
    overallScale = 0.01
print("Using overall scale: {}".format(overallScale))
if args.doRois:
    useOctane = False

if useOctane:
    # For a test cube, this change to ray_epsilon eliminated ringing.
    bpy.data.scenes["Scene"].octane.ray_epsilon *= 10
    print("Using ray_epsilon: {}".format(bpy.data.scenes["Scene"].octane.ray_epsilon))

overallCenter = bpy.data.objects["Bound.neurons"].location.copy()
print("Using overall center: {}".format(overallCenter))

for obj in bpy.data.objects:
    rescaleRecenter(obj, overallCenter, overallScale)

camera = bpy.data.cameras["Camera"]
camera.clip_start *= overallScale
camera.clip_end *= overallScale

print("Done")

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
        # Make the "Material" node use the non-node material being used
        # to preview in the UI's 3D View, so its animated alpha can be
        # reused as an input to alphaNode, below.  Thus we can preview
        # the animation in the 3D View and also see it in the final render.

        matNode = matNodes["Material"]
        matNode.material = mat

    glossyNode = matNodes.new("ShaderNodeOctGlossyMat")
    # Diffuse color is inputs[0]
    c = mat.diffuse_color
    glossyNode.inputs[0].default_value = (c[0], c[1], c[2], 1.0)

    if not animMat:
        animMat = mat
    if animMat.animation_data:
        # Opacity is inputs[11]
        # To transfer the animation from the material's alpha to this opacity,
        # it does not work to just add a link like the following:
        # matLinks.new(matNode.outputs["Alpha"], glossyNode.inputs[11])
        # Instead, it seems to be necessary to copy the keys.
        fcurvesAlpha = animMat.animation_data.action.fcurves.find(data_path="alpha")
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

    outputNode = matNodes.new("ShaderNodeOutputMaterial")

    # Connect the glossy node's "OutMat" output to the output node's "surface" input.
    matLinks.new(glossyNode.outputs[0], outputNode.inputs[0])

if args.doRois:
    for obj in bpy.data.objects:
        if obj.name.startswith("Neuron."):
            obj.hide = True
            obj.hide_render = True

    bpy.data.scenes["Scene"].render.use_textures = True
    bpy.data.scenes["Scene"].render.use_sss = False
    bpy.data.scenes["Scene"].render.use_shadows = False
    bpy.data.scenes["Scene"].render.use_raytrace = False
    bpy.data.scenes["Scene"].render.use_envmaps = False
else:
    if useOctane:
        print("Adding Octane materials...")
        for obj in bpy.data.objects:
            if obj.name.startswith("Roi.") or obj.name.startswith("ImagePlane.") or obj.name.startswith("Synapses."):
                matName = "Material." + obj.name
                if matName in bpy.data.materials:
                    mat = bpy.data.materials[matName]
                    bpy.data.materials.remove(mat, True)
                bpy.data.objects.remove(obj, True)
            elif obj.name.startswith("Neuron.") and not useSeparateNeuronFiles:
                addOctaneMaterial(obj)
        print("Done")
    else:
        bpy.data.scenes["Scene"].render.use_shadows = True
        bpy.data.scenes["Scene"].render.use_textures = True
        bpy.data.scenes["Scene"].render.use_sss = False
        bpy.data.scenes["Scene"].render.use_raytrace = False
        bpy.data.scenes["Scene"].render.use_envmaps = False

        print("Updating Blender materials...")
        for obj in bpy.data.objects:
            if obj.name.startswith("Neuron.") and not useSeparateNeuronFiles:
                matName = "Material." + obj.name
                if matName in bpy.data.materials:
                    mat = bpy.data.materials[matName]
                    if mat.animation_data:
                        fcurvesAlpha = mat.animation_data.action.fcurves.find(data_path="alpha")
                        if fcurvesAlpha:
                            # To make an object transparent it is not sufficient to set just its material's alpha.
                            # The material's specular_alpha must be set, too.  Using a driver to tie the specular_alpha
                            # to the alpha seems difficult to do, so just copy the alpha animation.
                            keyframes = fcurvesAlpha.keyframe_points
                            for i in range(len(keyframes)):
                                mat.specular_alpha = keyframes[i].co[1]
                                mat.keyframe_insert("specular_alpha", frame=keyframes[i].co[0])
        print("Done")

if not args.doRois or hasSynapses:
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
        neuronsBound = bpy.data.objects["Bound.neurons"]
        neuronsBoundRadius = neuronsBound["Radius"]
        for i in range(len(lampSpecs)):
            spec = lampSpecs[i]
            lampName = "Lamp." + str(i)
            if useOctane:
                lampData = bpy.data.lamps.new(name=lampName, type="AREA")
                lampData.use_nodes = True

                lampData.size = neuronsBoundRadius
                if "sizeFactor" in spec:
                    sizeFactor = spec["sizeFactor"]
                    lampData.size *= sizeFactor
                lampData.size *= jsonLightSizeScale
            else:
                lampData = bpy.data.lamps.new(name = "Lamp.Key", type = "SPOT")
                lampData.energy = 1.5
                lampData.energy *= jsonLightPowerScale[i]
                if jsonLightColor != "uniform":
                    lampData.color = spec["color"][0:3]
                lampData.falloff_type = "CONSTANT"
                lampData.spot_size = 1.4
                lampData.shadow_method = "BUFFER_SHADOW"
                lampData.use_auto_clip_start = True
                lampData.use_auto_clip_end = True
            lamp = bpy.data.objects.new(name=lampName, object_data=lampData)
            bpy.context.scene.objects.link(lamp)
            lamps.append(lamp)

            direction = mathutils.Vector(spec["direction"])
            direction.normalize()
            lampDistance = neuronsBoundRadius * 2.5
            lamp.location = direction * lampDistance

            lampTrackTo = lamp.constraints.new(type="TRACK_TO")
            lampTrackTo.target = neuronsBound
            lampTrackTo.track_axis = "TRACK_NEGATIVE_Z"
            lampTrackTo.up_axis = "UP_X"

            if useOctane:
                lampLamp = bpy.data.lamps[lampData.name]
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

                print("lamp {} power {} after scaling by {}".format(i, lampEmit.inputs[1].default_value, powerScale))

                if "powerFactor" in spec:
                    powerFactor = spec["powerFactor"]
                    lampEmit.inputs[1].default_value *= powerFactor
                lampOutput = lampNodes["Lamp Output"]
                lampLinks.new(lampDiffuse.outputs[0], lampOutput.inputs[0])

        # Put the lights in the correct orientation for the "standard" view,
        # with positive X right, positive Y out, positive Z down.
        lampRotator = bpy.data.objects.new("Lamps", None)
        bpy.context.scene.objects.link(lampRotator)
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
        # Rendering background color
        bpy.data.worlds["World"].horizon_color = (0, 0, 0)

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
            # Turn on the AI denoiser.
            bpy.context.scene.camera.data.octane.enable_denoising = True
            bpy.context.scene.camera.data.octane.denoise_on_completion = True

            # Eliminate flickering during animation, at least in theory.
            bpy.context.scene.octane.static_noise = True

            # Denoising requires turning on the "Octane Camera Imager (Render Mode)"
            bpy.context.scene.octane.hdr_tonemap_render_enable = True

            # The denoised result will be in a special beauty pass, called "OctDenoiserBeauty".
            bpy.context.scene.octane.use_passes = True
            bpy.context.scene.render.layers["RenderLayer"].use_pass_denoise_beauty = True

        bpy.context.scene.octane.filter_size *= args.filterSizeFactor
        print("Using filter size: {}".format(bpy.context.scene.octane.filter_size))


if willComp:
    # Use a transparent background, for compositing with other renderings (e.g., ROI)
    if useOctane:
        bpy.context.scene.octane.alpha_channel = True
    else:
        bpy.context.scene.render.alpha_mode = "TRANSPARENT"
    # Save depth with the output image
    bpy.context.scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
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

def addRestIntervals(collection):
    global restIntervals, numCurves
    for obj in collection:
        if obj.animation_data:
            for fc in obj.animation_data.action.fcurves:
                if fc.data_path.endswith(("location", "rotation_euler", "alpha", "diffuse_color")):
                    if (obj.name == "Orbiter" or obj.name.endswith(".Pivot")) and fc.data_path.endswith("location"):
                        continue

                    numCurves += 1
                    id = obj.name + "." + fc.data_path + "." + str(fc.array_index)
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
    for tex in bpy.data.textures:
        if isinstance(tex, bpy.types.ImageTexture):
            if tex.image.source == "MOVIE":
                numCurves += 1
                id = tex.name
                iu = tex.image_user
                restIntervals.append((1, "s", id))
                restIntervals.append((iu.frame_start, "e", id))
                restIntervals.append((iu.frame_start + iu.frame_duration, "s", id))
                restIntervals.append((bpy.data.scenes["Scene"].frame_end, "e", id))

addRestIntervals(bpy.data.objects)
addRestIntervals(bpy.data.materials)
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

fStartOverall = bpy.data.scenes["Scene"].frame_start
if args.start != None:
    fStartOverall = args.start

fEndOverall = bpy.data.scenes["Scene"].frame_end
if args.end != None:
    fEndOverall = args.end

if args.step != None:
    bpy.context.scene.frame_step = args.step

# TODO: There is a problem if fStartOverall is bewteen render intervals:
# we need to render one frame at the end of the preceding render interval,
# then copy.
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

def findHideRenderFrames(materials):
    hideRenderAtFrame = {}
    for mat in materials:
        name = mat.name[mat.name.find(".")+1:]
        if mat.animation_data:
            for fc in mat.animation_data.action.fcurves:
                if fc.data_path.endswith(("alpha")):
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
    return [];

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
        if mat.animation_data:
            for fc in mat.animation_data.action.fcurves:
                if fc.data_path.endswith(("alpha")):
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

    return renderIntervals4

def separateNeuronFilesHideRender(obj, hideRenderTrue):
    matName = "Material." + obj.name
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
                addOctaneMaterial(referencedObj, mat)

            # But do not render the proxy itself.
            obj.hide_render = True

    else:
        # Remove all neurons appended previously.
        try:
            bpy.data.materials.remove(mat, True)
            bpy.data.objects.remove(obj, True)
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
            if args.numSamples != None:
                numSamples= args.numSamples
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
                    if obj.name.startswith("Neuron"):
                        if useSeparateNeuronFiles:
                            separateNeuronFilesHideRender(obj, hideRenderTrue)
                        else:
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

bpy.context.scene.render.filepath = output

print(bpy.context.scene.render.engine)

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
