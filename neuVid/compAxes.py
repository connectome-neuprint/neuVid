import argparse
import bpy
import datetime
import json
import math
import mathutils
import numbers
import os
import os.path
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsGeneral import newObject, report_version
from utilsJson import guess_extraneous_comma, removeComments
from utilsMaterials import insertMaterialKeyframe, newBasicMaterial, new_shadeless_material, setMaterialValue

def get_image_size(input):
    for f in os.listdir(input):
        if os.path.splitext(f)[1] == ".png":
            filepath = os.path.join(input, f)
            image = bpy.data.images.load(filepath)
            res_x = image.size[0]
            res_y = image.size[1]
            bpy.data.images.remove(image)
            return (res_x, res_y)

def frame(t, fps):
    return round(t * fps) + 1

def get_arg(cmd, args, arg, types, type_error, default=None):
    if not arg in args:
        if not default:
            print(f"Error: {cmd}: missing argument '{arg}'")
            sys.exit()
        return default
    value = args[arg]
    if not isinstance(types, list):
        types = [types]
    for type in types:
        if isinstance(value, type):
            return value
    print(f"Error: {cmd}: argument '{arg}' {type_error}")
    sys.exit()

def get_image_basenames(dir):
    paths = [os.path.splitext(f)[0] for f in os.listdir(dir) if os.path.splitext(f)[1] == ".png"]
    paths.sort()
    return paths

def apply_image_size(axes_scene, comp_scene, image_size):
    for scene in [axes_scene, comp_scene]:
        scene.render.resolution_x = image_size[0]
        scene.render.resolution_y = image_size[1]

def get_frame_indices(start_frame, end_frame, images):
    if not start_frame:
        i0 = 0
    else:
        for i in range(len(images)):
            base = os.path.splitext(os.path.basename(images[i]))[0]
            base_int = int(base)
            if start_frame >= base_int:
                i0 = base_int
            else:
                break
    if not end_frame:
        i1 = len(images) - 1
    else:
        for i in range(len(images)-1, 0-1, -1):
            base = os.path.splitext(os.path.basename(images[i]))[0]
            base_int = int(base)
            if end_frame <= base_int:
                i1 = base_int
            else:
                break
    return i0, i1

def append_bound(input_blender_file):
    objs_dir = input_blender_file + "/Object"
    referenced_obj_name = "Bound.neurons"
    bpy.ops.wm.append(filename=referenced_obj_name, directory=objs_dir)
    if referenced_obj_name in bpy.data.objects:
        bound = bpy.data.objects[referenced_obj_name]
        if bound.location != mathutils.Vector((0, 0, 0)):
            return bpy.data.objects[referenced_obj_name]
    referenced_obj_name = "Bound.rois"
    bpy.ops.wm.append(filename=referenced_obj_name, directory=objs_dir)
    return bpy.data.objects[referenced_obj_name]

def append_axes_camera(input_blender_file, overall_scale):
    objs_dir = input_blender_file + "/Object"
    referenced_obj_name = "Camera"
    bpy.ops.wm.append(filename=referenced_obj_name, directory=objs_dir)
    camera = bpy.data.objects[referenced_obj_name]
    camera.data.clip_start = overall_scale

    camera.data.type = "ORTHO"
    # With this scale, the camera width (or height, if it is greater than the width) is one Blender unit.
    camera.data.ortho_scale = 1

    bpy.context.scene.camera = camera
    bpy.context.scene.render.film_transparent = True
    return camera

def rescale_recenter(obj, overall_center, overall_scale):
    if obj.name.startswith("Orbiter"):
        obj.location = (obj.location - overall_center) * overall_scale
    elif obj.name == "Camera":
        if obj.animation_data:
            for fc in obj.animation_data.action.fcurves:
                if fc.data_path.endswith("location"):
                    for key in fc.keyframe_points:
                        key.co[1] = (key.co[1] - overall_center[fc.array_index]) * overall_scale
                    fc.update()
        for con in obj.constraints:
            if con.type == "CHILD_OF":
                oldMat = con.inverse_matrix.inverted()
                oldTrans, oldRot, oldScale = oldMat.decompose()
                newTrans = (oldTrans - overall_center) * overall_scale
                if bpy.app.version < (2, 80, 0):
                    newMat = mathutils.Matrix.Translation(newTrans) * oldRot.to_matrix().to_4x4()
                else:
                    newMat = mathutils.Matrix.Translation(newTrans) @ oldRot.to_matrix().to_4x4()
                con.inverse_matrix = newMat.inverted()

