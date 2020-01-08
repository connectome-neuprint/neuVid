# Assembles frames into a movie.

# Run in Blender, e.g.:
# blender --background --python assembleFrames.py -- -i movie/framesFinal -o movie/results
# Assumes Blender 2.79.

import argparse
import bpy
import os
import sys

argv = sys.argv
if "--" not in argv:
    argv = []
else:
    argv = argv[argv.index("--") + 1:]

parser = argparse.ArgumentParser()
parser.add_argument("--input", "-i", dest="inputDir", help="path to the directory containing the input frames")
parser.add_argument("--output", "-o", dest="outputDir", help="path for the output movie")

args = parser.parse_args(argv)

seqEd = bpy.context.scene.sequence_editor_create()

pngs = [f for f in os.listdir(args.inputDir) if os.path.splitext(f)[1] == ".png"]
pngs.sort()

seq = seqEd.sequences.new_image(name="assemble", filepath=os.path.join(args.inputDir, pngs[0]), channel=1, frame_start=1)
for png in pngs[1:]:
    seq.elements.append(png)

bpy.context.scene.frame_end = len(pngs)

# HDTV 1080P
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080
bpy.context.scene.render.resolution_percentage = 100
bpy.context.scene.render.pixel_aspect_x = 1
bpy.context.scene.render.pixel_aspect_y = 1

bpy.context.scene.render.image_settings.file_format = "AVI_JPEG"
bpy.context.scene.render.fps = 24

outputDir = args.outputDir
if outputDir[:-1] != "/":
    outputDir += "/"
bpy.context.scene.render.filepath = outputDir

bpy.ops.render.render(animation=True)
