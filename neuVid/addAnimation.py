# Adds animation to a basic Blender file created by importMeshes.py.
# Runs relatively quickly to allow iteration on the details of the animation being added to
# the same basic Blender file.

# Run in Blender, e.g.:
# blender --background --python addAnimation.py -- -ij movieScript.json -ib movieWithoutAnimation.blend -ob movieWithAnimation.blend
# Assumes Blender 2.79.

import argparse
import bmesh
import bpy
import json
import math
import mathutils
import os
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsColors import colors, getColor
from utilsJson import parseNeuronsIds, parseRoiNames, parseSynapsesSetNames, removeComments

argv = sys.argv
if "--" not in argv:
    argv = []
else:
    argv = argv[argv.index("--") + 1:]

parser = argparse.ArgumentParser()
parser.add_argument("--inputJson", "-ij", dest="inputJsonFile", help="path to the JSON file describing the input")
parser.add_argument("--inputBlender", "-ib", dest="inputBlenderFile", help="path to the input .blend file")
parser.add_argument("--output", "-o", dest="outputFile", help="path for the output .blend file")
args = parser.parse_args(argv)

if args.inputJsonFile == None:
    parser.print_help()
    quit()

inputBlenderFile = args.inputBlenderFile
if inputBlenderFile == None:
    inputBlenderFile = os.path.splitext(args.inputJsonFile)[0] + ".blend"
print("Using input Blender file: '{}'".format(inputBlenderFile))

outputFile = args.outputFile
if outputFile == None:
    outputFile = os.path.splitext(args.inputJsonFile)[0] + "Anim.blend"
print("Using output Blender file: '{}'".format(outputFile))

jsonData = json.loads(removeComments(args.inputJsonFile))

if jsonData == None:
    print("Loading JSON file {} failed".format(args.inputJsonFile))
    quit()

if "neurons" in jsonData:
    jsonNeurons = jsonData["neurons"]
    neuronIds, groupToNeuronIds, groupToMeshesSourceIndex, useSeparateNeuronFiles = parseNeuronsIds(jsonNeurons)

if "rois" in jsonData:
    jsonRois = jsonData["rois"]
    roiNames, groupToRoiNames = parseRoiNames(jsonRois)

if "synapses" in jsonData:
    jsonSynapses = jsonData["synapses"]
    groupToSynapseSetNames = parseSynapsesSetNames(jsonSynapses)

if not "animation" in jsonData:
    print("JSON contains no 'animation' key, whose value is lists of commands specifying the animation")
    quit()
jsonAnim = jsonData["animation"]

def meshObjs(name):
    global groupToNeuronIds, groupToRoiNames, groupToSynapseSetNames, useSeparateNeuronFiles

    # Support names of the form "A - B + C - D", meaning everything in A or C
    # that is not also in B or D.

    addObjNames = set()
    subObjNames = set()
    sub = False
    for x in name.split():
        if x == "+":
            sub = False
        elif x == "-":
            sub = True
        else:
            i = x.find(".")
            if i != -1:
                type = x[0:i]
                group = x[i + 1:]
                dest = addObjNames
                if sub:
                    dest = subObjNames
                if type == "neurons":
                    if useSeparateNeuronFiles:
                        # For now, at least, support only the simplest case when using
                        # one or more separate files of neuron IDs.
                        if len(name.split()) == 1:
                            dest.add("Neuron.proxy." + group)
                        else:
                            print("Error: mesh expressions with '+'/'-' already not supported for separate neuron files")
                            return None
                    else:
                        for neuronId in groupToNeuronIds[group]:
                            dest.add("Neuron." + neuronId)
                elif type == "rois":
                    for roiName in groupToRoiNames[group]:
                        dest.add("Roi." + roiName)
                elif type == "synapses":
                    for synapseSetName in groupToSynapseSetNames[group]:
                        dest.add("Synapses." + synapseSetName)

    if len(addObjNames) == 0:
        return None

    result = []
    for objName in addObjNames:
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

    bnd = bpy.data.objects["Bound.neurons"]
    ctr = bnd.location
    d = max((camLoc1 - ctr).magnitude, (camLoc2 - ctr).magnitude)
    d += bnd["Radius"]
    if d > cam.clip_end:
        cam.clip_end = d
        print("Updating '{}' clip_end to {}".format(camName, cam.clip_end))

#

time = 0.0
tentativeEndTime = time

fps = 24.0
if "fps" in jsonData:
    fps = jsonData["fps"]
print("Using fps: {}".format(fps))

def frame(t = None):
    global time
    if t == None:
        t = time
    return round(t * fps) + 1