def make_axis(which, size, color, parent):
    vertices = 64

    cone_depth = size / 2
    radius1 = cone_depth / 8
    position = 2 * cone_depth
    if which == "X":
        location = mathutils.Vector((position, 0, 0))
        rotation_pos = (0, math.radians(90), 0)
        rotation_neg = (0, math.radians(-90), 0)
    elif which == "Y":
        location = mathutils.Vector((0, position, 0))
        rotation_pos = (math.radians(-90), 0, 0)
        rotation_neg = (math.radians(90), 0, 0)
    else:
        location = mathutils.Vector((0, 0, position))
        rotation_pos = (0, 0, 0)
        rotation_neg = (math.radians(180), 0, 0)

    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius1, radius2=0, depth=cone_depth, location=location, rotation=rotation_pos)
    cone_pos = bpy.context.object
    cone_pos.name = f"{which}-pos-cone"
    cone_pos.parent = parent

    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius1, radius2=0, depth=cone_depth, location=-location, rotation=rotation_neg)
    cone_neg = bpy.context.object
    cone_neg.name = f"{which}-neg-cone"
    cone_neg.parent = parent

    cylinder_radius = radius1 / 10
    cylinder_depth = 4 * cone_depth
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=cylinder_radius, depth=cylinder_depth, rotation=rotation_neg)
    cylinder = bpy.context.object
    cylinder.name = f"{which}-cylinder"
    cylinder.parent = parent

    material_name = f"Material.{which}"
    material = newBasicMaterial(material_name, color)
    cone_pos.data.materials.clear()
    cone_pos.data.materials.append(material)
    cone_neg.data.materials.clear()
    cone_neg.data.materials.append(material)
    cylinder.data.materials.clear()
    cylinder.data.materials.append(material)

    return cone_pos, cylinder, cone_neg

def make_text_object(text, size, color, parent, camera):
    if not text:
        return
    
    bpy.ops.object.text_add()
    obj = bpy.context.object
    obj.name = f"{text}-label"
    obj.data.body = text

    aligner = newObject(f"{text}-label-aligner")
    constraint = aligner.constraints.new(type="COPY_ROTATION")
    constraint.target = camera

    obj.parent = aligner
    aligner.parent = parent
    
    aligner.location = (0, 0, size * 0.75)
    scale = size / 2
    obj.location = (-scale / 3, -scale / 2, 0)
    obj.scale = (scale, scale, scale)

    mat_name = f"Material.{obj.name}"
    mat = new_shadeless_material(mat_name, color)
    obj.data.materials.clear()
    obj.data.materials.append(mat)

    return obj

def make_axes(axes_data, size, camera):
    red = (209/255, 21/255, 59/255, 1)
    green = (50/255, 204/155, 0/255, 1)
    blue = (0/255, 125/255, 255/255, 1)
    origin = newObject("Axes")
    pivot = newObject("Pivot")
    pivot.parent = origin
    origin.parent = camera
    x_pos_cone, _, x_neg_cone = make_axis("X", size, red, pivot)
    y_pos_cone, _, y_neg_cone = make_axis("Y", size, green, pivot)
    z_pos_cone, _, z_neg_cone = make_axis("Z", size, blue, pivot)
    make_text_object(axes_data["x-pos-label"], size, green, x_pos_cone, camera)
    make_text_object(axes_data["x-neg-label"], size, green, x_neg_cone, camera)
    make_text_object(axes_data["y-pos-label"], size, green, y_pos_cone, camera)
    make_text_object(axes_data["y-neg-label"], size, green, y_neg_cone, camera)
    make_text_object(axes_data["z-pos-label"], size, blue, z_pos_cone, camera)
    make_text_object(axes_data["z-neg-label"], size, blue, z_neg_cone, camera)
    rot = axes_data["rotation"] if "rotation" in axes_data else [0, 0, 0]
    constraint = pivot.constraints.new("LIMIT_ROTATION")
    constraint.use_limit_x = True
    constraint.min_x = rot[0]
    constraint.max_x = rot[0]
    constraint.use_limit_y = True
    constraint.min_y = rot[1]
    constraint.max_y = rot[1]
    constraint.use_limit_z = True
    constraint.min_z = rot[2]
    constraint.max_z = rot[2]
    return origin

def make_axes_light(axes):
    name = "Light.Axis"
    data = bpy.data.lights.new(name=name, type="AREA")
    data.size = 2
    data.energy = 50    
    data.cycles.cast_shadow = True
    data.cycles.use_multiple_importance_sampling = True

    light = newObject(name, data)
    light.parent = axes
    light.location = (1, 1, 1)

    constraint = light.constraints.new(type="TRACK_TO")
    constraint.target = axes
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"

    return light

