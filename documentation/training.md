<!-- First attempt at two steps: step 1 for declarations of "neurons", etc., step 2 for animation. -->

# Input for neuVid

## Overall Structure

<!-- CHUNK START -->
The neuVid system generates high-quality videos from biological data.
Videos are rendered by Blender.
Input is a JSON file.
<!-- CHUNK END -->

<!-- CHUNK START -->
The JSON file starts with one or more of the following:

* The `"neurons"` key has a value object specifying the neurons (or bodies, segments) in the video, and their data sources.
* The `"rois"` key's object specifies the ROIs (or regions of interest, neuropils) and their sources.
* The `"synapses"` key specifies which neurons have synapses.
* The `"grayscales"` key specifies image slices from the original microscopy data.
<!-- CHUNK END -->

<!-- CHUNK START -->
Then the JSON has the `"animation"` key, whose value is an array of animation commands.
<!-- CHUNK END -->

## The `"neurons"` Key

<!-- CHUNK START -->
<!-- STEP: 1 -->
Create a group named `"G"` that includes one neuron, with ID (identifier) `6`. The source for this neuron is the Janelia FlyEM hemibrain server v1.2 (or the hemibrain, or FlyEM hemibrain, or Janelia FlyEM hemibrain), meaning the neuron mesh is loaded from the server, with URL from the `"source"` key:
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
Create a group `"P"` including neurons `8` and `4`. The neuron meshes are loaded from the Janelia FlyEM MANC v1.0 server (or the MANC), per the `"source"`:
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
The `"lighRotationY"` and `"orbitCamera"` are described later.