def imagePlane(source, parented=False):
    name = "ImagePlane." + os.path.basename(source)
    if not name in bpy.data.objects:
        tex = bpy.data.textures.new("Texture." + name, type="IMAGE")
        img = bpy.data.images.load(source)
        tex.image = img

        # The following settings improve the sharpness of the image somewhat.
        tex.use_interpolation = False
        tex.use_mipmap = False
        tex.filter_type = "BOX"
        tex.filter_size = 0.1

        mat = bpy.data.materials.new("Material." + name)
        mat.alpha = 0.0

        mtex = mat.texture_slots.add()
        mtex.texture = tex
        mtex.mapping = "FLAT"
        mtex.texture_coords = "UV"

        bpy.ops.mesh.primitive_plane_add()
        plane = bpy.context.active_object
        plane.name = name

        mat.use_transparency = True
        # Make the object appear transparent in the interactive viewport rendering.
        plane.show_transparent = True

        constrained = plane
        if parented:
            pivotName = plane.name + ".Pivot"
            pivot = bpy.data.objects.new(pivotName, None)
            bpy.context.scene.objects.link(pivot)
            plane.parent = pivot
            constrained = pivot

        constraint = constrained.constraints.new(type="TRACK_TO")
        constraint.name = "AlignToCamera"
        constraint.target = bpy.data.objects["Camera"]
        constraint.track_axis = "TRACK_Z"
        constraint.up_axis = "UP_Y"

        bpy.ops.object.mode_set(mode="EDIT")
        me = plane.data
        bm = bmesh.from_edit_mesh(me)

        uv_layer = bm.loops.layers.uv.verify()
        bm.faces.layers.tex.verify()

        for f in bm.faces:
            for l in f.loops:
                luv = l[uv_layer]
                v = l.vert.co
                luv.uv = (1.0 - (v[0] + 1.0)/2.0, 1.0 - (v[1] + 1.0)/2.0)

        bmesh.update_edit_mesh(me)

        plane.data.materials.append(mat)

        # These last two steps are necessary to make the texture appear when
        # viewport shading mode is "Texture" (it will appear for "Material" without them)
        plane.data.uv_textures.new()
        # TODO: Why is data[0] not there?
        #plane.data.uv_textures[0].data[0].image = img

        # Do not apply lighting to the image plane.
        mat.use_shadeless = True
        # Do not involve the image plane in any aspect of shadows.
        mat.use_shadows = False
        mat.use_cast_shadows = False
        mat.use_transparent_shadows = False

        bpy.ops.object.mode_set(mode="OBJECT")

        if img.source == "MOVIE":
            duration = img.frame_duration
            # Due to a bug in Blender, a movie image's frame_duration must be called twice
            # to get the correct value.
            duration = img.frame_duration
            tex.image_user.frame_duration = duration

            tex.image_user.frame_offset = 0
            tex.image_user.use_auto_refresh = True

            return bpy.data.objects[name], tex
        else:
            return bpy.data.objects[name], None

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

def advanceTime(args):
    global time, tentativeEndTime
    if "by" in args:
        by = args["by"]
        if isinstance(by, float):
            time += by
            tentativeEndTime = max(time, tentativeEndTime)
        else:
            print("Error: advanceTime: argument 'by' is not a number")
    else:
        print("Error: advanceTime: missing argument 'by'")

def setValue(args):
    # Makes an instantaneous change, so mostly useful for setting an initial value.
    if "meshes" in args:
        meshes = args["meshes"]

        if "alpha" in args:
            alpha = args["alpha"]
            print("{}: setValue meshes '{}' alpha {}".format(frame(), meshes, alpha))
        elif "color" in args:
            colorId = args["color"]
            color = getColor(colorId, colors)
            print("{}: setValue meshes '{}' color {}: {}".format(frame(), meshes, colorId, color))
        else:
            print("Error: setValue: unsupported arguments {}".format(args))
            return

        objs = meshObjs(meshes)
        for obj in objs:
            matName = "Material." + obj.name
            mat = obj.data.materials[matName]

            if frame() != 1:
                if "alpha" in args:
                    mat.keyframe_insert("alpha", frame=frame()-1)
                else:
                    mat.keyframe_insert("diffuse_color", frame=frame()-1)

            if "alpha" in args:
                mat.alpha = alpha
                mat.keyframe_insert("alpha", frame=frame())
            else:
                mat.diffuse_color = color[0:3]
                mat.keyframe_insert("diffuse_color", frame=frame())

def bboxAxisForViewVector(v):
    # TODO: Pick the axis with maximal projection?
    return 2

def frameCamera(args):
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

        # Positive Y points out.
        eye = lastCameraCenter + dist * lastViewVector
        camera.location = eye
        camera.keyframe_insert("location", frame=frame(time + duration))
        updateCameraClip(camera.name)
    else:
        print("Error: frameCamera: unknown bound object '{}'".format(boundName))