def get_json_axes_label(axis, sign, json_axes):
    for key, value in json_axes.items():
        key = key.lower()
        if axis in key and sign in key:
            return value
    return None

def parse_labels(json_axes):
    if not "labels" in json_axes:
        return {}
    json_labels = json_axes["labels"]
    axes_data = {}
    axes_data["x-pos-label"] = get_json_axes_label("x", "+", json_labels)
    axes_data["x-neg-label"] = get_json_axes_label("x", "-", json_labels)
    axes_data["y-pos-label"] = get_json_axes_label("y", "+", json_labels)
    axes_data["y-neg-label"] = get_json_axes_label("y", "-", json_labels)
    axes_data["z-pos-label"] = get_json_axes_label("z", "+", json_labels)
    axes_data["z-neg-label"] = get_json_axes_label("z", "-", json_labels)
    return axes_data

def parse_rotation(json_axes, axes_data):
    if not "rotation" in json_axes:
        return
    rot = json_axes["rotation"]
    if not isinstance(rot, list) or len(rot) != 3:
        print("Error: axes 'rotation' must be a list of three Euler angles.")
        sys.exit()
    euler = mathutils.Euler([math.radians(e) for e in rot])
    axes_data["rotation"] = euler

def parse_position_size(json_axes, axes_data):
    if "position" in json_axes:
        pos = json_axes["position"]
        if not isinstance(pos, list) or len(pos) != 2:
            print(f"Axes 'position' must be a list [x, y] in normalized screen space")
            sys.exit()
        axes_data["position_norm"] = pos
    if "size" in json_axes:
        size = json_axes["size"]
        axes_data["size_norm"] = size

def process_advance_time(cmd, time):
    if cmd[0] != "advanceTime":
        return time
    
    args = cmd[1]
    by = get_arg(cmd, args, "by", numbers.Number, "is not a number")
    time += by
    return time

def process_fade(cmd, time, fps):
    if cmd[0] != "fade":
        return None
    
    args = cmd[1]
    meshes = get_arg(cmd, args, "meshes", str, "is not a string")
    if not meshes.startswith("axes"):
        return None
    
    time0 = time
    alpha0 = get_arg(cmd, args, "startingAlpha", numbers.Number, "is not a number")
    duration = get_arg(cmd, args, "duration", numbers.Number, "is not a number")
    time1 = time + duration
    alpha1 = get_arg(cmd, args, "endingAlpha", numbers.Number, "is not a number")

    return {
        "start_frame": frame(time0, fps), 
        "start_alpha": alpha0, 
        "end_frame": frame(time1, fps), 
        "end_alpha": alpha1
    }

def parse_axes(input_json_file, image_size):
    try:
        json_data = json.loads(removeComments(input_json_file))
    except json.JSONDecodeError as exc:
        print("Error reading JSON, line {}, column {}: {}".format(exc.lineno, exc.colno, exc.msg))
        guess_extraneous_comma(input_json_file)
        sys.exit()

    fps = 24
    if "fps" in json_data:
        fps = round(json_data["fps"])
    print(f"Using fps: {fps}")

    if not "axes" in json_data:
        print("No axes are specified")
        sys.exit()

    json_axes = json_data["axes"]
    if not isinstance(json_axes, dict):
        print("The 'axes' section must be a dictionary")
        sys.exit()

    key = [k for k in json_axes.keys()][0]
    if len(json_axes) > 1:
        print("Warning: using only the first item from 'axes': '{key}'")
    json_axes = json_axes[key]

    axes_data = parse_labels(json_axes)
    parse_rotation(json_axes, axes_data)
    parse_position_size(json_axes, axes_data)

    if not "animation" in json_data:
        print("Error: missing 'animation'")
        sys.exit()
    animation = json_data["animation"]
    if not type(animation) == list:
        print("Error: 'animation' must be a list of commands.")
        sys.exit()

    fades = []
    time = 0
    for cmd in animation:
        if type(cmd) != list or len(cmd) != 2:
            print("Error: 'animation' commands must be lists of the form [command, {{arguments}}]")
            sys.exit()
        time = process_advance_time(cmd, time)
        fade = process_fade(cmd, time, fps)
        if fade:
            fades.append(fade)
    
    axes_data["animation"] = fades
    return axes_data

def setup_axes_animation(axes_data):
    materials = [m for m in bpy.data.materials if m.name.startswith("Material.")]
    for segment in axes_data["animation"]:
        for mat in materials:
            setMaterialValue(mat, "alpha", segment["start_alpha"])
            insertMaterialKeyframe(mat, "alpha", segment["start_frame"])
            setMaterialValue(mat, "alpha", segment["end_alpha"])
            insertMaterialKeyframe(mat, "alpha", segment["end_frame"])

