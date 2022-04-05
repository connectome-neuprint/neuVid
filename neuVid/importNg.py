# Creates neuVid input JSON files from Neuroglancer, specifically from the text files of URL
# used as the input for the Neuroglancer video tool:
# https://github.com/google/neuroglancer/blob/master/python/neuroglancer/tool/video_tool.py

# Runs with standard Python (not through Blender), as in:
# $ python importNg.py -i video.txt -o video.json

import argparse
import functools
import json
import math
import numbers
import os
from re import A
import requests
import sys
import urllib
import urllib.parse

# Only a few vector and quaternion functions are needed.  Get them from a custom implementation
# instead of the standard Blender `mathutils` so this script can be run outside of Blender.
# Running it this way will allow for future extensions, like support for decompression of
# Draco encoded meshes, using extra Python packages that are easy to add with Conda but
# difficult to add to Blender's internal verison of Python.
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsMath import Vector, Quaternion

rois = {}
roi_sources = []
neurons = {}
neuron_sources = []
animation = []
contains_groups = {}
layer_alphas = {}
initial_layer_alphas = {}
orbit_look_at_last = None
orbit_look_from_last = None
orbit_axis_last = None
orbit_angle_start = 0
orbit_angle = 0
orbit_cmd_index = None
orbit_cmd_start_time = 0
result_json = {}

def sign(x):
    return 1 if x >= 0 else -1
    
def vector_snapped(v):
    # 0 everywhere except 1 at the component where `v` had the maximum magnitude
    m = max(abs(v.x), abs(v.y), abs(v.z))
    return Vector((v.x, 0, 0)) if abs(v.x) == m else Vector((0, v.y, 0)) if abs(v.y) == m else Vector((0, 0, v.z))

def vector_abs(v):
    return Vector((abs(v.x), abs(v.y), abs(v.z)))

def vector_snapped_name(snapped):
    return "x" if snapped.x != 0 else "y" if snapped.y != 0 else "z"

def vectors_equal(v1, v2, percent=0.005):
    if not v1 or not v2:
        return False
    m = ((v1 + v2)/2).length
    d = v2 - v1
    dm = d.length
    return dm / m < percent

# Swizzles a tuple representing a Neuroglancer quaternion (x, y, z, w) into a
# tuple suitable as the argument for constructing a Blender quaternion (w, x, y, w).
def qswzl(t):
    return (t[3], t[0], t[1], t[2])

def argmin(l):
    m = min(l)
    for i in range(len(l)):
        if l[i] == m:
            return i

# Transforms input like this:
#  URL of NG state A
#  1
#  URL of NG state B
#  URL of NG state C
#  2
#  3
#  URL of NG state D
# Into input like this:
#  URL of NG state A
#  1
#  URL of NG state C
#  5
#  URL of NG state D
def normalize_input(input):
    lines = []
    with open(input, "r") as f:
        for line in f:
            if not line.endswith("\n"):
                line += "\n"
            if line.startswith("http"):
                # If there are two Neuroglancer state URLs in a row, keep just the second one.
                if len(lines) > 0 and isinstance(lines[-1], str):
                    lines[-1] = line
                else:
                    lines.append(line)
            elif line[:-1].isnumeric():
                n = float(line[:-1])
                # Numbers indicate how many seconds should pass before the effects of the next
                # Neuroglancer state URL, and two numbers in a row should be summed.
                if len(lines) > 0 and not isinstance(lines[-1], str):
                    lines[-1] += n
                else:
                    lines.append(n)

    # Add a sentinel to make sure the last Neuroglancer state URL gets processed.
    lines.append("#!{}\n")

    return lines

def parse_nglink(link):
    url_base, pseudo_json = link.split("#!")
    pseudo_json = urllib.parse.unquote(pseudo_json)
    data = json.loads(pseudo_json)
    return data

def layer_is_roi(layer):
    if "source" in layer:
        if "url" in layer["source"]:
            return "roi" in layer["source"]["url"]
    return False

