# neuVid

## Summary

These Python scripts generate simple anatomical videos in [Blender](https://www.blender.org/), following the conventions common in neuroscience research on the *Drosophila* fruit fly.  The input is a [JSON](https://en.wikipedia.org/wiki/JSON) file giving a high-level description of anatomical elements (e.g., neurons, regions of interest, synapses) and how they are animated (e.g., the camera frames on some neurons, then those neurons fade out while the camera orbits around them).  Renderings of high quality can be done with a path-tracing renderer: Blender's Cycles, or the [OTOY Octane renderer](https://home.otoy.com/render/octane-render/) (which requires a commercial license).  Here is a video scripted with `neuVid` and rendered with Octane (with titles added separately in [iMovie](https://www.apple.com/imovie/)):

[![Watch the video](https://img.youtube.com/vi/nu0b_tjCGxQ/maxresdefault.jpg)](https://www.youtube.com/watch?v=nu0b_tjCGxQ)

## Basic Usage

Here is how to render a simple example video:
1. [Install Blender](https://www.blender.org/download/).  These scripts were developed originally for version 2.79 but now work for later versions, like 2.93 and 3.0.
2. Clone this repository.
3. Open a terminal shell, and change the current directory to the root of the cloned repository (i.e., the directory containing the subdirectories `documentation`, `examples`, etc.).
4. Copy `examples/example1.json` to some writable directory like `/tmp`.
5. Run the script to download meshes and create the basic Blender file without animation in the same directory as the JSON file.  This stage also creates two directories for downloaded mesh files, `neuVidNeuronMeshes` and `neuVidRoiMeshes`, also in the same directory as the JSON file.
```
blender --background --python neuVid/importMeshes.py -- -i /tmp/example1.json
```
6. Run the script to create a second Blender file with animation.  Adding animation is a separate step since it can take significantly less time than creating the basic Blender file, and may need to be done repeatedly as the animation specification is refined.
```
blender --background --python neuVid/addAnimation.py -- -i /tmp/example1.json
```
7. If desired, preview the animation by opening the second blender file (`/tmp/example1Anim.blender`) in a normal interactive (not background) Blender session.
8. Run the script to render the animation with Blender's Cycles renderer.  This step takes the longest, about 30-40 minutes on a modern desktop or laptop computer.
```
blender --background --python neuVid/render.py -- -i /tmp/example1.json -o /tmp/framesFinal
```
9. Run the script to assemble the rendered frames into a video (named `/tmp/1-N.avi`, where `N` is the number of rendered frames).
```
blender --background --python neuVid/assembleFrames.py -- -i /tmp/framesFinal -o /tmp
```

## Usage with Neuroglancer

One way to start authoring input for `neuVid` is to use [Neuroglancer](https://github.com/google/neuroglancer), a WebGL-based viewer for volumetric data.  Neuroglancer encodes all its state&mdash;the bodies it is showing, where they were loaded from, which ones are faded out, the camera orientation, etc.&mdash;in its URL.  Neuroglancer provides [a Python script](https://github.com/google/neuroglancer/blob/master/python/neuroglancer/tool/video_tool.py) that can interpolate between the states in URLs to create animation for video.  To make this animation easier to edit, and to improve the video quality with smoother transitions and more believable rendering, `neuVid` includes a utility for converting the text file of Neuroglancer URLs into a `neuVid` input JSON file.
```
python neuVid/importNg.py -i /tmp/ng.txt -o /tmp/fromNg.json
```

Some datasets in Neuroglancer use the ["precomputed"](https://github.com/google/neuroglancer/blob/master/src/neuroglancer/datasource/precomputed/README.md) format to store [multiresolution](https://github.com/google/neuroglancer/blob/master/src/neuroglancer/datasource/precomputed/meshes.md#multi-resolution-mesh-format) and/or [sharded](https://github.com/google/neuroglancer/blob/master/src/neuroglancer/datasource/precomputed/sharded.md) meshes.  Such meshes must be converted to [OBJ files](https://en.wikipedia.org/wiki/Wavefront_.obj_file) for futher processing in `neuVid`. The `fetchMeshes.py` script in `neuVid` performs the conversion using the [MeshParty](https://github.com/sdorkenw/MeshParty) package (whose installation is best managed with [Miniconda](https://docs.conda.io/en/latest/miniconda.html)):
```
conda create --name neuVid-precomputed python=3.9
conda activate neuVid-precomputed
pip install meshparty open3d
python neuVid/fetchMeshes.py -i /tmp/fromNg.json
```
Unfortunately, this installation does not work yet with the "arm64" version of Conda for Apple silicon, like the M1 chip; use the legacy "x86_64" version of Conda instead. (_Note that `neuVid's` conversion of Neuroglancer precomputed format is still experimental and the details could change._)

The `neuVid` input file is then processed with the standard steps.
```
blender --background --python neuVid/importMeshes.py -- -i /tmp/fromNg.json
blender --background --python neuVid/addAnimation.py -- -i /tmp/fromNg.json
blender --background --python neuVid/render.py -- -i /tmp/fromNg.json -o /tmp/framesFinal
blender --background --python neuVid/assembleFrames.py -- -i /tmp/framesFinal -o /tmp
```
An example of a dataset supported by this approach is the [FlyEM hemibrain dataset in Neuroglancer](https://hemibrain-dot-neuroglancer-demo.appspot.com/#!%7B%22dimensions%22:%7B%22x%22:%5B8e-9%2C%22m%22%5D%2C%22y%22:%5B8e-9%2C%22m%22%5D%2C%22z%22:%5B8e-9%2C%22m%22%5D%7D%2C%22position%22:%5B17114%2C20543%2C18610%5D%2C%22crossSectionScale%22:54.23751620061224%2C%22crossSectionDepth%22:-37.62185354999912%2C%22projectionScale%22:64770.91726975332%2C%22layers%22:%5B%7B%22type%22:%22image%22%2C%22source%22:%22precomputed://gs://neuroglancer-janelia-flyem-hemibrain/emdata/clahe_yz/jpeg%22%2C%22tab%22:%22source%22%2C%22name%22:%22emdata%22%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%22precomputed://gs://neuroglancer-janelia-flyem-hemibrain/v1.0/segmentation%22%2C%22tab%22:%22segments%22%2C%22name%22:%22segmentation%22%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%7B%22url%22:%22precomputed://gs://neuroglancer-janelia-flyem-hemibrain/v1.0/rois%22%2C%22subsources%22:%7B%22default%22:true%2C%22properties%22:true%2C%22mesh%22:true%7D%2C%22enableDefaultSubsources%22:false%7D%2C%22pick%22:false%2C%22tab%22:%22segments%22%2C%22selectedAlpha%22:0%2C%22saturation%22:0%2C%22objectAlpha%22:0.8%2C%22ignoreNullVisibleSet%22:false%2C%22meshSilhouetteRendering%22:3%2C%22colorSeed%22:2685294016%2C%22name%22:%22roi%22%7D%2C%7B%22type%22:%22annotation%22%2C%22source%22:%22precomputed://gs://neuroglancer-janelia-flyem-hemibrain/v1.0/synapses%22%2C%22tab%22:%22rendering%22%2C%22ignoreNullSegmentFilter%22:false%2C%22shader%22:%22#uicontrol%20vec3%20preColor%20color%28default=%5C%22red%5C%22%29%5Cn#uicontrol%20vec3%20postColor%20color%28default=%5C%22blue%5C%22%29%5Cn#uicontrol%20float%20preConfidence%20slider%28min=0%2C%20max=1%2C%20default=0%29%5Cn#uicontrol%20float%20postConfidence%20slider%28min=0%2C%20max=1%2C%20default=0%29%5Cn%5Cnvoid%20main%28%29%20%7B%5Cn%20%20setColor%28defaultColor%28%29%29%3B%5Cn%20%20setEndpointMarkerColor%28%5Cn%20%20%20%20vec4%28preColor%2C%200.5%29%2C%5Cn%20%20%20%20vec4%28postColor%2C%200.5%29%29%3B%5Cn%20%20setEndpointMarkerSize%282.0%2C%202.0%29%3B%5Cn%20%20setLineWidth%282.0%29%3B%5Cn%20%20if%20%28prop_pre_synaptic_confidence%28%29%3C%20preConfidence%20%7C%7C%5Cn%20%20%20%20%20%20prop_post_synaptic_confidence%28%29%3C%20postConfidence%29%20discard%3B%5Cn%7D%5Cn%22%2C%22linkedSegmentationLayer%22:%7B%22pre_synaptic_cell%22:%22segmentation%22%2C%22post_synaptic_cell%22:%22segmentation%22%7D%2C%22filterBySegmentation%22:%5B%22post_synaptic_cell%22%2C%22pre_synaptic_cell%22%5D%2C%22name%22:%22synapse%22%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%22precomputed://gs://neuroglancer-janelia-flyem-hemibrain/mito_20190717.27250582%22%2C%22pick%22:false%2C%22tab%22:%22segments%22%2C%22selectedAlpha%22:0.82%2C%22name%22:%22mito%22%2C%22visible%22:false%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%22precomputed://gs://neuroglancer-janelia-flyem-hemibrain/mask_normalized_round6%22%2C%22pick%22:false%2C%22tab%22:%22segments%22%2C%22selectedAlpha%22:0.53%2C%22segments%22:%5B%222%22%5D%2C%22name%22:%22mask%22%2C%22visible%22:false%7D%5D%2C%22showSlices%22:false%2C%22selectedLayer%22:%7B%22visible%22:true%2C%22layer%22:%22segmentation%22%7D%2C%22layout%22:%22xy-3d%22%2C%22selection%22:%7B%7D%7D)
and it also works with the [Neuroglancer viewer in neuPrint](https://neuprint.janelia.org/?dataset=hemibrain:v1.2.1).  An example using the "precomputed" format is the [FAFB dataset in Neuroglancer](https://fafb-dot-neuroglancer-demo.appspot.com/#!%7B%22dimensions%22:%7B%22x%22:%5B4e-9%2C%22m%22%5D%2C%22y%22:%5B4e-9%2C%22m%22%5D%2C%22z%22:%5B4e-8%2C%22m%22%5D%7D%2C%22position%22:%5B109421.8984375%2C41044.6796875%2C5417%5D%2C%22crossSectionScale%22:2.1875%2C%22projectionOrientation%22:%5B-0.08939177542924881%2C-0.9848012924194336%2C-0.07470247149467468%2C0.12882165610790253%5D%2C%22projectionScale%22:27773.019357116023%2C%22layers%22:%5B%7B%22type%22:%22image%22%2C%22source%22:%22precomputed://gs://neuroglancer-fafb-data/fafb_v14/fafb_v14_orig%22%2C%22name%22:%22fafb_v14%22%2C%22visible%22:false%7D%2C%7B%22type%22:%22image%22%2C%22source%22:%22precomputed://gs://neuroglancer-fafb-data/fafb_v14/fafb_v14_clahe%22%2C%22name%22:%22fafb_v14_clahe%22%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%22precomputed://gs://fafb-ffn1-20190805/segmentation%22%2C%22segments%22:%5B%22710435991%22%5D%2C%22name%22:%22fafb-ffn1-20190805%22%7D%2C%7B%22type%22:%22annotation%22%2C%22source%22:%22precomputed://gs://neuroglancer-20191211_fafbv14_buhmann2019_li20190805%22%2C%22tab%22:%22rendering%22%2C%22annotationColor%22:%22#cecd11%22%2C%22shader%22:%22#uicontrol%20vec3%20preColor%20color%28default=%5C%22blue%5C%22%29%5Cn#uicontrol%20vec3%20postColor%20color%28default=%5C%22red%5C%22%29%5Cn#uicontrol%20float%20scorethr%20slider%28min=0%2C%20max=1000%29%5Cn#uicontrol%20int%20showautapse%20slider%28min=0%2C%20max=1%29%5Cn%5Cnvoid%20main%28%29%20%7B%5Cn%20%20setColor%28defaultColor%28%29%29%3B%5Cn%20%20setEndpointMarkerColor%28%5Cn%20%20%20%20vec4%28preColor%2C%200.5%29%2C%5Cn%20%20%20%20vec4%28postColor%2C%200.5%29%29%3B%5Cn%20%20setEndpointMarkerSize%285.0%2C%205.0%29%3B%5Cn%20%20setLineWidth%282.0%29%3B%5Cn%20%20if%20%28int%28prop_autapse%28%29%29%20%3E%20showautapse%29%20discard%3B%5Cn%20%20if%20%28prop_score%28%29%3Cscorethr%29%20discard%3B%5Cn%7D%5Cn%5Cn%22%2C%22shaderControls%22:%7B%22scorethr%22:80%7D%2C%22linkedSegmentationLayer%22:%7B%22pre_segment%22:%22fafb-ffn1-20190805%22%2C%22post_segment%22:%22fafb-ffn1-20190805%22%7D%2C%22filterBySegmentation%22:%5B%22post_segment%22%2C%22pre_segment%22%5D%2C%22name%22:%22synapses_buhmann2019%22%7D%2C%7B%22type%22:%22image%22%2C%22source%22:%22n5://gs://fafb-v14-synaptic-clefts-heinrich-et-al-2018-n5/synapses_dt_reblocked%22%2C%22opacity%22:0.73%2C%22shader%22:%22void%20main%28%29%20%7BemitRGBA%28vec4%280.0%2C0.0%2C1.0%2CtoNormalized%28getDataValue%28%29%29%29%29%3B%7D%22%2C%22name%22:%22clefts_Heinrich_etal%22%2C%22visible%22:false%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%22precomputed://gs://neuroglancer-fafb-data/elmr-data/FAFBNP.surf/mesh#type=mesh%22%2C%22segments%22:%5B%221%22%2C%2210%22%2C%2211%22%2C%2212%22%2C%2213%22%2C%2214%22%2C%2215%22%2C%2216%22%2C%2217%22%2C%2218%22%2C%2219%22%2C%222%22%2C%2220%22%2C%2221%22%2C%2222%22%2C%2223%22%2C%2224%22%2C%2225%22%2C%2226%22%2C%2227%22%2C%2228%22%2C%2229%22%2C%223%22%2C%2230%22%2C%2231%22%2C%2232%22%2C%2233%22%2C%2234%22%2C%2235%22%2C%2236%22%2C%2237%22%2C%2238%22%2C%2239%22%2C%224%22%2C%2240%22%2C%2241%22%2C%2242%22%2C%2243%22%2C%2244%22%2C%2245%22%2C%2246%22%2C%2247%22%2C%2248%22%2C%2249%22%2C%225%22%2C%2250%22%2C%2251%22%2C%2252%22%2C%2253%22%2C%2254%22%2C%2255%22%2C%2256%22%2C%2257%22%2C%2258%22%2C%2259%22%2C%226%22%2C%2260%22%2C%2261%22%2C%2262%22%2C%2263%22%2C%2264%22%2C%2265%22%2C%2266%22%2C%2267%22%2C%2268%22%2C%2269%22%2C%227%22%2C%2270%22%2C%2271%22%2C%2272%22%2C%2273%22%2C%2274%22%2C%2275%22%2C%228%22%2C%229%22%5D%2C%22name%22:%22neuropil-regions-surface%22%2C%22visible%22:false%7D%2C%7B%22type%22:%22mesh%22%2C%22source%22:%22vtk://https://storage.googleapis.com/neuroglancer-fafb-data/elmr-data/FAFB.surf.vtk.gz%22%2C%22shader%22:%22void%20main%28%29%20%7BemitRGBA%28vec4%281.0%2C%200.0%2C%200.0%2C%200.5%29%29%3B%7D%22%2C%22name%22:%22neuropil-full-surface%22%2C%22visible%22:false%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%5B%7B%22url%22:%22precomputed://gs://fafb-ffn1-20190805/segmentation%22%2C%22subsources%22:%7B%22default%22:true%2C%22bounds%22:true%7D%2C%22enableDefaultSubsources%22:false%7D%2C%22precomputed://gs://fafb-ffn1-20190805/segmentation/skeletons_32nm%22%5D%2C%22selectedAlpha%22:0%2C%22segments%22:%5B%224613663523%22%5D%2C%22name%22:%22skeletons_32nm%22%2C%22visible%22:false%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%22precomputed://gs://fafb-ffn1/fafb-public-skeletons%22%2C%22name%22:%22public_skeletons%22%2C%22visible%22:false%7D%5D%2C%22showAxisLines%22:false%2C%22showSlices%22:false%2C%22layout%22:%22xy-3d%22%7D).  Other examples are the [OpenOrganelle](https://openorganelle.janelia.org/) data sets, like the [macrophage cell](https://neuroglancer-demo.appspot.com/#!%7B%22dimensions%22:%7B%22x%22:%5B1e-9%2C%22m%22%5D%2C%22y%22:%5B1e-9%2C%22m%22%5D%2C%22z%22:%5B1e-9%2C%22m%22%5D%7D%2C%22position%22:%5B20000.5%2C4000.5%2C18578.5%5D%2C%22crossSectionOrientation%22:%5B1%2C0%2C0%2C0%5D%2C%22crossSectionScale%22:50%2C%22projectionOrientation%22:%5B0.7035731673240662%2C0.00672326423227787%2C0.0016863985219970345%2C0.7105889916419983%5D%2C%22projectionScale%22:65536%2C%22layers%22:%5B%7B%22type%22:%22segmentation%22%2C%22source%22:%5B%22n5://s3://janelia-cosem-datasets/jrc_macrophage-2/jrc_macrophage-2.n5/labels/mito_seg%22%2C%22precomputed://s3://janelia-cosem-datasets/jrc_macrophage-2/neuroglancer/mesh/mito_seg%22%5D%2C%22tab%22:%22source%22%2C%22segmentDefaultColor%22:%22#008000%22%2C%22name%22:%22mito_seg%22%7D%2C%7B%22type%22:%22image%22%2C%22source%22:%7B%22url%22:%22precomputed://s3://janelia-cosem-datasets/jrc_macrophage-2/neuroglancer/em/fibsem-uint8.precomputed%22%2C%22transform%22:%7B%22matrix%22:%5B%5B1%2C0%2C0%2C0%5D%2C%5B0%2C-1%2C0%2C8000%5D%2C%5B0%2C0%2C1%2C0%5D%5D%2C%22outputDimensions%22:%7B%22x%22:%5B1e-9%2C%22m%22%5D%2C%22y%22:%5B1e-9%2C%22m%22%5D%2C%22z%22:%5B1e-9%2C%22m%22%5D%7D%7D%7D%2C%22tab%22:%22rendering%22%2C%22opacity%22:0.75%2C%22blend%22:%22additive%22%2C%22shader%22:%22#uicontrol%20invlerp%20normalized%28range=%5B214%2C%20233%5D%2C%20window=%5B0%2C%20255%5D%29%5Cn%20%20%20%20%20%20%20%20#uicontrol%20int%20invertColormap%20slider%28min=0%2C%20max=1%2C%20step=1%2C%20default=0%29%5Cn%20%20%20%20%20%20%20%20#uicontrol%20vec3%20color%20color%28default=%5C%22white%5C%22%29%5Cn%20%20%20%20%20%20%20%20float%20inverter%28float%20val%2C%20int%20invert%29%20%7Breturn%200.5%20+%20%28%282.0%20%2A%20%28-float%28invert%29%20+%200.5%29%29%20%2A%20%28val%20-%200.5%29%29%3B%7D%5Cn%20%20%20%20%20%20%20%20%20%20void%20main%28%29%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20emitRGB%28color%20%2A%20inverter%28normalized%28%29%2C%20invertColormap%29%29%3B%5Cn%20%20%20%20%20%20%20%20%7D%22%2C%22name%22:%22fibsem-uint8%22%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%5B%22n5://s3://janelia-cosem-datasets/jrc_macrophage-2/jrc_macrophage-2.n5/labels/golgi_seg%22%2C%22precomputed://s3://janelia-cosem-datasets/jrc_macrophage-2/neuroglancer/mesh/golgi_seg%22%5D%2C%22tab%22:%22source%22%2C%22segmentDefaultColor%22:%22#00ffff%22%2C%22name%22:%22golgi_seg%22%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%5B%22n5://s3://janelia-cosem-datasets/jrc_macrophage-2/jrc_macrophage-2.n5/labels/er_seg%22%2C%22precomputed://s3://janelia-cosem-datasets/jrc_macrophage-2/neuroglancer/mesh/er_seg%22%5D%2C%22tab%22:%22source%22%2C%22segmentDefaultColor%22:%22#0000ff%22%2C%22name%22:%22er_seg%22%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%5B%7B%22url%22:%22n5://s3://janelia-cosem-datasets/jrc_macrophage-2/jrc_macrophage-2.n5/labels/nucleus_seg%22%2C%22transform%22:%7B%22outputDimensions%22:%7B%22x%22:%5B1e-9%2C%22m%22%5D%2C%22y%22:%5B1e-9%2C%22m%22%5D%2C%22z%22:%5B1e-9%2C%22m%22%5D%7D%2C%22inputDimensions%22:%7B%22x%22:%5B4e-9%2C%22m%22%5D%2C%22y%22:%5B4e-9%2C%22m%22%5D%2C%22z%22:%5B3.36e-9%2C%22m%22%5D%7D%7D%7D%2C%22precomputed://s3://janelia-cosem-datasets/jrc_macrophage-2/neuroglancer/mesh/nucleus_seg%22%5D%2C%22tab%22:%22source%22%2C%22segmentDefaultColor%22:%22#ff0000%22%2C%22name%22:%22nucleus_seg%22%7D%5D%2C%22selectedLayer%22:%7B%22visible%22:true%2C%22layer%22:%22nucleus_seg%22%7D%2C%22crossSectionBackgroundColor%22:%22#000000%22%2C%22layout%22:%224panel%22%7D).  See the
[detailed `neuVid` documentation](https://github.com/connectome-neuprint/neuVid/tree/master/documentation#neuroglancer) for more on the capabilities and limitations of this approach.

## Usage with Synapses

Neuroglancer synapse layers are imported with the approach just described, but in some cases it is useful to have more control over the details of the synapses.  This control is provided by the [`neuprint-python` module](https://github.com/connectome-neuprint/neuprint-python).  As mentioned on its project page, `neuprint-python` can be installed with either `conda` or `pip`.  Either approach has the unfortunate consequence that an extra script must be run outside of Blender before `importMeshes.py`, because Blender comes with its own version of Python.
Here is how to render the second example video.

1. To use Conda, first [install Miniconda](https://docs.conda.io/en/latest/miniconda.html).

2. Create a new Conda environment.
```
conda create --name neuVid-example
conda activate neuVid-example
```

3. Install `neuprint-python` from the `flyem-forge` channel.
```
conda install -c flyem-forge neuprint-python
```

4. In a web browser, visit [`https://neuprint.janelia.org/?dataset=hemibrain:v1.0.1`](https://neuprint.janelia.org/?dataset=hemibrain:v1.0.1) and log on.  Click on the second button on the top right, and choose the "Account" menu item to show the "Account" page.

5. Copy the three-or-so-line-long string from the "Auth Token:" section and use it to set the `NEUPRINT_APPLICATION_CREDENTIALS` environment variable in the shell where `neuVid` is to be run.  For a `bash` shell, use a command like the following:
```
export NEUPRINT_APPLICATION_CREDENTIALS="eyJhbGci...xwRYI3dg"
```

6. Run the script to create query the synapses.  This stage creates a directory for the synapse meshes, `neuVidSynapseMeshes`, in the same directory as the JSON file (assumed to have been copied to `/tmp` as in the first example).
```
python neuVid/buildSynapses.py -i /tmp/example2.json
```

7. Now proceed with the normal steps, as described in the previous section.
```
blender --background --python neuVid/importMeshes.py -- -i /tmp/example2.json
blender --background --python neuVid/addAnimation.py -- -i /tmp/example2.json
blender --background --python neuVid/render.py -- -i /tmp/example2.json -o /tmp/framesFinal
blender --background --python neuVid/assembleFrames.py -- -i /tmp/framesFinal -o /tmp
```

## History

These scripts come from a collaboration at [HHMI's Janelia Research Campus](https://www.janelia.org/) between the [FlyEM project](https://www.janelia.org/project-team/flyem) and the [Scientific Computing Software group](https://www.janelia.org/support-team/scientific-computing-software).
The first use was for the [hemibrain connectome release](https://www.janelia.org/project-team/flyem/hemibrain) in January, 2020.  Videos made with `neuVid` were the winner and second runner up for the [2021 Drosophila Image Award](https://drosophila-images.org/2021-2/) from the [Genetics Society of America](https://genetics-gsa.org/).



## Acknowledgements

[David Ackerman](https://github.com/davidackerman) contributed the first version of the code to fetch [OpenOrganelle](https://openorganelle.janelia.org/) meshes.