def unnormalize(location_norm, size_norm, image_size):
    # If the final image is wider than it is tall (i.e., its aspect ratio is greater than 1)
    # then the camera view has (-0.5, 0) at the left and (0.5, 0) at the right, for any final image width.
    # The Y coordinates at the bottom and top depend on the final image aspect ratio.
    # If the final image is taller than it is wide (aspect ratio less than 1)
    # then the camera view has (0, 0.5) at the top center and (0, -0.5) at the bottom center.

    if image_size[0] > image_size[1]:
        y_range = image_size[1] / image_size[0]
        size = size_norm * y_range
    else:
        size = size_norm

    if image_size[0] > image_size[1]:
        x_range = 1
        y_range = image_size[1] / image_size[0]
    else:
        x_range = image_size[0] / image_size[1]
        y_range = 1
    x = location_norm[0]
    y = location_norm[1]
    z = location_norm[2]
    location = [x * x_range - x_range / 2, y * y_range - y_range / 2, z]

    return location, size

def setup_axes_scene(axes_data, input_blender_file, image_size):
    scene = bpy.context.scene
    scene.name = "Scene.axes"

    for obj in scene.objects:
        bpy.data.objects.remove(obj, do_unlink=True)

    bound = append_bound(input_blender_file)
    overall_center = bound.location.copy()
    print("Using overall center: {}".format(overall_center))

    camera = append_axes_camera(input_blender_file, overall_scale)
    size_norm = 0.0245 * args.rescale_factor
    if "size_norm" in axes_data:
        size_norm = axes_data["size_norm"]

    location_norm = [0.945, 0.099, -5 * size_norm]
    if "position_norm" in axes_data:
        location_norm[0], location_norm[1] = axes_data["position_norm"]

    location, size = unnormalize(location_norm, size_norm, image_size)

    for obj in bpy.data.objects:
        rescale_recenter(obj, overall_center, overall_scale)

    axes = make_axes(axes_data, size, camera)
    axes.location = location
    make_axes_light(axes)
    setup_axes_animation(axes_data)

    tmp_dir = tempfile.TemporaryDirectory().name
    scene.render.filepath = tmp_dir
    scene.render.image_settings.file_format = "PNG"
    print(f"Using temporary directory for axes renderings: {tmp_dir}")

    return scene

def setup_comp_scene(output):
    scene = bpy.data.scenes.new("Scene.comp")

    scene.use_nodes = True
    scene.render.use_compositing = True
    nodes = scene.node_tree.nodes
    nodes.clear()
    links = scene.node_tree.links

    image_node1 = nodes.new(type="CompositorNodeImage")
    image_node1.name = "image_node1"
    image_node2 = nodes.new(type="CompositorNodeImage")
    image_node2.name = "image_node2"
    over_node = nodes.new(type="CompositorNodeAlphaOver")
    over_node.name = "alpha_over_node"
    over_node.use_premultiply = True

    output_node = nodes.new(type="CompositorNodeOutputFile")
    output_node.name = "output_node"
    output_node.format.file_format = "PNG"
    output_node.base_path = output
    links.new(over_node.outputs[0], output_node.inputs[0])

    # Do not use the default "Filmic" tone mapping because the individual frames
    # should have any desired tone mapping already.
    scene.view_settings.view_transform = "Standard"

    return scene

def render_axes(axes_scene, frame):
    axes_scene.frame_set(frame)
    filepath_base = axes_scene.render.filepath
    filepath = os.path.join(filepath_base, f"{str(frame).zfill(4)}.png")
    axes_scene.render.filepath = filepath

    bpy.context.window.scene = axes_scene
    bpy.ops.render.render(write_still=True)

    axes_scene.render.filepath = filepath_base
    return filepath

def comp_frame(comp_scene, axes_image_file, rendered_image, frame):
    nodes = comp_scene.node_tree.nodes
    links = comp_scene.node_tree.links

    image_node1 = nodes["image_node1"]
    image_node1.image = bpy.data.images.load(rendered_image)

    image_node2 = nodes["image_node2"]
    image_node2.image = bpy.data.images.load(axes_image_file)

    over_node = nodes["alpha_over_node"]
    links.new(image_node1.outputs["Image"], over_node.inputs[1])
    links.new(image_node2.outputs["Image"], over_node.inputs[2])

    output_node = nodes["output_node"]

    # These two steps make the name of the rendered output file be just the frame number
    # (filled with zeros to four digits) and the ".png" extension.
    output_node.file_slots[0].path = ""
    comp_scene.frame_set(frame)

    bpy.context.window.scene = comp_scene
    bpy.ops.render.render(write_still=True)

    # Delete the images when the compositing of this frame is finished, to avoid
    # ever-increasing memory usage, leading to a crash.
    if image_node1.image:
        bpy.data.images.remove(image_node1.image)
    if image_node2.image:
        bpy.data.images.remove(image_node2.image)

