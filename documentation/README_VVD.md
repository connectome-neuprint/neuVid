# neuVid and VVDViewer Documentation

*Incomplete*

## Introduction

For volumetric data sets lacking an explicit segmentation.
Examples: 
* [Janelia FlyLight Split-GAL4 driver collection](https://splitgal4.janelia.org/cgi-bin/splitgal4.cgi)
* [Janelia FlyLight Generation 1 MCFO collection](https://gen1mcfo.janelia.org/cgi-bin/gen1mcfo.cgi)

Rendered with [VVDViewer](https://github.com/JaneliaSciComp/VVDViewer), a high-performance system for [direct volume rendering](https://en.wikipedia.org/wiki/Volume_rendering) of fluorescence microscopy volumes.

## Volumes

The `"volumes"` section of the JSON file associates volume files with names to be used in the `"animation"` section.

The `"source"` indicates where to find the volume files.  It can be an absolute path, or a local path, but note that a local path must start with `./`.  For example, the following specifies a volume file in the `Davis-etal-2020/JRC_SS04438-20151118_31_F1` subdirectory (folder) of the directory containing the generated VVDViewer project (.vrp) file:

```json
  "volumes": {
    "source": "./Davis-etal-2020",
    "JRC_SS04438-20151118_31_F1": "JRC_SS04438-20151118_31_F1/JRC2018_Unisex_20x_HR (CMTK)-REG_UNISEX_20x_HR.h5j"
  }
```

Currently only [H5J format](https://github.com/JaneliaSciComp/workstation/blob/master/docs/H5JFileFormat.md) volume files are supported.

By default, the first channel ("Channel_0") is used for all volumes.  This default channel can be changed with the command-line argument `--channel` (`-ch`).  The channel for an individual volume can be specified with an array, as in the following example, which specifies the fourth channel ("Channel_3"):
```json
  "volumes": {
    "source": "./Davis-etal-2020",
    "JRC_SS04438-20151118_31_F1-ch3": ["JRC_SS04438-20151118_31_F1/JRC2018_Unisex_20x_HR (CMTK)-REG_UNISEX_20x_HR.h5j", 3]
  }
```

Note that channels are "zero-based", so the first channel is 0.

## Fetching Volumes

If local copies of the volume files are not yet available, the companion `fetchVvd` program can fetch them from a cloud data source, like `https://s3.amazonaws.com/janelia-flylight-imagery` where the [Janelia FlyLight Split-GAL4 driver collection](https://splitgal4.janelia.org/cgi-bin/splitgal4.cgi) and [Janelia FlyLight Generation 1 MCFO collection](https://gen1mcfo.janelia.org/cgi-bin/gen1mcfo.cgi) are stored.  The fetched volume files are stored in a directory `neuVidVolumes` located as a sibling of the input JSON file.

To use `fetchVvd`, download it from the [releases page](https://github.com/JaneliaSciComp/VVDViewer/releases).

The input to `fetchVvd` is a JSON file with a `"volumes"` section of a particular format, as in the following example:
```json
  "volumes": {
    "source": "https://s3.amazonaws.com/janelia-flylight-imagery",
    "R10A06": {"line": "R10A06"},
    "R10A12": {"line": "R10A12"},
    "R10A12_ref": [{"line": "R10A12"}, 3]
  }
```

 The `"source"` is the URL of the cloud data source.  The other items specify a pattern to use when searching for the volume in the cloud data source.  The most basic pattern has the line name.  More advanced patterns can include the region or sex:
 ```json
  "volumes": {
    "source": "https://s3.amazonaws.com/janelia-flylight-imagery",
    "R10A06": {"line": "R10A06", "region": "vnc"},
    "R10A12": {"line": "R10A12", "region": "(central|brain)", "sex": "male"}
  }
```
The `"(central|brain)"` pattern element matches either `central` or `brain` in the volume file name on the cloud data source.

By default `fetchVvd` rewrites the input JSON file with a new `"volumes"` section that refers to the local copies of the volume files.  Use the `--output` (`-o`) command-line option to specify a different file for the output (leaving the input file unmodified).

## Commands

To be used in the `"animation"` section of the JSON file.
General command syntax (quotes are necessary):
```
[ "commandName", { "argumentKey1" : argumentValue1, ..., "argumentKeyN" : argumentValueN }]
```

### `advanceTime`

Required arguments:
- `by`: a time, in seconds.

Note that only the `advanceTime` and `flash` commands advance the current time, to make subsequent comamnds start later.

### `centerCamera`

Required arguments:
- `at`: a point, [*x*, *y*, *z*], -1 <= *x*, *y*, *z* <= 1, with -1 being one edge of the volume's bounding box and 1 being the other edge.

Optional arguments:
- `duration` (default: 1)

### `fade`

Required arguments:
- `startingAlpha`
- `endingAlpha`
- `volume`: don't forget the `"volumes."` prefix.

Optional arguments:
- `duration` (default: 1)

### `flash`

Required arguments:
- `volume`: don't forget the `"volumes."` prefix.

Optional arguments:
- `ramp`: The time, in seconds, to go from alpha 0 to 1 at the start, and also the time to go from alpha 1 to 0 at the end.
- `duration`: The overall number of seconds for the ramp up, hold, and ramp down.
- `advanceTime`: Equivalent to an `advanceTime` command added after the start of the `flash` command.

Note that only the `flash` and `advanceTime` commands advance the current time, to make subsequent comamnds start later.

When optional arguments are unspecified, the are given the values of the previous `flash` command, making it simpler to specifiy a series of similarly-timed `flash` operations affecting different volumes.

### `orbitCamera`

Optional arguments:
- `endingRelativeAngle` (default: 360)
- `axis` (default: `"-y"`): Can be `"x"`, `"-x"`, `"y"`, `"-y"`, `"z"`, `"-z"`, or a vector like `[1, 0, 1]`.
- `duration` (default: 1)

Multiple `orbitCamera` commands may overlap in time. The orbit defined earlier in the script will be applied first at each frame. This convention supports definining a long-duration orbit around one axis, which continues smoothly while other shorter-duration orbits modify it, as in this example:
```json
["orbitCamera", {"axis": "z", "duration": 10}],
["orbitCamera", {"axis": "y", "endingRelativeAngle": 90, "duration": 5}],
["advanceTime", {"by": 5}],
["orbitCamera", {"axis": "y", "endingRelativeAngle": -90, "duration": 5}],
["advanceTime", {"by": 5}]
```

### `zoomCamera`

Required arguments:
- `to`: Matches the "Zoom" slider at the right of VVDViewer's "Render View: 1" panel, with 100 being the default and 200 being more zoomed in.

Optional arguments:
- `duration` (default: 1)

A `zoomCamera` command may overlap in time with an `orbitCamera` command, making the camera move in a spiral.

## Examples

The first example references volumes to be downloaded with `fetchVvd`:
```json
{
    "volumes": {
        "source": "https://s3.amazonaws.com/janelia-flylight-imagery",
        "Ref": [{"line": "R10A06", "region": "vnc"}, 3],
        "R10A06": {"line": "R10A06", "region": "vnc"},
        "R10A12": {"line": "R10A12", "region": "vnc"},
        "R10B01": {"line": "R10B01", "region": "vnc"},
        "R10B02": {"line": "R10B02", "region": "vnc"}
    },
    "animation": [
        ["zoomCamera", {"to": 100, "duration": 0}],

        ["fade", {"volume": "volumes.Ref", "startingAlpha": 0, "endingAlpha": 1, "duration": 1}],
        ["advanceTime", {"by": 1}],
        ["advanceTime", {"by": 1}],
        ["fade", {"volume": "volumes.Ref", "startingAlpha": 1, "endingAlpha": 0, "duration": 1}],
        ["fade", {"volume": "volumes.R10A06", "startingAlpha": 0, "endingAlpha": 1, "duration": 1}],
        ["advanceTime", {"by": 1}],
        ["fade", {"volume": "volumes.R10A12", "startingAlpha": 0, "endingAlpha": 1, "duration": 1}],
        ["advanceTime", {"by": 1}],
        ["fade", {"volume": "volumes.R10B01", "startingAlpha": 0, "endingAlpha": 1, "duration": 1}],
        ["advanceTime", {"by": 1}],
        ["fade", {"volume": "volumes.R10B02", "startingAlpha": 0, "endingAlpha": 1, "duration": 1}],
        ["advanceTime", {"by": 1}],

        ["orbitCamera", {"axis": "z", "endingRelativeAngle": -90, "duration": 2}],
        ["advanceTime", {"by": 2}],

        ["zoomCamera", {"to": 200, "duration": 4}],
        ["orbitCamera", {"axis": "y", "duration": 4}],
        ["advanceTime", {"by": 4}],
        ["advanceTime", {"by": 1}]
    ]
}
```

The next two examples use the names of some volumes from the  "Optic lobe TAPIN-Seq 2020" release of the 
[Janelia FlyLight Split-GAL4 driver collection](https://splitgal4.janelia.org/cgi-bin/splitgal4.cgi).  Citation: Fred P. Davis et al., "A genetic, genomic, and computational resource for exploring neural circuit function," _eLife_, 2020; https://doi.org/10.7554/eLife.50901.  These volumes must be downloaded to a directory `Davis-etal-2020` that is a sibling of the JSON file.

When building a basic JSON file from a directory (folder) of volumes, `animateVvd` creates a sequence of `flash` commands that show each volume in turn, with a little overlap.  With the default values of `duration` = 4, `advanceTime` = 1, at most 4 volumes will be visible at once, as illustrated by this timing diagram for volumes `A` through `F`:

```
Time 0: A
     1: A, B
     2: A, B, C
     3: A, B, C, D
     4:    B. C, D. E
     5:       C. D. E. F
     ...
```
The general formula relating the total duration of the video to volume count and the `duration` and `advanceTime` arguments is:
```
totalDuration = volumeCount * duration - (volumeCount - 1) * (duration - advanceTime)
```
For the default values `duration` = 4 and `advanceTime` = 1, the formula reduces to:
```
totalDuration = volumeCount + 3
```

Here is a summary of how the total duration relates to several argument values:

| `duration` | `advanceTime` | totalDuration       |
| ---------- | ------------- | ------------------- |
| 3          | 1             | volumeCount + 2     |
| 4          | 1             | volumeCount + 3     |
| 2.5        | 0.5           | volumeCount / 2 + 2 |   
| 3.5        | 0.5           | volumeCount / 2 + 3 |
| 4          | 2             | 2 * volumeCount + 2 |

These formulas are useful for making camera motion fit into the pattern of appearing volumes.  In the following example, the camera rocks back and forth for one cycle, with three segments of lengths _t_, _2 * t_ and _t_.  This motion fits best if the total duration is divisible by 4, hence the example uses a volume count of 13 (and hence a total duration of 13 + 3 = 16). 

This example starts with a `zoomCamera` of `duration` = 0, which sets the initial zoom to be greater than the default.  It then has a `zoomCamera` whose `duration` covers the total duration of the video, providing a gradual zooming in simultaneous with the other camera motion.

```json
{
  "volumes": {
    "source": "./Davis-etal-2020",
    "JRC_SS04438-20151118_31_F1": "JRC_SS04438-20151118_31_F1/JRC2018_Unisex_20x_HR (CMTK)-REG_UNISEX_20x_HR.h5j",
    "JRC_SS23757-20160621_31_C5": "JRC_SS23757-20160621_31_C5/JRC2018_Unisex_20x_HR (CMTK)-REG_UNISEX_20x_HR.h5j",
    "SS00116-20150123_43_G5": "SS00116-20150123_43_G5/JRC2018_Unisex_20x_HR (CMTK)-REG_UNISEX_20x_HR.h5j",
    "SS00308-20130612_33_A5": "SS00308-20130612_33_A5/JRC2018_Unisex_20x_HR (CMTK)-REG_UNISEX_20x_HR.h5j",
    "SS00355-20130604_33_E1": "SS00355-20130604_33_E1/JRC2018_Unisex_20x_HR (CMTK)-REG_UNISEX_20x_HR.h5j",
    "SS00657-20130618_31_I5": "SS00657-20130618_31_I5/JRC2018_Unisex_20x_HR (CMTK)-REG_UNISEX_20x_HR.h5j",
    "SS00657-20140425_32_A5": "SS00657-20140425_32_A5/JRC2018_Unisex_20x_HR (CMTK)-REG_UNISEX_ColorMIP_HR.h5j",
    "SS02204-IVS-myr-FLAG_Syt-HA_3_0055-A01-20141112_31_C2": "SS02204-IVS-myr-FLAG_Syt-HA_3_0055-A01-20141112_31_C2/JRC2018_Unisex_20x_HR (CMTK)-REG_UNISEX_20x_HR.h5j",
    "SS02268-IVS-myr-FLAG_Syt-HA_3_0055-A01-20141121_31_E2": "SS02268-IVS-myr-FLAG_Syt-HA_3_0055-A01-20141121_31_E2/JRC2018_Unisex_20x_HR (CMTK)-REG_UNISEX_20x_HR.h5j",
    "SS02302-IVS-myr-FLAG_Syt-HA_3_0055-A01-20141104_31_E5": "SS02302-IVS-myr-FLAG_Syt-HA_3_0055-A01-20141104_31_E5/JRC2018_Unisex_20x_HR (CMTK)-REG_UNISEX_20x_HR.h5j",
    "SS02437-20141201_32_F3": "SS02437-20141201_32_F3/JRC2018_Unisex_20x_HR (CMTK)-REG_UNISEX_20x_HR.h5j",
    "SS02575-20150204_31_F1": "SS02575-20150204_31_F1/JRC2018_Unisex_20x_HR (CMTK)-REG_UNISEX_20x_HR.h5j",
    "SS02594-20150211_31_C1": "SS02594-20150211_31_C1/JRC2018_Unisex_20x_HR (CMTK)-REG_UNISEX_20x_HR.h5j"
  },
  "animation": [
    ["zoomCamera", {"to": 150, "duration": 0}],
    ["zoomCamera", {"to": 175, "duration": 16}],

    ["orbitCamera", {"endingRelativeAngle": 25, "duration": 4}],

    ["flash", {"volume": "volumes.JRC_SS04438-20151118_31_F1", "ramp": 0.5, "duration": 4, "advanceTime": 1}],
    ["flash", {"volume": "volumes.JRC_SS23757-20160621_31_C5"}],
    ["flash", {"volume": "volumes.SS00116-20150123_43_G5"}],
    ["flash", {"volume": "volumes.SS00308-20130612_33_A5"}],

    ["orbitCamera", {"endingRelativeAngle": -50, "duration": 8}],

    ["flash", {"volume": "volumes.SS00355-20130604_33_E1"}],
    ["flash", {"volume": "volumes.SS00657-20130618_31_I5"}],
    ["flash", {"volume": "volumes.SS00657-20140425_32_A5"}],
    ["flash", {"volume": "volumes.SS02204-IVS-myr-FLAG_Syt-HA_3_0055-A01-20141112_31_C2"}],
    ["flash", {"volume": "volumes.SS02268-IVS-myr-FLAG_Syt-HA_3_0055-A01-20141121_31_E2"}],
    ["flash", {"volume": "volumes.SS02302-IVS-myr-FLAG_Syt-HA_3_0055-A01-20141104_31_E5"}],
    ["flash", {"volume": "volumes.SS02437-20141201_32_F3"}],
    ["flash", {"volume": "volumes.SS02575-20150204_31_F1"}],

    ["orbitCamera", {"endingRelativeAngle": 25, "duration": 4}],

    ["flash", {"volume": "volumes.SS02594-20150211_31_C1"}]
  ]
}
```

The next example shows fewer volumes but has more camera motion.  After a bit of orbiting around the center of the volumes, the camera pans over to be centered on the middle of the right half of the volumes.  Then it zooms in and orbits back, with the orbit using the new camera center. 

Note the use of the `advanceTime` commands to control when each operation starts. Note also that the visibility of only two volumes is ever explicitly mentioned, in the `fade` command that makes those two become invisible.  All other volumes stay visible for the entire video by default.

```json
{
    "volumes": {
      "source": "./Davis-etal-2020",
      "SS00355-20130604_33_E1": "SS00355-20130604_33_E1/JRC2018_Unisex_20x_HR (CMTK)-REG_UNISEX_20x_HR.h5j",
      "SS00657-20130618_31_I5": "SS00657-20130618_31_I5/JRC2018_Unisex_20x_HR (CMTK)-REG_UNISEX_20x_HR.h5j",
      "SS00657-20140425_32_A5": "SS00657-20140425_32_A5/JRC2018_Unisex_20x_HR (CMTK)-REG_UNISEX_ColorMIP_HR.h5j",
      "SS02204-IVS-myr-FLAG_Syt-HA_3_0055-A01-20141112_31_C2": "SS02204-IVS-myr-FLAG_Syt-HA_3_0055-A01-20141112_31_C2/JRC2018_Unisex_20x_HR (CMTK)-REG_UNISEX_20x_HR.h5j"
    },
    "animation": [
        ["zoomCamera", {"to": 150, "duration": 0}],
        ["orbitCamera", {"endingRelativeAngle": 30, "duration": 2}],
        ["advanceTime", {"by": 2}],

        ["centerCamera", {"at": [0.5, 0.25, 0], "duration": 2}],
        ["advanceTime", {"by": 2}],

        ["zoomCamera", {"to": 300, "duration": 2}],
        ["fade", {"volume": "volumes.SS00355-20130604_33_E1", "duration": 2}],
        ["fade", {"volume": "volumes.SS00657-20130618_31_I5", "duration": 2}],
        ["advanceTime", {"by": 2}],

        ["orbitCamera", {"endingRelativeAngle": -30, "duration": 2}]  
    ]
  }
```

## Tips

After loading the project (.vrp) file, avoid doing anything in the VVDViewer user interface other than switching to the "Record/Export" panel's "Advanced" tab and pressing the "Save..." button.  Other operations might change the project in a way that would affect the video rendering.