def layer_is_visible(layer):
    if "visible" in layer:
        return layer["visible"]
    return True

def layer_alpha(layer):
    if not layer_is_visible(layer):
        return 0.0
    alpha = 1.0
    if "objectAlpha" in layer:
        alpha = layer["objectAlpha"]
    if layer_is_roi(layer):
        # Neuroglancer tends to make the alpha for ROIs too high.
        if alpha > 0.5:
            alpha = 0.2
    return alpha

def layer_name(layer):
    if "name" in layer:
        return layer["name"].replace(" ", "-").replace("(", "").replace(")", "")
    raise KeyError

def layer_category(layer):
    global neurons, neuron_sources, rois, roi_sources
    return (rois, roi_sources) if layer_is_roi(layer) else (neurons, neuron_sources)

def layer_category_name(layer):
    return "rois" if layer_is_roi(layer) else "neurons"

def layer_group_name(layer):
    return layer_category_name(layer) + "." + layer_name(layer)

def state_camera_look_at(ng_state):
    if "position" in ng_state:
        p = ng_state["position"]
        return Vector((p[0], p[1], p[2]))
    return None

def layer_segments(layer):
    seg_strs = layer["segments"] if "segments" in layer else []
    result = []
    for seg_str in seg_strs:
        if seg_str.isnumeric():
            result.append(int(seg_str))
        else:
            result.append(seg_str)
    return result

def set_layer_segments(layer, segments):
    layer["segments"] = segments

def layer_source(layer):
    if "source" in layer:
        if "url" in layer["source"]:
            return layer["source"]["url"]
        else:
            return layer["source"]
    return ""

def set_layer_source(layer, url):
    if "source" in layer:
        if "url" in layer["source"]:
            layer["source"]["url"] = url
        else:
            layer["source"] = url

def state_camera_quaternion(ng_state):
    if "projectionOrientation" in ng_state:
        q = ng_state["projectionOrientation"]
        # The Blender Quaternion constructor takes w first, not last.
        return Quaternion(qswzl(q))
    return Quaternion(qswzl((0, 0, 0, 1)))

def state_camera_distance(ng_state):
    if "projectionScale" in ng_state:
        return ng_state["projectionScale"]
    return None

def state_camera_look_from(ng_state):
    at = state_camera_look_at(ng_state)
    d = state_camera_distance(ng_state)
    q = state_camera_quaternion(ng_state)
    if at and d and q:
        # From the "FlyEM hemibrain" example on https://github.com/google/neuroglancer,
        # the view is down the positive Z axis when "projectionOrientation" is omitted from
        # the view state.  And from `src/neuroglancer/navigateion_state.ts` it is omitted by
        # `OrientationState.toJSON()` if `quaternionIsIdentity(orientation)`, which returns true
        # if the orientation is (0, 0, 0, 1)
        v = Vector((0, 0, -1)) * d
        v.rotate(q)
        v = at + v
        return v
    return None

def compress_category(category, ids, sources):
    global rois, initial_layer_alphas
    names_to_omit = []
    sources_to_omit = set()
    for name, srcAndSegments in ids.items():
        segments = srcAndSegments[1]
        group = category + "." + name
        if len(segments) == 0 or (group in initial_layer_alphas and initial_layer_alphas[group] == 0):
            names_to_omit.append(name)
            sources_to_omit.add(srcAndSegments[0])
    for name, srcAndSegments in ids.items():
        if not name in names_to_omit:
            src = srcAndSegments[0]
            if src in sources_to_omit:
                sources_to_omit.remove(src)
    for name in names_to_omit:
        del ids[name]
    for name in ids:
        src = ids[name]
    for name, srcAndSegments in ids.items():
        src = srcAndSegments[0]
        n = functools.reduce(lambda a, b: a + (src > b), sources_to_omit, 0)
        srcAndSegments[0] -= n
    if len(sources_to_omit) > 0:
        sources_to_omit = list(sources_to_omit)
        sources_to_omit.sort(reverse=True)
        for i in sources_to_omit:
            del sources[i]