def comp_frames(axes_scene, comp_scene, input, image_size, start_frame, end_frame):
    rendered_frames = get_image_basenames(input)
    apply_image_size(axes_scene, comp_scene, image_size)
    i0, i1 = get_frame_indices(start_frame, end_frame, rendered_frames)
    for i in range(i0, i1 + 1):
        progress = round((i - i0) / (i1 - i0 + 1) * 100, 1)
        rendered_image = os.path.join(input, f"{rendered_frames[i]}.png")
        frame = int(rendered_frames[i])
        print(f"{progress}%: {rendered_image}\n")

        axes_image_file = render_axes(axes_scene, frame)
        comp_frame(comp_scene, axes_image_file, rendered_image, frame)

if __name__ == "__main__":
    report_version()

    if bpy.app.version < (2, 80, 0):
        print("Blender version {} not supported".format(bpy.app.version))
        sys.exit()

    argv = sys.argv
    if "--" not in argv:
        argv = []
    else:
        argv = argv[argv.index("--") + 1:]

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", dest="input_json_file", help="path to the JSON file describing the labels")
    parser.set_defaults(input_frames="")
    parser.add_argument("--inputFrames", "-if", dest="input_frames", help="path to the input rendered frames")
    parser.set_defaults(output=None)
    parser.add_argument("--output", "-o", help="path to the output composited frames")
    parser.set_defaults(start=None)
    parser.add_argument("--frame-start", "-s", type=int, dest="start", help="first frame to composite")
    parser.set_defaults(end=None)
    parser.add_argument("--frame-end", "-e", type=int, dest="end", help="last frame to composite")
    parser.set_defaults(threads=None)
    parser.add_argument("--threads", "-t", dest="threads", type=int, help="thread count for Cycles (default: let Cycles choose)")
    parser.set_defaults(rescale_factor=1.0)
    parser.add_argument("--rescale", "-re", type=float, dest="rescale_factor", help="rescale factor (for numerical precision)")
    parser.set_defaults(debug=False)
    parser.add_argument("--debug", dest="debug", action="store_true", help="for debugging, write a Blender file instead of doing the comp")
    args = parser.parse_args(argv)

    print(f"Using JSON: {args.input_json_file}")
    input = args.input_frames
    if not input:
        input = f"{os.path.splitext(args.input_json_file)[0]}-frames"
    print(f"Using input rendered images: {input}")
    output = args.output
    if not output:
        output = f"{input}-axes"
    # Ensure a final path separator, which is important for how Blender generates output file names
    # from frame numbers.
    output = os.path.join(output, "")
    print(f"Using output composited images: {output}")

    runtime0 = datetime.datetime.now()

    image_size = get_image_size(input)
    print(f"Using final image size: {image_size}")

    # Works for neuron (FlyEM) data with Cycles.
    overall_scale = 0.01
    print("Original overall scale: {}, factor: {}".format(overall_scale, args.rescale_factor))
    overall_scale *= args.rescale_factor
    print("Using overall scale: {}".format(overall_scale))

    input_blender_file = os.path.splitext(args.input_json_file)[0] + "Anim.blend"

    axes_data = parse_axes(args.input_json_file, image_size)
    axes_scene = setup_axes_scene(axes_data, input_blender_file, image_size)
    comp_scene = setup_comp_scene(output)

    if args.threads != None:
        for scene in [comp_scene, axes_scene]:
            scene.render.threads_mode = "FIXED"
            scene.render.threads = args.threads
        print("Using thread count: {}".format(args.threads))

    if not args.debug:
        comp_frames(axes_scene, comp_scene, input, image_size, args.start, args.end)
    else:
        test_output = os.path.splitext(args.input_json_file)[0] + "Axes.blend"
        print("Writing {}".format(test_output))
        bpy.ops.wm.save_as_mainfile(filepath=test_output)

    runtime1 = datetime.datetime.now()
    print(f"Compositing started at {runtime0}")
    print(f"Compositing ended at {runtime1}")
    print(f"Elapsed time {(runtime1 - runtime0)}")
