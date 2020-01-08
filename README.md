# neuVid

## Summary

These Python scripts generate simple anatomical videos in [Blender](https://www.blender.org/), following the conventions common in neuroscience research on the *Drosophila* fruit fly.  The input is a JSON file giving a high-level description of anatomical elements (e.g., neurons, regions of interest, synapses) and how they are animated (e.g., the camera frames on some neurons, then those neurons fade out while the camera orbits around them).  Rendering of medium quality can be done relatively quickly using the Blender internal renderer, and high-quality renderings can be done more slowly with the [OTOY Octane path-tracing renderer](https://home.otoy.com/render/octane-render/) (which requires a commercial license).



## Basic Usage
Here is how to render the example video.  It assumes access to data on the internal network for the [HHMI Janelia Research Campus](http://www.janelia.org).
1. Install Blender.  Currently, these scripts assume [Blender 2.79](https://download.blender.org/release/Blender2.79/).
2. Open a terminal shell, and change the current directory to the root of a neuVid repository.
3. Run the script to download meshes and create the basic Blender file without animation (in `/tmp`, for simplicity).  This stage creates two directories for downloaded mesh files, `neuVidNeuronMeshes` and `neuVidRoiMeshes`, in the same directory as the JSON file.
```
blender --background --python neuVid/importMeshes.py -- -ij examples/example1.json -o /tmp/example1.blend
```
4. Run the script to create another Blender file with animation.  Adding animation is a separate step since it can take significantly less time than creating the basic Blender file, and may need to be done repeatedly as the animation specification is refined.
```
blender --background --python neuVid/addAnimation.py -- -ij examples/example1.json -ib /tmp/example1.blend -o /tmp/example1Anim.blender
```
5. If desired, preview the animation by opening the blender file (`/tmp/example1Anim.blender`) in a normal (not background) Blender session.
6. Make an directory for the rendered frames (`/tmp/framesFinal`).
7. Run the script to render the animation with the internal Blender renderer.  This step takes the longest.
```
blender --background --python neuVid/render.py -- -ib /tmp/example1Anim.blender -o /tmp/framesFinal
```
8. Run the script to assemble the rendered frames into a video (named `1-N.avi`, where `N` is the number of rendered frames).
```
blender --background --python neuVid/assembleFrames.py -- -i /tmp/framesFinal -o /tmp
```
