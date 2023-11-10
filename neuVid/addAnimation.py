# Adds animation to a basic Blender file created by importMeshes.py.
# Runs relatively quickly to allow iteration on the details of the animation being added to
# the same basic Blender file.

# Run in Blender, e.g.:
# blender --background --python addAnimation.py -- -ij movieScript.json -ib movieWithoutAnimation.blend -ob movieWithAnimation.blend
# Assumes Blender 2.79.

import argparse
import bmesh
import bpy
import collections
import colorsys
import json
import math
import mathutils
import numbers
import os
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsColors import colors, getColor
from utilsGeneral import newObject, report_version
from utilsMaterials import getMaterialValue, insertMaterialKeyframe, newShadelessImageMaterial, setMaterialValue
from utilsJson import guess_extraneous_comma, parseFov, parseNeuronsIds, parseRoiNames, parseSynapsesSetNames, removeComments
from utilsNg import ng_camera_look_from, quat_ng_to_blender

report_version()

argv = sys.argv
if "--" not in argv:
    argv = []
else:
    argv = argv[argv.index("--") + 1:]

parser = argparse.ArgumentParser()
parser.add_argument("--inputJson", "-ij", "-i", dest="inputJsonFile", help="path to the JSON file describing the input")
parser.add_argument("--inputBlender", "-ib", dest="inputBlenderFile", help="path to the input .blend file")
parser.add_argument("--output", "-o", dest="outputFile", help="path for the output .blend file")
args = parser.parse_args(argv)

if args.inputJsonFile == None:
    parser.print_help()
    sys.exit()

inputBlenderFile = args.inputBlenderFile
if inputBlenderFile == None:
    inputBlenderFile = os.path.splitext(args.inputJsonFile)[0] + ".blend"
print("Using input Blender file: '{}'".format(inputBlenderFile))

outputFile = args.outputFile
if outputFile == None:
    outputFile = os.path.splitext(args.inputJsonFile)[0] + "Anim.blend"
print("Using output Blender file: '{}'".format(outputFile))

try:
    jsonData = json.loads(removeComments(args.inputJsonFile))
except json.JSONDecodeError as exc:
    print("Error reading JSON, line {}, column {}: {}".format(exc.lineno, exc.colno, exc.msg))
    guess_extraneous_comma(args.inputJsonFile)
    sys.exit()

if jsonData == None:
    print("Loading JSON file {} failed".format(args.inputJsonFile))
    sys.exit()

if "neurons" in jsonData:
    jsonNeurons = jsonData["neurons"]
    neuronIds, groupToNeuronIds, _, useSeparateNeuronFiles = parseNeuronsIds(jsonNeurons)

if "rois" in jsonData:
    jsonRois = jsonData["rois"]
    roiNames, groupToRoiNames, _ = parseRoiNames(jsonRois)

if "synapses" in jsonData:
    jsonSynapses = jsonData["synapses"]
    groupToSynapseSetNames = parseSynapsesSetNames(jsonSynapses)

if not "animation" in jsonData:
    print("JSON contains no 'animation' key, whose value is lists of commands specifying the animation")
    sys.exit()
jsonAnim = jsonData["animation"]

def meshObjs(name):
    global groupToNeuronIds, groupToRoiNames, groupToSynapseSetNames, useSeparateNeuronFiles

    # Support names of the form "A - B + C - D", meaning everything in A or C
    # that is not also in B or D.  Use `OrderedDict` to preserve the order of items
    # as much as possible (e.g., the order of E in "E - F" or even simply "E").

    addObjNames = collections.OrderedDict()
    subObjNames = collections.OrderedDict()
    sub = False
    for x in name.split():
        if x == "+":
            sub = False
        elif x == "-":
            sub = True
        else:
            dest = addObjNames
            if sub:
                dest = subObjNames
            i = x.find(".")
            if i != -1:
                # x is something like "neurons.a"
                type = x[0:i]
                group = x[i + 1:]
                if type == "neurons":
                    if useSeparateNeuronFiles:
                        # For now, at least, support only the simplest case when using
                        # one or more separate files of neuron IDs.
                        if len(name.split()) == 1:
                            dest["Neuron.proxy." + group] = None
                        else:
                            print("Error: mesh expressions with '+'/'-' are not supported for separate neuron files")
                            sys.exit()
                    else:
                        for neuronId in groupToNeuronIds[group]:
                            dest["Neuron." + neuronId] = None
                elif type == "rois":
                    for roiName in groupToRoiNames[group]:
                        dest["Roi." + roiName] = None
                elif type == "synapses":
                    for synapseSetName in groupToSynapseSetNames[group]:
                        dest["Synapses." + synapseSetName] = None
            else:
                # x is "neurons", "rois" or "synapses"
                for o in bpy.data.objects:
                    if o.name.startswith(x[:-1].capitalize()):
                        dest[o.name] = None

    if len(addObjNames) == 0:
        return None

    result = []
    for objName in addObjNames.keys():
        if not objName in subObjNames:
            result.append(bpy.data.objects[objName])
    return result

def bounds(name):

    # Support names of the form "A + B + C", meaning a union.

    terms = [term.strip() for term in name.split("+")]

    limit = sys.float_info.max
    bboxMin = [ limit,  limit,  limit]
    bboxMax = [-limit, -limit, -limit]

    for term in terms:
        boundName = "Bound." + term
        if boundName in bpy.data.objects:
            bound = bpy.data.objects[boundName]
            termBboxMin = bound["Min"]
            termBboxMax = bound["Max"]
            for i in range(len(bboxMin)):
                bboxMin[i] = min(bboxMin[i], termBboxMin[i])
                bboxMax[i] = max(bboxMax[i], termBboxMax[i])
        else:
            print("Error: unknown bound name '{}'".format(boundName))

    bboxCenter = mathutils.Vector(((bboxMin[0] + bboxMax[0]) / 2, (bboxMin[1] + bboxMax[1]) / 2, (bboxMin[2] + bboxMax[2]) / 2))

    maxRadius = -limit
    for term in terms:
        boundName = "Bound." + term
        if boundName in bpy.data.objects:
            bound = bpy.data.objects[boundName]
            radius = bound["Radius"]
            radius = (bboxCenter - mathutils.Vector(bound.location)).length + radius
            maxRadius = max(maxRadius, radius)

    return bboxCenter, bboxMin, bboxMax, maxRadius

