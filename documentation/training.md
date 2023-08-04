# Input for neuVid

## Overall Structure

<!-- CHUNK START -->
The neuVid system generates high-quality videos from biological data.
The videos are rendered by Blender.
The input to neuVid is a JSON file.
<!-- CHUNK END -->

<!-- CHUNK START -->
The JSON file must start with one or more of the following keys:

* The `"neurons"` key has a value that is an object, which specifies the neurons (a.k.a. bodies, segments) that appear in the video, and where to get their segmentation data (polygonal meshes).
* The `"rois"` key has a value that is an object, which specifies the ROIs (a.k.a. regions of interest, neuropils) that appear in the video, and where to get their segmentation data (polygonal meshes).
* `"synapses"`
* `"grayscales"`
<!-- CHUNK END -->

<!-- CHUNK START -->
Then the JSON file must contain the `"animation"` key, whose value is an array of animation commands.
<!-- CHUNK END -->

## The `"neurons"` Key

<!-- CHUNK START -->
Create a group named `"G"` that includes one neuron, with ID (identifier) `6`. The source for this neuron is the Janelia FlyEM hemibrain server v1.2 (a.k.a., the hemibrain, or the FlyEM hemibrain, or the Janelia FlyEM hemibrain), meaning the neuron mesh is loaded from the server, with URL from the `"source"` key:
```json
{
  "neurons": {
    "source": "https://hemibrain-dvid.janelia.org/api/node/31597/segmentation_meshes",
    "G": [6]
  },
  "animation": []
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
Create a group called `"P"` that includes two neurons, with IDs `8` and `4`. The neuron meshes are loaded from the Janelia FlyEM MANC v1.0 server (a.k.a., the MANC), with URL from the `"source"` key:
```json
{
  "neurons": {
    "source": "https://manc-dvid.janelia.org/api/node/v1.0/segmentation_meshes",
    "P": [8, 4]
  },
  "animation": [
    ["orbitCamera", {"axis": "y", "endingRelativeAngle": 180}]
  ]
}
```
<!-- CHUNK END -->
The `"orbitCamera"` is described later.

<!-- CHUNK START -->
Create two groups of neurons, one named `"U"` containing neurons with IDs `3` and `7`, and the other named `"J"` containing neurons with IDs `6`, `4` and `9`. The neuronm meshes are loaded from the FlyWire FAFB server, with URL from the `"source"` key:
```json
{
  "neurons": {
    "source": "precomputed://gs://flywire_v141_m630",
    "U": [3, 7],
    "J": [6, 4, 9]
  },
  "animation": [
    ["orbitCamera", {"axis": "x", "endingRelativeAngle": -90}]
  ]
}
```
<!-- CHUNK END -->
The `"orbitCamera"` is described later.

<!-- CHUNK START -->
Create a group named `"N"` containing three neurons, with IDs `7`, `3`, and `5`. The neuron meshes are loaded from a directory (a.k.a., folder) on the local file system, with the path from the `"source"` key.
```json
{
  "neurons": {
    "source": "t/x",
    "E" : [7, 3, 5]
  },
  "animation": []
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
Use multiple sources for neuron meshes by giving the `"source"` key an array value, with each element being a path to a directory on the local file system (server URLs are also supported). Create a group of neurons named `"K"`, and the value of that key is an object whose `"ids"` key says the group contains the two neurons with IDs  `4` and `2`, and whose `"sourceIndex"` key says the neuron meshes come from the source array at index `0`. Also create a group of neurons named `"S"`, and the value of that key is an object whose `"ids"` key says the group contains the neuron with ID  `6`, and whose `"sourceIndex"` key says the neuron mesh comes from the source array at index `1`:
```json
{
  "neurons": {
    "source": ["g/v", "s/y"],
    "K": {"ids": [4, 2], "sourceIndex": 0},
    "S": {"ids": [6], "sourceIndex": 1},
  },
  "animation": []
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
Create three groups of neurons but the IDs in the groups are not specified as literal arrays in the JSON. Instead, the IDs come from files in a directory on the local file system, with the directory path coming from the `"idsSource"` key. Each such file contains one neuron ID per line. Create a group named `"H"`, and the value for that key is an object, with an `"ids"` key whose value is the name, `"H.txt"`, of the file with the IDs for the neurons in the group. Create a second group named `"A"`, and the value for that key is an object, with an `"ids"` key whose value is the name, `"A.txt"`, of the file with the groups's neuron IDs. The JSON creates a third group, `"P"`, and the value for that key is an object, with an `"ids"` key whose value is the name, `"P.txt"`, of the file with group's neuron IDs:
```json
{
  "neurons": {
    "source": "j/i",
    "idsSource": "o/m",
    "H": {"ids": "H.txt"},
    "A": {"ids": "A.txt"},
    "P": {"ids": "P.txt"}
  },
  "animation": []
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
Use a `"source"` key whose value is an array of directories on the local file system, with each directory containing neuron mesh files. Create two groups of neurons with IDs from files in another directory, with each such file containing one neuron ID per line; the path to this other directory is the value of the `"idsSource"` key. The key for the first group, `"S"`, has a value that is an object specifying the group's details: the `"ids"` key gives the name of the file, `"S.txt"`, with group's neuron IDs, and the `"sourceIndex"` key gives the index in the `"source"` array of the directory for group's neron meshes. The key for the second group, `"C"`, has a value that is another object, with `"ids"` and `"sourceIndex"` keys:
```json
{
  "neurons": {
    "source": ["u/q", "z/p"],
    "idsSource": "y/i",
    "S": {"ids": "S.txt", "sourceIndex": 0},
    "C": {"ids": "C.txt", "sourceIndex": 1}
  },
  "animation": []
}
```
<!-- CHUNK END -->

To reiterate:
<!-- CHUNK START -->
The neuron `"source"` URL for loading neurons from the Janelia FlyEM hemibrain v1.2 (a.k.a., the FlyEM hemibrain, or the hemibrain) is: `"https://hemibrain-dvid.janelia.org/api/node/31597/segmentation_meshes"`.
<!-- CHUNK END -->
<!-- CHUNK START -->
The neuron `"source"` URL for loading neurons from the Janelia FlyEM MANC (a.k.a., the FlyEM MANC, or the MANC, or the FlyEM VNC, or the VNC) is: `"https://manc-dvid.janelia.org/api/node/v1.0/segmentation_meshes"`.
<!-- CHUNK END -->
<!-- CHUNK START -->
The neuron `"source"` URL for loading neurons from the FlyWire FAFB (a.k.a., FlyWire) is: `"precomputed://gs://flywire_v141_m630"`.
<!-- CHUNK END -->

## The `"rois"` Key

The term "ROI" means "region of interest". ROIs are rendered as silhouettes.

<!-- CHUNK START -->
<!-- KEYWORDS: roi, region, neuropil -->
Create a group named `"FB"` that includes one ROI, `"FB"`, the fan-shaped body. The source for this neuron is the Janelia FlyEM hemibrain server v1.2 (a.k.a., the hemibrain, or the FlyEM hemibrain, or the Janelia FlyEM hemibrain):
```json
{
  "rois": {
    "source": "https://hemibrain-dvid.janelia.org/api/node/31597/roisSmoothedDecimated",
    "FB": ["FB"]
  },
  "animation": []
}
```
<!-- CHUNK END -->

## The `"synapses"` Key

## The `"grayscales"` Key

## The `"animation"` Key

<!-- CHUNK START -->
The value of the `"animation"` key is an array of animation commands.
Each animation command is an array.
The first element of a command array is a string, the name of the command.
The second element of a command array is an object, the arguments to the command.
<!-- CHUNK END -->

### `"fade"` command

<!-- CHUNK START -->
Make the neurons in group `"Y"` fade from alpha `0` (fully transparent or invisible) to alpha `1` (fully opaque or fully visible), with the fading taking `2` seconds per the `"duration"`:
```json
{
    "neurons": {
      "source": "https://hemibrain-dvid.janelia.org/api/node/31597/segmentation_meshes",
      "Y": [9, 2]
    },
    "animation": [
      ["fade", {"meshes": "neurons.Y", "startingAlpha": 0, "endingAlpha": 1, "duration": 2}]
    ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
Make the neurons in group `"G"` fade from alpha `1` (fully opaque or fully visible) to alpha `0.5` in staggered form, one neuron after another spread out over the length of the fading, `5` seconds per the `"duration"`:
```json
{
    "neurons": {
      "source": "https://manc-dvid.janelia.org/api/node/v1.0/segmentation_meshes",
      "G": [3, 6]
    },
    "animation": [
      ["orbitCamera", {"axis": "y", "endingRelativeAngle": 180}],
      ["fade", {"meshes": "neurons.G", "startingAlpha": 0, "endingAlpha": 1, "stagger": true, "duration": 5}]
    ]
}
```
<!-- CHUNK END -->
The `"orbitCamera"` is described later.

### `"frameCamera"` command

<!-- CHUNK START -->
Make the camera frame on the neurons in group `"V"`, meaning the camera will point at those neurons from just far enough away that the neurons fill the camera's view. The framing happens instantaneously, at the current time:
```json
{
    "neurons": {
      "source": "precomputed://gs://flywire_v141_m630",
      "V": [7, 9]
    },
    "animation": [
      ["orbitCamera", {"axis": "x", "endingRelativeAngle": -90}],
      ["frameCamera", {"bound": "neurons.V"}]
    ]
}
```
<!-- CHUNK END -->
The `"orbitCamera"` is described later.

<!-- CHUNK START -->
Animate the movement of the camera from its current position to where the neurons in  group `"T"` fill its view, with the movement taking `3` seconds, per the `"duration"` argument:
```json
{
    "neurons": {
      "source": "y/d",
      "T": [5, 2]
    },
    "animation": [
      ["frameCamera", {"bound": "neurons.T", "duration": 3}]
    ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
With the `"scale"` value being `0.5`, the camera is half again as far from the neurons in group `"M"` as it would be for a normal framing (so the neurons appear 2 times bigger).  The framing happens instantaneously, at the current time:
```json
{
    "neurons": {
      "source": ["r/w", "y/l"],
      "M": {"ids": [8, 9], "sourceIndex": 0},
      "D": {"ids": [6, 3], "sourceIndex": 1}
    },
    "animation": [
      ["frameCamera", {"bound": "neurons.M", "scale": 0.5}]
    ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
With the `"scale"` value being `3`, the camera ends up 3 times farther away from the neurons in group `"E"` than it would be for a normal framing (so the neurons appear 1/3 as big), and the movement of the camera takes `5` seconds, per the `"duration"` argument:
```json
{
    "neurons": {
      "source": ["h/e", "q/c"],
      "idsSource": "i/r",
      "E": {"ids": "E.txt", "sourceIndex": 0},
      "W": {"ids": "W.txt", "sourceIndex": 1}
    },
    "animation": [
      ["frameCamera", {"bound": "neurons.E", "scale": 3, "duration": 5}]
    ]
}
```
<!-- CHUNK END -->

### `"orbitCamera"` command

<!-- CHUNK START -->
Orbit the camera (i.e., rotate it while staying the same distance away) all the way around (i.e., 360 degrees around) what the camera is pointed at (centered on) currently.  Here, it is centered on neuron group `"G"` because of the `"frameCamera"` before the `"orbitCamera"`.  The orbit takes `7` seconds, per the `"duration"` argument. The rotation axis is `"z"` by default:
```json
{
    "neurons": {
      "source": "https://hemibrain-dvid.janelia.org/api/node/31597/segmentation_meshes",
      "G": [9, 1]
    },
    "animation": [
      ["frameCamera", {"bound": "neurons.G"}],
      ["orbitCamera", {"duration": 7}]
    ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
Orbit (i.e., rotate) the camera halfway around (i.e., `180` degrees, per the `"endingRelativeAngle"` argument) what the camera is pointed at (centered on) currently.  Here, it is centered on neuron group `"C"` because of the `"frameCamera"` before the `"orbitCamera"`.  The orbit takes `4` seconds, per the `"duration"` argument. The rotation axis is `"z"` by default:
```json
{
    "neurons": {
      "source": "z/p",
      "C": [2, 8]
    },
    "animation": [
      ["frameCamera", {"bound": "neurons.C"}],
      ["orbitCamera", {"endingRelativeAngle": 180, "duration": 4}]
    ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
Orbit the camera by `-90` degrees, per the `"endingRelativeAngle"` argument, about the `"x"` axis (i.e., the axis of rotation is x), per the `"axis"` argument. The orbit takes `3` seconds, per the `"duration"` argument:
```json
{
    "neurons": {
      "source": "https://hemibrain-dvid.janelia.org/api/node/31597/segmentation_meshes",
      "E": [5, 3]
    },
    "animation": [
      ["orbitCamera", {"axis": "x", "endingRelativeAngle": -90, "duration": 3}]
    ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
Orbit the camera `30` degrees, per the `"endingRelativeAngle"` argument, with the center of rotation being the neurons in the group `"H"` (i.e., the center of their bounding box), per the `"around"` argument. The orbit takes `1` second, per the `"duration"` argument:
```json
{
    "neurons": {
      "source": ["q/v", "b/l"],
      "H": {"ids": [6, 5], "sourceIndex": 0}
    },
    "animation": [
      ["orbitCamera", {"around": "neurons.H", "endingRelativeAngle": 30, "duration": 1}]
    ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
Orbit the camera `150` degrees, per the `"endingRelativeAngle"` argument, with the orbit taking `6` seconds, per the `"duration"` argument. Move the camera in (i.e., closer to what it is orbiting around) as the orbiting proceeds, so it ends up half as far away as it started, per the `"scale"` argument's `0.5` value:
```json
{
    "neurons": {
      "source": ["j/o", "e/s"],
      "idsSource": "k/u",
      "Z": {"ids": "Z.txt", "sourceIndex": 0}
    },
    "animation": [
      ["orbitCamera", {"endingRelativeAngle": 150, "duration": 6, "scale": 0.5}]
    ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
Orbit the camera `-80` degrees, per the `"endingRelativeAngle"` argument, and move the camera out (i.e., farther from what it is orbiting around) as the orbiting proceeds, so it ends up twice as far away as it started, per the `"scale"` argument's `2` value:
```json
{
    "neurons": {
      "source": "https://hemibrain-dvid.janelia.org/api/node/31597/segmentation_meshes",
      "K": [6, 9]
    },
    "animation": [
      ["orbitCamera", {"endingRelativeAngle": -80, "duration": 4.5, "scale": 2}]
    ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
When using the neuron `"source"` URL for loading neurons from the Janelia FlyEM MANC (a.k.a., the FlyEM MANC, or the MANC, or the FlyEM VNC, or the VNC), the `"animation"` array *must* start with an `"orbitCamera"` of angle `180` about the `"y"` axis and no `"duration"`. All other commands (`"frameCamera"`, `"fade"`, `"setValue"`, etc.) *must* follow this first command:
```json
{
    "neurons": {
      "source": "https://manc-dvid.janelia.org/api/node/v1.0/segmentation_meshes"
    },
    "animation": [
      ["orbitCamera", {"axis": "y", "endingRelativeAngle": 180}]
    ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
When using the neuron `"source"` URL for loading neurons from the FlyWire FAFB (a.k.a., FlyWire), the `"animation"` array *must* start with an `"orbitCamera"` of `-90` about the `"x"` axis and no `"duration"`. All other commands (`"frameCamera"`, `"fade"`, `"setValue"`, etc.) *must* follow this first command:
```json
{
    "neurons": {
      "source": "precomputed://gs://flywire_v141_m630"
    },
    "animation": [
      ["orbitCamera", {"axis": "x", "endingRelativeAngle": -90}]
    ]
}
```
<!-- CHUNK END -->

### `"setValue"` command

<!-- CHUNK START -->
Set the color of the neurons in group `"M"` to `"green"`, per the `"color"` argument, from the current time forward.  Legal named colors are: `"orange"`, `"brown"`, `"pink"`, `"blue"`, `"lightBlue"`, `"yellow"`, `"green"` and `"darkBlue"`, or hex (i.e., CSS) colors like `"#ffffff"`:
```json
{
    "neurons": {
      "source": "z/h",
      "M": [8, 9]
    },
    "animation": [
      ["setValue", {"meshes": "neurons.M", "color": "green"}]
    ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
Set the alpha (i.e., transparency) of the neurons in group `"G"` to 0.2, per the `"alpha"` argument, from the current time forward:
```json
{
    "neurons": {
      "source": ["f/p", "q/c"],
      "G": {"ids": [9, 1], "sourceIndex": 0},
      "U": {"ids": [3, 5], "sourceIndex": 1}
    },
    "animation": [
      ["setValue", {"meshes": "neurons.G", "alpha": 0.2}]
    ]
}
```
<!-- CHUNK END -->

### `"advanceTime"` command

<!-- CHUNK START -->
Two commands without `"duration"` occuring at the same time (simultaneously), with no `"advanceTime"` between them:
```json
{
    "neurons": {
      "source": "precomputed://gs://flywire_v141_m630",
      "I": [5, 6]
    },
    "animation": [
      ["orbitCamera", {"axis": "x", "endingRelativeAngle": -90}],
      ["frameCamera", {"bound": "neurons.I"}],
      ["orbitCamera", {"axis": "x", "endingRelativeAngle": 180}]
    ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
Two commands with `"duration"` starting at the same time (simultaneously), with no `"advanceTime"` between them:
```json
{
    "neurons": {
      "source": "f/h",
      "Q": [5, 2]
    },
    "animation": [
      ["fade", {"meshes": "neurons.Q", "startingAlpha": 0.5, "endingAlpha": 1, "duration": 3}],
      ["frameCamera", {"bound": "neurons.A", "duration": 3}]
    ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
One command without `"duration"` followed at the same time (simultaneonsly) by another command with `"duration"`, with no `"advanceTime"` between them:
```json
{
    "neurons": {
      "source": ["s/i", "f/b"],
      "K": {"ids": [1, 7], "sourceIndex": 0},
      "V": {"ids": [8, 4], "sourceIndex": 1}
    },
    "animation": [
      ["orbitCamera", {"axis": "z", "endingRelativeAngle": -90}]
      ["fade", {"meshes": "neurons.K", "startingAlpha": 1, "endingAlpha": 0.5, "duration": 4}]
    ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
One command with `"duration"` and another command starting immediately after the first command finishes, achieved by placing between the commands an `"advanceTime"` with `"by"` matching (equaling) the `"duration"` of the first command:
```json
{
    "neurons": {
      "source": ["y/w", "p/f"],
      "idsSource": "u/g",
      "N": {"ids": "N.txt", "sourceIndex": 0},
      "J": {"ids": "J.txt", "sourceIndex": 1}
    },
    "animation": [
      ["orbitCamera", {"duration": 20}]
      ["advanceTime", {"by": 20}],
      ["frameCamera", {"bound": "neurons.N", "duration": 4}]
    ]
}
```
<!-- CHUNK END -->

<!-- CHUNK START -->
A framing command with `"duration"` `2`.  Then an `"advanceTime"` of the same `"duration"`, `2,` so the next fading command starts right after the framing finishes.  Then another `"advanceTime"` of `"duration"` `1`, matching the `"duration"` of the fading, so the last orbiting command happens immediately after the fading finishes: 
```json
{
    "neurons": {
      "source": "https://hemibrain-dvid.janelia.org/api/node/31597/segmentation_meshes",
      "M": [6, 3]
    },
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
To pause by 5 seconds between a fading command and a framing command, add one `"advanceTime"` after the fading with `"duration"` `1`, matching the `"duration"` of the fading, then add a second `"advanceTime"` with `"duration"` `5`, the length of the pause:
```json
{
    "neurons": {
      "source": "j/i",
      "R": [8, 1]
    },
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
Frame on both the neurons from group `"M"` and from group `"X"` by using the argument value `"neurons.M + neurons.X"`.  Make this framing take `2` seconds per the `"duration"` argument.  At the same time, fade group `"X"`, also with `"duration"` `2`.  Wait until the framing and fading are done, with an `"advanceTime"` having `"by"` that matches the framing and fading `"duration"` of `2`.  Then pause `1` second, with another `"advanceTime"`.  When that pause is done, orbit `90` degrees with `"duration"` `5`:
```json
{
    "neurons": {
      "source": "https://manc-dvid.janelia.org/api/node/v1.0/segmentation_meshes",
      "N": [2, 4],
      "X": [5, 6]
    },
    "animation": [
      ["orbitCamera", {"axis": "y", "endingRelativeAngle": 180}]
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
Frame on `"R"`, taking `3` seconds.  When that framing is over, pause for `4` seconds, then orbit for `5` seconds.  At the end of that orbit, pause for `6` seconds.  Then frame on `"U"` for 7 seconds.  When that framing is over, wait for `8` seconds.  Then orbit for `9` seconds:
```json
{
    "neurons": {
      "source": "e/x",
      "R": [7, 1],
      "U": [3, 5]
    },
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

<!-- CHUNK START -->
When adding new commands at the end of an old animation, first add an `"advanceTime"`" with `"by"` matching the `"duration"` of the last command in the old animation.  Here, the old commands are `"frameCamera"` and `"orbitCamera"`, with `5` seconds between them, and the new comand is `"fade"`:
```json
{
    "neurons": {
      "source": ["s/f", "g/k"],
      "D": {"ids": [9, 8], "sourceIndex": 0},
      "T": {"ids": [3, 1], "sourceIndex": 1}
    },
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

<!-- HEY!! Does not handle extending an earlier JSON with: "Now add an orbit ..." -->

### Preventing Problems

<!-- CHUNK START -->
Do not allow an `"orbitCamera"` and a `"frameCamera"` to overlap in time, or the camera will move strangely.  The following is bad, because the `"frameCamera"` and `"orbitCamera"` both start at the same time and have a `"duration"`:
```json
{
    "neurons": {
      "source": "https://hemibrain-dvid.janelia.org/api/node/31597/segmentation_meshes",
      "B": [9, 3]
    },
    "animation": [
      ["frameCamera", {"bound": "neurons.B", "duration": 2}],
      ["orbitCamera", {"endingRelativeAngle": 30, "duration": 2}]
    ]
}
```
A fix is to make the second command, `"orbitCamera"`, start after the first command, `"frameCamera"`:
```json
{
    "neurons": {
      "source": "https://hemibrain-dvid.janelia.org/api/node/31597/segmentation_meshes",
      "B": [9, 3]
    },
    "animation": [
      ["frameCamera", {"bound": "neurons.B", "duration": 2}],
      ["advanceTime", {"by": 2}],
      ["orbitCamera", {"endingRelativeAngle": 30, "duration": 2}]
    ]
}

```
<!-- CHUNK END -->

<!-- CHUNK START -->
Do not allow an `"orbitCamera"` and a `"frameCamera"` to overlap in time, even partially, or the camera will move in odd ways.  The following is bad, because the `"frameCamera"` starts during the duration of the `"orbitCamera"`:
```json
{
    "neurons": {
      "source": "w/d",
      "V": [4, 8]
    },
    "animation": [
      ["orbitCamera", {"endingRelativeAngle": -50, "duration": 4, "scale": 3}]
      ["advanceTime", {"by": 2}],
      ["frameCamera", {"bound": "neurons.V", "duration": 3}],
    ]
}
```
A solution is to increase the `"by"` of the `"advanceTime"` between the `"orbitCamera"` and `"frameCamera"` so that the first finishes before the second starts:
```json
{
    "neurons": {
      "source": "w/d",
      "V": [4, 8]
    },
    "animation": [
      ["orbitCamera", {"endingRelativeAngle": -50, "duration": 4, "scale": 3}]
      ["advanceTime", {"by": 4}],
      ["frameCamera", {"bound": "neurons.V", "duration": 3}],
    ]
}
```
<!-- CHUNK END -->

TO ADD:
- `"frameCamera"` `"scale"`