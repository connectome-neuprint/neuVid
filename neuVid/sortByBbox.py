# Can be run in two ways:
# $ blender --background --python sortByBbox.py -- -i ids.txt etc
# Or:
# $ conda activate environment-with-numpy
# $ python sortByBbox.py -i ids.txt etc

import argparse
import datetime
import os
import numpy as np
import sys

# Not actually very helpful
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsGeneral import report_version
from utilsJson import get_ids_from_file

def read_obj_filenames(path):
    ids = get_ids_from_file(path)
    filenames = [id + ".obj" for id in ids]
    return filenames

def read_obj_verts_np(path):
    verts = []
    with open(path, "r") as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith("v"):
                v, x, y, z = line.split(" ")
                verts.append((float(x), float(y), float(z)))
    result = np.asarray(verts)
    return result

def read_obj_verts(filenames, dir):
    result = []
    for i in range(len(filenames)):
        filename = filenames[i]
        path = os.path.join(dir, filename)
        verts = read_obj_verts_np(path)

        percent = (i + 1) / len(filenames) * 100
        print(f"{i + 1} / {len(filenames)} ({percent:.1f}%) {path}, {len(verts)} vertices")

        result.append(verts)
    return result

# Does not seem to be any faster in practice.
def read_obj_verts_parallel(filenames, dir):
    def read(filename):
        path = os.path.join(dir, filename)
        verts = read_obj_verts_np(path)
        return verts
    
    results = []
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = [executor.submit(read, filename) for filename in filenames]
        for future in futures:
            results.append(future.result())
    return results

def get_bboxes(objs_verts):
    result = []
    for obj_verts in objs_verts:
        mini = np.min(obj_verts, axis=0)
        maxi = np.max(obj_verts, axis=0)
        result.append((mini, maxi))    
    return result

def sort_bboxes(bboxes, which, axis, ascending=True):
    def size(bbox):
        mi, ma = bbox
        d = [ma[j] - mi[j] for j in range(3)]
        return d[0] * d[1] * d[2]
    def mini(bbox, axis):
        mi, ma = bbox
        return mi[axis]
    def maxi(bbox, axis):
        mi, ma = bbox
        return ma[axis]
    def mid(bbox, axis):
        mi, ma = bbox
        c = [(mi[j] + ma[j]) / 2 for j in range(3)]
        return c[axis]

    match which:
        case "size":
            keyed = [(size(bboxes[i]), i) for i in range(len(bboxes))]
        case "min":
            keyed = [(mini(bboxes[i], axis), i) for i in range(len(bboxes))]
        case "max":
            keyed = [(maxi(bboxes[i], axis), i) for i in range(len(bboxes))]
        case "mid":
            keyed = [(mid(bboxes[i], axis), i) for i in range(len(bboxes))]

    keyed.sort()
    indices = [k[1] for k in keyed]
    if not ascending:
        indices.reverse()
    return indices

def write_obj_filenames(filenames, path):
    ids = [os.path.splitext(f)[0] for f in filenames]
    with open(path, "w") as f:
        for id in ids:
            f.write(f"{id}\n")

if __name__ == "__main__":
    report_version()

    argv = sys.argv
    if "--" in argv:
        # Running as `blender --background --python sortByBbox.py -- <more arguments>`
        argv = argv[argv.index("--") + 1:]
    else:
        # Running as `python sortByBbox.py <more arguments>`
        argv = argv[1:]

    parser = argparse.ArgumentParser()
    parser.set_defaults(input="")
    parser.add_argument("--input", "-i", help="path to input file listing objs")
    parser.add_argument("--inputmeshes", "-im", dest="input_meshes", help="path to directory of input obj meshes")
    parser.add_argument("--output", "-o", help="path to output file for sorted list")
    parser.set_defaults(sort="size")
    parser.add_argument("--sort", help="sorting type: 'size', 'min', 'max', 'mid'")
    parser.set_defaults(axis=0)
    parser.add_argument("--axis", type=int, help="sorting axis")
    parser.set_defaults(descending=False)
    parser.add_argument("--descending", action="store_true", help="sort descending")
    args = parser.parse_args(argv)

    output = args.output
    if not output:
        root, ext = os.path.splitext(args.input)
        output = root + "-ascending" + ext

    which = args.sort
    if not which in ["size", "min", "max", "mid"]:
        which = "size"

    print(f"Using input file listing obj files: '{args.input}")
    print(f"Using input directory of obj mesh files: '{args.input_meshes}")
    print(f"Using input output listing sorted obj files: '{output}")
    print(f"Using sort type: '{which}'")
    print(f"Using sort axis: {args.axis}")
    print(f"Sorting descending: {args.descending}")

    time_start = datetime.datetime.now()

    obj_filenames = read_obj_filenames(args.input)
    obj_verts = read_obj_verts(obj_filenames, args.input_meshes)
    bboxes = get_bboxes(obj_verts)
    sorted_indices = sort_bboxes(bboxes, which, args.axis, not args.descending)
    obj_filenames_sorted = [obj_filenames[i] for i in sorted_indices]
    write_obj_filenames(obj_filenames_sorted, output)

    time_end = datetime.datetime.now()
    print("Sorting started at {}".format(time_start))
    print("Sorting ended at {}".format(time_end))
    print("Elapsed time: {}".format(time_end - time_start))