def updateCameraClip(camName):
    cam = bpy.data.cameras[camName]
    camObj = bpy.data.objects[camName]

    camLoc1 = camObj.location
    # When the camera has a parent (e.g., for orbiting), the following is better.
    # But the previous is still needed if scene.frame_set(t) was not called.
    camLoc2 = camObj.matrix_world.translation

    for which in ["Bound.neurons", "Bound.rois"]:
        if which in bpy.data.objects:
            bnd = bpy.data.objects[which]
            ctr = bnd.location
            d = max((camLoc1 - ctr).magnitude, (camLoc2 - ctr).magnitude)
            d += bnd["Radius"]
            if d > cam.clip_end:
                cam.clip_end = d
                print("Updating '{}' clip_end to {}".format(camName, cam.clip_end))

#

time = 0.0
tentativeEndTime = time

fps = 24
if "fps" in jsonData:
    fps = round(jsonData["fps"])
print("Using fps: {}".format(fps))

def frame(t = None):
    global time
    if t == None:
        t = time
    return round(t * fps) + 1

def imagePlane(source, parented=False, aligned=True, flip=True):
    name = "ImagePlane." + os.path.basename(source)
    if not name in bpy.data.objects:
        mat = newShadelessImageMaterial("Material." + name, source)
        setMaterialValue(mat, "alpha", 0)

        bpy.ops.mesh.primitive_plane_add()
        plane = bpy.context.active_object
        plane.name = name

        constrained = plane
        if parented:
            pivotName = plane.name + ".Pivot"
            pivot = newObject(pivotName)
            plane.parent = pivot
            constrained = pivot

        # For showSlice
        if aligned:
            constraint = constrained.constraints.new(type="TRACK_TO")
            constraint.name = "AlignToCamera"
            constraint.target = bpy.data.objects["Camera"]
            constraint.track_axis = "TRACK_Z"
            constraint.up_axis = "UP_Y"

        bpy.ops.object.mode_set(mode="EDIT")
        me = plane.data
        bm = bmesh.from_edit_mesh(me)

        uv_layer = bm.loops.layers.uv.verify()
        if bpy.app.version < (2, 80, 0):
            bm.faces.layers.tex.verify()

        for f in bm.faces:
            for l in f.loops:
                luv = l[uv_layer]
                v = l.vert.co
                if flip:
                    luv.uv = (1.0 - (v[0] + 1.0)/2.0, 1.0 - (v[1] + 1.0)/2.0)
                else:
                    luv.uv = ((v[0] + 1.0)/2.0, 1.0 - (v[1] + 1.0)/2.0)
        bmesh.update_edit_mesh(me)

        plane.data.materials.append(mat)

        if bpy.app.version < (2, 80, 0):
            # Make the object appear transparent in the interactive viewport rendering.
            plane.show_transparent = True

            # These last two steps are necessary to make the texture appear when
            # viewport shading mode is "Texture" (it will appear for "Material" without them)
            plane.data.uv_textures.new()
            # TODO: Why is data[0] not there?
            #plane.data.uv_textures[0].data[0].image = img

        # Prevent shadows from these objects in renderers like Cycles.
        if bpy.app.version >= (3, 0, 0):
            plane.visible_shadow = False
            plane.visible_diffuse = False
            plane.visible_glossy = False
        elif bpy.app.version >= (2, 80, 0):
            plane.cycles_visibility.shadows = False

        bpy.ops.object.mode_set(mode="OBJECT")

        return plane

def keysAtFrame(obj, dataPath, frame):
    result = []
    if obj.animation_data:
        for fc in obj.animation_data.action.fcurves:
            if fc.data_path.endswith(dataPath):
                for key in fc.keyframe_points:
                    if key.co[0] == frame:
                        result.append(key)
                        break
    return result

#

def validateCmdArgs(cmdName, supportedArgs, actualArgs):
    for arg in actualArgs.keys():
        if not arg in supportedArgs:
            supportedArgs.sort()
            print("For animation command: {}\nUnrecognized argument: {}".format(cmdName, arg))
            print("Supported arguments: {}".format(", ".join(supportedArgs)))
            sys.exit()

# The Python function implementing command `x` must be named `xCmd`.  The `Cmd` suffix simplifies  
# printing all the supported commands when an erroneous command is parsed.

def advanceTimeCmd(args):
    validateCmdArgs("advanceTime", ["by"], args)

    global time, tentativeEndTime
    if "by" in args:
        by = args["by"]
        if isinstance(by, numbers.Number):
            time += by
            tentativeEndTime = max(time, tentativeEndTime)
        else:
            print("Error: advanceTime: argument 'by' is not a number")
            sys.exit()
    else:
        print("Error: advanceTime: missing argument 'by'")
        sys.exit()