def fade(args):
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

        startingTime = time
        deltaTime = []
        stagger = False
        nStaggerSubgroup = min(5, int(len(objs) / 6))
        if "stagger" in args:
            stagger = args["stagger"]
        if stagger:
            deltaTime.append(duration / 3 / nStaggerSubgroup)
            deltaTime.append(duration / 3 / (2 * nStaggerSubgroup))
            deltaTime.append(duration / 3 / (len(objs) - 3 * nStaggerSubgroup))

            print("{}, {}: fade, meshes '{}', {} {} to {}".
                format(frame(), frame(time + duration), meshes, type, startingValue, endingValue))
            print(" stagger: {} x {}, {} x {}, {} x {}".
                format(nStaggerSubgroup, frame(deltaTime[0]),
                       2 * nStaggerSubgroup, frame(deltaTime[1]),
                       len(objs) - 3 * nStaggerSubgroup, frame(deltaTime[2])))

        else:
            deltaTime.append(duration)
            print("{}, {}: fade, meshes '{}', {} {} to {}".format(frame(), frame(time + duration),
                meshes, type, startingValue, endingValue))

        i = 0
        for obj in objs:
            matName = "Material." + obj.name
            mat = obj.data.materials[matName]
            if type == "alpha":
                mat.alpha = startingValue
            elif type == "location":
                obj.location = startingValue

            else:
                mat.diffuse_color = startingValue
            startingFrame = frame(startingTime)
            if type == "location":
                obj.keyframe_insert(type, frame=startingFrame)
            else:
            	mat.keyframe_insert(type, frame=startingFrame)
            if type == "alpha":
                mat.alpha = endingValue
            elif type == "location":
                obj.location = endingValue

            else:
                mat.diffuse_color = endingValue
            endingFrame = max(frame(startingTime + deltaTime[0]), startingFrame + 1)
            if type == "location":
                obj.keyframe_insert(type, frame=endingFrame)
            else:
            	mat.keyframe_insert(type, frame=endingFrame)
            i += 1
            if len(deltaTime) > 1 and (i == nStaggerSubgroup or i == 3 * nStaggerSubgroup):
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

            plane, _ = imagePlane(source)
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
            mat.alpha = startingAlpha
            mat.keyframe_insert("alpha", frame=frame())
            mat.alpha = endingAlpha
            mat.keyframe_insert("alpha", frame=frame(time + duration))

def pulse(args):
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
            baseColor = mat.diffuse_color.copy()

            deltaTime = 1 / (2 * rate)
            n = int(duration / deltaTime)
            if n % 2 == 1:
                n -= 1
            if n <= 0:
                return
            mat.keyframe_insert("diffuse_color", frame=frame())
            t = time + deltaTime
            colors = [pulseColor, baseColor]
            for i in range(n):
                mat.diffuse_color = colors[i % 2]
                mat.keyframe_insert("diffuse_color", frame=frame(t))
                t += deltaTime

def orbitAxis(args):
    axis = "z"
    if "axis" in args:
        axis = args["axis"].lower()
    try:
        return {"x" : 0, "y": 1, "z" :2}[axis]
    except:
        return None

