import argparse
import bpy
import datetime
import json
import numbers
import os
import os.path
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsColors import colors, getColor
from utilsGeneral import newObject, report_version
from utilsJson import guess_extraneous_comma, removeComments
from utilsMaterials import insertMaterialKeyframe, new_shadeless_material, setMaterialValue
    
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

def process_advance_time(cmd, time):
    if cmd[0] == "advanceTime":
        args = cmd[1]
        by = get_arg(cmd, args, "by", numbers.Number, "is not a number")
        time += by
    return time

def unnormalize(position_norm, size_norm, image_size):
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

    if isinstance(position_norm, str):
        if position_norm.lower() == "top":
            if image_size[0] > image_size[1]:
                y_max = 0.5 * image_size[1] / image_size[0]
                position = [-0.45, 0.8 * y_max]
            else:
                x_max = 0.5 * image_size[0] / image_size[1]
                position = [-0.8 * x_max, 0.45]
            position[1] -= size
        elif position_norm.lower() == "bottom":
            if image_size[0] > image_size[1]:
                y_max = 0.5 * image_size[1] / image_size[0]
                position = [-0.45, -0.8 * y_max]
            else:
                x_max = 0.5 * image_size[0] / image_size[1]
                position = [-0.8 * x_max, -0.45]
        else:
            print(f"Error: label: unrecognized position '{position_norm}'")
            sys.exit()
    else:
        if len(position_norm) != 2:
            print(f"Error: label: position vector must be [x, y]")
            sys.exit()
        if image_size[0] > image_size[1]:
            x_range = 1
            y_range = image_size[1] / image_size[0]
        else:
            x_range = image_size[0] / image_size[1]
            y_range = 1
        x = position_norm[0]
        y = position_norm[1]
        position = [x * x_range - x_range / 2, y * y_range - y_range / 2]

    return position, size

def process_label(cmd, time, fps, image_size):
    label = None
    if (cmd[0] == "label"):
        args = cmd[1]
        text = get_arg(cmd, args, "text", str, "is not a string")
        duration = get_arg(cmd, args, "duration", numbers.Number, "is not a number")
        size = get_arg(cmd, args, "size", numbers.Number, "is not a number", 0.053)
        position = get_arg(cmd, args, "position", [list, str], "is not [x, y] or a descriptor like 'top'", "bottom")
        position, size = unnormalize(position, size, image_size)
        color = get_arg(cmd, args, "color", str, "a color string", "white")
        start_frame = frame(time, fps)
        end_frame = frame(time + duration, fps)
        label = {
            "start_frame": start_frame,
            "end_frame": end_frame,
            "text": text,
            "position": position,
            "size": size,
            "color": color
        }
    return label

def parse_labels(input_json_file, image_size):
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

    if not "animation" in json_data:
        print("Error: missing 'animation'")
        sys.exit()
    animation = json_data["animation"]
    if not type(animation) == list:
        print("Error: 'animation' must be a list of commands.")
        sys.exit()

    labels = []
    time = 0
    for cmd in animation:
        if type(cmd) != list or len(cmd) != 2:
            print("Error: 'animation' commands must be lists of the form [command, {{arguments}}]")
            sys.exit()
        time = process_advance_time(cmd, time)
        label = process_label(cmd, time, fps, image_size)
        if label:
            labels.append(label)
    
    return labels

def setup_labels_camera(scene):
    obj = bpy.data.objects["Camera"]
    cam = bpy.data.cameras["Camera"]
    cam.type = "ORTHO"

    # The camera is looking down the Z axis, so the view has +X pointing right, +Y pointing up.
    obj.location = (0, 0, 1)
    obj.rotation_euler = (0, 0, 0)

    # With this scale, the camera width (or height, if it is greater than the width) is one Blender unit.
    cam.ortho_scale = 1

    scene.render.film_transparent = True

def make_text_object(name, label, z):
    bpy.ops.object.text_add()
    obj = bpy.context.object

    obj.name = name
    obj.data.body = label["text"]
    obj.location = label["position"] + [z]
    size = label["size"]
    obj.scale = (size, size, size)

    color_name = label["color"]
    color = getColor(color_name, colors)
    if len(color) == 3:
        color = (color[0], color[1], color[2], 1)
    mat_name = f"Material.{name}"
    mat = new_shadeless_material(mat_name, color)
    obj.data.materials.clear()
    obj.data.materials.append(mat)

    return obj

def setup_label_animation(obj, label):
    mat_name = f"Material.{obj.name}"
    mat = bpy.data.materials[mat_name]

    start_frame = label["start_frame"]
    end_frame = label["end_frame"]
    fade_length = 4
    fade_length = min(fade_length, (end_frame - start_frame) / 2)

    setMaterialValue(mat, "alpha", 0)
    insertMaterialKeyframe(mat, "alpha", start_frame)

    setMaterialValue(mat, "alpha", 1)
    insertMaterialKeyframe(mat, "alpha", start_frame + fade_length)
    insertMaterialKeyframe(mat, "alpha", end_frame - fade_length)

    setMaterialValue(mat, "alpha", 0)
    insertMaterialKeyframe(mat, "alpha", end_frame)

