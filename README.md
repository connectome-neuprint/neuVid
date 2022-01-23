# neuVid

## Summary

These Python scripts generate simple anatomical videos in [Blender](https://www.blender.org/), following the conventions common in neuroscience research on the *Drosophila* fruit fly.  The input is a [JSON](https://en.wikipedia.org/wiki/JSON) file giving a high-level description of anatomical elements (e.g., neurons, regions of interest, synapses) and how they are animated (e.g., the camera frames on some neurons, then those neurons fade out while the camera orbits around them).  Renderings of medium quality can be done relatively quickly using the default Blender renderer, and high-quality renderings can be done more slowly with a path-tracing renderer: Blender's Cycles, or the [OTOY Octane renderer](https://home.otoy.com/render/octane-render/) (which requires a commercial license).  Here is a video scripted with `neuVid` and rendered with Octane (with titles added separately in [iMovie](https://www.apple.com/imovie/)):

[![Watch the video](https://img.youtube.com/vi/nu0b_tjCGxQ/maxresdefault.jpg)](https://www.youtube.com/watch?v=nu0b_tjCGxQ)

## Basic Usage
Here is how to render a simple example video:
1. [Install Blender](https://www.blender.org/download/).  These scripts were developed originally for version 2.79 but now work for later versions, like 2.93 and 3.0.
2. Clone this repository.
3. Open a terminal shell, and change the current directory to the root of the cloned repository (i.e., the directory containing the subdirectories `documentation`, `examples`, etc.).
4. Copy `examples/example1.json` to some writable directory like `/tmp`.
5. Run the script to download meshes and create the basic Blender file without animation in the same directory as the JSON file.  This stage also creates two directories for downloaded mesh files, `neuVidNeuronMeshes` and `neuVidRoiMeshes`, also in the same directory as the JSON file.
```
blender --background --python neuVid/importMeshes.py -- -ij /tmp/example1.json
```
6. Run the script to create a second Blender file with animation.  Adding animation is a separate step since it can take significantly less time than creating the basic Blender file, and may need to be done repeatedly as the animation specification is refined.
```
blender --background --python neuVid/addAnimation.py -- -ij /tmp/example1.json
```
7. If desired, preview the animation by opening the second blender file (`/tmp/example1Anim.blender`) in a normal interactive (not background) Blender session.
8. Run the script to render the animation with the default Blender renderer (Eevee for Blender 2.80 and later).  This step takes the longest, about 30-40 minutes on a modern desktop or laptop computer.
```
blender --background --python neuVid/render.py -- -o /tmp/framesFinal
```
9. Run the script to assemble the rendered frames into a video (named `/tmp/1-N.avi`, where `N` is the number of rendered frames).
```
blender --background --python neuVid/assembleFrames.py -- -i /tmp/framesFinal -o /tmp
```

## Usage with Synapses

Synapse locations come from queries processed by the [`neuprint-python` module](https://github.com/connectome-neuprint/neuprint-python).  As mentioned on its project page, `neuprint-python` can be installed with either `conda` or `pip`.  Either approach has the unfortunate consequence that an extra script must be run outside of Blender before `importMeshes.py`, because Blender comes with its own version of Python.
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

6. Run the script to create query the synapses.  This stage creates a directory for the synapse meshes, `neuVidSynapseMeshes`, in the same directory as the JSON file (assumed to have been copied to `/tmp` as in the first example)
```
python neuVid/buildSynapses.py -ij /tmp/example2.json
```

7. Now proceed with the normal steps, as described in the previous section.
```
blender --background --python neuVid/importMeshes.py -- -ij /tmp/example2.json
blender --background --python neuVid/addAnimation.py -- -ij /tmp/example2.json
blender --background --python neuVid/render.py -- -ib /tmp/example2.json -o /tmp/framesFinal
blender --background --python neuVid/assembleFrames.py -- -i /tmp/framesFinal -o /tmp
```

## History

These scripts come from a collaboration at [HHMI's Janelia Research Campus](https://www.janelia.org/) between the [FlyEM project](https://www.janelia.org/project-team/flyem) and the [Scientific Computing Software group](https://www.janelia.org/support-team/scientific-computing-software).
The first use was for the [hemibrain connectome release](https://www.janelia.org/project-team/flyem/hemibrain) in January, 2020.  Videos made with `neuVid` were the winner and second runner up for the [2021 Drosophila Image Award](https://drosophila-images.org/2021-2/) from the [Genetics Society of America](https://genetics-gsa.org/).
