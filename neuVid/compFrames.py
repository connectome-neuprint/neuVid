# Composites into single frames the pairs of frames rendered separately:
# neurons rendered with Octane;
# ROIs and other unlit content rendered with the default Blender renderer
# (Eevee for Blender 2.80 and later).
# The input frames should be OpenEXR format with a depth channel, and the
# output frames will be PNG format.

# Run in Blender, e.g.:
# blender --background --python compFrames.py -- -ir movie/framesROIs -in movie/framesNeurons -o movie/framesFinal --octane --requireBoth
# Assumes Blender 2.79.

import argparse
import bpy
import datetime
import os
import sys

timeStart = datetime.datetime.now()

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsGeneral import report_version

report_version()

argv = sys.argv

if "--" not in argv:
    argv = []
else:
    argv = argv[argv.index("--") + 1:]

parser = argparse.ArgumentParser()
parser.set_defaults(start=1)
parser.set_defaults(end=999999)
parser.add_argument("--start", "-s", dest="start", type=int, help="first frame to comp")
parser.add_argument("--end", "-e", dest="end", type=int, help="last frame to comp")
parser.add_argument("--inputRois", "-ir", dest="inputROI", help="directory for input of ROI EXR files")
parser.add_argument("--inputNeurons", "-in", dest="inputNeurons", help="directory for input of neuron EXR files")
parser.set_defaults(requireBoth=False)
parser.add_argument("--requireBoth", dest="requireBoth", action="store_true", help="do NOT output only one frame if the other is missing")
parser.add_argument("--output", "-o", dest="output", help="directory for output of PNG files")
parser.set_defaults(useOctane=False)
parser.add_argument("--octane", "-oct", dest="useOctane", action="store_true", help="neurons were rendered with Octane")
args = parser.parse_args(argv)

backgroundColor = (0, 0, 0, 1)

inputROIDir = args.inputROI
if inputROIDir == None:
    print("Missing -ri")
    exit()

if inputROIDir[-1] != "/":
    inputROIDir = inputROIDir + "/"

inputNeuronsDir = args.inputNeurons
if inputNeuronsDir == None:
    print("Missing -ni")
    exit()

if inputNeuronsDir[-1] != "/":
    inputNeuronsDir = inputNeuronsDir + "/"

outputDir = args.output
if outputDir == None:
    outputDir = "./"

if outputDir[-1] != "/":
    outputDir = outputDir + "/"

rois = [os.path.splitext(f)[0] for f in os.listdir(inputROIDir) if os.path.splitext(f)[1] == ".exr"]
rois = [x for x in rois if args.start <= int(x) and int(x) <= args.end]
neurons = [os.path.splitext(f)[0] for f in os.listdir(inputNeuronsDir) if os.path.splitext(f)[1] == ".exr"]
pngs = [os.path.splitext(f)[0] for f in os.listdir(outputDir) if os.path.splitext(f)[1] == ".png"]
roisToInput = [f for f in rois if f not in pngs]

bpy.context.scene.use_nodes = True
bpy.context.scene.render.use_compositing = True
tree = bpy.context.scene.node_tree
treeLinks = tree.links

for node in tree.nodes:
    tree.nodes.remove(node)

roiImageNode = tree.nodes.new(type="CompositorNodeImage")
neuronImageNode = tree.nodes.new(type="CompositorNodeImage")

if bpy.app.version >= (2, 80, 0):
    # To get depth for depth compositing (z-combine), either the "Z" pass or "Mist" pass
    # could be used, but "Mist" has multiple samples and thus less aliasing.  But to
    # get either pass, the transparency mode must be alpha hashed ("HASHED").
    # This hashed sampling averages in the z (depth) values from behind, and thus
    # skews the final z value.  Skewed z values do not work well for depth compositing.
    # To approximate the true z from the skewed z, z', assume that what behind is the
    # view frustum's far clipping plane, with zFar = 1.  Then:
    # z' = a * z + (1 - a) * zFar = a * z + (1 - a) * 1
    # z = (z' - 1 + a) / a
    # So we need some extra nodes to perform this calculation.
    getAlphaNode = tree.nodes.new(type="CompositorNodeSepRGBA")

    minusOneNode = tree.nodes.new(type="CompositorNodeMath")
    minusOneNode.operation = "SUBTRACT"
    minusOneNode.inputs[1].default_value = 1

    plusAlphaNode = tree.nodes.new(type="CompositorNodeMath")
    plusAlphaNode.operation = "ADD"

    divideByAlphaNode = tree.nodes.new(type="CompositorNodeMath")
    divideByAlphaNode.operation = "DIVIDE"