def setup_labels_scene(labels):
    scene = bpy.context.scene
    scene.name = "Scene.labels"

    for obj in scene.objects:
        if obj.name != "Camera":
            bpy.data.objects.remove(obj, do_unlink=True)

    setup_labels_camera(scene)

    # The orthographic camera is looking straight down the Z axis, so the Z coordinate
    # does not affect the geometric appearance of the text.  But different pieces of text
    # must be a different Z values to avoid problems with transparency.
    z = 0
    for label in labels:
        name = f"Text{label['start_frame']}-{label['end_frame']}"
        obj = make_text_object(name, label, z)
        setup_label_animation(obj, label)
        z -= 0.1

    tmp_dir = tempfile.TemporaryDirectory().name
    scene.render.filepath = tmp_dir
    scene.render.image_settings.file_format = "PNG"
    print(f"Using temporary directory for label renderings: {tmp_dir}")

    # Do not use the default "Filmic" tone mapping because the individual frames
    # should have any desired tone mapping already.
    scene.view_settings.view_transform = "Standard"

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

def get_image_paths(dir):
    paths = [os.path.splitext(f)[0] for f in os.listdir(dir) if os.path.splitext(f)[1] == ".png"]
    paths.sort()
    return paths

def apply_image_size(labels_scene, comp_scene, image_size):
    for scene in [labels_scene, comp_scene]:
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

def render_label(labels_scene, frame):
    labels_scene.frame_set(frame)
    filepath_base = labels_scene.render.filepath
    filepath = os.path.join(filepath_base, f"{str(frame).zfill(4)}.png")
    labels_scene.render.filepath = filepath

    bpy.context.window.scene = labels_scene
    bpy.ops.render.render(write_still=True)

    labels_scene.render.filepath = filepath_base
    return filepath

def comp_label(comp_scene, label_image, rendered_image, frame):
    nodes = comp_scene.node_tree.nodes
    links = comp_scene.node_tree.links

    image_node1 = nodes["image_node1"]
    image_node1.image = bpy.data.images.load(rendered_image)

    image_node2 = nodes["image_node2"]
    image_node2.image = bpy.data.images.load(label_image)

    over_node = nodes["alpha_over_node"]
    links.new(image_node1.outputs["Image"], over_node.inputs[1])
    links.new(image_node2.outputs["Image"], over_node.inputs[2])

    output_node = nodes["output_node"]
    base_path = output_node.base_path
    tmp = os.path.join(base_path, f"{str(frame).zfill(4)}")
    output_node.base_path = tmp

    bpy.context.window.scene = comp_scene
    bpy.ops.render.render(write_still=True)

    # Necessary to work around problems directly setting the output file name.
    filepath = f"{tmp}.png"
    os.rename(f"{tmp}/Image0001.png", filepath)
    os.rmdir(tmp)

    output_node.base_path = base_path

    # Delete the images when the compositing of this frame is finished, to avoid
    # ever-increasing memory usage, leading to a crash.
    if image_node1.image:
        bpy.data.images.remove(image_node1.image)
    if image_node2.image:
        bpy.data.images.remove(image_node2.image)

def comp_labels(labels_scene, comp_scene, input, image_size, start_frame, end_frame):
    rendered_frames = get_image_paths(input)
    apply_image_size(labels_scene, comp_scene, image_size)
    i0, i1 = get_frame_indices(start_frame, end_frame, rendered_frames)
    for i in range(i0, i1 + 1):
        progress = round((i - i0) / (i1 - i0 + 1) * 100, 1)
        rendered_image = os.path.join(input, f"{rendered_frames[i]}.png")
        frame = int(rendered_frames[i])
        print(f"{progress}%: {rendered_image}\n")

        label_image = render_label(labels_scene, frame)
        comp_label(comp_scene, label_image, rendered_image, frame)

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
    args = parser.parse_args(argv)

    print(f"Using JSON: {args.input_json_file}")
    input = args.input_frames
    if not input:
        input = f"{os.path.splitext(args.input_json_file)[0]}-frames"
    print(f"Using input rendered images: {input}")
    output = args.output
    if not output:
        output = f"{input}-labeled"
    # Ensure a final path separator, which is important for how Blender generates output file names
    # from frame numbers.
    output = os.path.join(output, "")
    print(f"Using output composited images: {output}")

    runtime0 = datetime.datetime.now()

    image_size = get_image_size(input)
    print(f"Using final image size: {image_size}")

    labels = parse_labels(args.input_json_file, image_size)
    labels_scene = setup_labels_scene(labels)
    comp_scene = setup_comp_scene(output)

    if args.threads != None:
        for scene in [comp_scene, labels_scene]:
            scene.render.threads_mode = "FIXED"
            scene.render.threads = args.threads
        print("Using thread count: {}".format(args.threads))

    comp_labels(labels_scene, comp_scene, input, image_size, args.start, args.end)

    runtime1 = datetime.datetime.now()
    print(f"Compositing started at {runtime0}")
    print(f"Compositing ended at {runtime1}")
    print(f"Elapsed time {(runtime1 - runtime0)}")