def setValueCmd(args):
    validateCmdArgs("setValue", ["meshes", "alpha", "color", "exponent", "threshold", "stagger"], args)

    # Makes an instantaneous change, so mostly useful for setting an initial value.
    if "meshes" in args:
        meshes = args["meshes"]

        if "alpha" in args:
            alpha = args["alpha"]
            print("{}: setValue meshes '{}' alpha {}".format(frame(), meshes, alpha))
        elif "color" in args:
            colorId = args["color"]
            color = getColor(colorId, colors)

            staggerFrac = 0
            if "stagger" in args:
                staggerFrac = args["stagger"]

            colorFormatted = [round(c, 2) for c in color]
            print("{}: setValue meshes '{}' color {}: {}, staggerFrac {}".format(frame(), meshes, colorId, colorFormatted, staggerFrac))

            if staggerFrac:
                # "Stagger" here means to assign the meshes variations on the basic color.
                colorHSV0 = colorsys.rgb_to_hsv(color[0], color[1], color[2])
                colorHSV = (colorHSV0[0], colorHSV0[1] * (1 - staggerFrac), colorHSV0[2] * (1 - staggerFrac))
        elif "exponent" in args:
            exp = args["exponent"]
            print("{}: setValue meshes '{}' exponent {}".format(frame(), meshes, exp))
        elif "threshold" in args:
            threshold = args["threshold"]
            print("{}: setValue meshes '{}' threshold {}".format(frame(), meshes, threshold))
        else:
            print("Error: setValue: unsupported arguments {}".format(args))
            return

        objs = meshObjs(meshes)

        if "color" in args and staggerFrac:
            deltaS = (colorHSV0[1] - colorHSV[1]) / (len(objs) - 1)
            deltaV = (colorHSV0[2] - colorHSV[2]) / (len(objs) - 1)

        for obj in objs:
            matName = "Material." + obj.name
            mat = obj.data.materials[matName]

            if frame() != 1:
                if "alpha" in args:
                    insertMaterialKeyframe(mat, "alpha", frame=frame()-1)
                else:
                    insertMaterialKeyframe(mat, "diffuse_color", frame=frame()-1)

            if "alpha" in args:
                setMaterialValue(mat, "alpha", alpha)
                insertMaterialKeyframe(mat, "alpha", frame())
            elif "color" in args:
                if staggerFrac:
                    color = colorsys.hsv_to_rgb(colorHSV[0], colorHSV[1], colorHSV[2])
                    colorHSV = (colorHSV[0], colorHSV[1] + deltaS, colorHSV[2] + deltaV)

                setMaterialValue(mat, "diffuse_color", color)
                insertMaterialKeyframe(mat, "diffuse_color", frame=frame())
            elif "exponent" in args:
                try:
                    setMaterialValue(mat, "exponent", exp)
                    insertMaterialKeyframe(mat, "exponent", frame())
                except:
                    print("'{}' does not support 'exponent'.".format(matName))
                    sys.exit()
            else:
                try:
                    setMaterialValue(mat, "threshold", threshold)
                    insertMaterialKeyframe(mat, "threshold", frame())
                except:
                    print("'{}' does not support 'threshold'.".format(matName))
                    sys.exit()

def bboxAxisForViewVector(v):
    # TODO: Pick the axis with maximal projection?
    return 2

def frameCameraCmd(args):
    validateCmdArgs("frameCamera", ["bound", "scale", "duration"], args)

    global time, tentativeEndTime, lastCameraCenter
    camera = bpy.data.objects["Camera"]
    duration = 0
    if "duration" in args:
        duration = args["duration"]
        tentativeEndTime = max(time + duration, tentativeEndTime)

    scale = 1.0
    if "scale" in args:
        scale = args["scale"]

    if "bound" in args:
        bboxCenter, bboxMin, bboxMax, radius = bounds(args["bound"])

        startFrame = frame()
        # The following can prevent a little "wiggle" at the transition from a
        # partial orbit to a framing.  But it is important to have the clause
        # that skips frame 1 at the start of the animation, or else the initial
        # speed of a framing dolly at that point is too high.  Also, orbitCamera
        # should NOT have code like this, or else the preceding framing ends
        # too abruptly.
        if startFrame > 1 and len(keysAtFrame(camera, "location", startFrame)) > 0:
            startFrame += 1

        if scale == 1.0:
            print("{}, {}: frameCamera, '{}'".format(startFrame, frame(time + duration), args["bound"]))
        else:
            print("{}, {}: frameCamera, '{}', scale {}".format(startFrame, frame(time + duration), args["bound"], scale))

        camera.keyframe_insert("location", frame=startFrame)

        # Heuristic for tightening radius?  Works pretty well, for -Z up.
        i = bboxAxisForViewVector(lastViewVector)
        b = bboxMax[i] - bboxCenter[i]
        radius = radius * (2/3) + b * (1/3)

        lastCameraCenter = bboxCenter

        angle = bpy.data.cameras["Camera"].angle
        render = bpy.context.scene.render
        aspectRatio = render.resolution_y / render.resolution_x
        angle = 2.0 * math.atan(math.tan(angle / 2.0) * aspectRatio)

        dist = radius / math.sin(angle / 2.0)
        dist *= scale

        eye = lastCameraCenter + dist * lastViewVector
        camera.location = eye
        camera.keyframe_insert("location", frame=frame(time + duration))
        updateCameraClip(camera.name)
    else:
        print("Error: frameCamera: unknown bound object '{}'".format(args["bound"]))