def add_category(category, ids, sources):
    global result_json
    if len(ids) > 0:
        result_json[category] = {}
        if len(sources) == 1:
            result_json[category]["source"] = sources[0]
        else:
            result_json[category]["source"] = sources
    for key in ids.keys():
        if len(sources) == 1:
            result_json[category][key] = ids[key][1]
        else:
            result_json[category][key] = {
                "ids": ids[key][1],
                "sourceIndex": ids[key][0]
            }
            
def add_categories():
    global neurons, neuron_sources, rois, roi_sources
    global result_json
    compress_category("rois", rois, roi_sources)
    compress_category("neurons", neurons, neuron_sources)
    add_category("rois", rois, roi_sources)
    add_category("neurons", neurons, neuron_sources)

def add_advance_time(time, time_next):
    global animation
    duration = time_next - time
    if duration > 0:
        animation.append([
            "advanceTime", { "by": duration }
        ])
    print("advance time by {} to {}".format(duration, time_next))

def add_fade(group, to_omit, startingAlpha, endingAlpha, duration):
    global animation
    meshes = group
    for sub in to_omit:
        meshes += " - " + sub
    animation.append([
        "fade", { "meshes": meshes, "startingAlpha": startingAlpha, "endingAlpha": endingAlpha, "duration": duration }
    ])

    print("'{}' fade alpha from {} to {} duration {}".format(meshes, startingAlpha, endingAlpha, duration))

def add_set_value(group, alpha, index=-1):
    global animation
    if index == -1:
        index = len(animation)
    animation.insert(index, [
        "setValue", { "meshes": group, "alpha": alpha }
    ])

    print("'{}' set alpha to {} ".format(group, alpha))

def add_frame_camera(group, index=-1):
    global animation
    if index == -1:
        index = len(animation)
    animation.insert(index, [
        "frameCamera", { "bound": group }
    ])

    print("frame camera on '{}'".format(group))

def add_orbit_camera(group, endRelAngle, duration, axis="z", index=-1):
    global animation
    angle = float(round(endRelAngle))
    if index == -1:
        index = len(animation)
    if group == None:
        animation.insert(index, [
            "orbitCamera", { "axis": axis, "endingRelativeAngle": angle, "duration": duration }
        ])

        if duration > 0:
            print("orbit camera, ending relative angle {}, duration {}".format(angle, duration))
    else:
        animation.insert(index, [
            "orbitCamera", { "around": group,  "axis": axis, "endingRelativeAngle": angle, "duration": duration }
        ])

        if duration > 0:
            print("orbit camera around '{}', ending relative angle {}, duration {}".format(group, angle, duration))

    return len(animation) - 1

def update_orbit_camera(endRelAngle, duration, axis, index):
    if index < len(animation):
        if animation[index][0] == "orbitCamera":
            animation[index][1]["axis"] = axis
            angle = float(round(endRelAngle))
            animation[index][1]["endingRelativeAngle"] = angle
            animation[index][1]["duration"] = duration

            print("updated previous orbit camera to have axis '{}', ending relative angle {}, duration {}".format(axis, angle, duration))

def add_initial_frame_camera():
    global rois, neurons
    global animation
    candidates = []
    for cmd in animation:
        if "fade" in cmd:
            candidates.append(cmd[1]["meshes"])
        if "advanceTime" in cmd and len(candidates) > 0:
            break
    if len(candidates) == 0:
        candidates = ["rois." + key for key in rois.keys() if not key == "source" and len(rois[key][1]) > 0]
    if len(candidates) == 0:
        candidates = ["neurons." + key for key in neurons.keys() if not key == "source" and len(neurons[key][1]) > 0]
    if len(candidates) == 1:
        add_frame_camera(candidates[0], 0)
    else:
        chosen = None
        for candidate in candidates:
            if "all" in candidate:
                chosen = candidate
                break
        if not chosen:
            chosen = candidates[0]
        add_frame_camera(chosen, 0)