def orbitCamera(args):
    # If arg "around" is "a.b" then orbiting will be around the location of
    # "Bounds.a.b".
    global time, tentativeEndTime, lastCameraCenter, lastOrbitEndingAngle
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

    # Mostly for debugging.
    axis = orbitAxis(args)
    if axis == None:
        exit("Unrecognized axis in '{}'".format(args));

    startingAngle = lastOrbitEndingAngle[axis]
    startingEuler = mathutils.Euler((0, 0, 0), "XYZ")
    startingEuler[axis] = startingAngle

    endingAngle = math.radians(-360)
    if "endingRelativeAngle" in args:
        endingRelativeAngle = math.radians(args["endingRelativeAngle"])
        endingAngle = startingAngle + endingRelativeAngle
        lastOrbitEndingAngle[axis] = endingAngle
        lastViewVectorEuler = mathutils.Euler((0, 0, 0), "XYZ")
        lastViewVectorEuler[axis] = endingRelativeAngle
        lastViewVector.rotate(lastViewVectorEuler)
    endingEuler = mathutils.Euler((0, 0, 0), "XYZ")
    endingEuler[axis] = endingAngle

    printAxis = ["x", "y", "z"][axis]
    printStartingAngle = math.degrees(startingAngle)
    printEndingAngle = math.degrees(endingAngle)
    print("{}, {}: orbitCamera, axis {}, angle {:.2f} - {:.2f}".format(startFrame, endFrame, printAxis, printStartingAngle, printEndingAngle))

    orbiterName = "Orbiter.{}-{}".format(startFrame, endFrame)
    orbiter = bpy.data.objects.new(orbiterName, None)
    bpy.context.scene.objects.link(orbiter)

    orbiter.location = center
    orbiter.rotation_euler = startingEuler
    orbiter.keyframe_insert("rotation_euler", frame=startFrame)

    constraint = camera.constraints.new(type="CHILD_OF")
    constraint.name = "Orbit.{}-{}".format(startFrame, endFrame)
    constraint.target = orbiter

    bpy.context.scene.frame_set(startFrame)
    constraint.inverse_matrix = orbiter.matrix_world.inverted()

    camera.keyframe_insert("location", frame=startFrame)
    camera.keyframe_insert("rotation_euler", frame=startFrame)

    constraint.influence = 0
    constraint.keyframe_insert("influence", frame=startFrame-1)
    constraint.influence = 1
    constraint.keyframe_insert("influence", frame=startFrame)

    orbiter.rotation_euler = endingEuler
    orbiter.keyframe_insert("rotation_euler", frame=endFrame)

    constraint.influence = 1
    constraint.keyframe_insert("influence", frame=endFrame-1)

    # Needed if the rotation does not go all the way back to the start (360 degrees).
    camera.keyframe_insert("location", frame=endFrame-1)
    camera.keyframe_insert("rotation_euler", frame=endFrame-1)
    bpy.context.scene.frame_set(endFrame)
    (t, r, s) = camera.matrix_world.decompose()
    camera.location = t
    camera.rotation_euler = r.to_euler()
    camera.keyframe_insert("location", frame=endFrame)
    camera.keyframe_insert("rotation_euler", frame=endFrame)

    constraint.influence = 0
    constraint.keyframe_insert("influence", frame=endFrame)

    updateCameraClip(camera.name)

def centerCamera(args):
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
            # TODO: This code is shared with fade().  Refactor,
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

def showPictureInPicture(args):
    global time, tentativeEndTime
    duration = 3
    if "duration" in args:
        duration = args["duration"]
        tentativeEndTime = max(time + duration, tentativeEndTime)
    image = args["image"]
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

        plane, tex = imagePlane(source, True)
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
        mat.alpha = 0.0
        mat.keyframe_insert("alpha", frame=frame() - 1)
        mat.alpha = 1.0
        mat.keyframe_insert("alpha", frame=frame())
        mat.keyframe_insert("alpha", frame=frame(time + duration))
        mat.alpha = 0.0
        mat.keyframe_insert("alpha", frame=frame(time + duration) + 1)

        plane.rotation_euler = mathutils.Euler((math.radians(90), 0, 0), "XYZ")
        plane.keyframe_insert("rotation_euler", frame=frame())
        plane.rotation_euler = mathutils.Euler((0, 0, 0), "XYZ")
        plane.keyframe_insert("rotation_euler", frame=frame(time + rotationDuration))
        plane.keyframe_insert("rotation_euler", frame=frame(time + duration - rotationDuration))
        plane.rotation_euler = mathutils.Euler((math.radians(90), 0, 0), "XYZ")
        plane.keyframe_insert("rotation_euler", frame=frame(time + duration))

        if tex:
            tex.image_user.frame_start = frame(time + rotationDuration)
            print("  frame_start {}, frame_duration {}".format(tex.image_user.frame_start, tex.image_user.frame_duration))

bpy.ops.wm.open_mainfile(filepath=inputBlenderFile)

bpy.context.scene.render.fps = fps

lastCameraCenter = mathutils.Vector(bpy.data.objects["Bound.neurons"].location)
lastOrbitEndingAngle = [0, 0, 0]
lastViewVector = mathutils.Vector((0, 1, 0))

camera = bpy.data.objects["Camera"]
camera.rotation_euler = mathutils.Euler((math.radians(-90), 0, 0), "XYZ")

for step in jsonAnim:
    cmdName = step[0]
    args = step[1]
    if cmdName in globals():
        cmd = globals()[cmdName]
        cmd(args)
    else:
        print("Skipping unrecognized animation command '{}'".format(cmdName))

bpy.context.scene.frame_set(1)

if time < tentativeEndTime:
    time = tentativeEndTime
bpy.context.scene.frame_end = frame()

# Make the 3D view look through the movie camera when the .blend file is loaded.
# https://blender.stackexchange.com/questions/30643/how-to-toggle-to-camera-view-via-python
area = next(area for area in bpy.context.screen.areas if area.type == "VIEW_3D")
area.spaces[0].region_3d.view_perspective = "CAMERA"

area.spaces[0].show_relationship_lines = False
area.spaces[0].show_floor = False

# Make sure ImagePlane is not selected, which seems to prevent it from being rendered transparently.
#bpy.context.scene.objects.active = None

bpy.ops.wm.save_as_mainfile(filepath=outputFile)