def fadeCmd(args):
    validateCmdArgs("fade", ["meshes", "image", "source", "startingAlpha", "endingAlpha", "startingColor", "endingColor", 
                             "startingLocation", "endingLocation", "stagger", "duration"], args)

    global time, tentativeEndTime
    startingValue = 1
    type = "alpha"
    if "startingAlpha" in args:
        startingValue = args["startingAlpha"]
    elif "startingColor" in args:
        colorId = args["startingColor"]
        startingValue = getColor(colorId, colors)[0:3]
        type = "diffuse_color"
    elif "startingLocation" in args:
        startingValue = args["startingLocation"]
        type = "location"

    endingValue = 0
    if type == "alpha" and "endingAlpha" in args:
        endingValue = args["endingAlpha"]
    elif type == "diffuse_color" and "endingColor" in args:
        colorId = args["endingColor"]
        endingValue = getColor(colorId, colors)[0:3]
    elif "endingLocation" in args:
        endingValue = args["endingLocation"]
        type = "location"

    else:
        print("Error: fade arguments {}".format(args))
        return
    duration = 1
    if "duration" in args:
        duration = args["duration"]
        tentativeEndTime = max(time + duration, tentativeEndTime)
    if "meshes" in args:
        meshes = args["meshes"]
        objs = meshObjs(meshes)
        if objs is None: # empty list of meshes skips the fade
            return

        startingTime = time
        deltaTime = []
        stagger = False
        accelerating = False

        # Accelerating pace: `"stagger": true`
        # Constant pace: `"stagger": "constant"` or `"stagger": "const"`, etc.
        # All at once: `"stagger": false` or no mention of "stagger"
        if "stagger" in args:
            stagger = args["stagger"]
            if len(objs) >= 6:
                if not isinstance(stagger, str) or not stagger.lower().startswith("const"):
                    accelerating = True

        # For stagger and not accelerating, each item fades on/off in this many frames.
        FADE_FRAMES_NOT_ACCEL = 3

        if type == "alpha" and len(objs) == 1 and "ids" in objs[0]:
            # Proxy for a separate Blender file.
            proxy = objs[0]
            proxyMatName = "Material." + proxy.name
            proxyMat = proxy.data.materials[proxyMatName]
            if not "alpha-fcurves" in proxyMat:
                proxyMat["alpha-fcurves"] = {}
            # IDs of what the proxy will be replaced by when the separate file is loaded.
            # Their animation must be stored on the proxy, to make staggering work.
            objs = proxy["ids"]

            # And the proxy itself must still have some overall animation, so render.py does not
            # think the proxy is always visible and should be expanded right away.
            startingFrame = frame(startingTime)
            endingFrame = frame(startingTime + duration)
            setMaterialValue(proxyMat, type, startingValue)
            insertMaterialKeyframe(proxyMat, type, startingFrame)
            setMaterialValue(proxyMat, type, endingValue)
            insertMaterialKeyframe(proxyMat, type, endingFrame)

        nStaggerSubgroup = 0
        if stagger:
            if len(objs) >= 6:
                nStaggerSubgroup = min(5, round(len(objs) / 6))
            else:
                nStaggerSubgroup = len(objs)
            if len(objs) < 6:
                deltaTime.append(duration / nStaggerSubgroup)
            elif accelerating:
                n0 = nStaggerSubgroup
                n1 = 2 * n0
                n2 = len(objs) - (n0 + n1)
                if n1 > n2 / 2:
                    n1 -= 1
                    n2 = len(objs) - (n0 + n1)
                deltaTime.append(duration / 3 / n0)
                deltaTime.append(duration / 3 / n1)
                deltaTime.append(duration / 3 / n2)
            else:
                durationWithoutLastFade = duration - FADE_FRAMES_NOT_ACCEL * (1 / fps)
                dt = durationWithoutLastFade / len(objs)
                for i in range(len(objs)):
                    deltaTime.append(dt)
                nStaggerSubgroup = 1

            print("{}, {}: fade, meshes '{}', {} {} to {}".
                format(frame(), frame(time + duration), meshes, type, startingValue, endingValue))
            if accelerating and len(deltaTime) > 1:
                print(" stagger: {} x {}, {} x {}, {} x {}".
                    format(n0, frame(deltaTime[0]), n1, frame(deltaTime[1]), n2, frame(deltaTime[2])))
            else:
                print(" stagger: {} x {}".
                    format(nStaggerSubgroup, frame(deltaTime[0])))
        else:
            deltaTime.append(duration)
            print("{}, {}: fade, meshes '{}', {} {} to {}".format(frame(), frame(time + duration),
                meshes, type, startingValue, endingValue))

        i = 0
        for obj in objs:
            startingFrame = frame(startingTime)
            minimum = FADE_FRAMES_NOT_ACCEL if stagger and not accelerating else 1
            endingFrame = max(frame(startingTime + deltaTime[0]), startingFrame + minimum)
            if not isinstance(obj, str):
                matName = "Material." + obj.name
                mat = obj.data.materials[matName]
                if type == "location":
                    obj.location = startingValue
                    obj.keyframe_insert("location", frame=startingFrame)
                    obj.location = endingValue
                    obj.keyframe_insert("location", frame=endingFrame)
                else:
                    setMaterialValue(mat, type, startingValue)
                    insertMaterialKeyframe(mat, type, startingFrame)
                    setMaterialValue(mat, type, endingValue)
                    insertMaterialKeyframe(mat, type, endingFrame)
            else:
                # For applying the staggered alphas in render.py, when the separate Blender file has been loaded.
                if not obj in proxyMat["alpha-fcurves"]:
                    proxyMat["alpha-fcurves"][obj] = []
                l = proxyMat["alpha-fcurves"][obj]
                if not isinstance(l, list):
                    l = l.to_list()
                l += [(startingValue, startingFrame), (endingValue, endingFrame)]
                proxyMat["alpha-fcurves"][obj] = l
            i += 1
            if len(deltaTime) > 1 and (not accelerating or i == nStaggerSubgroup or i == 3 * nStaggerSubgroup):
                deltaTime.pop(0)
            if stagger:
                startingTime += deltaTime[0]

    elif "image" in args:
        image = args["image"]
        imageSteps = args["image"].split(".")
        json = jsonData
        for i in range(len(imageSteps)):
            if imageSteps[i] in json:
                json = json[imageSteps[i]]
        if "source" in json:
            source = json["source"]
            position = json["position"]

            print("{}, {}: fade, image '{}'".format(frame(), frame(time + duration), source))

            plane = imagePlane(source)
            plane.location = position

            bpy.context.scene.frame_set(frame())
            cameraLocation = bpy.data.objects["Camera"].location
            d = (cameraLocation - plane.location).length
            camera = bpy.data.cameras["Camera"]
            w = d * math.tan(camera.angle_x / 2)
            h = d * math.tan(camera.angle_y / 2)
            plane.scale = (w, h, 1)

            matName = "Material." + plane.name
            mat = plane.data.materials[matName]
            setMaterialValue(mat, "alpha", startingAlpha)
            insertMaterialKeyframe(mat, "alpha", frame())
            setMaterialValue(mat, "alpha", endingAlpha)
            insertMaterialKeyframe(mat, "alpha", frame(time + duration))

