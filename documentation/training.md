<!-- VERSION: 1.1.0 -->

# Input for neuVid

## Overall Structure

<!-- CHUNK START -->
The neuVid system generates high-quality videos from biological data, rendered by Blender.
Input is a JSON file.
<!-- CHUNK END -->

<!-- CHUNK START -->
The JSON file starts with one or more of:

* The `"neurons"` key's value object specifies the neurons (bodies, segments) in the video, and their data sources.
* The `"rois"` key's object specifies the ROIs (regions of interest, neuropils) and their sources.
* The `"synapses"` key specifies which neurons have synapses.
<!-- CHUNK END -->
<!-- TODO: Include grayscales if doing so does not dilute the context. -->
* The `"grayscales"` key specifies image slices from the original microscopy data.

<!-- CHUNK START -->
Next is the `"animation"` key, whose value is an array of animation commands.
<!-- CHUNK END -->

## The `"neurons"` Key

<!-- CHUNK START -->
<!-- STEP: 1 -->
Here are examples of a request followed by the JSON that should be generated.
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 1 -->
Example: Create a group named `"G"` with one neuron, ID (identifier) 6. The source for this neuron is the Janelia FlyEM hemibrain server v1.2 (the hemibrain, or FlyEM hemibrain, or Janelia FlyEM hemibrain), meaning the neuron mesh is loaded from the server, with URL from the `"source"` key:
```json
{
  "neurons": {
    "source": "https://hemibrain-dvid.janelia.org/api/node/31597/segmentation_meshes",
    "G": [6]
  },
  "rois": {},
  "animation": []
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 1 -->
Example: Create a group `"P"` of neurons 8 and 4. The neuron meshes are loaded from the Janelia FlyEM MANC v1.0 server (the MANC), per the `"source"`.
```json
{
  "neurons": {
    "source": "https://manc-dvid.janelia.org/api/node/v1.0/segmentation_meshes",
    "P": [8, 4]
  },
  "rois": {},
  "lightRotationY": 180,
  "animation": [
    ["orbitCamera", {"axis": "y", "endingRelativeAngle": 180}]
  ]
}
```
<!-- CHUNK END -->
The `"lighRotationY"` and `"orbitCamera"` commands are described later.

<!-- CHUNK START -->
<!-- STEP: 1 -->
Example: Create two groups, `"U"` containing neurons 3 and 7, `"J"` containing  6, 4 and 9. The neuron meshes come from the FlyWire FAFB server per the `"source"`.
```json
{
  "neurons": {
    "source": "precomputed://gs://flywire_v141_m783",
    "U": [3, 7],
    "J": [6, 4, 9]
  },
  "rois": {},
  "lightRotationX": -90,
  "animation": [
    ["orbitCamera", {"axis": "x", "endingRelativeAngle": -90}]
  ]
}
```
<!-- CHUNK END -->
The `"lightRotationX"` and `"orbitCamera"` commands are described later. 
A JSON file with the FlyWire source requires an extra step during the conversion into a Blender file for rendering; see the discussion of `fetchMeshes.py` in 
[the documentation](https://github.com/connectome-neuprint/neuVid#usage-with-neuroglancer).

<!-- CHUNK START -->
<!-- STEP: 1 -->
Example: Create a group `"N"` of three neurons, 7, 3, and 5. The meshes come from a directory (folder) on the local file system, with the path from the `"source"` key.
```json
{
  "neurons": {
    "source": "t/x",
    "E": [7, 3, 5]
  },
  "rois": {},
  "animation": []
}
```
<!-- CHUNK END -->
The neuron mesh files should be in OBJ format with the `.obj` extension: `t/x/7.obj`, `t/x/3.obj`, `t/x/5.obj`.

<!-- CHUNK START -->
<!-- STEP: 1 -->
Example: Use two neuron mesh sources: local directory `"g/v"` and the hemibrain server. Group `"K"` is the neurons 4 and 2 with meshes from the local source. Group `"S"` is the neuron 6 using the hemibrain meshes:
```json
{
  "neurons": {
    "source": [
        "g/v",
        "https://hemibrain-dvid.janelia.org/api/node/31597/segmentation_meshes"
    ],
    "K": {"ids": [4, 2], "sourceIndex": 0},
    "S": {"ids": [6], "sourceIndex": 1},
  },
  "rois": {},
  "animation": []
}
```
<!-- CHUNK END -->
The `"lighRotationY"` and `"orbitCamera"` commands are described later.

<!-- CHUNK START -->
<!-- STEP: 1 -->
Example: Create three groups of neurons, with the IDs for each group coming from a file in local directory `"j/i"`. Group `"H"` has ID file `"H.txt"`, group `"A"` has ID file `"A.txt"`, group `"P"` ID file `"P.txt"`. The neuron meshes all come from local directory `"j/i".
```json
{
  "neurons": {
    "source": "j/i",
    "idsSource": "o/m",
    "H": {"ids": "H.txt"},
    "A": {"ids": "A.txt"},
    "P": {"ids": "P.txt"}
  },
  "rois": {},
  "animation": []
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 1 -->
Example: Use two local directories for meshes, `"u/q"` and `"z/p"`. Neuron group `"S"` has IDs from file `"S.txt"` and meshes from the first source. Group `"C"` uses IDs from `"C.txt"` and the second mesh source. All neuron ID files are in the local directory `"y/i"`.
```json
{
  "neurons": {
    "source": ["u/q", "z/p"],
    "idsSource": "y/i",
    "S": {"ids": "S.txt", "sourceIndex": 0},
    "C": {"ids": "C.txt", "sourceIndex": 1}
  },
  "rois": {},
  "animation": []
}
```
<!-- CHUNK END -->

To reiterate:
<!-- CHUNK START -->
<!-- STEP: 1 -->
The neuron `"source"` URL for the Janelia FlyEM hemibrain v1.2 (FlyEM hemibrain, hemibrain) is: `"https://hemibrain-dvid.janelia.org/api/node/31597/segmentation_meshes"`. Also use this source for neurons if the ROI source is the hemibrain.
<!-- CHUNK END -->
<!-- CHUNK START -->
<!-- STEP: 1 -->
The neuron `"source"` URL for the Janelia FlyEM MANC (the FlyEM MANC, the MANC, the FlyEM VNC, the VNC) is: `"https://manc-dvid.janelia.org/api/node/v1.0/segmentation_meshes"`. Also use this source for neurons if the ROI source is the MANC.
<!-- CHUNK END -->
<!-- CHUNK START -->
<!-- STEP: 1 -->
The neuron `"source"` URL for the FlyWire FAFB (or FlyWire) is: `"precomputed://gs://flywire_v141_m783"`.
<!-- CHUNK END -->

## The `"rois"` Key

The term "ROI" means "region of interest". ROIs are rendered with silhouette edges.

<!-- CHUNK START -->
<!-- STEP: 1 -->
Here are examples of a request followed by the JSON that should be generated.
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 1 -->
Example: Create a group `"F"` with one ROI, `"FB"`. The source is the Janelia FlyEM hemibrain server v1.2 (the hemibrain, the FlyEM hemibrain, the Janelia FlyEM hemibrain). Also make `"K"` with the ROI `"all_neuropils"`, the hemibrain's outer shell or boundary:
```json
{
  "rois": {
    "source": "https://hemibrain-dvid.janelia.org/api/node/31597/roisSmoothedDecimated",
    "F": ["FB"],
    "K": ["all_neuropils"]
  },
  "animation": []
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 1 -->
Example: `"G"` includes two ROIs, `"IntNp(T1)(L)"` and `"IntNp(T1)(R)"`, from the Janelia FlyEM MANC (the FlyEM MANC, the MANC, the FlyEM VNC, the VNC). `"A"` is the ROI `"all_VNC"`, the MANC's boundary:
```json
{
  "rois": {
    "source": "https://manc-dvid.janelia.org/api/node/v1.0/roisSmoothedDecimated",
    "G": ["IntNp(T1)(L)", "IntNp(T1)(R)"],
    "A": ["all_VNC"]
  },
  "lightRotationY": 180,
  "animation": [
    ["orbitCamera", {"axis": "y", "endingRelativeAngle": 180}]
  ]
}
```
<!-- CHUNK END -->
The `"lightRotationY"` and `"orbitCamera"` commands are described later.

<!-- CHUNK START -->
<!-- STEP: 1 -->
Example: `"R"` includes two ROIs, `"IB"` and `"PB"`, from local directory (folder) `"w/y"`. `"Q"` has the ROI `"SMP"` from the local path `"h/j"`.
```json
{
  "rois": {
    "source": ["w/y", "h/j"],
    "R": {"ids": ["IB", "PB"], "sourceIndex": 0},
    "Q": {"ids": ["SMP"], "sourceIndex": 1},
  },
  "animation": []
}
```
<!-- CHUNK END -->
The ROI mesh files should be in OBJ format with the `.obj` extension: `w/y/IB.obj`, `w/y/PB.obj`, `h/j/SMP.obj`.

<!-- CHUNK START -->
<!-- STEP: 1 -->
Example: Fade on ROI `"EB"` from the hemibrain:
```json
{
  "rois": {
    "source": "https://hemibrain-dvid.janelia.org/api/node/31597/roisSmoothedDecimated",
    "EB": ["FB"],
  },
  "animation": [
    ["fade", {"meshes": "rois.EB", "startingAlpha": 0, "endingAlpha": 0.2, "duration": 1}],
    ["advanceTime", {"by": 1}]
  ]
}
```
<!-- CHUNK END -->
The `"fade"` and `'advanceTime"` commands are described later.

<!-- CHUNK START -->
<!-- STEP: 1 -->
Example: Show FlyWire's main ROI (a.k.a., the full brain, the outer shell, the all ROI).
```json
{
  "rois": {
    "source": "precomputed://gs://flywire_neuropil_meshes/whole_neuropil/brain_mesh_v3",
    "all": ["1"]
  },
  "lightRotationX": -90,
  "animation": [
    ["orbitCamera", {"axis": "x", "endingRelativeAngle": -90}],
    ["setValue", {"meshes": "rois", "alpha": 0.05}],
    ["frameCamera", {"bound": "rois.all"}]
  ]
}
```
<!-- CHUNK END -->
The `"orbitCamera"`, `"setValue"`, and `"frameCamera"` commands are described later.

## The `"synapses"` Key

The simplest way to include synapses is to import them from Neuroglancer with the `importNg.py` script; see 
[the documentation](https://github.com/connectome-neuprint/neuVid#usage-with-neuroglancer).
This approach does not support the `"partner"` key described below, and the `"source"` URL is a bit different.

An alternative is to use the specifications described here. These specifications must be processed by the `buildSynapses.py` script; see [the documentation](https://github.com/connectome-neuprint/neuVid#advanced-usage-with-synapses).

<!-- CHUNK START -->
<!-- STEP: 1 -->
Here are examples of a request followed by the JSON that should be generated.
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 1 -->
Example: `"9post"` are neuron 9's postsynaptic sites (the postsynaptic sites on 9, or 9's input synapses, or the input synapses on 9, or 9's T-bars), coming from any other neuron. Infer the `"synapses"` `"source"` from the `"neurons"` `"source"` (the hemibrain). `"9pre"` are 9's presynaptic sites (or the presynaptic sites on 9, or 9's output synapses, or the output synapses on '9, 9's PSDs), going to any other neuron. Each synapse is rendered as a ball. The synapses' default radius is 80 (use the default `"radius": 80` if none is mentioned).
```json
{
  "neurons": {
    "source": "https://hemibrain-dvid.janelia.org/api/node/31597/segmentation_meshes",
    "N": [9, 4]
  },
  "synapses": {
    "source": "https://neuprint.janelia.org/?dataset=hemibrain%3Av1.2.1",
    "9post": {
      "type": "post", "neuron": 9,
      "radius": 80
    },
    "9pre": {
      "type": "pre", "neuron": 9,
      "radius": 80
    }
  },
  "animation": []
}
```
<!-- CHUNK END -->
The units for the `"radius"` are the units of the neuron and ROI mesh vertex coordinates.

<!-- CHUNK START -->
<!-- STEP: 1 -->
Example: `"2post1"` are neuron 2's postsynaptic sites (the postsynaptic sites on 2, or 2's input synapses, or the input synapses on 2, or 2's T-bars) coming from neuron 1. `"2pre3"` are 2's presynaptic sites (the presynaptic sites on 9, or 9's output synapses, or the output synapses on 9, 9's PSDs) going to neuron 3. Infer the `"synapses"` `"source"` from the `"neurons"` `"source"` (the MANC). The radius of each synapse ball is 60 (overriding the default `"radius": 80`).
```json
{
  "neurons": {
    "source": "https://manc-dvid.janelia.org/api/node/v1.0/segmentation_meshes",
    "M": [1, 2, 3]
  },
  "synapses": {
    "source": "https://neuprint.janelia.org/?dataset=manc",
    "2post1": {
      "type": "post", "neuron": 2, "partner": 1,
      "radius": 60
    },
    "2pre3": {
      "type": "pre", "neuron": 2, "partner": 3,
      "radius": 60
    }
  },
  "animation": []
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 1 -->
Example: Fade on the output synapses of hemibrain neuron 6 connecting to neuron 4, taking 2 seconds:
```json
{
  "synapses": {
    "source": "https://neuprint.janelia.org/?dataset=hemibrain%3Av1.2.1",
    "6post4": {
      "type": "post", "neuron": 6, "partner": 4,
      "radius": 80
    }
  },
  "animation": [
    ["fade", {"meshes": "synapses.6post4", "startingAlpha": 0, "endingAlpha": 1, "duration": 2}],
    ["advanceTime", {"by": 2}]
  ]
}
```
<!-- CHUNK END -->
The `"fade"` and `"advanceTime"` commands are described later.

<!-- TODO: Include grayscales if doing so does not dilute the context. -->
## The `"grayscales"` Key

Description pending.

## Light Rotation

<!-- CHUNK START -->
<!-- STEP: 3 -->
When the MANC is the neuron mesh source,
or there is more than one mesh source including the MANC,
then before the `"animation"` array add a `"lightRotationY"` key to give the lights an orientation matching this data set:
```json
{
  "lightRotationY": 180,
  "animation": [
    ["orbitCamera", {"axis": "y", "endingRelativeAngle": 180}]
  ]
}
```
<!-- CHUNK END -->
The `"orbitCamera"` command is described later.

<!-- CHUNK START -->
<!-- STEP: 3 -->
When the any of the neurons (even only one element of a  `"neruons"` `"source"` array) come from the FlyWire FAFB, `"precomputed://gs://flywire_v141_m783"`, or the ROIs, then before the `"animation"` array add a `"lightRotationX"` key to give the  lights the orientation of this data set: 
```json
{
  "lightRotationX": -90,
  "animation": [
    ["orbitCamera", {"axis": "x", "endingRelativeAngle": -90}]
  ]
}
```
<!-- CHUNK END -->
The `"orbitCamera"` command is described later.

<!-- CHUNK START -->
<!-- STEP: 3 -->
But when neurons come from other sources, like the FlyEM hemibrain (URL `"https://hemibrain-dvid.janelia.org/api/node/31597/segmentation_meshes"`), then there is no `"lightRotationX"` or `"lightRotationY"` before the `"animation"` array:
```json
{
  "animation": [
  ]
}
```
<!-- CHUNK END -->

## The `"animation"` Key

<!-- CHUNK START -->
<!-- STEP: 2 -->
The `"animation"` key's value is an array of animation commands.
Each command is an array: command name, then command arguments object.
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Here are examples of requests followed by the animation commands (in JSON) that should be generated.
<!-- CHUNK END -->
The `"advanceTime"` command in these examples is described later.

### The `"fade"` Command

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Show `"Y"` by making it fade from alpha 0 (fully transparent or invisible) to alpha 1 (fully opaque or fully visible), taking 2 seconds per the `"duration"`.
```json
{
  "animation": [
    ["fade", {"meshes": "neurons.Y", "startingAlpha": 0, "endingAlpha": 1, "duration": 2}],
    ["advanceTime", {"by": 2}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Make `"G"` fade from alpha 1 to alpha 0.5 in staggered form, one neuron after another spread out over the 5 second duration of the fading:
```json
{
  "animation": [
    ["fade", {"meshes": "neurons.G", "startingAlpha": 0, "endingAlpha": 1, "stagger": "constant", "duration": 5}],
    ["advanceTime", {"by": 5}]
  ]
}
```
<!-- CHUNK END -->

### The `"frameCamera"` Command

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Make the camera frame on the neurons in group `"V"` (the camera points at those neurons from far enough that they fill its view). Framing happens immediately at the current time:
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.V"}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Move the camera to where the neurons in `"T"` fill its view, taking 3 seconds:
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.T", "duration": 3}],
    ["advanceTime", {"by": 3}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
With `"scale"` of 0.5, the camera is half again as far from `"M"` as for a normal framing (so the neurons appear 2 times bigger).
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.M", "scale": 0.5}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: With `"scale"` of 3, the camera ends up 3 times farther away from the neurons in group `"E"` than for a normal framing (so the neurons appear 1/3 as big), and the camera movement takes 5 seconds:
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.E", "scale": 3, "duration": 5}],
    ["advanceTime", {"by": 5}]
  ]
}
```
<!-- CHUNK END -->

### The `"orbitCamera"` Command

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Orbit the camera (rotate it while staying the same distance away) all the way (360 degrees) around what the camera is framed on now (`"G"` due to the `"frameCamera"`), taking 7 seconds and using the default rotation axis, `"z"`.
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.G"}],
    ["orbitCamera", {"duration": 7}],
    ["advanceTime", {"by": 7}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Orbit halfway (180 degrees, per `"endingRelativeAngle"`) around what the camera is centered on now (`"C"` due to the `"frameCamera"`), for 4 seconds:
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.C"}],
    ["orbitCamera", {"endingRelativeAngle": 180, "duration": 4}],
    ["advanceTime", {"by": 4}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Orbit by -90 degrees about the `"x"` axis, per the `"axis"`, taking 3 seconds:
```json
{
  "animation": [
    ["orbitCamera", {"axis": "x", "endingRelativeAngle": -90, "duration": 3}],
    ["advanceTime", {"by": 3}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Orbit 30 degrees with rotation center being `"H"` (the center of its neurons' bounding box), per `"around"`, taking 1 second:
```json
{
  "animation": [
    ["orbitCamera", {"around": "neurons.H", "endingRelativeAngle": 30, "duration": 1}],
    ["advanceTime", {"by": 1}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Orbit 150 degrees, taking 6 seconds. Move the camera in (closer to what it is orbiting) as the orbiting proceeds, so it ends up half as far away as it started, per`"scale"` 0.5.
```json
{
  "animation": [
    ["orbitCamera", {"endingRelativeAngle": 150, "duration": 6, "scale": 0.5}],
    ["advanceTime", {"by": 6}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Orbit -80 degrees, and move the camera out (farther from what it is orbiting) as the orbiting proceeds, so it ends up twice as far away as it started, per `"scale"` 2.
```json
{
  "animation": [
    ["orbitCamera", {"endingRelativeAngle": -80, "duration": 4.5, "scale": 2}],
    ["advanceTime", {"by": 4.5}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 3 -->
When the MANC is the neuron mesh source,
or there is more than one mesh source including the MANC, URL `"https://manc-dvid.janelia.org/api/node/v1.0/segmentation_meshes"`, then the `"animation"` array starts with an `"orbitCamera"` of angle 180 about the `"y"` axis and no `"duration"`. All other commands (`"frameCamera"`, `"fade"`, `"setValue"`, etc.) follow this first command:
```json
{
  "lightRotationY": 180,
  "animation": [
    ["orbitCamera", {"axis": "y", "endingRelativeAngle": 180}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 3 -->
When any neurons come from the FlyWire FAFB server (or FlyWire), URL `"precomputed://gs://flywire_v141_m783"` (even as an item in a `"neurons"` `"source"` array), the `"animation"` array starts with an `"orbitCamera"` of -90 about the `"x"` axis and no `"duration"`. All other commands follow:
```json
{
  "lightRotationX": -90,
  "animation": [
    ["orbitCamera", {"axis": "x", "endingRelativeAngle": -90}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 3 -->
But when neurons come from other sources, like the FlyEM hemibrain (URL `"https://hemibrain-dvid.janelia.org/api/node/31597/segmentation_meshes"`), even as an item in a `"neurons"` `"source"` array, then the `"animation"` array needs no extra `"orbitCamera"` at the start:
```json
{
  "animation": [
  ]
}
```
<!-- CHUNK END -->

### The `"setValue"` Command

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Set the color of the neurons in group `"M"` to `"green"`, per the `"color"`, from the current time forward. Legal named colors: `"orange"`, `"brown"`, `"pink"`, `"blue"`, `"lightBlue"`, `"yellow"`, `"green"`, `"darkBlue"`, `"white"`, or hex (CSS) colors like `"#ffffff"`.
```json
{
  "animation": [
    ["setValue", {"meshes": "neurons.M", "color": "green"}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Set the alpha (transparency) of `"G"` to 0.2, per `"alpha"`, from the current time forward:
```json
{
  "animation": [
    ["setValue", {"meshes": "neurons.G", "alpha": 0.2}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
For an ROI, the exponent controls the silhoutte line rendering: a lower exponent (e.g., 2, 3) makes the ROI appear heavier and more prominent, while a higher exponent (e.g., 5, 6) makes the ROI appear lighter and less conspicuous. Set the exponents of `"R"` to 6, from the current time forward:
```json
{
  "animation": [
    ["setValue", {"meshes": "rois.R", "exponent": 6}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 3 -->
If `"rois"` has `"source"` and only one other key, then add a `"setValue"` for `"threshold"` at the start of the `"animation"` array.
Example:
```json
{
  "rois": {
    "source": "https://hemibrain-dvid.janelia.org/api/node/31597/roisSmoothedDecimated",
    "B": ["3"]
  },
  "animation": [
    ["setValue", {"meshes": "rois", "threshold": 1}]
  ]
}
```
<!-- CHUNK END -->
This setting hides distracting lines on the back of the ROI mesh, but it is tricky to use when there are multiple ROIs.

<!-- CHUNK START -->
<!-- STEP: 3 -->
Example:
```json
{
  "rois": {
    "source": "https://manc-dvid.janelia.org/api/node/v1.0/roisSmoothedDecimated",
    "D": ["8"]
  },
  "animation": [
    ["setValue", {"meshes": "rois", "threshold": 1}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 3 -->
Example:
```json
{
  "rois": {
    "source": "precomputed://gs://flywire_neuropil_meshes/whole_neuropil/brain_mesh_v3",
    "C": ["6"]
  },
  "animation": [
    ["setValue", {"meshes": "rois", "threshold": 1}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 3 -->
But if `"rois"` has `"source"` and two or more other keys, then do not add `"setValue"`.
Example:
```json
{
  "rois": {
    "source": "https://hemibrain-dvid.janelia.org/api/node/31597/roisSmoothedDecimated",
    "B": ["3"],
    "Q": ["5"]
  },
  "animation": [
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 3 -->
Example:
```json
{
  "rois": {
    "source": "https://manc-dvid.janelia.org/api/node/v1.0/roisSmoothedDecimated",
    "D": ["8"],
    "H": ["1"]
  },
  "animation": [
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 3 -->
Example:
```json
{
  "rois": {
    "source": "precomputed://gs://flywire_neuropil_meshes/whole_neuropil/brain_mesh_v3",
    "C": ["6"],
    "K": ["1"]
  },
  "animation": [
  ]
}
```
<!-- CHUNK END -->

<!-- TODO: Include grayscales if doing so does not dilute the context. -->
### The `"showPictureInPicture"` Command

Description pending.

<!-- TODO: ["showSlice", {"image": "grayscales.1", "euler": [-38.199, 0.701, -129.445], "scale": 300, "distance": 600, "duration": 6, "fade": 0.5}] -->

### The `"advanceTime"` Command

<!-- CHUNK START -->
<!-- STEP: 2 -->
In most cases a command with `"duration"` must be followed by an `"advanceTime"` with `"by"` matching that `"duration"`. The execption is for simultaneous commands at the same time, marked "exception example" here.
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Fade on `T` for 3 second. Then fade off `H` over 1 second:
```json
{
  "animation": [
    ["fade", {"meshes": "neurons.T", "startingAlpha": 0, "endingAlpha": 1, "duration": 3}]
    ["advanceTime", {"by": 3}],
    ["fade", {"meshes": "rois.H", "startingAlpha": 1, "endingAlpha": 0, "duration": 1}],
    ["advanceTime", {"by": 1}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Fade off `E` taking 4 seconds. Next, lasting 1 second, frame on `Q`.
```json
{
  "animation": [
    ["fade", {"meshes": "synapses.E", "startingAlpha": 1, "endingAlpha": 0, "duration": 4}]
    ["advanceTime", {"by": 4}],
    ["frameCamera", {"bound": "neurons.Q", "duration": 1}],
    ["advanceTime", {"by": 1}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: For 5 seconds, fade on `U`. Orbit by 9 degrees over 2 seconds:
```json
{
  "animation": [
    ["fade", {"meshes": "rois.U", "startingAlpha": 0, "endingAlpha": 1, "duration": 5}]
    ["advanceTime", {"by": 5}],
    ["orbitCamera", {"endingRelativeAngle": 9, "duration": 2}],
    ["advanceTime", {"by": 2}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Orbit the camera for 4 seconds while fading `B` down to alpha 0.5. Then frame on `D` in 2 seconds.
```json
{
  "animation": [
    ["orbitCamera", {"duration": 4}],
    ["fade", {"meshes": "synapses.B", "startingAlpha": 1, "endingAlpha": 0.5, "duration": 4}],
    ["advanceTime", {"by": 4}],
    ["frameCamera", {"bound": "neurons.S", "duration": 2}],
    ["advanceTime", {"by": 2}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Exception example: Fade on `A` taking 5 seconds. At the same time, fade `M` off for 3 seconds.
```json
{
  "animation": [
    ["fade", {"meshes": "rois.A", "startingAlpha": 0, "endingAlpha": 1, "duration": 5}],
    ["fade", {"meshes": "synapses.M", "startingAlpha": 1, "endingAlpha": 0, "duration": 3}],
    ["advanceTime", {"by": 5}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Exception example: For 2 seconds fade `P` and `W` on, and frame the camera on `S` in 8 seconds.
```json
{
  "animation": [
    ["fade", {"meshes": "neurons.P + neurons.W", "startingAlpha": 0, "endingAlpha": 1, "duration": 2}],
    ["frameCamera", {"bound": "rois.S", "duration": 8}],
    ["advanceTime", {"by": 8}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Frame on `S`. Reveal `J` in 2 seconds.
```json
{
  "animation": [
    ["frameCamera", {"bound": "rois.S"}],
    ["fade", {"meshes": "neurons.J", "startingAlpha": 0, "endingAlpha": 1, "duration": 2}],
    ["advanceTime", {"by": 2}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Frame on `I` taking 6 seconds. 5 seconds later, fade off `C` lasting 3 seconds:
```json
{
  "animation": [
    ["frameCamera", {"bound": "synapses.I", "duration": 6}],
    ["advanceTime", {"by": 6}],
    ["advanceTime", {"by": 5}],
    ["fade", {"meshes": "neurons.C", "startingAlpha": 1, "endingAlpha": 0, "duration": 3}],
    ["advanceTime", {"by": 3}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: For 5 seconds, frame on `K`. Then 8 seconds later, frame `B` over 9 seconds:
```json
{
  "animation": [
    ["frameCamera", {"bound": "rois.K", "duration": 5}],
    ["advanceTime", {"by": 5}],
    ["advanceTime", {"by": 8}],
    ["frameCamera", {"bound": "synapses.B", "duration": 9}],
    ["advanceTime", {"by": 9}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Frame on `R` taking 7 seconds. Next, wait 9 seconds. Orbit lasting 3 seconds.
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.R", "duration": 7}],
    ["advanceTime", {"by": 7}],
    ["advanceTime", {"by": 9}],
    ["orbitCamera", {"duration": 2}],
    ["advanceTime", {"by": 2}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: For 3 seconds, orbit the camera about _x_. And after 1 second, fade `N` and `D` off over 4 seconds.
```json
{
  "animation": [
    ["orbitCamera", {"axis": "x", "duration": 3}],
    ["advanceTime", {"by": 3}],
    ["advanceTime", {"by": 1}],
    ["fade", {"meshes": "rois.N + rois.D", "startingAlpha": 1, "endingAlpha": 0, "duration": 4}],
    ["advanceTime", {"by": 4}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Orbit taking 10 seconds. 5 seconds later, frame on `F` lasting 9 seconds.
```json
{
  "animation": [
    ["orbitCamera", {"duration": 10}],
    ["advanceTime", {"by": 10}],
    ["advanceTime", {"by": 4}],
    ["frameCamera", {"bound": "synapses.F", "duration": 9}],
    ["advanceTime", {"by": 9}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: For 2 seconds orbit -21 degrees. Wait 6 seconds. Orbit around _y_ over 5 seconds.
```json
{
  "animation": [
    ["orbitCamera", {"endingRelativeAngle": -21, "duration": 2}],
    ["advanceTime", {"by": 2}],
    ["advanceTime", {"by": 6}],
    ["orbitCamera", {"axis": "y", "duration": 5}],
    ["advanceTime", {"by": 5}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Orbit lasting 9 seconds. 7 seconds into the orbit, fade `V` on over 1 second.
```json
{
  "animation": [
    ["orbitCamera", {"duration": 9}],
    ["advanceTime", {"by": 7}],
    ["fade", {"meshes": "synapses.V", "startingAlpha": 0, "endingAlpha": 1, "duration": 1}],
    ["advanceTime", {"by": 1}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Frame `E` for 3 seconds. 1 second from the frame starting, fade `R` off for 4 seconds.
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.E", "duration": 3}],
    ["advanceTime", {"by": 1}],
    ["fade", {"meshes": "rois.R", "startingAlpha": 1, "endingAlpha": 0, "duration": 4}],
    ["advanceTime", {"by": 4}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Frame on `L` over 7 seconds. 4 seconds in, fade `A` off for 1 second. Then fade `Z` off taking 3 seconds.
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.L", "duration": 7}],
    ["advanceTime", {"by": 4}],
    ["fade", {"meshes": "rois.A", "startingAlpha": 1, "endingAlpha": 0, "duration": 1}],
    ["advanceTime", {"by": 1}],
    ["fade", {"meshes": "synapses.Z", "startingAlpha": 1, "endingAlpha": 0, "duration": 3}],
    ["advanceTime", {"by": 3}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example: Orbit 75 degrees for 8 seconds. 2 seconds in, fade on `X` over 3 seconds. Then 1 second later, fade on `Y` and `C` for 2 seconds.
```json
{
  "animation": [
    ["orbitCamera", {"endingRelativeAngle": 75, "duration": 8}],
    ["advanceTime", {"by": 2}],
    ["fade", {"meshes": "neurons.X", "startingAlpha": 0, "endingAlpha": 1, "duration": 3}],
    ["advanceTime", {"by": 3}],
    ["advanceTime", {"by": 1}],
    ["fade", {"meshes": "neurons.Y + neurons.C", "startingAlpha": 0, "endingAlpha": 1, "duration": 2}],
    ["advanceTime", {"by": 2}]
  ]
}
```
<!-- CHUNK END -->

### Extending an Animation

<!-- CHUNK START -->
<!-- STEP: 2 -->
New commands appear at the end of the old JSON, not in the middle unless explicitly specified.
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
When adding new commands at the end of an old animation, first add an `"advanceTime"` with `"by"` matching the `"duration"` of the last command in the old animation. 

Example old request: Frame on `"D"` for 1.5 seconds.  Wait 5 seconds. Orbit 60 degrees for 4 seconds>
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.D", "duration": 1.5}],
    ["advanceTime", {"by": 1.5}],
    ["advanceTime", {"by": 5}],
    ["orbitCamera", {"endingRelativeAngle": 60, "duration": 4}]
  ]
}
```
Example new request: Fade on `"T"` in 1 second.
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.D", "duration": 1.5}],
    ["advanceTime", {"by": 1.5}],
    ["advanceTime", {"by": 5}],
    ["orbitCamera", {"endingRelativeAngle": 60, "duration": 4}],
    ["advanceTime", {"by": 4}],
    ["fade", {"meshes": "neurons.T", "startingAlpha": 0, "endingAlpha": 1, "duration": 1}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Example old request: Orbit for 11 seconds with scale 0.6.
```json
{
  "animation": [
    ["orbitCamera", {"scale": 0.6, "duration": 11}]
  ]
}
```
Example new request: Make `"K"` disappear in 1 second.
```json
{
  "animation": [
    ["orbitCamera", {"scale": 0.6, "duration": 11}],
    ["advanceTime", {"by": 11}],
    ["fade", {"meshes": "neurons.K", "startingAlpha": 1, "endingAlpha": 0, "duration": 1}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
A command inserted into old JSON should be followed by an `"advanceTime"` matching the command's `"duration"`.

Example old request: Fade on `"N"` in 2 seconds.  Orbit for 9 seconds.
```json
{
  "animation": [
    ["fade", {"meshes": "neurons.N", "startingAlpha": 0, "endingAlpha": 1, "duration": 2}],
    ["orbitCamera", {"duration": 9}],
    ["advanceTime", {"by": 9}]
  ]
}
```
Example new request: Insert framing on `"N"` for 3 seconds after the fade:
```json
{
  "animation": [
    ["fade", {"meshes": "neurons.N", "startingAlpha": 0, "endingAlpha": 1, "duration": 2}],
    ["frameCamera", {"bound": "neurons.N", "duration": 3}],
    ["advanceTime", {"by": 3}],
    ["orbitCamera", {"duration": 9}],
    ["advanceTime", {"by": 9}]
  ]
}
```
<!-- CHUNK END -->

### Preventing Problems

<!-- CHUNK START -->
<!-- STEP: 2 -->
Do not allow `"orbitCamera"` and `"frameCamera"` to overlap in time, or the camera will move strangely. The following is bad, because `"frameCamera"` and `"orbitCamera"` both start at the same time and have `"duration"`.
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.B", "duration": 2}],
    ["orbitCamera", {"endingRelativeAngle": 30, "duration": 2}],
    ["advanceTime", {"by": 2}]
  ]
}
```
A fix is to make the second command, `"orbitCamera"`, start after the first, `"frameCamera"`.
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.B", "duration": 2}],
    ["advanceTime", {"by": 2}],
    ["orbitCamera", {"endingRelativeAngle": 30, "duration": 2}],
    ["advanceTime", {"by": 2}]
  ]
}
```
<!-- CHUNK END -->
