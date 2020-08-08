# neuVid

## Summary

These Python scripts generate simple anatomical videos in [Blender](https://www.blender.org/), following the conventions common in neuroscience research on the *Drosophila* fruit fly.  The input is a JSON file giving a high-level description of anatomical elements (e.g., neurons, regions of interest, synapses) and how they are animated (e.g., the camera frames on some neurons, then those neurons fade out while the camera orbits around them).  Rendering of medium quality can be done relatively quickly using the Blender internal renderer, and high-quality renderings can be done more slowly with the [OTOY Octane path-tracing renderer](https://home.otoy.com/render/octane-render/) (which requires a commercial license).  Here is an example of a video scripted with `neuVid` and rendered with Octane (with titles added separately in iMovie):

[![Watch the video](https://img.youtube.com/vi/nu0b_tjCGxQ/maxresdefault.jpg)](https://www.youtube.com/watch?v=nu0b_tjCGxQ)

## Basic Usage
Here is how to render the example video:
1. Install Blender.  Currently, these scripts assume [Blender 2.79](https://download.blender.org/release/Blender2.79/).
2. Open a terminal shell, and change the current directory to the root of a `neuVid` repository.
3. Run the script to download meshes and create the basic Blender file without animation (in `/tmp`, for simplicity).  This stage creates two directories for downloaded mesh files, `neuVidNeuronMeshes` and `neuVidRoiMeshes`, in the same directory as the JSON file.
```
blender --background --python neuVid/importMeshes.py -- -ij examples/example1.json -o /tmp/example1.blend
```
4. Run the script to create another Blender file with animation.  Adding animation is a separate step since it can take significantly less time than creating the basic Blender file, and may need to be done repeatedly as the animation specification is refined.
```
blender --background --python neuVid/addAnimation.py -- -ij examples/example1.json -ib /tmp/example1.blend -o /tmp/example1Anim.blend
```
5. If desired, preview the animation by opening the blender file (`/tmp/example1Anim.blender`) in a normal (not background) Blender session.
6. Make an directory for the rendered frames (`/tmp/framesFinal`).
7. Run the script to render the animation with the internal Blender renderer.  This step takes the longest, about 30-40 minutes on a modern desktop or laptop computer.
```
blender --background --python neuVid/render.py -- -ib /tmp/example1Anim.blend -o /tmp/framesFinal
```
8. Run the script to assemble the rendered frames into a video (named `1-N.avi`, where `N` is the number of rendered frames).
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

6. Run the script to create query the synapses.  This stage creates a directory for the synapse meshes, `neuVidSynapseMeshes`, in the same directory as the JSON file.
```
python neuVid/buildSynapses.py -ij examples/example2.json
```

7. Now proceed with the normal steps, as described in the previous section.
```
blender --background --python neuVid/importMeshes.py -- -ij examples/example2.json -o /tmp/example2.blend
blender --background --python neuVid/addAnimation.py -- -ij examples/example2.json -ib /tmp/example2.blend -o /tmp/example2Anim.blend
blender --background --python neuVid/render.py -- -ib /tmp/example2Anim.blend -o /tmp/framesFinal
blender --background --python neuVid/assembleFrames.py -- -i /tmp/framesFinal -o /tmp
```

## History

These scripts come from a collaboration at [HHMI's Janelia Research Campus](https://www.janelia.org/) between the [FlyEM project](https://www.janelia.org/project-team/flyem) and the [Scientific Computing Software group](https://www.janelia.org/support-team/scientific-computing-software).
The first use was for the [hemibrain connectome release](https://www.janelia.org/project-team/flyem/hemibrain) in January, 2020.