def pulseCmd(args):
    validateCmdArgs("pulse", ["meshes", "toColor", "rate", "duration"], args)

    global time, tentativeEndTime, colors
    duration = 1
    if "duration" in args:
        duration = args["duration"]
        tentativeEndTime = max(time + duration, tentativeEndTime)
    rate = 1
    if "rate" in args:
        rate = args["rate"]
    if "meshes" in args:
        meshes = args["meshes"]

        colorId = "#ffffff"
        if "toColor" in args:
            colorId = args["toColor"]
        pulseColor = getColor(colorId, colors)
        print("{}, {}: pulse meshes '{}' to color {}: {}".format(frame(), frame(time + duration), meshes, colorId, pulseColor))

        objs = meshObjs(meshes)
        for obj in objs:
            matName = "Material." + obj.name
            mat = obj.data.materials[matName]
            baseColor = tuple(getMaterialValue(mat, "diffuse_color"))

            deltaTime = 1 / (2 * rate)
            n = int(duration / deltaTime)
            if n % 2 == 1:
                n -= 1
            if n <= 0:
                return
            insertMaterialKeyframe(mat, "diffuse_color", frame())
            t = time + deltaTime
            colors = [pulseColor, baseColor]
            for i in range(n):
                setMaterialValue(mat, "diffuse_color", colors[i % 2])
                insertMaterialKeyframe(mat, "diffuse_color", frame(t))
                t += deltaTime

def orbitAxis(args):
    axis = "z"
    if "axis" in args:
        axis = args["axis"].lower()
    local = False
    if "localAxis" in args:
        axis = args["localAxis"].lower()
        local = True

        if "axis" in args:
            print("Error: orbitCamera cannot take both 'axis' and 'localAxis' arguments")
            sys.exit()

    try:
        return {"x": 0, "y": 1, "z": 2}[axis], local
    except:
        return None

def orbitCameraCmd(args):
    validateCmdArgs("orbitCamera", ["around", "axis", "localAxis", "endingRelativeAngle", "scale", "duration"], args)

    # If arg "around" is "a.b" then orbiting will be around the location of
    # "Bounds.a.b".
    global time, tentativeEndTime, lastCameraCenter, lastOrbitEndingAngle, lastViewVector
    camera = bpy.data.objects["Camera"]
    duration = 1
    if "duration" in args:
        duration = args["duration"]
        tentativeEndTime = max(time + duration, tentativeEndTime)
    startFrame = frame(time)
    endFrame = frame(time + duration)
    center = lastCameraCenter

    if "around" in args:
        targetName = args["around"]
        boundName = "Bound." + targetName
        if boundName in bpy.data.objects:
            bound = bpy.data.objects[boundName]
            center = bound.location
            lastCameraCenter = center

    axis, local = orbitAxis(args)
    if axis == None:
        print("Unrecognized axis in '{}'".format(args))
        sys.exit()

    startingAngle = 0 if local else lastOrbitEndingAngle[axis]
    startingEuler = mathutils.Euler((0, 0, 0), "XYZ")
    startingEuler[axis] = startingAngle

    endingAngle = math.radians(-360)
    if "endingRelativeAngle" in args:
        endingRelativeAngle = math.radians(args["endingRelativeAngle"])
        endingAngle = startingAngle + endingRelativeAngle
        lastOrbitEndingAngle[axis] = endingAngle
    endingEuler = mathutils.Euler((0, 0, 0), "XYZ")
    endingEuler[axis] = endingAngle

    printAxis = ["x", "y", "z"][axis]
    printStartingAngle = math.degrees(startingAngle)
    printEndingAngle = math.degrees(endingAngle)
    print("{}, {}: orbitCamera, axis {}, angle {:.2f} - {:.2f}".format(startFrame, endFrame, printAxis, printStartingAngle, printEndingAngle))
    orbiterName = "Orbiter.{}-{}".format(startFrame, endFrame)
    orbiter = newObject(orbiterName)
    target = orbiter

    if local:
        # This object will be the one rotating (and carrying the camera with it).
        pivot = newObject("Pivot")
        pivot.parent = orbiter
        target = pivot
        # This orientation makes it so the change to `axis` is in the local space.
        orbiter.matrix_world = camera.matrix_world

    orbiter.location = center
    target.rotation_euler = startingEuler
    target.keyframe_insert("rotation_euler", frame=startFrame)

    constraint = camera.constraints.new(type="CHILD_OF")
    constraint.name = "Orbit.{}-{}".format(startFrame, endFrame)
    constraint.target = target

    bpy.context.scene.frame_set(startFrame)
    constraint.inverse_matrix = orbiter.matrix_world.inverted()

    if "scale" in args:
        scale = args["scale"]
        d = camera.location - center
        camera.location = center + d

    camera.keyframe_insert("location", frame=startFrame)
    camera.keyframe_insert("rotation_euler", frame=startFrame)

    constraint.influence = 0
    constraint.keyframe_insert("influence", frame=startFrame-1)
    constraint.influence = 1
    constraint.keyframe_insert("influence", frame=startFrame)

    target.rotation_euler = endingEuler
    target.keyframe_insert("rotation_euler", frame=endFrame)

    constraint.influence = 1
    constraint.keyframe_insert("influence", frame=endFrame-1)

    if "scale" in args:
        scale = args["scale"]
        d = camera.location - center
        camera.location = center + scale * d

    # Needed if the rotation does not go all the way back to the start (360 degrees).
    camera.keyframe_insert("location", frame=endFrame-1)
    camera.keyframe_insert("rotation_euler", frame=endFrame-1)
    bpy.context.scene.frame_set(endFrame)
    (t, r, s) = camera.matrix_world.decompose()
    camera.location = t
    camera.rotation_euler = r.to_euler()
    camera.keyframe_insert("location", frame=endFrame)
    camera.keyframe_insert("rotation_euler", frame=endFrame)

    # With the additional camera movement caused by "scale", the standard Bezier interpolation
    # can have odd "swooping" at the beginning.  Fix it by changing the interpolation method.
    if "scale" in args:
        for fcurve in camera.animation_data.action.fcurves:
            for kf in fcurve.keyframe_points:
                kf.interpolation = "SINE"
                kf.easing = "EASE_IN_OUT"

    constraint.influence = 0
    constraint.keyframe_insert("influence", frame=endFrame)

    lastViewVector = (camera.location - lastCameraCenter).normalized()
    updateCameraClip(camera.name)