def add_initial_orient_camera(lines):
    for line in lines:
        if line.startswith("http"):
            ng_state = parse_nglink(line)
            q = state_camera_quaternion(ng_state)

            # Various initial Neuroglancer orientations and how the Blender camera needs to be
            # rotated (orbited with duration 0) to flip it to match.
            # TODO: Add more initial Neuroglancer orientations.
            orientations = [
                (Quaternion(qswzl((0.7071, 0, 0, 0.7071))), []),
                (Quaternion(qswzl((0, 0, 0, 1))), [("x", -90)]),
                (Quaternion(qswzl((0, 0.7071, -0.7071, 0))), [("z", 180), ("x", 180)])
            ]

            diffs = [q.rotation_difference_angle(orientation[0]) for orientation in orientations]
            i = argmin(diffs)
            for orient in orientations[i][1]:
                if orient:
                    axis = orient[0]
                    angle = orient[1]
                    duration = 0
                    add_orbit_camera(None, angle, duration, axis=axis, index=0)
            break

def compress_time_advances():
    global animation
    to_delete = []
    cmd_prev = None
    cmd_advance_time_prev = None
    for i in range(len(animation)):
        cmd = animation[i]
        if cmd[0] == "advanceTime":
            if not cmd_advance_time_prev:
                use_it = False
                if cmd_prev:
                    if cmd_prev[0] != "advanceTime":
                        # Say there is a command of duration `d` followed by an "advanceTime" of `d` and
                        # a second "advanceTime".  Do not compress the second "advanceTime" into the first,
                        # because it is useful to see that the first just gets past the command of duration `d`
                        # and the second adds an additional pause.
                        if "duration" in cmd_prev[1] and abs(cmd_prev[1]["duration"] - cmd[1]["by"]) > 0.001:
                            use_it = True
                    elif not cmd_advance_time_prev:
                        use_it = True
                    if use_it:
                        cmd_advance_time_prev = cmd
            else:
                # Do the actual compression of two "advanceTime" commands.
                cmd_advance_time_prev[1]["by"] += cmd[1]["by"]
                to_delete.append(i)
        else:
            cmd_advance_time_prev = None
        cmd_prev = cmd

    # Delete higher indices first, so lower indices are still valid.
    to_delete = list(reversed(to_delete))
    for i in to_delete:
        del animation[i]

# Must be preceeded by `process_layer_source` for each ROI layer, so that ROI ID numbers
# (which are not unique to the source) will have been converted to ROI names (which are
# unique).
def setup_containment_if_needed(ng_state):
    global contains_groups
    if not "layers" in ng_state or len(contains_groups) > 0:
        return
    segment_sets = {}
    for layer in ng_state["layers"]:
        group = layer_group_name(layer)
        segment_sets[group] = set(layer_segments(layer))

    for layerA in ng_state["layers"]:
        groupA = layer_group_name(layerA)
        setA = segment_sets[groupA]
        for layerB in ng_state["layers"]:
            groupB = layer_group_name(layerB)
            if groupA != groupB:
                setB = segment_sets[groupB]
                inter = setA.intersection(setB)
                if len(inter) > 0:
                    if inter == setA:
                        print("'{}' fully contains '{}'".format(groupB, groupA))
                        if not groupB in contains_groups:
                            contains_groups[groupB] = []
                        contains_groups[groupB].append(groupA)
                    elif inter != setB:
                        print("Warning: '{}' partially intersects '{}', so fading may be wrong".format(groupA, groupB))

def setup_initial_alphas_if_needed(ng_state):
    global initial_layer_alphas, layer_alphas
    if not "layers" in ng_state or len(initial_layer_alphas) > 0:
        return
    for layer in ng_state["layers"]:
        group = layer_group_name(layer)
        initial_layer_alphas[group] = layer_alpha(layer)
        layer_alphas[group] = initial_layer_alphas[group]

