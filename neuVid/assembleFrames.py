# Assembles frames into a movie.

# Run in Blender, e.g.:
# blender --background --python assembleFrames.py -- -i movie/framesFinal -o movie/results
# Assumes Blender 2.79.

import argparse
import bpy
import os
import shutil
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsGeneral import report_version

report_version()

argv = sys.argv
if "--" not in argv:
    argv = []
else:
    argv = argv[argv.index("--") + 1:]

parser = argparse.ArgumentParser()

parser.add_argument("--input", "-i", dest="inputDir", help="path to the directory containing the input frames")
parser.add_argument("--output", "-o", dest="outputDir", help="path for the output movie")

# HDTV 1080P is width 1920, height 1080
parser.set_defaults(width=1920)
parser.add_argument("--width", "-iw", type=int, dest="width", help="width")
parser.set_defaults(height=1080)
parser.add_argument("--height", "-ih", type=int, dest="height", help="height")

parser.set_defaults(stretch=1)
parser.add_argument("--stretch", "-s", type=int, dest="stretch", help="stretch factor (e.g., 2 means twice as long)")
parser.set_defaults(padding=0)
parser.add_argument("--pad", "-p", type=int, dest="padding", help="pad with this many copies of the last frame")

parser.add_argument("--frame-jump", "-j", type=int, dest="step", help="number of frames to step forward")

args = parser.parse_args(argv)

if args.inputDir == None:
    parser.print_help()
    quit()

inputDir = args.inputDir
input, ext = os.path.splitext(inputDir)
if ext.lower() == ".json":
    inputDir = input + "-frames"
print("Using input directory: '{}'".format(inputDir))

outputDir = args.outputDir
if outputDir == None:
    outputDir = inputDir

# Necesary in some cases on Windows.
outputDir = os.path.abspath(outputDir)

if outputDir[:-1] != "/":
    outputDir += "/"
print("Using output directory: '{}'".format(outputDir))

seqEd = bpy.context.scene.sequence_editor_create()

pngs = [f for f in os.listdir(inputDir) if os.path.splitext(f)[1] == ".png"]
pngs.sort()

tmp = None
if args.stretch > 1 or args.padding > 0:
    tmp = tempfile.mkdtemp()
    if args.stretch > 1:
        print("Using stretch {}, with temporary directory {}".format(args.stretch, tmp))
    i = 1
    srcs = pngs.copy()
    pngs = []
    for src in srcs:
        src = os.path.join(args.inputDir, src)
        for j in range(args.stretch):
            dst = os.path.join(tmp, str(i).zfill(4)) + ".png"
            shutil.copy(src, dst)
            pngs.append(os.path.split(dst)[1])
            i += 1

    if args.padding > 0:
        print("Using padding {}, with temporary directory {}".format(args.padding, tmp))
        src = os.path.join(args.inputDir, srcs[-1])
        for j in range(args.padding):
            dst = os.path.join(tmp, str(i).zfill(4)) + ".png"
            shutil.copy(src, dst)
            pngs.append(os.path.split(dst)[1])
            i += 1

    pngs.sort()
    inputDir = tmp

if args.step != None:
    bpy.context.scene.frame_step = args.step

seq = seqEd.sequences.new_image(name="assemble", filepath=os.path.join(inputDir, pngs[0]), channel=1, frame_start=1)
for png in pngs[1:]:
    seq.elements.append(png)

bpy.context.scene.frame_end = len(pngs)

bpy.context.scene.render.resolution_x = args.width
bpy.context.scene.render.resolution_y = args.height
bpy.context.scene.render.resolution_percentage = 100
bpy.context.scene.render.pixel_aspect_x = 1
bpy.context.scene.render.pixel_aspect_y = 1

bpy.context.scene.render.image_settings.file_format = "AVI_JPEG"
bpy.context.scene.render.fps = 24

bpy.context.scene.render.filepath = outputDir

# Do not use the default "Filmic" tone mapping because the individual frames
# should have any desired tone mapping already.
bpy.context.scene.view_settings.view_transform = "Standard"

bpy.ops.render.render(animation=True)

if tmp:
    print("Removing temporary directory {}".format(tmp))
    shutil.rmtree(tmp)