def centerCameraCmd(args):
    validateCmdArgs("centerCamera", ["position", "fraction", "duration"], args)

    global time, tentativeEndTime, lastCameraCenter
    camera = bpy.data.objects["Camera"]
    duration = 1
    if "duration" in args:
        duration = args["duration"]
        tentativeEndTime = max(time + duration, tentativeEndTime)
    if "position" in args:
        position = None
        if isinstance(args["position"], list):
            position = args["position"]
        else:
            # TODO: This code is shared with fadeCmd().  Refactor,
            positionSteps = args["position"].split(".")
            json = jsonData
            for i in range(len(positionSteps)):
                if positionSteps[i] in json:
                    json = json[positionSteps[i]]
            if "position" in json:
                position = json["position"]

        if position:
            center = mathutils.Vector(position)
            dist = (camera.location - center).magnitude

            fraction = 1
            if "fraction" in args:
                fraction = args["fraction"]
                dist *= fraction

            startFrame = frame()
            if len(keysAtFrame(camera, "location", startFrame)) > 0:
                startFrame += 1

            print("{}, {}: centerCamera, fraction {}".format(startFrame, frame(time + duration), fraction))

            camera.keyframe_insert("location", frame=startFrame)
            # Positive Y points out.
            camera.location = center + dist * lastViewVector
            camera.keyframe_insert("location", frame=frame(time + duration))
            updateCameraClip(camera.name)

            lastCameraCenter = center

def showPictureInPictureCmd(args):
    validateCmdArgs("showPictureInPicture", ["image", "duration"], args)

    global time, tentativeEndTime
    duration = 3
    if "duration" in args:
        duration = args["duration"]
        tentativeEndTime = max(time + duration, tentativeEndTime)
    imageSteps = args["image"].split(".")
    json = jsonData
    for i in range(len(imageSteps)):
        if imageSteps[i] in json:
            json = json[imageSteps[i]]
    if "source" in json:
        source = json["source"]
        position = mathutils.Vector(json["position"])

        rotationDuration = min(1.0, duration / 4.0)
        translationDuration = rotationDuration / 3.0

        plane = imagePlane(source, parented=True)
        pivot = plane.parent

        print("{}, {}: showPictureInPicture, '{}'".format(frame(), frame(time + duration), source))

        location0 = position
        bpy.context.scene.frame_set(frame())
        cameraLocation = bpy.data.objects["Camera"].location
        v = (cameraLocation - position)
        location1 = position + 0.9 * v

        pivot.location = location0
        pivot.keyframe_insert("location", frame=frame())
        pivot.location = location1
        pivot.keyframe_insert("location", frame=frame(time + translationDuration))
        pivot.keyframe_insert("location", frame=frame(time + duration - translationDuration))
        pivot.location = location0
        pivot.keyframe_insert("location", frame=frame(time + duration))

        camera = bpy.data.cameras["Camera"]
        d = (location1 - cameraLocation).length
        h = d * math.tan(camera.angle_y / 2)
        plane.scale = (h * 2/3, h * 2/3, 1)

        matName = "Material." + plane.name
        mat = plane.data.materials[matName]
        setMaterialValue(mat, "alpha", 0)
        insertMaterialKeyframe(mat, "alpha", frame() - 1)
        setMaterialValue(mat, "alpha", 1)
        insertMaterialKeyframe(mat, "alpha", frame())
        insertMaterialKeyframe(mat, "alpha", frame(time + duration))
        setMaterialValue(mat, "alpha", 0)
        insertMaterialKeyframe(mat, "alpha", frame(time + duration) + 1)

        plane.rotation_euler = mathutils.Euler((math.radians(90), 0, 0), "XYZ")
        plane.keyframe_insert("rotation_euler", frame=frame())
        plane.rotation_euler = mathutils.Euler((0, 0, 0), "XYZ")
        plane.keyframe_insert("rotation_euler", frame=frame(time + rotationDuration))
        plane.keyframe_insert("rotation_euler", frame=frame(time + duration - rotationDuration))
        plane.rotation_euler = mathutils.Euler((math.radians(90), 0, 0), "XYZ")
        plane.keyframe_insert("rotation_euler", frame=frame(time + duration))

        if bpy.app.version < (2, 80, 0):
            tex = bpy.data.textures["Texture." + plane.name]
        else:
            tex = mat.node_tree.nodes["texImage"]
        if tex:
            tex.image_user.frame_start = frame(time + rotationDuration)

            print("  frame_start {}, frame_duration {}".format(tex.image_user.frame_start, tex.image_user.frame_duration))