def add_initial_alphas():
    for (group, alpha) in initial_layer_alphas.items():
        category, name = group.split(".")
        m = rois if category == "rois" else neurons
        if name in m:
            add_set_value(group, alpha, 0)

def add_animation():
    global result_json, animation
    compress_time_advances()
    result_json["animation"] = animation

def sort_containing_first(layers):
    def visit(group, groups_sorted):
        global contains_groups
        if group in contains_groups:
            for contained in contains_groups[group]:
                visit(contained, groups_sorted)
        groups_sorted.insert(0, group)
    groups_sorted = []
    group_to_layer = {}
    for layer in layers:
        group = layer_group_name(layer)
        group_to_layer[group] = layer
        if not group in groups_sorted:
            visit(group, groups_sorted)
    result = map(lambda group: group_to_layer[group], groups_sorted)
    return result

# TODO: Find an alternative to this special-case processing.
def process_layer_source(layer):
    src = layer_source(layer)
    GS_PREFIX = "precomputed://gs://"
    if src.startswith(GS_PREFIX):
        url_mid = src.split(GS_PREFIX)[1]

        if url_mid.startswith("neuroglancer-janelia-flyem-hemibrain/v1"):
            # TODO: Reirecting to a DVID server would not be needed if this script could load meshes in the
            # multi-resolution, chunked, shared format:
            # https://github.com/google/neuroglancer/blob/master/src/neuroglancer/datasource/precomputed/meshes.md
            if "v1.0" in url_mid:
                url_base = "https://hemibrain-dvid.janelia.org/api/node/52a13/"
            else:
                url_base = "https://hemibrain-dvid.janelia.org/api/node/31597/"
            if layer_is_roi(layer):
                url_base += "roisSmoothedDecimated"
                # When redirecting to DVID for ROIs, the ROI ID numbers must be remaped to ROI names.  Although such
                # a hard-coded remapping table seems undesirable, the mapping should not change because the data has
                # been released for use general use, and additionally, the neuVid input JSON files are more readable
                # and maintainable when they contain references like "EB" and "FB" instead of "17" and "20".
                roiIdToName = [
                    "", "AB(L)", "AB(R)", "AL(L)", "AL(R)", "AME(R)", "AOTU(R)", "ATL(L)", "ATL(R)", "AVLP(R)", 
                    "BU(L)", "BU(R)", "CA(L)", "CA(R)", "CAN(R)", "CRE(L)", "CRE(R)", "EB", "EPA(L)", "EPA(R)", 
                    "FB", "FLA(R)", "GNG", "GOR(L)", "GOR(R)", "IB", "ICL(L)", "ICL(R)", "IPS(R)", "LAL(L)", 
                    "LAL(R)", "LH(R)", "LO(R)", "LOP(R)", "ME(R)", "NO", "PB", "PED(R)", "PLP(R)", "PRW", 
                    "PVLP(R)", "SAD", "SCL(L)", "SCL(R)", "SIP(L)", "SIP(R)", "SLP(R)", "SMP(L)", "SMP(R)", "SPS(L)",
                    "SPS(R)", "VES(L)", "VES(R)", "WED(R)", "a'L(L)", "a'L(R)", "aL(L)", "aL(R)", "b'L(L)", "b'L(R)",
                    "bL(L)", "bL(R)", "gL(L)", "gL(R)"
                ]
                segments = layer_segments(layer)
                segments_processed = []
                for id in segments:
                    if 0 < id and id < len(roiIdToName):
                        segments_processed.append(roiIdToName[id])
                set_layer_segments(layer, segments_processed)
            else:
                url_base += "segmentation_meshes"

        elif layer_is_roi(layer):
            url_base = "https://storage.googleapis.com/" + url_mid + "/mesh/"
            segments = layer_segments(layer)
            segments_processed = []
            for id in segments:
                url = url_base + str(id) + ":0"
                try:
                    r = requests.get(url)
                    r.raise_for_status()
                    if "fragments" in r.json():
                        fragments = r.json()["fragments"]
                        if isinstance(fragments, list) and len(fragments) == 1:
                            key = fragments[0]
                            segments_processed.append(key)
                except requests.exceptions.RequestException as e:
                    print("Error: request URL '{}' failed: {}".format(url, str(e)))
            set_layer_segments(layer, segments_processed)
        else:
            url_base = "https://storage.googleapis.com/" + url_mid + "/"

        set_layer_source(layer, url_base)