<!-- CHUNK START -->
<!-- STEP: 1 -->
Create two groups, `"U"` containing neurons `3` and `7`, and `"J"` containing  `6`, `4` and `9`. The neuron meshes are loaded from the FlyWire FAFB server per the `"source"`:
```json
{
  "neurons": {
    "source": "precomputed://gs://flywire_v141_m630",
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
The `"lightRotationX"` and `"orbitCamera"` are described later. 
A JSON file with the FlyWire source requires an extra step during the conversion into a Blender file for rendering; see the discussion of `fetchMeshes.py` in 
[the documentation](https://github.com/connectome-neuprint/neuVid#usage-with-neuroglancer).

<!-- CHUNK START -->
<!-- STEP: 1 -->
Create a group `"N"` containing three neurons, `7`, `3`, and `5`. The meshes are loaded from a directory (or folder) on the local file system, with the path from the `"source"` key.
```json
{
  "neurons": {
    "source": "t/x",
    "E" : [7, 3, 5]
  },
  "rois": {},
  "animation": []
}
```
<!-- CHUNK END -->
The neuron mesh files should be in OBJ format with the `.obj` extension: `t/x/7.obj`, `t/x/3.obj`, `t/x/5.obj`.

<!-- CHUNK START -->
<!-- STEP: 1 -->
Use two neuron mesh sources: local directory `"g/v"` and the hemibrain server. Group `"K"` is the neurons `4` and `2` with meshes from the local source. Group `"S"` is the neuron `6` using the hemibrain meshes:
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
The `"lighRotationY"` and `"orbitCamera"` are described later.

<!-- CHUNK START -->
<!-- STEP: 1 -->
Create three groups of neurons, with the IDs for each group coming from a file in local directory `"j/i"`. Group `"H"` has ID file `"H.txt"`. Group `"A"` has ID file `"A.txt"` and group `"P"` has ID file `"P.txt"`. The neuron meshes all come from local directory `"j/i"`:
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
Use two local directories for meshes, `"u/q"` and `"z/p"`. Neuron group `"S"` has IDs from file `"S.txt"` and meshes from the first source. Group `"C"` uses IDs from `"C.txt"` and the second mesh source. All neuron ID files are in the local directory `"y/i"`:
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
The neuron `"source"` URL for the Janelia FlyEM hemibrain v1.2 (or the FlyEM hemibrain, or the hemibrain) is: `"https://hemibrain-dvid.janelia.org/api/node/31597/segmentation_meshes"`. Also use this source for neurons if the ROI source it the hemibrain.
<!-- CHUNK END -->
<!-- CHUNK START -->
<!-- STEP: 1 -->
The neuron `"source"` URL for the Janelia FlyEM MANC (or the FlyEM MANC, or the MANC, or the FlyEM VNC, or the VNC) is: `"https://manc-dvid.janelia.org/api/node/v1.0/segmentation_meshes"`. Also use this source for neurons if the ROI source is the MANC.
<!-- CHUNK END -->
<!-- CHUNK START -->
<!-- STEP: 1 -->
The neuron `"source"` URL for the FlyWire FAFB (or FlyWire) is: `"precomputed://gs://flywire_v141_m630"`.
<!-- CHUNK END -->

## The `"rois"` Key

The term "ROI" means "region of interest". ROIs are rendered with silhouette edges.

<!-- CHUNK START -->
<!-- STEP: 1 -->
Create a group `"F"` with one ROI, `"FB"`. The source is the Janelia FlyEM hemibrain server v1.2 (or the hemibrain, or the FlyEM hemibrain, or the Janelia FlyEM hemibrain). Also make `"K"`, with the ROI `"all_neuropils"`, the hemibrain's outer shell or boundary:
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
`"G"` includes two ROIs, `"IntNp(T1)(L)"` and `"IntNp(T1)(R)"`, from the Janelia FlyEM MANC (or the FlyEM MANC, or the MANC, or the FlyEM VNC, or the VNC). `"A"` is the ROI `"all_VNC"`, the MANC's boundary:
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
The `"lightRotationY"` and `"orbitCamera"` are described later.

<!-- CHUNK START -->
<!-- STEP: 1 -->
`"R"` includes two ROIs, `"IB"` and `"PB"`, from local directory (folder) `"w/y"`. `"Q"` has the ROI `"SMP"` from the local path `"h/j"`:
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

## The `"synapses"` Key

The simplest way to include synapses is to import them from Neuroglancer with the `importNg.py` script; see 
[the documentation](https://github.com/connectome-neuprint/neuVid#usage-with-neuroglancer).
This approach does not support the `"partner"` key described below, and the `"source"` URL is a bit different.

An alternative is to use the specifications described here. These specifications must be processed by the `buildSynapses.py` script; see [the documentation](https://github.com/connectome-neuprint/neuVid#advanced-usage-with-synapses).

<!-- CHUNK START -->
<!-- STEP: 1 -->
`"9from"` are neuron `9`'s postsynaptic sites (or the postsynaptic sites on `9`, or `9`'s input synapses, or the input synapses on `9`, or `9`'s T-bars), coming from any other neuron. Infer the `"synapses"` `"source"` from the `"neurons"` `"source"` (i.e., the hemibrain). `"9to"` are`9`'s presynaptic sites (or the presynaptic sites on `9`, or `9`'s output synapses, or the output synapses on '`9`, `9`'s PSDs), going to any other neuron. Each synapse is rendered as a ball of radius `80` (use `"radius": 80` if none is mentioned):
```json
{
  "neurons": {
    "source": "https://hemibrain-dvid.janelia.org/api/node/31597/segmentation_meshes",
    "N": [9, 4]
  },
  "synapses": {
    "source": "https://neuprint.janelia.org/?dataset=hemibrain%3Av1.2.1",
    "9from": {
      "type": "post", "neuron": 9,
      "radius": 80
    },
    "9to" : {
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
`"2from1"` are neuron `2`'s postsynaptic sites (or the postsynaptic sites on `2`, or `2`'s input synapses, or the input synapses on `2`, or `2`'s T-bars) coming from neuron `1`.  `"2to3"` are `2`'s presynaptic sites (or the presynaptic sites on `9`, or `9`'s output synapses, or the output synapses on '`9`, `9`'s PSDs) going to neuron `3`. Infer the `"synapses"` `"source"` from the `"neurons"` `"source"` (i.e., the MANC). The radius of each synapse ball is `60` (use `"radius": 80` if none is mentioned):
```json
{
  "neurons": {
    "source": "https://manc-dvid.janelia.org/api/node/v1.0/segmentation_meshes",
    "M": [1, 2, 3]
  },
  "synapses": {
    "source": "https://neuprint.janelia.org/?dataset=manc",
    "2from1": {
      "type": "post", "neuron": 2, "partner": 1,
      "radius": 60
    },
    "2to3" : {
      "type": "pre", "neuron": 2, "partner": 3,
      "radius": 60
    }
  },
  "animation": []
}
```
<!-- CHUNK END -->

## The `"grayscales"` Key

Not included.

## Light Rotation

<!-- CHUNK START -->
<!-- STEP: 2 -->
When the MANC is the neuron mesh source,
or there is more than one mesh source including the MANC,
then before the `"animation"` array there should be a `"lightRotationY"` key to give the three area lights an orientation that matches this data set:
```json
{
  "lightRotationY": 180,
  "animation": [
    ["orbitCamera", {"axis": "y", "endingRelativeAngle": 180}]
  ]
}
```
<!-- CHUNK END -->
The `"orbitCamera"` is described later.

<!-- CHUNK START -->
<!-- STEP: 2 -->
When the any of the neurons (even only one element of a  `"neruons"` `"source"` array) come from the FlyWire FAFB (or FlyWire), `"precomputed://gs://flywire_v141_m630"`, then before the `"animation"` array there should be a `"lightRotationX"` key to give the three area lights an orientation that matches this data set: 
```json
{
  "lightRotationX": -90,
  "animation": [
    ["orbitCamera", {"axis": "x", "endingRelativeAngle": -90}]
  ]
}
```
<!-- CHUNK END -->
The `"orbitCamera"` is described later.

## The `"animation"` Key

<!-- CHUNK START -->
<!-- STEP: 2 -->
The `"animation"` key's value is an array of animation commands.
Each animation command is an array: command name, then command arguments object.
<!-- CHUNK END -->

### The `"fade"` Command

<!-- CHUNK START -->
<!-- STEP: 2 -->
Show `"Y"` by making it fade from alpha `0` (fully transparent or invisible) to alpha `1` (fully opaque or fully visible), taking `2` seconds per the `"duration"`:
```json
{
  "animation": [
    ["fade", {"meshes": "neurons.Y", "startingAlpha": 0, "endingAlpha": 1, "duration": 2}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Make `"G"` fade from alpha `1` to alpha `0.5` in staggered form, one neuron after another spread out over the length of the fading, `5` seconds per the `"duration"`:
```json
{
  "animation": [
    ["fade", {"meshes": "neurons.G", "startingAlpha": 0, "endingAlpha": 1, "stagger": true, "duration": 5}]
  ]
}
```
<!-- CHUNK END -->

### The `"frameCamera"` Command

<!-- CHUNK START -->
<!-- STEP: 2 -->
Make the camera frame on the neurons in group `"V"`: the camera points at those neurons from far enough that they fill its view. The framing happens at the current time:
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
Move the camera from its current position to where the neurons in `"T"` fill its view, taking `3` seconds, per the `"duration"` argument:
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.T", "duration": 3}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
With `"scale"` of `0.5`, the camera is half again as far from `"M"` as for a normal framing (so the neurons appear 2 times bigger). The framing happens at the current time:
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
With `"scale"` of `3`, the camera ends up 3 times farther away from the neurons in group `"E"` than for a normal framing (so the neurons appear 1/3 as big), and the movement of the camera takes `5` seconds, per the `"duration"` argument:
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.E", "scale": 3, "duration": 5}]
  ]
}
```
<!-- CHUNK END -->

### The `"orbitCamera"` Command

<!-- CHUNK START -->
<!-- STEP: 2 -->
Orbit the camera (rotate it while staying the same distance away) all the way around (360 degrees around) what the camera is pointed at (centered on) now. Here, it is centered on `"G"` because of the `"frameCamera"` before the `"orbitCamera"`. The orbit takes `7` seconds, per the `"duration"`. The rotation axis is `"z"` by default:
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.G"}],
    ["orbitCamera", {"duration": 7}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Orbit halfway around (`180` degrees, per `"endingRelativeAngle"`) what the camera is pointed at (centered on) now. Here, it is centered on `"C"` because of the `"frameCamera"` before the `"orbitCamera"`. The orbit takes `4` seconds, per the `"duration"`. The rotation axis is `"z"` by default:
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.C"}],
    ["orbitCamera", {"endingRelativeAngle": 180, "duration": 4}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Orbit by `-90` degrees, per `"endingRelativeAngle"`, about the `"x"` axis (the axis of rotation is x), per the `"axis"`. The orbit takes `3` seconds, per the `"duration"`:
```json
{
  "animation": [
    ["orbitCamera", {"axis": "x", "endingRelativeAngle": -90, "duration": 3}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Orbit `30` degrees, per `"endingRelativeAngle"`, with the center of rotation being `"H"` (the center of their bounding box), per the `"around"`. The orbit takes `1` second, per the `"duration"`:
```json
{
  "animation": [
    ["orbitCamera", {"around": "neurons.H", "endingRelativeAngle": 30, "duration": 1}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Orbit `150` degrees, per `"endingRelativeAngle"`, taking `6` seconds, per the `"duration"`. Move the camera in (closer to what it is orbiting around) as the orbiting proceeds, so it ends up half as far away as it started, per the `"scale"` of `0.5`:
```json
{
  "animation": [
    ["orbitCamera", {"endingRelativeAngle": 150, "duration": 6, "scale": 0.5}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Orbit `-80` degrees, per the `"endingRelativeAngle"`, and move the camera out (farther from what it is orbiting around) as the orbiting proceeds, so it ends up twice as far away as it started, per the `"scale"` of `2`:
```json
{
  "animation": [
    ["orbitCamera", {"endingRelativeAngle": -80, "duration": 4.5, "scale": 2}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
When the MANC is the neuron mesh source,
or there is more than one mesh source including the MANC,
then the `"animation"` array starts with an `"orbitCamera"` of angle `180` about the `"y"` axis and no `"duration"`. All other commands (`"frameCamera"`, `"fade"`, `"setValue"`, etc.) follow this first command:
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
<!-- STEP: 2 -->
When any neurons come from the FlyWire FAFB server (or FlyWire), URL `"precomputed://gs://flywire_v141_m630"` (even as an item in a `"neurons"` `"source"` array), the `"animation"` array *must* start with an `"orbitCamera"` of `-90` about the `"x"` axis and no `"duration"`. All other commands *must* follow this first command:
```json
{
  "animation": [
    ["orbitCamera", {"axis": "x", "endingRelativeAngle": -90}]
  ]
}
```
<!-- CHUNK END -->

### The `"setValue"` Command

<!-- CHUNK START -->
<!-- STEP: 2 -->
Set the color of the neurons in group `"M"` to `"green"`, per the `"color"`, from the current time forward. Legal named colors: `"orange"`, `"brown"`, `"pink"`, `"blue"`, `"lightBlue"`, `"yellow"`, `"green"` and `"darkBlue"`, or hex (i.e., CSS) colors like `"#ffffff"`:
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
Set the alpha (transparency) of `"G"` to 0.2, per the `"alpha"`, from the current time forward:
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
For an ROI, the exponent controls the silhoutte line rendering: a lower exponent (e.g., `2`, `3`) makes the ROI appear heavier and more prominent, while a higher exponent (e.g., `5`, `6`) makes the ROI appear lighter and less conspicuous. Set the exponents of `"R"` to `6`, per the `"exponent"`, from the current time forward:
```json
{
  "animation": [
    ["setValue", {"meshes": "rois.R", "exponent": 6}]
  ]
}
```
<!-- CHUNK END -->

### The `"showPictureInPicture"` Command

Not included.

<!-- TODO: ["showSlice", {"image" : "grayscales.1", "euler": [-38.199, 0.701, -129.445], "scale": 300, "distance" : 600, "duration" : 6, "fade" : 0.5}] -->

### The `"advanceTime"` Command

<!-- CHUNK START -->
<!-- STEP: 2 -->
Two commands without `"duration"` occuring at the same time (simultaneously), with no `"advanceTime"` between them:
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.I"}],
    ["orbitCamera", {"axis": "x", "endingRelativeAngle": 180}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Two commands with `"duration"` starting at the same time (simultaneously), with no `"advanceTime"` between them:
```json
{
  "animation": [
    ["fade", {"meshes": "neurons.Q", "startingAlpha": 0.5, "endingAlpha": 1, "duration": 3}],
    ["frameCamera", {"bound": "neurons.A", "duration": 3}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
One command with `"duration"` and another command starting immediately after the first finishes, achieved by placing between the commands an `"advanceTime"` with `"by"` matching (equaling) the `"duration"` of the first command:
```json
{
  "animation": [
    ["orbitCamera", {"duration": 20}]
    ["advanceTime", {"by": 20}],
    ["frameCamera", {"bound": "neurons.N", "duration": 4}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
A framing command with `"duration"` `2`. Then an `"advanceTime"` of the same `"duration"`, `2,` so the next fading command starts right after the framing finishes. Then another `"advanceTime"` of `"duration"` `1`, matching the `"duration"` of the fading, so the last orbiting happens immediately after the fading finishes: 
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.M", "duration": 2}],
    ["advanceTime", {"by": 2}],
    ["fade", {"meshes": "neurons.M", "startingAlpha": 1, "endingAlpha": 0.6, "duration": 1}]
    ["advanceTime", {"by": 1}],
    ["orbitCamera", {"duration": 10}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Fade for `1` second. Wait (pause) for `5` seconds, then frame for `2` seconds. Note there must be one `"advanceTime"` matching the fading `"duration"` then another `"advanceTime"` for the `5` seconds of the waiting (pausing):
```json
{
  "animation": [
    ["fade", {"meshes": "neurons.R", "startingAlpha": 1, "endingAlpha": 0.6, "duration": 1}]
    ["advanceTime", {"by": 1}],
    ["advanceTime", {"by": 5}],
    ["frameCamera", {"bound": "neurons.M", "duration": 2}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Frame on both the neurons from group `"M"` and from group `"X"` by using the argument value `"neurons.M + neurons.X"`. Make this framing take `2` seconds per the `"duration"`. At the same time, fade `"X"`, also with `"duration"` `2`. Wait until the framing and fading are done, with an `"advanceTime"` having `"by"` that matches the framing and fading `"duration"` of `2`. Then pause `1` second, with another `"advanceTime"`. When that pause is done, orbit `90` degrees with `"duration"` `5`:
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.M + neurons.X", "duration": 2}],
    ["fade", {"meshes": "neurons.X", "startingAlpha": 1, "endingAlpha": 0, "duration": 2}]
    ["advanceTime", {"by": 2}],
    ["advanceTime", {"by": 1}],
    ["orbitCamera", {"endingRelativeAngle": 90, "duration": 5}]
  ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
<!-- STEP: 2 -->
Frame on `"R"`, taking `3` seconds. Then (when that framing is over) pause for `4` seconds, then orbit for `5` seconds. Then (at the end of that orbit) pause for `6` seconds. Next, frame on `"U"` for 7 seconds. And (when that framing is over,) wait for `8` seconds. Then orbit for `9` seconds:
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.R", "duration": 3}],
    ["advanceTime", {"by": 3}],
    ["advanceTime", {"by": 4}],
    ["orbitCamera", {"endingRelativeAngle": -90, "duration": 5}]
    ["advanceTime", {"by": 5}],
    ["advanceTime", {"by": 6}],
    ["frameCamera", {"bound": "neurons.U", "duration": 7}],
    ["advanceTime", {"by": 7}],
    ["advanceTime", {"by": 8}],
    ["orbitCamera", {"endingRelativeAngle": 90, "duration": 9}]
  ]
}
```
<!-- CHUNK END -->

### Extending an Animation

<!-- CHUNK START -->
<!-- STEP: 2 -->
When adding new commands at the end of an old animation, first add an `"advanceTime"` with `"by"` matching the `"duration"` of the last command in the old animation. Here, the old commands are `"frameCamera"` and `"orbitCamera"`, with `5` seconds between them, and the new comand is `"fade"`:
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
Start with this JSON, orbiting for `11` seconds while scaling by `0.6`:
```json
{
  "animation": [
    ["orbitCamera", {"scale": 0.6, "duration": 11}]
  ]
}
```
Then fade `"K"` for `1` second. Don't forget to first `"advanceTime"` with `"by"` matching the `"duration"` of `11` from the end of the old JSON:
```json
{
  "animation": [
    ["orbitCamera", {"scale": 0.6, "duration": 11}],
    ["advanceTime", {"by": 11}],
    ["fade", {"meshes": "neurons.K", "startingAlpha": 1, "endingAlpha": 0.5, "duration": 1}]
  ]
}
```
<!-- CHUNK END -->

### Preventing Problems

<!-- CHUNK START -->
<!-- STEP: 2 -->
Do not allow an `"orbitCamera"` and a `"frameCamera"` to overlap in time, or the camera will move strangely. The following is bad, because the `"frameCamera"` and `"orbitCamera"` both start at the same time and have a `"duration"`:
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.B", "duration": 2}],
    ["orbitCamera", {"endingRelativeAngle": 30, "duration": 2}]
  ]
}
```
A fix is to make the second command, `"orbitCamera"`, start after the first command, `"frameCamera"`:
```json
{
  "animation": [
    ["frameCamera", {"bound": "neurons.B", "duration": 2}],
    ["advanceTime", {"by": 2}],
    ["orbitCamera", {"endingRelativeAngle": 30, "duration": 2}]
  ]
}
```
<!-- CHUNK END -->