def showSliceCmd(args):
    validateCmdArgs("showSlice", ["image", "bound", "euler", "scale", "distance", "delay", "fade", "duration"], args)

    global time, tentativeEndTime
    duration = 3
    if "duration" in args:
        duration = args["duration"]
        tentativeEndTime = max(time + duration, tentativeEndTime)

    bboxCenter = None
    eulerTuple = None
    if "bound" in args:
        bound = args["bound"]
        bboxCenter, bboxMin, bboxMax, radius = bounds(bound)
    elif "euler" in args:
        eulerTupleDeg = args["euler"]
        eulerTuple = [math.radians(x) for x in eulerTupleDeg]

    fade = 0.5
    if "fade" in args:
        fade = args["fade"]

    delay = fade
    if "delay" in args:
        delay = args["delay"]

    imageSteps = args["image"].split(".")
    json = jsonData
    for i in range(len(imageSteps)):
        if imageSteps[i] in json:
            json = json[imageSteps[i]]

    if "source" in json:
        source = json["source"]
        plane = imagePlane(source, parented=False, aligned=False, flip=False)   

        if bboxCenter:
            w = (bboxMax[0] - bboxMin[0]) / 2
            h = (bboxMax[1] - bboxMin[1]) / 2
            plane.scale = (w, h, 1)

            location0 = mathutils.Vector((bboxCenter[0], bboxCenter[1], bboxMin[2]))
            location1 = mathutils.Vector((bboxCenter[0], bboxCenter[1], bboxMax[2]))
        else:
            euler = mathutils.Euler((0, 0, 0), "XYZ")
            if eulerTuple:
                euler = mathutils.Euler(eulerTuple, "XYZ")
            s = 1
            if "scale" in args:
                s = args["scale"]
            plane.scale = (s, s, 1)
            plane.rotation_euler = euler
            if "position" in json:
                position = json["position"]
                location0 = mathutils.Vector(position)
            distance = 1
            if "distance" in args:
                distance = args["distance"]
            displacement = euler.to_matrix() @ mathutils.Vector((0, 0, distance))
            location1 = location0 + displacement

        print("{}, {}: showSlice, '{}'".format(frame(), frame(time + duration), source))

        plane.location = location0
        plane.keyframe_insert("location", frame=frame(time))
        if delay > 0:
            plane.keyframe_insert("location", frame=frame(time + delay))
        plane.location = location1
        plane.keyframe_insert("location", frame=frame(time + duration - fade))

        # Linear interpolation instead of any ease-in-ease-out, to match Neuroglancer.
        for fcurve in plane.animation_data.action.fcurves:
            for kf in fcurve.keyframe_points:
                kf.interpolation = "LINEAR"

        matName = "Material." + plane.name
        mat = plane.data.materials[matName]
        setMaterialValue(mat, "alpha", 0)
        insertMaterialKeyframe(mat, "alpha", frame(time))
        setMaterialValue(mat, "alpha", 1)
        insertMaterialKeyframe(mat, "alpha", frame(time + fade))
        insertMaterialKeyframe(mat, "alpha", frame(time + duration - fade))
        setMaterialValue(mat, "alpha", 0)
        insertMaterialKeyframe(mat, "alpha", frame(time + duration) + 1)

        if bpy.app.version < (2, 80, 0):
            tex = bpy.data.textures["Texture." + plane.name]
        else:
            tex = mat.node_tree.nodes["texImage"]
        if tex:
            tex.image_user.frame_start = frame(time + delay)

def poseCameraCmd(args):
    # The "target" is what Neuroglancer calls "position", what the camera is looking at.
    # The "orientation" is a quaternion, in Neuroglancer format (x, y, z, w).
    # The "distance" also matches Neuroglancer's camera state, the distance from the 
    # "position" ("target") to the camera's location, where it is looking from.
    validateCmdArgs("poseCamera", ["target", "orientation", "distance", "duration"], args)

    global time, tentativeEndTime, lastCameraCenter, lastViewVector
    camera = bpy.data.objects["Camera"]

    distance = 0
    if "distance" in args:
        distance = args["distance"]
    # Quaternion, Blender format: (w, x, y, z), Neuroglancer format: (x, y, z, w)
    quaternionBlenderFormat = [1, 0, 0, 0]
    if "orientation" in args:
        quaternionNgFormat = args["orientation"]
        quaternionBlenderFormat = mathutils.Quaternion(quat_ng_to_blender(quaternionNgFormat))
    duration = 0
    if "duration" in args:
        duration = args["duration"]
        tentativeEndTime = max(time + duration, tentativeEndTime)
    target = None
    warn = False
    if "target" in args:
        if isinstance(args["target"], list):
            target = args["target"]
        else:
            bboxCenter, _, _, bboxRadius = bounds(args["target"])
            target = bboxCenter
            warn = (distance < bboxRadius)

    if target:
        position = mathutils.Vector(target)
        cameraFrom = ng_camera_look_from(position, distance, quaternionBlenderFormat)
        cameraFrom = mathutils.Vector(cameraFrom)

        startFrame = frame()
        if len(keysAtFrame(camera, "location", startFrame)) > 0:
            startFrame += 1

        p = [position.x, position.y, position.z]
        print("{}, {}: poseCamera target {} orientation {} distance {}".format(startFrame, frame(time + duration), p, quaternionNgFormat, distance))
        if warn:
            print("  Camera is within the target bounding box")

        camera.keyframe_insert("location", frame=startFrame)

        camera.location = (cameraFrom.x, cameraFrom.y, cameraFrom.z)
        camera.keyframe_insert("location", frame=frame(time + duration))

        camera.keyframe_insert("rotation_euler", frame=startFrame)

        e1 = quaternionBlenderFormat.to_euler("XYZ")
        # The following probably helps prevent the animation from rotating "the wrong way around".
        # But animation still has a strange "swoopy" quality.
        e0 = camera.rotation_euler
        e1.make_compatible(e0)

        camera.rotation_euler = e1
        camera.keyframe_insert("rotation_euler", frame=frame(time + duration))

        updateCameraClip(camera.name)
        lastCameraCenter = position
        lastViewVector = (camera.location - lastCameraCenter).normalized()

    else:
        print("Error: poseCamera: missing argument 'target'")
        sys.exit()

def labelCmd(args):
    validateCmdArgs("label", ["text", "size", "position", "color", "duration"], args)

    global time, tentativeEndTime, lastCameraCenter
    duration = 0
    if "duration" in args:
        duration = args["duration"]
        tentativeEndTime = max(time + duration, tentativeEndTime)

    if "text" in args:
        text = args["text"]

    startFrame = frame()
    print("{}, {}: label, text '{}'".format(startFrame, frame(time + duration), text))

    # All the work for this command is done in the separate `compLabels.py` script, after standard frames have been rendered.