zCombineNode = tree.nodes.new(type="CompositorNodeZcombine")
zCombineNode.use_alpha = True

backgroundNode = tree.nodes.new(type="CompositorNodeRGB")
backgroundNode.outputs[0].default_value = backgroundColor

overNode = tree.nodes.new(type="CompositorNodeAlphaOver")
# Turning on "Convert Premult" in this way is essential when using neuron images
# from Octane, to properly use its antialiasing, and to correctly handle surfaces
# with material that have opacity less than 1.
overNode.use_premultiply = True

treeLinks.new(backgroundNode.outputs[0], overNode.inputs[1])
treeLinks.new(zCombineNode.outputs["Image"], overNode.inputs[2])

outputNode = tree.nodes.new(type="CompositorNodeOutputFile")
outputNode.format.file_format = "PNG"

treeLinks.new(overNode.outputs[0], outputNode.inputs[0])

missing = []
for i in range(len(roisToInput)):
    print("{} of {}, {:.2f}%".format(i, len(roisToInput), 100 * i / len(roisToInput)))

    roi = roisToInput[i]
    roiPath = inputROIDir + roi + ".exr"
    pngPath = outputDir + roi + ".png"
    neuronPath = inputNeuronsDir + roi + ".exr"

    if args.requireBoth and not roi in neurons:
        continue

    roiImageNode.image = bpy.data.images.load(roiPath)
    if bpy.app.version < (2, 80, 0):
        roiImageNode.layer = "RenderLayer"
    else:
        roiImageNode.layer = "View Layer"

    treeLinks.new(roiImageNode.outputs["Combined"], zCombineNode.inputs[0])
    if bpy.app.version < (2, 80, 0):
        treeLinks.new(roiImageNode.outputs["Depth"], zCombineNode.inputs[1])
    else:
        # Unskewing z (mist) from the recorded mist value, z' (see above):
        # z = (z' - 1 + a) / a
        treeLinks.new(roiImageNode.outputs["Combined"], getAlphaNode.inputs["Image"])

        treeLinks.new(roiImageNode.outputs["Mist"], minusOneNode.inputs[0])

        treeLinks.new(minusOneNode.outputs["Value"], plusAlphaNode.inputs[0])
        treeLinks.new(getAlphaNode.outputs["A"], plusAlphaNode.inputs[1])

        treeLinks.new(plusAlphaNode.outputs["Value"], divideByAlphaNode.inputs[0])
        treeLinks.new(getAlphaNode.outputs["A"], divideByAlphaNode.inputs[1])

        treeLinks.new(divideByAlphaNode.outputs["Value"], zCombineNode.inputs[1])

    # Links have to be established after the images are loaded, apparently.

    if roi in neurons:
        neuronImageNode.image = bpy.data.images.load(neuronPath)
        if bpy.app.version < (2, 80, 0):
            neuronImageNode.layer = "RenderLayer"
        else:
            neuronImageNode.layer = "View Layer"

        if args.useOctane:
            treeLinks.new(neuronImageNode.outputs["OctDenoiserBeauty"], zCombineNode.inputs[2])
        else:
            treeLinks.new(neuronImageNode.outputs["Combined"], zCombineNode.inputs[2])
        if "Depth" in neuronImageNode.outputs.keys():
            treeLinks.new(neuronImageNode.outputs["Depth"], zCombineNode.inputs[3])
    else:
        for link in zCombineNode.inputs[2].links:
            treeLinks.remove(link)
        for link in zCombineNode.inputs[3].links:
            treeLinks.remove(link)
        zCombineNode.inputs[2].default_value = backgroundColor
        zCombineNode.inputs[3].default_value = 1

    outputNode.base_path = outputDir + roi
    bpy.ops.render.render()

    # Necessary to workaround problems directly setting the output file name.
    os.rename(outputDir + roi + "/Image0001.png", pngPath)
    os.rmdir(outputDir + roi)

    if not os.path.isfile(pngPath):
        print("*** missing {}".format(pngPath))
        missing.append(pngPath)

    # Delete the images when the compositing of this frame is finished, to avoid
    # ever-increasing memory usage, leading to a crash.
    if roiImageNode.image:
        bpy.data.images.remove(roiImageNode.image)
    if neuronImageNode.image:
        bpy.data.images.remove(neuronImageNode.image)

if len(missing) > 0:
    print("Frames missing from the final composite: {}".format(missing))

timeEnd = datetime.datetime.now()
print("Compositing started at {}".format(timeStart))
print("Compositing ended at {}".format(timeEnd))