def process_ng_state_sources(ng_state, time, time_next):
    if not "layers" in ng_state:
        return
    for layer in ng_state["layers"]:
        name = layer_name(layer)
        category, sources = layer_category(layer)
        # "Categories" (e.g., which bodies are in which named ROI or neuron groups) are not
        # declared in advance, so their declarations have to be added as they are found and used.
        if not name in category:
            process_layer_source(layer)
            src = layer_source(layer)
            if not src in sources:
                sources.append(src)
            category[name] = [sources.index(src), layer_segments(layer)]

def process_ng_state_alphas(ng_state, time, time_next):
    global initial_layer_alphas, contains_groups
    if not "layers" in ng_state:
        return
    # If `layer[i]` is contained in `layer[j]`, process `layer[j]` first.
    layers = sort_containing_first([layer for layer in ng_state["layers"]])
    for layer in layers:
        if layer_is_visible(layer):
            group = layer_group_name(layer)

            alpha = layer_alphas[group]
            alpha_next = layer_alpha(layer)
            duration = time_next - time
            if alpha != alpha_next and duration > 0:
                to_omit = []
                if group in contains_groups:
                    for contained_group in contains_groups[group]:
                        _, contained_layer_name = contained_group.split(".")
                        contained_layer = next(filter(lambda l: l["name"] == contained_layer_name, layers))

                        # If the contained layers's next alpha is greater than the containing layer's next alpha,
                        # omit the contained layer from the fading off of the containing layer.
                        if layer_alpha(contained_layer) > alpha_next:
                            to_omit.append(contained_group)
                        else:
                            layer_alphas[contained_group] = alpha_next

                add_fade(group, to_omit, alpha, alpha_next, duration)

                layer_alphas[group] = alpha_next
                if group in initial_layer_alphas:
                    del initial_layer_alphas[group]        

def process_ng_state_orbit(ng_state, time, time_next):
    global orbit_look_from_last, orbit_look_at_last, orbit_axis_last, orbit_angle, orbit_angle_start
    global orbit_cmd_index, orbit_cmd_start_time
    look_from = state_camera_look_from(ng_state)
    look_at = state_camera_look_at(ng_state)
    axis_snapped = None
    angle = 0
    if look_from and look_at:
        end = False
        if orbit_look_from_last and orbit_look_at_last:
            if vectors_equal(orbit_look_at_last, look_at):
                # If the camera is looking at the same point it looked at in the previous state,
                # then that point and the points the camera is looking from in the two states
                # define a rotation axis and angle.
                v0 = (orbit_look_from_last - orbit_look_at_last).normalized()
                v1 = (look_from - look_at).normalized()
                axis = v0.cross(v1).normalized()
                angle = math.degrees(v0.angle(v1))

                # For now, at least, snap that angle to one of the principal axes.
                axis_snapped = vector_snapped(axis).normalized()
                axis_snapped_abs = vector_abs(axis_snapped)
                print("Snapping orbit axis {} to {}".format(axis, axis_snapped_abs))
                if axis.dot(axis_snapped_abs) < 0:
                    angle = -angle

                # If the axis has switched direction since the last time it was computed,
                # then the current orbit command needs to be ended.
                if orbit_axis_last:
                    if orbit_axis_last.dot(axis_snapped) != 1:
                        end = (orbit_cmd_index != None)
            else:
                # The current orbit command also needs to be ended if the camera is looing at
                # a different point than it had been.
                end = (orbit_cmd_index != None)
        if end:
            axis_name = vector_snapped_name(orbit_axis_last)
            relative_angle = orbit_angle - orbit_angle_start
            duration = time - orbit_cmd_start_time
            # The orbit command being ended was added to the command list earlier, with dummy
            # arguments, and now those arguments can be updated. 
            update_orbit_camera(relative_angle, duration, axis_name, orbit_cmd_index)
            orbit_cmd_index = None
        if angle != 0 and orbit_cmd_index == None:
            # Create a new orbit command if appropriate.
            orbit_cmd_index = add_orbit_camera(None, 0, 0)
            orbit_cmd_start_time = time
            orbit_angle_start = orbit_angle

    elif time > 0 and orbit_cmd_index != None:
        # At the very end of the animation, end the current orbit command.
        axis_name = vector_snapped_name(orbit_axis_last)
        relative_angle = orbit_angle - orbit_angle_start
        duration = time - orbit_cmd_start_time
        update_orbit_camera(relative_angle, duration, axis_name, orbit_cmd_index)

    # Save information about this state for comparison when processing the next state.
    orbit_look_at_last = look_at
    orbit_look_from_last = look_from
    orbit_axis_last = axis_snapped
    orbit_angle += angle

