[![DOI](https://zenodo.org/badge/232590929.svg)](https://zenodo.org/badge/latestdoi/232590929)

# neuVid

## Summary

These Python scripts generate simple anatomical videos in [Blender](https://www.blender.org/), following the conventions common in neuroscience research on the *Drosophila* fruit fly.  The input is a [JSON](https://en.wikipedia.org/wiki/JSON) file giving a high-level description of anatomical elements (e.g., segmented neurons, regions of interest, synapses) and how they are animated (e.g., the camera frames on some neurons, then those neurons fade out while the camera orbits around them).  An experimental application can [create the JSON from natural language using generative AI](README.md#usage-with-natural-language-input).  Renderings of high quality can be done with a path-tracing renderer: Blender's Cycles, or the [OTOY Octane renderer](https://home.otoy.com/render/octane-render/) (which requires a commercial license).  Here is a video scripted with `neuVid` and rendered with Octane (with titles added separately in [iMovie](https://www.apple.com/imovie/)):

[![Fly Central Complex Circuitry](https://img.youtube.com/vi/nu0b_tjCGxQ/maxresdefault.jpg)](https://www.youtube.com/watch?v=nu0b_tjCGxQ)

See more examples in [the neuVid gallery](https://github.com/connectome-neuprint/neuVid/tree/master/documentation/gallery.md).

These scripts also support volumetric data sets with no explicit segmentation. An example is the [H5J format](https://github.com/JaneliaSciComp/workstation/blob/master/docs/H5JFileFormat.md) volumes in the [Janelia FlyLight Split-GAL4 driver collection](https://splitgal4.janelia.org/cgi-bin/splitgal4.cgi).  This kind of data is rendered with direct volume rendering by [VVDViewer](https://github.com/JaneliaSciComp/VVDViewer).

## Usage with `neuPrint`

The simplest way to start using `neuVid` is to import data from [`neuPrint`](https://neuprint.janelia.org/), a web-based system for browsing the neurons and synapses in connectomes.  The set-up involves just two downloads, and the hands-on time can be as little as a few minutes, as demonstrated in the following tutorial video:

[![Making Neuron Videos with neuPrint and neuVid](https://img.youtube.com/vi/bxbW0cumPPQ/maxresdefault.jpg)](https://www.youtube.com/watch?v=bxbW0cumPPQ)

Here are the steps:
1. [Install Blender](https://www.blender.org/download/).  These scripts will work with the latest version, and older versions back to 2.79.
2. Open a terminal (shell) and clone this repository.
3. Find some neurons (and synapses if desired) in `neuPrint`, and switch to `neuPrint`'s [Neuroglancer](https://github.com/google/neuroglancer) tab.
4. Press the "Copy view URL to clipboard" button (icon: two overlapping squares) at right side of the Neuroglancer header bar.
5. Run the script to read the clipboard and output the JSON file that specifies the video.  In the following, `blender` is shorthand for the actual platform-specific path to the Blender executable: `/Applications/Blender.app/Contents/MacOS/Blender` on macOS; something like `/usr/local/blender/blender-3.4.1-linux-x64/blender` on Linux; something like `"C:\Program Files\Blender Foundation\Blender 3.4\blender.exe"` on Windows, with the quotes being necessary due to the spaces in the path.  Note also that with Windows PowerShell, the executable must be preceded by `&`, as in `& "C:\Program Files\Blender Foundation\Blender 3.4\blender.exe"`.

        blender --background --python neuVid/neuVid/importNg.py -- -o ex1.json

    Note that on Windows, the path to the Blender executable may well contain spaces, as in `C:\Program Files\Blender Foundation\Blender 3.3\blender.exe`.  To run it in the command shell, put quotes around the path, as in `"C:\Program Files\Blender Foundation\Blender 3.3\blender.exe" --background --python ...`.

    Experimental option `-t` (or `--typesplit`): groups imported neurons by type, where available.

6. Run the script to download meshes and create the basic Blender file (without animation) in the same directory as the JSON file.  This stage also creates directories for downloaded mesh files (`neuVidNeuronMeshes`,  `neuVidRoiMeshes`, `neuVidSynapseMeshes`) in the same directory as the JSON file.

        blender --background --python neuVid/neuVid/importMeshes.py -- -i ex1.json

7. Run the script to create a second Blender file with animation.  Adding animation is a separate step since it can take significantly less time than creating the basic Blender file, and may need to be done repeatedly as the animation specification is refined.

        blender --background --python neuVid/neuVid/addAnimation.py -- -i ex1.json

8. If desired, preview the animation by opening the second blender file (`ex1Anim.blend`) in a normal interactive (not background) Blender session.
9. Run the script to render the animation with Blender's Cycles renderer.  This step takes the longest (tens of minutes on a modern desktop or laptop computer).  The rendered frames go to a subdirectory (`ex1-frames`) in the same directory as the JSON file.

        blender --background --python neuVid/neuVid/render.py -- -i ex1.json

10. Run the script to assemble the rendered frames into a video (named `ex1-frames/0001-N.avi`, where `N` is the number of rendered frames).

        blender --background --python neuVid/neuVid/assembleFrames.py -- -i ex1.json

A second tutorial shows how to make more sophisticated videos with more camera motion:
[![Camera Motion in Neuron Videos with neuPrint and neuVid](https://img.youtube.com/vi/P3VbpETjCjY/maxresdefault.jpg)](https://www.youtube.com/watch?v=P3VbpETjCjY)

## Usage with Neuroglancer (e.g., FlyWire Codex, OpenOrganelle)

Note how the `neuPrint` workflow involves [Neuroglancer](https://github.com/google/neuroglancer), a WebGL-based viewer for large data sets like those from connectomics.  Neuroglancer handles other data sets, and some of them can be imported into `neuVid`, too.  An example from neuroscience is the FAFB data set in its [FlyWire Codex](https://codex.flywire.ai/) and [FFN1](https://fafb-dot-neuroglancer-demo.appspot.com/#!%7B%22dimensions%22:%7B%22x%22:%5B4e-9%2C%22m%22%5D%2C%22y%22:%5B4e-9%2C%22m%22%5D%2C%22z%22:%5B4e-8%2C%22m%22%5D%7D%2C%22position%22:%5B109421.8984375%2C41044.6796875%2C5417%5D%2C%22crossSectionScale%22:2.1875%2C%22projectionOrientation%22:%5B-0.08939177542924881%2C-0.9848012924194336%2C-0.07470247149467468%2C0.12882165610790253%5D%2C%22projectionScale%22:27773.019357116023%2C%22layers%22:%5B%7B%22type%22:%22image%22%2C%22source%22:%22precomputed://gs://neuroglancer-fafb-data/fafb_v14/fafb_v14_orig%22%2C%22name%22:%22fafb_v14%22%2C%22visible%22:false%7D%2C%7B%22type%22:%22image%22%2C%22source%22:%22precomputed://gs://neuroglancer-fafb-data/fafb_v14/fafb_v14_clahe%22%2C%22name%22:%22fafb_v14_clahe%22%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%22precomputed://gs://fafb-ffn1-20190805/segmentation%22%2C%22segments%22:%5B%22710435991%22%5D%2C%22name%22:%22fafb-ffn1-20190805%22%7D%2C%7B%22type%22:%22annotation%22%2C%22source%22:%22precomputed://gs://neuroglancer-20191211_fafbv14_buhmann2019_li20190805%22%2C%22tab%22:%22rendering%22%2C%22annotationColor%22:%22#cecd11%22%2C%22shader%22:%22#uicontrol%20vec3%20preColor%20color%28default=%5C%22blue%5C%22%29%5Cn#uicontrol%20vec3%20postColor%20color%28default=%5C%22red%5C%22%29%5Cn#uicontrol%20float%20scorethr%20slider%28min=0%2C%20max=1000%29%5Cn#uicontrol%20int%20showautapse%20slider%28min=0%2C%20max=1%29%5Cn%5Cnvoid%20main%28%29%20%7B%5Cn%20%20setColor%28defaultColor%28%29%29%3B%5Cn%20%20setEndpointMarkerColor%28%5Cn%20%20%20%20vec4%28preColor%2C%200.5%29%2C%5Cn%20%20%20%20vec4%28postColor%2C%200.5%29%29%3B%5Cn%20%20setEndpointMarkerSize%285.0%2C%205.0%29%3B%5Cn%20%20setLineWidth%282.0%29%3B%5Cn%20%20if%20%28int%28prop_autapse%28%29%29%20%3E%20showautapse%29%20discard%3B%5Cn%20%20if%20%28prop_score%28%29%3Cscorethr%29%20discard%3B%5Cn%7D%5Cn%5Cn%22%2C%22shaderControls%22:%7B%22scorethr%22:80%7D%2C%22linkedSegmentationLayer%22:%7B%22pre_segment%22:%22fafb-ffn1-20190805%22%2C%22post_segment%22:%22fafb-ffn1-20190805%22%7D%2C%22filterBySegmentation%22:%5B%22post_segment%22%2C%22pre_segment%22%5D%2C%22name%22:%22synapses_buhmann2019%22%7D%2C%7B%22type%22:%22image%22%2C%22source%22:%22n5://gs://fafb-v14-synaptic-clefts-heinrich-et-al-2018-n5/synapses_dt_reblocked%22%2C%22opacity%22:0.73%2C%22shader%22:%22void%20main%28%29%20%7BemitRGBA%28vec4%280.0%2C0.0%2C1.0%2CtoNormalized%28getDataValue%28%29%29%29%29%3B%7D%22%2C%22name%22:%22clefts_Heinrich_etal%22%2C%22visible%22:false%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%22precomputed://gs://neuroglancer-fafb-data/elmr-data/FAFBNP.surf/mesh#type=mesh%22%2C%22segments%22:%5B%221%22%2C%2210%22%2C%2211%22%2C%2212%22%2C%2213%22%2C%2214%22%2C%2215%22%2C%2216%22%2C%2217%22%2C%2218%22%2C%2219%22%2C%222%22%2C%2220%22%2C%2221%22%2C%2222%22%2C%2223%22%2C%2224%22%2C%2225%22%2C%2226%22%2C%2227%22%2C%2228%22%2C%2229%22%2C%223%22%2C%2230%22%2C%2231%22%2C%2232%22%2C%2233%22%2C%2234%22%2C%2235%22%2C%2236%22%2C%2237%22%2C%2238%22%2C%2239%22%2C%224%22%2C%2240%22%2C%2241%22%2C%2242%22%2C%2243%22%2C%2244%22%2C%2245%22%2C%2246%22%2C%2247%22%2C%2248%22%2C%2249%22%2C%225%22%2C%2250%22%2C%2251%22%2C%2252%22%2C%2253%22%2C%2254%22%2C%2255%22%2C%2256%22%2C%2257%22%2C%2258%22%2C%2259%22%2C%226%22%2C%2260%22%2C%2261%22%2C%2262%22%2C%2263%22%2C%2264%22%2C%2265%22%2C%2266%22%2C%2267%22%2C%2268%22%2C%2269%22%2C%227%22%2C%2270%22%2C%2271%22%2C%2272%22%2C%2273%22%2C%2274%22%2C%2275%22%2C%228%22%2C%229%22%5D%2C%22name%22:%22neuropil-regions-surface%22%2C%22visible%22:false%7D%2C%7B%22type%22:%22mesh%22%2C%22source%22:%22vtk://https://storage.googleapis.com/neuroglancer-fafb-data/elmr-data/FAFB.surf.vtk.gz%22%2C%22shader%22:%22void%20main%28%29%20%7BemitRGBA%28vec4%281.0%2C%200.0%2C%200.0%2C%200.5%29%29%3B%7D%22%2C%22name%22:%22neuropil-full-surface%22%2C%22visible%22:false%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%5B%7B%22url%22:%22precomputed://gs://fafb-ffn1-20190805/segmentation%22%2C%22subsources%22:%7B%22default%22:true%2C%22bounds%22:true%7D%2C%22enableDefaultSubsources%22:false%7D%2C%22precomputed://gs://fafb-ffn1-20190805/segmentation/skeletons_32nm%22%5D%2C%22selectedAlpha%22:0%2C%22segments%22:%5B%224613663523%22%5D%2C%22name%22:%22skeletons_32nm%22%2C%22visible%22:false%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%22precomputed://gs://fafb-ffn1/fafb-public-skeletons%22%2C%22name%22:%22public_skeletons%22%2C%22visible%22:false%7D%5D%2C%22showAxisLines%22:false%2C%22showSlices%22:false%2C%22layout%22:%22xy-3d%22%7D) forms (_FAFB synapses are not yet supported_), and an example from cell biology is the [interphase HeLa cell](https://neuroglancer-demo.appspot.com/#!%7B%22dimensions%22:%7B%22x%22:%5B1e-9%2C%22m%22%5D%2C%22y%22:%5B1e-9%2C%22m%22%5D%2C%22z%22:%5B1e-9%2C%22m%22%5D%7D%2C%22position%22:%5B24800.5%2C2000.5%2C19440.5%5D%2C%22crossSectionOrientation%22:%5B1%2C0%2C0%2C0%5D%2C%22crossSectionScale%22:50%2C%22projectionOrientation%22:%5B1%2C0%2C0%2C0%5D%2C%22projectionScale%22:65536%2C%22layers%22:%5B%7B%22type%22:%22segmentation%22%2C%22source%22:%5B%22n5://s3://janelia-cosem-datasets/jrc_hela-3/jrc_hela-3.n5/labels/er_seg%22%2C%22precomputed://s3://janelia-cosem-datasets/jrc_hela-3/neuroglancer/mesh/er_seg%22%5D%2C%22tab%22:%22source%22%2C%22segmentDefaultColor%22:%22#0000ff%22%2C%22name%22:%22er_seg%22%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%5B%22n5://s3://janelia-cosem-datasets/jrc_hela-3/jrc_hela-3.n5/labels/endo_seg%22%2C%22precomputed://s3://janelia-cosem-datasets/jrc_hela-3/neuroglancer/mesh/endo_seg%22%5D%2C%22tab%22:%22source%22%2C%22segmentDefaultColor%22:%22#ff00ff%22%2C%22name%22:%22endo_seg%22%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%5B%22n5://s3://janelia-cosem-datasets/jrc_hela-3/jrc_hela-3.n5/labels/golgi_seg%22%2C%22precomputed://s3://janelia-cosem-datasets/jrc_hela-3/neuroglancer/mesh/golgi_seg%22%5D%2C%22tab%22:%22source%22%2C%22segmentDefaultColor%22:%22#00ffff%22%2C%22name%22:%22golgi_seg%22%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%5B%22n5://s3://janelia-cosem-datasets/jrc_hela-3/jrc_hela-3.n5/labels/mito_seg%22%2C%22precomputed://s3://janelia-cosem-datasets/jrc_hela-3/neuroglancer/mesh/mito_seg%22%5D%2C%22tab%22:%22source%22%2C%22segmentDefaultColor%22:%22#008000%22%2C%22name%22:%22mito_seg%22%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%5B%22n5://s3://janelia-cosem-datasets/jrc_hela-3/jrc_hela-3.n5/labels/nucleus_seg%22%2C%22precomputed://s3://janelia-cosem-datasets/jrc_hela-3/neuroglancer/mesh/nucleus_seg%22%5D%2C%22tab%22:%22source%22%2C%22segmentDefaultColor%22:%22#ff0000%22%2C%22name%22:%22nucleus_seg%22%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%5B%22n5://s3://janelia-cosem-datasets/jrc_hela-3/jrc_hela-3.n5/labels/pm_seg%22%2C%22precomputed://s3://janelia-cosem-datasets/jrc_hela-3/neuroglancer/mesh/pm_seg%22%5D%2C%22tab%22:%22source%22%2C%22segmentDefaultColor%22:%22#ffa500%22%2C%22name%22:%22pm_seg%22%7D%2C%7B%22type%22:%22image%22%2C%22source%22:%7B%22url%22:%22precomputed://s3://janelia-cosem-datasets/jrc_hela-3/neuroglancer/em/fibsem-uint8.precomputed%22%2C%22transform%22:%7B%22matrix%22:%5B%5B1%2C0%2C0%2C0%5D%2C%5B0%2C-1%2C0%2C4000%5D%2C%5B0%2C0%2C1%2C0%5D%5D%2C%22outputDimensions%22:%7B%22x%22:%5B1e-9%2C%22m%22%5D%2C%22y%22:%5B1e-9%2C%22m%22%5D%2C%22z%22:%5B1e-9%2C%22m%22%5D%7D%7D%7D%2C%22tab%22:%22rendering%22%2C%22opacity%22:0.75%2C%22blend%22:%22additive%22%2C%22shader%22:%22#uicontrol%20invlerp%20normalized%28range=%5B55%2C%20240%5D%2C%20window=%5B0%2C%20255%5D%29%5Cn%20%20%20%20%20%20%20%20%20%20#uicontrol%20int%20invertColormap%20slider%28min=0%2C%20max=1%2C%20step=1%2C%20default=0%29%5Cn%20%20%20%20%20%20%20%20%20%20#uicontrol%20vec3%20color%20color%28default=%5C%22white%5C%22%29%5Cn%20%20%20%20%20%20%20%20%20%20float%20inverter%28float%20val%2C%20int%20invert%29%20%7Breturn%200.5%20+%20%28%282.0%20%2A%20%28-float%28invert%29%20+%200.5%29%29%20%2A%20%28val%20-%200.5%29%29%3B%7D%5Cn%20%20%20%20%20%20%20%20%20%20%20%20void%20main%28%29%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20%20%20emitRGB%28color%20%2A%20inverter%28normalized%28%29%2C%20invertColormap%29%29%3B%5Cn%20%20%20%20%20%20%20%20%20%20%7D%22%2C%22name%22:%22fibsem-uint8%22%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%5B%22n5://s3://janelia-cosem-datasets/jrc_hela-3/jrc_hela-3.n5/labels/vesicle_seg%22%2C%22precomputed://s3://janelia-cosem-datasets/jrc_hela-3/neuroglancer/mesh/vesicle_seg%22%5D%2C%22tab%22:%22source%22%2C%22segmentDefaultColor%22:%22#ff0000%22%2C%22name%22:%22vesicle_seg%22%7D%5D%2C%22selectedLayer%22:%7B%22visible%22:true%2C%22layer%22:%22er_seg%22%7D%2C%22crossSectionBackgroundColor%22:%22#000000%22%2C%22layout%22:%224panel%22%7D) from the [OpenOrganelle](https://openorganelle.janelia.org/) collection:

[![Interphase HeLa Cell](https://img.youtube.com/vi/3hVHbIRS48Q/maxresdefault.jpg)](https://www.youtube.com/watch?v=3hVHbIRS48Q)

When importing from Neuroglancer outside `neuPrint`, some extra Python modules are needed.  These modules process the Neuroglancer ["precomputed"](https://github.com/google/neuroglancer/blob/master/src/neuroglancer/datasource/precomputed/README.md) format that stores [multiresolution](https://github.com/google/neuroglancer/blob/master/src/neuroglancer/datasource/precomputed/meshes.md#multi-resolution-mesh-format) and/or [sharded](https://github.com/google/neuroglancer/blob/master/src/neuroglancer/datasource/precomputed/sharded.md) meshes, converting the meshes to [OBJ files](https://en.wikipedia.org/wiki/Wavefront_.obj_file) for futher processing in `neuVid`. A good way to manage the installation of these modules (so they do not interfere with other uses of Python) is to use the [Miniforge version of Conda](https://github.com/conda-forge/miniforge) (which is free of license fees for educational and non-profit institutions).  First, [install Miniforge itself](https://github.com/conda-forge/miniforge?tab=readme-ov-file#install). (Note that there is an "arm64" version of Conda for Apple silicon, like the M1 chip, but the packages needed here do not yet work with it; use the legacy "x86_64" version of Conda instead.) Next, create an environment (named "neuVid-NG", for example) with the extra modules, like [MeshParty](https://github.com/sdorkenw/MeshParty):
```
conda create --name neuVid-NG python=3.9
conda activate neuVid-NG
python -m pip install meshparty==1.16.7 open3d==0.15.1 trimesh==3.15.1 'numpy<2'
```
Note that as of Q4 2024, the explicit versions for `meshparty`, `open3d` and `trimesh`, and the requirement of not using `numpy` version 2, seem to be necessary to get the (arguably fragile) process of importing from FlyWire to work successfuly.

Then follow these steps to use `neuVid`:

1. Make sure Blender is installed, and this repository is cloned, as above.
2. Make sure that the browser is showing Neuroglancer with a URL visible.  For example, with FlyWire Codex, press the "NGL↗" button.
2. In Neuroglancer, make the desired segments visible (e.g., right-click on the layer tab to get the side bar, switch to the "Seg" tab, click the top check box to make all IDs visible).
3. Click on the browser URL for Neuroglancer to select it, and copy it to the clipboard.  (It is a very long URL.)
4. In a terminal (shell), activate the Conda environment to make the extra modules available:

        conda activate neuVid-NG

5. Run the script to convert the Neuroglancer URL in the clipboard into the JSON file that specifies the video.  Remember that `blender` is shorthand for the actual platform-specific path to the Blender executable, as described above.

        blender --background --python neuVid/neuVid/importNg.py -- -o ex2.json

6. Run the script that fetches the meshes from the Neuroglancer sources.  Note that this script runs with `python` directly instead of using Blender (which does not know about the extra Python modules).

        python neuVid/neuVid/fetchMeshes.py -i ex2.json

   (Don't worry if a spurious error like `Exception ignored in: <function Pool.__del__ at 0x7f97b9d13e50>` appears as this script completes.)

7. Edit the `ex2.json` file to create the desired animation; see the [detailed `neuVid` documentation](https://github.com/connectome-neuprint/neuVid/tree/master/documentation).  That documentation discusses another approach to defining the animation, involving [multiple Neuroglancer URLs that define key moments in the animation](https://github.com/connectome-neuprint/neuVid/tree/master/documentation#neuroglancer).
8. Run the remaining `neuVid` scripts as above:

        blender --background --python neuVid/neuVid/importMeshes.py -- -i ex2.json
        blender --background --python neuVid/neuVid/addAnimation.py -- -i ex2.json
        blender --background --python neuVid/neuVid/render.py -- -i ex2.json
        blender --background --python neuVid/neuVid/assembleFrames.py -- -i ex2.json

## Usage from Scratch

If you feel comfortable specifying the mesh sources and segment IDs by hand, as described in the [detailed `neuVid` documentation](https://github.com/connectome-neuprint/neuVid/tree/master/documentation#neuroglancer), then there is no need to start with `neuPrint` or Neuroglancer:
1. Make sure Blender is installed, and this repository is cloned, as above.
2. Create a JSON file (e.g., `ex3.json`) to specify the sources and animation.
3. Run the last four `neuVid` script as above.  Remember that `blender` is shorthand for the actual platform-specific path to the Blender executable, as described above.

        blender --background --python neuVid/neuVid/importMeshes.py -- -i ex3.json
        blender --background --python neuVid/neuVid/addAnimation.py -- -i ex3.json
        blender --background --python neuVid/neuVid/render.py -- -i ex3.json
        blender --background --python neuVid/neuVid/assembleFrames.py -- -i ex3.json

## Advanced Usage with Synapses

Neuroglancer synapse layers from `neuPrint` are imported as described above, but in some cases it is useful to have more control over the details of the synapses.  This control is provided by the [`neuprint-python` module](https://github.com/connectome-neuprint/neuprint-python).  As mentioned on its project page, `neuprint-python` can be installed with either [Conda](https://docs.conda.io) or [Pip](https://pypi.org/project/pip).  Here are the steps:

1. To use Conda, first install the [Miniforge version of Conda](https://github.com/conda-forge/miniforge).
2. Create a new Conda environment and install `neuprint-python` from the `flyem-forge` channel.

        conda create --name neuVid-synapses
        conda activate neuVid-synapses
        conda install -c flyem-forge neuprint-python

    Or add `neuprint-python` to an existing Conda environment, like `neuVid-NG` created above.

3. The `neuprint-python` code requires `neuPrint` credentials.  In a web browser, visit [`https://neuprint.janelia.org`](https://neuprint.janelia.org) and log on.  Click on the second button on the top right, and choose the "Account" menu item to show the "Account" page.

4. Copy the three-or-so-line-long string from the "Auth Token:" section and use it to set the `NEUPRINT_APPLICATION_CREDENTIALS` environment variable in the shell where `neuVid` is to be run.  For a `bash` shell, use a command like the following:

        export NEUPRINT_APPLICATION_CREDENTIALS="eyJhbGci...xwRYI3dg"

5. Run the script to query the synapses.  This stage creates a directory for the synapse meshes, `neuVidSynapseMeshes`, in the same directory as the JSON file.   Note that this script runs with `python` directly instead of using Blender (which does not know about the `neuprint-python` module).

        python neuVid/neuVid/buildSynapses.py -i ex4.json

6. Run the last four `neuVid` scripts as above.  Remember that `blender` is shorthand for the actual platform-specific path to the Blender executable, as described above.

        blender --background --python neuVid/neuVid/importMeshes.py -- -i ex4.json
        blender --background --python neuVid/neuVid/addAnimation.py -- -i ex4.json
        blender --background --python neuVid/neuVid/render.py -- -i ex4.json
        blender --background --python neuVid/neuVid/assembleFrames.py -- -i ex4.json

## Usage with SWC Files

Some projects, such as the [Janelia MouseLight project](https://www.janelia.org/project-team/mouselight), represent neurons in [SWC format](https://neuroinformatics.nl/swcPlus/). The extra step of converting SWC files to [OBJ files](https://en.wikipedia.org/wiki/Wavefront_.obj_file) is handled automatically by `neuVid`.

1. Create an input JSON file that mentions the SWC files, as in the examples from the [detailed documentation](documentation/README.md#swc-files).

2. Run `importMeshes.py` as in the other examples. It will create OBJ files (in the `neuVidNeuronMeshes` directory, a sibling to the input JSON file) from the SWC files. See the [detailed documentation](documentation/README.md#swc-files) for some options related to the size and resolution of the generated OBJ files.

3. Use `buildSynapses.py`, `addAnimation.py`, `render.py`, `compLabels.py` (described below) and `assembleFrames.py` as in the other examples.

## Rendering on a Compute Cluster

Rendering can be performed on a compute cluster, a collection of computers shared between users to meet a facility's needs for high-performance computing (HPC). [IBM Spectrum LSF](https://www.ibm.com/docs/en/spectrum-lsf/10.1.0?topic=started-quick-start-guide) is the HPC platform that `neuVid` assumes is available. Rendering on a cluster involves the following steps:

1. Run `importNg.py`, `buildSynapses.py`, `importMeshes.py` and `addAnimation.py` as in the other examples.
2. Make sure machines on the cluster can access the `.json` and `.blend` files, the Blender executable, and the directory for the final rendered frames.
3. Open a shell (terminal) on the cluster's host machine for submitting jobs.
4. The `neuVid` script for rendering on a cluster is `clusterRender.py`, and its arguments are almost identical to those for the standard `render.py` script.  Say standard rendering would be invoked as follows:

        blender --background --python neuVid/neuVid/render.py -- ...

    Cluster rendering then would be invoked in this way:

        blender --background --python neuVid/neuVid/clusterRender.py -- -P account ...

    The new argument, `-P account`, specifies the account to be billed for the time on the cluster. Note that this use of the `clusterRendering.py` script is synchronous: the script does not finish until the cluster job comes off the "pending" queue and runs to completion.
5. For additional options (e.g., to specify the cluster or the "slot" count), see the [detailed documentation](documentation/README.md#compute-cluster-usage).


## Usage with Axes

In some videos, it is helpful to include a small set of arrows in the corner indicating biological directions like anterior, posterior, dorsal, ventral.  Such axes can be added by running the `compAxes.py` script before assembling the final video with `assembleFrames.py`.  The `compAxes.py` script uses the camera from the Blender file produced by `addAnimation.py` so the axes match the camera motion.  This approach involves the following steps:

1. Use `importNg.py`, `fetchMeshes.py`, `importMeshes.py`, `buildSynapses.py`, `addAnimation.py`, and `render.py` as in the other examples.
2. Add the `axes` category as a sibling to `neurons`, `rois` and `synapses`, to specify the arrow's orientations and identifying labels (see the [detailed documentation](documentation/README.md#axes)).
3. If the axes need to disappear during parts of the video, add `fade` commands.
4. Composite the axes onto the rendered frames:

        blender --background --python neuVid/neuVid/compAxes.py -- -i ex5.json

   The resulting frames will be in the directory (folder) `ex5-frames-axes`.
5. If the details or timing of the axes needs revision, edit the `axes` category and `fade` commands and run only `compAxes.py` again.  Doing so is much faster than running `render.py`.
6. Assemble the final video from these frames:

        blender --background --python neuVid/neuVid/assembleFrames.py -- -i ex5-frames-axes

## Usage with Labels

One way to add textual labels and titles is to add them to the finished video with an interactive editing application like [iMovie](https://www.apple.com/imovie/) or [Premiere](https://www.adobe.com/products/premiere.html).  Another way is to describe the labels in `neuVid`'s input JSON file and use the `compLabels.py` script to add the labels before assembling the final video with `assembleFrames.py`.  The latter approach makes it simpler to keep track of multiple labels, and to coordinate the timing of the labels with the timing of the animation.  This approach involves the following steps:

1. Use `importNg.py`, `fetchMeshes.py`, `importMeshes.py`, `buildSynapses.py`, `addAnimation.py`, `render.py`, and `compAxes.py` as in the other examples.
2. Define the labels and their timing with `label` commands in the JSON file (see the [detailed documentation](documentation/README.md#label)).
3. Composite the labels onto the rendered frames:

        blender --background --python neuVid/neuVid/compLabels.py -- -i ex6.json

   The resulting frames will be in the directory (folder) `ex6-frames-labeled`.  If axes have been added already, add the `-if` (`--inputFrames`) argument to indicate the directory with the input frames (produced by `compAxes.py`):

        blender --background --python neuVid/neuVid/compLabels.py -- -i ex6.json -if ex6-frames-axes

   The resulting frames will be in the directory `ex6-frames-axes-labeled`.
4. If the content or timing of the labels needs revision, edit the `label` commands and run only `compLabels.py` again.  Doing so is much faster than running `render.py`.
5. Assemble the final video from these frames:

        blender --background --python neuVid/neuVid/assembleFrames.py -- -i ex6-frames-labeled

    Or:

        blender --background --python neuVid/neuVid/assembleFrames.py -- -i ex6-frames-axes-labeled


## Usage with Natural Language Input

An experimental component of `neuVid` takes a description of a video in natural language and translates it to JSON using 
[generative AI](https://en.wikipedia.org/wiki/Generative_artificial_intelligence).  For now, at least, an [Anthropic API key](https://console.anthropic.com/login) or [OpenAI API key](https://platform.openai.com/signup) is required to use this component. Use the following steps:

1. The `generate` desktop application launches the user interface for entering descriptions and generating JSON.  Install `generate` by downloading an executable from the [releases page of this repository](https://github.com/connectome-neuprint/neuVid/releases). *Chrome on macOS or Windows raises a dialog that incorrectly calls the compressed (.zip) file with the executable "suspicious" or "uncommon". To unblock and complete the donwload, press the right arrow on the dialog, then press the download button that appears. On Windows a "protected your PC" dialog may then appear; press "More info" and then "Run anyway".*  Safari on macOS and Chrome on Linux do not have these problems. After downloading, extract the executable from the .zip file: double-click on macOS, or right-click on Windows and choose "Extract All" or an item from the "7-Zip" menu, or use the `unzip` command on Linux. Move the executable to a standard place, like `/Applications` on macOS, or `C:\Program Files\newVid` on Windows, or `~/bin` on Linux.

2. The first time `generate` is run, it prompts for the name of the large-language model (LLM) to use.  Enter an [Anthropic model](https://docs.anthropic.com/claude/docs/models-overview#claude-3-a-new-generation-of-ai) (e.g., `claude-3-opus-20240229`, the best peforming model so far) or an [OpenAI model](https://platform.openai.com/docs/models/gpt-4-and-gpt-4-turbo) (e.g., `gpt-4-0613`, which works better than `gpt-4-turbo-preview` for neuVid input). The model name is saved for use in futures sessions, and it can be changed using the "Settings/Model..." menu item.

3. Then `generate` prompts for an API key, from either Anthropic or OpenAI based on the model just chosen. The entered key is saved for future sessions, and can be changed using the "Settings/API Key..." menu item.

4. Type the description of the video in the lower text area, and press the "Generate" button.

5. After some processing time (which could be a minute or so for longer descriptions), the generated JSON will appear in the upper text area.  Press the "Save..." button to save it to a file for use as input to the other `neuVid` scripts.

For more information, see the [detailed documentation](documentation/README.md#natural-language-input-and-generative-ai).

## Usage with VVDViewer

For volumetric data sets lacking a segmentation, use the following approach.  

[![Representative Expression Patterns in the Drosophila Visual System](https://img.youtube.com/vi/OE9icXDM8q8/maxresdefault.jpg)](https://www.youtube.com/watch?v=OE9icXDM8q8)

1. Install [VVDViewer](https://github.com/JaneliaSciComp/VVDViewer).  The simplest approach is to download an installer from the [releases page](https://github.com/JaneliaSciComp/VVDViewer/releases).

2. Install `animateVvd` by downloading an executable from the [releases page of this repository](https://github.com/connectome-neuprint/neuVid/releases).  It will be a compressed (.zip) file, so extract it on macOS by double-clicking; or extract it on Windows by right-clicking and choosing "Extract All" or an item from the "7-Zip" menu; or extract it on Linux with the `unzip` command.  Move the executable to a standard place, like `/Applications` on macOS, or `C:\Program Files\newVid` on Windows, or `~/bin` on Linux.

3. To get a head start on the animation, `animateVvd` can build a basic JSON from a directory of volumes in [H5J format](https://github.com/JaneliaSciComp/workstation/blob/master/docs/H5JFileFormat.md), say, `exampleVolumes`.  In a shell (terminal), run the following, where `animateVvd` is shorthand for the actual platform-specific path to the executable (something like `/Applications/animateVvd.app/Contents/MacOS/animateVvd` on macOS; or like `"C:\Program Files\neuVid\animateVvd.exe"` on Windows, where the quotes are significant since the path contains a space; or like `~/bin/animateVvd.bin` on Linux).

        animateVvd -i exampleVolumes

4. Edit `exampleVolumes.json` to add more animation commands.  See the [detailed documentation](documentation/README_VVD.md).

5. Use `animateVvd` again, to convert `exampleVolumes.json` into a project file for VVDViewer, `exampleVolumes.vrp`:

        animateVvd -i exampleVolumes.json

6. Run VVDViewer, and press the "Open Project" button at the top to load `exampleVolumes.vrp`.

7. Close all the VVDViewer panels except "Render: View 1" and "Record/Export" to make the rendered view as big as possible (as its size is the size of the final video).

8. In the "Record/Export" panel, switch to the "Advanced" tab.

9. Press the "Save..." button to render the video.  Do not press the "Play" button and then rewind back to the start before pressing "Save...", as doing so sometimes causes glitches in the saved video.

## History

These scripts come from a collaboration at [HHMI's Janelia Research Campus](https://www.janelia.org/) between the [FlyEM project](https://www.janelia.org/project-team/flyem) and the [Scientific Computing Software group](https://www.janelia.org/support-team/scientific-computing-software).
The first use was for the [hemibrain connectome release](https://www.janelia.org/project-team/flyem/hemibrain) in January, 2020.  Videos made with `neuVid` were the winner and second runner up for the [2021 Drosophila Image Award](https://drosophila-images.org/2021-2/) from the [Genetics Society of America](https://genetics-gsa.org/).



## Acknowledgements

[David Ackerman](https://github.com/davidackerman) contributed the first version of the code to fetch [OpenOrganelle](https://openorganelle.janelia.org/) meshes.
[Marisa Dreher](https://dreherdesignstudio.com) and [Frank Loesche](https://github.com/floesche) helped improve the system's usability.
