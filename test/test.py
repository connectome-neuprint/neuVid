import argparse
import datetime
import os
import platform
import shutil
import sys

def clean_date(d):
    d0 = str(d)
    d1 = d0.replace(" ", "_")
    d2 = d1.replace(":", "-")
    i = d2.index(".")
    d3 = d2[:i]
    return d3

def get_latest(exe_paths):
    paths_to_sort = [(f, os.path.getmtime(f)) for f in exe_paths]
    paths_sorted = sorted(paths_to_sort, reverse=True, key=lambda x: x[1])
    return paths_sorted[0][0]

def get_blender():
    if platform.system() == "Darwin":
        dir = "/Applications"
        exe_paths = [os.path.join(dir, f) for f in os.listdir(dir) if f.startswith("Blender")]
        latest = get_latest(exe_paths)
        return os.path.join(latest, "Contents", "MacOS", "Blender")
    elif platform.system() == "Linux":
        # TODO
        return None
    elif platform.system() == "Windows":
        # TODO
        return None
    return None

def get_test_paths(test_name, tests_path, output_path):
    test_json_src_path = os.path.join(tests_path, test_name + ".json")
    test_json_path = os.path.join(output_path, test_name + ".json")
    import_output_path = os.path.join(output_path, test_name + ".blend")
    anim_output_path = os.path.join(output_path, test_name + "Anim.blend")
    frames_output_path = os.path.join(output_path, test_name + "-frames")
    try:
        if not os.path.exists(frames_output_path):
            os.makedirs(frames_output_path)
        shutil.copyfile(test_json_src_path, test_json_path)
    except OSError as err:
        print(err)
        sys.exit()
   
    return test_json_path, import_output_path, anim_output_path, frames_output_path

def run(cmd):
    if "importMeshes.py" in cmd:
        print("\n====================\n")
    else:
        print("\n--------------------\n")
    print(cmd)
    os.system(cmd)

def run_test(test_name, frames, cmds):
    test_json_path, import_output_path, anim_output_path, frames_output_path = get_test_paths(test_name, cmds["input"], cmds["output"])
    blender_cmd = cmds["blender"]
    import_cmd = cmds["import"]
    anim_cmd = cmds["anim"]
    render_cmd = cmds["render"]
    run(f"{blender_cmd} {import_cmd} -i {test_json_path} -o {import_output_path}")
    run(f"{blender_cmd} {anim_cmd} -i {test_json_path} -ib {import_output_path} -o {anim_output_path}")
    if render_cmd:
        for frame in frames:
            run(f"{blender_cmd} {render_cmd} -i {test_json_path} -ib {anim_output_path} -o {frames_output_path} -s {frame} -e {frame}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.set_defaults(input=".")
    parser.add_argument("--input", "-i", help="path to the input directory with the tests")
    parser.set_defaults(output=None)
    parser.add_argument("--output", "-o", help="path to the output directory")
    parser.set_defaults(blender=None)
    parser.add_argument("--blender", "-b", help="path to the Blender to use")
    parser.set_defaults(render=True)
    parser.add_argument("--norender", "-nr", dest="render", action="store_false", help="do not render")
    args = parser.parse_args()

    blender = args.blender
    if not blender:
        blender = get_blender()
    print(f"Using Blender: {blender}")
    print(f"Using input directory of tests: {args.input}")
    neuVid = os.path.join(args.input, "..", "neuVid")
    print (f"Using neuVid script directory: {neuVid}")
    output = args.output
    if not output:
        s = clean_date(datetime.datetime.now())
        output = f"/tmp/neuVid-tests-{s}"
    print(f"Using output directory: {output}")
    if not args.render:
        print(f"Skipping rendering")

    try:
        if not os.path.exists(output):
            os.makedirs(output)
    except OSError as err:
        print(err)
        sys.exit()

    blender_cmd = blender + " --background --python"
    import_cmd = os.path.join(neuVid, "importMeshes.py --")
    anim_cmd = os.path.join(neuVid, "addAnimation.py --")
    render_cmd = os.path.join(neuVid, "render.py -- -sa 64 --resX 500 --resY 281")
    cmds = {
        "blender": blender_cmd,
        "import": import_cmd,
        "anim": anim_cmd,
        "render": render_cmd if args.render else None,
        "input": args.input,
        "output": output
    }

    run_test("test-id-list-hemi", [1, 75, 100, 190], cmds)
    run_test("test-id-file-manc", [1, 25, 50, 75, 100, 125, 144], cmds)
    run_test("test-source-array-synapses-hemi", [1, 25, 50, 75, 100, 125, 150, 175, 200, 225, 240], cmds)
    run_test("test-pose-orbit-local-frame", [1, 25, 50, 75, 96], cmds)
    run_test("test-id-list-swc", [1, 100, 150], cmds)
    run_test("test-id-file-swc", [1, 100, 150], cmds)