def process_ng_state(ng_state, time, time_next):
    process_ng_state_sources(ng_state, time, time_next)
    setup_containment_if_needed(ng_state)
    setup_initial_alphas_if_needed(ng_state)
    process_ng_state_alphas(ng_state, time, time_next)
    process_ng_state_orbit(ng_state, time, time_next)

def formatted():
    global result_json
    result_str = "{\n"

    indent = "  "
    for (key0, val0) in result_json.items():
        if isinstance(val0, dict):
            result_str += indent + "{}: {{\n".format(json.dumps(key0))
            indent += "  "

            for (key1, val1) in val0.items():
                result_str += indent + "{}: {},\n".format(json.dumps(key1), json.dumps(val1))

            indent = indent[:-2]
            result_str = result_str.removesuffix(",\n") + "\n"
            result_str += indent + "},\n"
        elif isinstance(val0, list):
            result_str += indent + "{}: [\n".format(json.dumps(key0))
            indent += "  "

            for item in val0:
                result_str += indent + json.dumps(item) + ",\n"

            indent = indent[:-2]
            result_str = result_str.removesuffix(",\n") + "\n"
            result_str += indent + "],\n"
        else:
            result_str += json.dumps(val0) + ",\n"

    result_str = result_str.removesuffix(",\n") + "\n"
    result_str += "}\n"
    return result_str

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", dest="input", help="path to the file of Neuroglancer links")
    parser.add_argument("--output", "-o", dest="output", help="path to output JSON file")
    args = parser.parse_args()

    print("Using input file: {}".format(args.input))
    print("Using output file: {}".format(args.output))

    lines = normalize_input(args.input)
    time = 0
    time_next = 0
    for line in lines:
        if isinstance(line, numbers.Number):
            dt = line
            # We cannot advance `time` by `dt` until we have read the next state, because
            # it will define the ending conditions for commands starting at `time`.  So just
            # keep track of what time will be advanced to.
            time_next = time + dt
        else:
            ng_state = parse_nglink(line)
            process_ng_state(ng_state, time, time_next)

            # We have just processed a command that spans the period from `time` to `time_next`.
            # So now we can advance `time` to `time_next`.
            add_advance_time(time, time_next)
            time = time_next
    
    add_categories()
    add_initial_orient_camera(lines)
    add_initial_frame_camera()
    add_initial_alphas()
    add_animation()

    result_json_formatted = formatted()

    print("Writing {}...".format(args.output))
    with open(args.output, "w") as f:
        f.write(result_json_formatted)
    print("Done")