def removeUnused():
    for obj in bpy.data.objects:
        if "." in obj.name:
            category, name = obj.name.split(".", 1)
            if category == "Neuron" and not "proxy" in name:
                found = False
                for group, ids in groupToNeuronIds.items():
                    if name in ids:
                        found = True
                        break
                if not found:
                    bpy.data.objects.remove(obj, do_unlink=True)
            elif category == "Roi":
                found = False
                for group, names in groupToRoiNames.items():
                    if name in names:
                        found = True
                        break
                if not found:
                    bpy.data.objects.remove(obj, do_unlink=True)
            elif category == "Synapses" and name not in groupToSynapseSetNames:
                bpy.data.objects.remove(obj, do_unlink=True)

def toJsonQuotes(x):
    return str(x).replace("'", "\"")

def invalidLineMsg(line):
    return "Invalid animation line:\n  {}".format(toJsonQuotes(line))

def properCmdStructure():
    return 'An animation command must have the structure:\n  ["cmd-name", {"arg-name-1": arg-value-1, ..., "arg-name-N": arg-value-N}]'

def cmdNamePublic(cmd):
    # Remove the "Cmd" suffix.
    return cmd[:-3]

def supportedCmds():
    cmds = [cmdNamePublic(cmd) for cmd in globals().keys() if cmd.endswith("Cmd")]
    cmds.sort()
    return cmds

bpy.ops.wm.open_mainfile(filepath=inputBlenderFile)

bpy.context.scene.render.fps = fps

lastCameraCenter = mathutils.Vector(bpy.data.objects["Bound.neurons"].location)
lastOrbitEndingAngle = [0, 0, 0]
# From the camera center ("look at" point) to the camera location("look from" point).
# Positive Y points out by default.
lastViewVector = mathutils.Vector((0, 1, 0))

camera = bpy.data.objects["Camera"]
camera.rotation_euler = mathutils.Euler((math.radians(-90), 0, 0), "XYZ")
dist = 2 * bpy.data.objects["Bound.neurons"]["Radius"]
camera.location = lastCameraCenter + dist * lastViewVector

cameraData = bpy.data.cameras["Camera"]
width = bpy.context.scene.render.resolution_x
height = bpy.context.scene.render.resolution_y
fovx, fovy = parseFov(jsonData, width, height)
aspect = width / height
if aspect > 1:
    if fovx:
        cameraData.lens_unit = "FOV"
        cameraData.angle = math.radians(fovx)
else:
    if fovy:
        cameraData.lens_unit = "FOV"
        cameraData.angle = math.radians(fovy)
print("Using FOV horizontal {}, FOV vertical {}".format(fovx, fovy))

removeUnused()

for step in jsonAnim:
    if not isinstance(step, list) or len(step) != 2:
        print(invalidLineMsg(step))
        print("Invalid animation command structure")
        print(properCmdStructure())
        sys.exit()
    cmdName = step[0]
    if not isinstance(cmdName, str):
        print(invalidLineMsg(step))
        print("Invalid animation command name: '{}'".format(toJsonQuotes(cmdName)))
        print(properCmdStructure())
        sys.exit()
    args = step[1]
    if not isinstance(args, dict):
        print(invalidLineMsg(step))
        print("Invalid animation command arguments: '{}'".format(toJsonQuotes(args)))
        print(properCmdStructure())
        sys.exit()
    # The Python function implementing command `x` must be named `xCmd`.  The `Cmd` suffix simplifies  
    # printing all the supported commands when an erroneous command is parsed.
    cmdName += "Cmd"
    if cmdName in globals():
        cmd = globals()[cmdName]
        cmd(args)
    else:
        print("Invalid animation step:\n  {}".format(step))
        print("Unrecognized animation command: '{}'".format(cmdNamePublic(cmdName)))
        print("Supported animation commands: {}".format(", ".join(supportedCmds())))
        sys.exit()

bpy.context.scene.frame_set(1)

if time < tentativeEndTime:
    time = tentativeEndTime
bpy.context.scene.frame_end = frame()

# Make the 3D view look through the movie camera when the .blend file is loaded.
# https://blender.stackexchange.com/questions/30643/how-to-toggle-to-camera-view-via-python
area = next(area for area in bpy.context.screen.areas if area.type == "VIEW_3D")
area.spaces[0].region_3d.view_perspective = "CAMERA"

if bpy.app.version < (2, 80, 0):
    area.spaces[0].show_relationship_lines = False
    area.spaces[0].show_floor = False
else:
    # Use more samples in the viewport (static interactive preview) display, to improve silhouettes.
    bpy.data.scenes["Scene"].eevee.taa_samples = 64
    # Turn off denoising in the viewport, as it makes the silhouettes almost invisible during animation preview.
    bpy.data.scenes["Scene"].eevee.use_taa_reprojection = False

    for a in bpy.context.screen.areas:
        if a.type == 'VIEW_3D':
            # Make materials, like silhouettes, visible in the viewport.
            a.spaces[0].shading.type = "MATERIAL"
            # Hide some distracting editor tools.
            a.spaces[0].overlay.show_relationship_lines = False
            a.spaces[0].overlay.show_floor = False
            a.spaces[0].overlay.show_axis_x = False
            a.spaces[0].overlay.show_axis_y = False
            a.spaces[0].overlay.show_axis_z = False    

# Make sure ImagePlane is not selected, which seems to prevent it from being rendered transparently.
for obj in bpy.data.objects:
    obj.select_set(False)

if bpy.app.version < (3, 1, 0):
    print("Writing {}".format(outputFile))
    bpy.ops.wm.save_as_mainfile(filepath=outputFile)
else:
    outputAbsPath = os.path.join(os.getcwd(), outputFile)
    print("Writing {}".format(outputAbsPath))
    bpy.ops.wm.save_as_mainfile(filepath=outputAbsPath)
