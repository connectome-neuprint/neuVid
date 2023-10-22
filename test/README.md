# neuVid Tests

Run the suite of tests as follows:
```
$ python test.py
```
Each test in the suite runs `importMeshes.py`, `addAnimation.py` and `render.py` on a test JSON file.  Currently, there is no automated evaluation of the results; the user must check the `.blend` files and/or the rendered frames manually.

Arguments:
* `--input` [`-i`][optional, default: `.`]: the path to the input directory containing the test JSON files
* `--output` [`-o`][optional, default `/tmp/neuVid-tests-`_timestamp_]: the path to the directory where the `.blend` files and rendered frames will be created
* `--blender` [`-b`][optional, default: the latest installed version] the path to the Blender executable to use
* `--norender` [`-nr`][optional, default: false]: if true, rendering is skipped
* `--renderall` [`-ra`][optional, default: false]: if true, all frames are rendered (instead of just a few important frames) and a video is assembled, with the paths to the videos displayed at the very end of the test suite