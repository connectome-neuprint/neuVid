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
7. Run the script to render the animation with the internal Blender renderer.  This step takes the longest, about 30-40 minutes on a modern desktop or laptop computer.
```
blender --background --python neuVid/render.py -- -ib /tmp/example1Anim.blender -o /tmp/framesFinal
```
8. Run the script to assemble the rendered frames into a video (named `1-N.avi`, where `N` is the number of rendered frames).
```
blender --background --python neuVid/assembleFrames.py -- -i /tmp/framesFinal -o /tmp
```

## Tips

These scripts avoid literal positions as much as possible (e.g., `frameCamera` sets the camera position implicitly so some objects fill the view).  Nevertheless, litera positions sometimes are unavoidable (e.g., when the camera view should be filled with just part of an object, with `centerCamera`).  One way to get the coordinates of a literal position is to use `neuPrintExplorer` (i.e., [https://neuprint.janelia.org/](https://neuprint.janelia.org/)): in the skeleton view, shift-click on a particular position on a neuron body sets the camera target to that position.  All we need, then, is a way to get that target position from `neuPrintExplorer`.

For better or worse, `neuPrintExplorer`'s current user interface does not present that target position.  The best work-around for now is to get the target position from the URL `neuPrintExplorer` creates for the skeleton view.  Doing so requires a few particular steps, to force the URL to be updated accordingly:

1. Do a "Find Neurons" query for the neuron body in question.
2. Click on "eye" icon to split the query result panel, with the right half being a skeleton view showing the neuron.
3. Close the skeleton viewer in the right half.
4. Go to the "SKELETON" tab that still exists after the "NEUROGLANCER" tab.
5. Shift-click to set the camera target.
6. Go to the "NEUROGLANCER" tab, then immediately back to the "SKELETON" tab.
7. The switching of tabs in the previous step makes the `neuPrintExplorer` URL contain a "coordinates" section near the end, with the camera position and target.
8. In a terminal shell run the script to parse that URL and extract the target.  Note: with most shells, the URL must be enclosed in single quotes(') to avoid problems due to the special characters in the URL.
```
python neuVid/parseTarget.py 'https://neuprint-test.janelia.org/results?dataset...%5D%5Bcoordinates%5D=31501.69753529602%2C63202.63782931245%2C23355.220703777315%2C22390.66247762118%2C24011.276508917697%2C31327.48613433571&tab=2&ftab='
```
9. The camera target position will be printed to the shell, in a form that can be used directly with, say, `centerCamera`.
```
[22391, 24011, 31327]
```
10. To get another target position, shift-click again, and then repeat steps 6 through 9 again.  It is necessary to go to the "NEUROGLANCER" tab and then back to the "SKELETON" tab to force the URL to update with the new camera target.
