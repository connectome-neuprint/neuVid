# $ conda create --name neuvid
# $ conda activate neuvid
# $ conda install h5py
# $ python animateVvd.py -i <directory of H5J files> -o example.json
# or
# $ python animateVvd.py -i example.json
# $ VVDViewer example.vrp
# In VVDViewer's "Record/Export" panel, change to the "Advanced" tab.
# Close other VVDViewer panels to make the 3D view bigger.
# Press the "Save..." button to save the video (with the size of the 3D view).

# Avoid playing the animation (with the play button on the "Advanced" tab, as opposed to the
# "Save..." button) because doing so, then rewinding and pressing "Save..." may produce
# glitches in the saved video.

import argparse
import h5py
import json
import math
import os
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsGeneral import report_version
from utilsJson import formatted

def quaternion_tuple(axis, angle):
    s = math.sin(angle / 2)
    w = math.cos(angle / 2)
    return (axis[0] * s, axis[1] * s, axis[2] * s, w)

def quaternion_product(q1, q2):
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    x = x1 * w2 + y1 * z2 - z1 * y2 + w1 * x2
    y = -x1 * z2 + y1 * w2 + z1 * x2 + w1 * y2
    z = x1 * y2 - y1 * x2 + z1 * w2 + w1 * z2
    w = -x1 * x2 - y1 * y2 - z1 * z2 + w1 * w2
    return (x, y, z, w)

# In VVDViewer, a key for the first frame seems to be at `t=0`.
# Then a frame at 1 second is at `t=30`, assuming 30 frames per second, 
def frame_from_time(time, fps):
    if time < 0:
        return 0
    return round(time * fps)

# Assumes t in [0, 1].  Returns the ease-in value in [0, 1].
def ease_in_cubic(t):
    if t < 0:
        return 0
    if t > 1:
        return 1
    return t * t * t

# Assumes t in [0, 1].  Returns the ease-out value in [0, 1].
def ease_out_cubic(t):
    if t < 0:
        return 1
    if t > 1:
        return 0
    return 1 - (1 - t)**3

# Assumes t in [0, 1].  Returns the ease-in, ease-out value in [0, 1].
def ease_in_ease_out_quadratic(t):
    if t < 0:
        return 0
    if t > 1:
        return 1
    if t < 0.5:
        return 2 * t * t
    t -= 0.5
    return 2 * t * (1 - t) + 0.5

# Assumes t in [0, 1].  Returns the ease-in, ease-out value in [0, 1].
def ease_in_ease_out_bezier(t):
    if t < 0:
        return 0
    if t > 1:
        return 1
    return t * t * (3 - 2 * t)

def interpolation_parameter(frame, frame0, frame1):
    # If `frame` is before (after) the real range, then extend the value at the start (end)
    # of the range, to support gaps between animators.
    if frame < frame0:
        frame = frame0
    elif frame > frame1:
        frame = frame1
    if frame1 - frame0 > 0:
        t = (frame - frame0) / (frame1 - frame0)
    else:
        t = 0
    return t

# TODO: Return an angle in the range [-180, 180]
def normalize_angle(angle):
    return angle

def to_json_quotes(x):
    return str(x).replace("'", "\"")

def invalid_line_msg(line):
    return "Invalid animation line:\n  {}".format(to_json_quotes(line))

def proper_cmd_structure():
    return 'An animation command must have the structure:\n  ["cmd-name", {"arg-name-1": arg-value-1, ..., "arg-name-N": arg-value-N}]'

def cmd_name_public(cmd):
    # Remove the "_cmd" suffix.
    return cmd[:-4]

def supported_cmds():
    cmds = [cmd_name_public(cmd) for cmd in globals().keys() if cmd.endswith("_cmd")]
    cmds.sort()
    return cmds

def validate_cmd_args(cmd_name, supported_args, actual_args):
    for arg in actual_args.keys():
        if not arg in supported_args:
            supported_args.sort()
            print("For animation command: {}\nUnrecognized argument: {}".format(cmd_name, arg))
            print("Supported arguments: {}".format(", ".join(supported_args)))
            sys.exit()

def advanceTime_cmd(state, args):
    validate_cmd_args("advanceTime", ["by"], args)
    if "by" not in args:
        print("The 'advanceTime' command must have a 'by' argument")
        sys.exit()
    advance = args["by"]
    state["current_time"] += advance
    state["max_time"] = state["current_time"]

class Orbiter:
    def __init__(self, starting_time, duration, starting_angle, ending_angle, axis, current_angle, fps):
        self.starting_time = starting_time
        self.duration = duration
        self.frame0 = frame_from_time(starting_time, fps)
        self.frame1 = frame_from_time(starting_time + duration, fps)
        self.starting_angle = normalize_angle(starting_angle)
        self.ending_angle = normalize_angle(ending_angle)
        self.axis = axis

        print("{} - {}: orbit, angle {} to {} around axis {}".format(self.frame0, self.frame1, self.starting_angle, self.ending_angle, self.axis))

        current = normalize_angle(current_angle)
        self.starting_angle -= current
        self.ending_angle -= current

    def keys(self, frame, id_interpolator, id_key, current_keys, state):
        if self.duration > 0:
            t = interpolation_parameter(frame, self.frame0, self.frame1)
            eased = ease_in_ease_out_quadratic(t)
            angle_eased = self.starting_angle + eased * (self.ending_angle - self.starting_angle)
        else:
            angle_eased = self.ending_angle
        quaternion = quaternion_tuple(self.axis, math.radians(angle_eased))

        if len(current_keys) == 0:
            # This frame will have one "interpolator" with keys for all orbits (rotations) currently in effect.
            # If it does not exist yet, create it for just this orbit.

            result  = "[interpolator/{}/keys/{}]\n".format(id_interpolator, id_key)
            result += "type=2\n"
            result += "l0=1\n"
            result += "l0_name=Render View:1\n"
            result += "l1=1\n"
            result += "l1_name=Render View:1\n"
            result += "l2=0\n"
            result += "l2_name=rotation\n"
            result += "val={} {} {} {}\n".format(quaternion[0], quaternion[1], quaternion[2], quaternion[3])
            return current_keys + result
        else:
            # But if there is an interpolator with keys for this frame already, this orbit's effects must be
            # merged into it. Doing so involves setting that interpolator's quaternion to be the product of
            # its current quaternion and the quaternion being created here. To understand the product order,
            # consider this example:
            #   ["orbitCamera", {"axis": "z", "duration": 10}],
            #     ["orbitCamera", {"axis": "y", "endingRelativeAngle": 90, "duration": 5}],
            #     ["advanceTime", {"by": 5}],
            #     ["orbitCamera", {"axis": "y", "endingRelativeAngle": -90, "duration": 5}],
            #     ["advanceTime", {"by": 5}]
            # It's intuitive to specify the longer-duration orbit (around "z", the spine of a VNC volume) as the
            # outer orbit with the shorter-duration orbits (around "y") nested inside it. By applying the outer
            # quaternion first, it takes effect continuously over its longer duration; the inner quaternions
            # are applied after it, providing shorter-duraction modifications to the longer-duration effect.
            # So the quaternion product has the quaternion being created here (the nested one) on the left.

            # Note that this approach has implications for a sequence of orbits, like the following:
            #   ["orbitCamera", {"axis": "z", "duration": 10}],
            #   ["advanceTime", {"by": 10}],
            #   ["orbitCamera", {"axis": "y", "endingRelativeAngle": 90, "duration": 5}],
            #   ["advanceTime", {"by": 5}],
            #   ["orbitCamera", {"axis": "y", "endingRelativeAngle": -90, "duration": 5}],
            #   ["advanceTime", {"by": 5}]
            # Here, the earlier orbit (around "z") finishes before the later orbits (around "y") so those later
            # orbits are not nested. The final rotation of the ealier orbit must conintue to affect the later
            # orbits, and that is implemeted by the `describe_interpolators()` function (defined later in this
            # file), which build the interpolators and their keys. It handles the sequence of orbits by preserving
            # the final quaternion of any interpolator whose final frame is earlier than the current frame (the
            # orbit around "z" here). That quaternion should be on the left in the quaternion product, which means
            # the code here has to treat it like a nested orbit. To get this effect, `describe_interpolators()`
            # temporarily reorders the animators so the the earlier ones (around "z" here) are applied later
            # (as if they were nested). See the comments in `describe_interpolators()`.

            current_keys_prefix, current_quaternion_str = current_keys.split("val=")
            current_quaternion = [float(x) for x in current_quaternion_str.split(" ")]
            full_quaternion = quaternion_product(quaternion, current_quaternion)
            full_quaternion_str = " ".join([str(x) for x in full_quaternion])
            return current_keys_prefix + "val=" + full_quaternion_str + "\n"

    def key_count(self, frame):
        return 1
    
def orbitCamera_cmd(state, args):
    validate_cmd_args("orbitCamera", ["duration", "endingRelativeAngle", "axis"], args)
    animators = state["animators"]
    fps = state["fps"]
    current_time = state["current_time"]

    axis = (0, -1, 0)
    if "axis" in args:
        axis = args["axis"]
        axes = {"x": (1,0,0), "-x": (-1,0,0), "y": (0,1,0), "-y": (0,-1,0), "z": (0,0,1), "-z": (0,0,-1)}
        if type(axis) == str and axis.lower() in axes:
            axis = axes[axis]
        elif type(axis) == list and len(axis) == 3:
            d = math.sqrt(axis[0] * axis[0] + axis[1] * axis[1] + axis[2] * axis[2])
            axis = [a / d for a in axis]
        else:
            print("Invalid 'orbitCamera' command: unrecognized 'axis' {}".format(axis))
            sys.exit()

    current_angle = 0
    current_angles = {}
    current_angle_key = str(axis)
    if "camera_current_angles" in state:
        current_angles = state["camera_current_angles"]
        current_angle_key = str(axis)
        if current_angle_key in current_angles:
            current_angle = current_angles[current_angle_key]

    starting_time = current_time
    duration = args["duration"]
    starting_angle = current_angle
    ending_angle = 360
    if "endingRelativeAngle" in args:
        ending_angle = starting_angle + args["endingRelativeAngle"]

    orbiter = Orbiter(starting_time, duration, starting_angle, ending_angle, axis, current_angle, fps)
    animators["camera_rotation"].append(orbiter)

    current_angles[current_angle_key] = ending_angle
    state["camera_current_angles"] = current_angles

    state["max_time"] = current_time + duration

class Panner:
    # Fractions should be ([-1, 1], [-1, 1], [-1, 1]).
    def __init__(self, starting_time, duration, starting_frac, ending_frac, bbox, fps):
        starting_frac = [max(-1, min(x, 1)) for x in starting_frac]
        ending_frac = [max(-1, min(x, 1)) for x in ending_frac]

        self.starting_time = starting_time
        self.duration = duration
        self.frame0 = frame_from_time(starting_time, fps)
        self.frame1 = frame_from_time(starting_time + duration, fps)

        # Convert from [-1, 1] to [-0.5, 0.5]
        frac0 = [x / 2 for x in starting_frac]
        frac1 = [x / 2 for x in ending_frac]

        # For some reason, size must be halved again to match VVDViewer.
        frac0 = [x / 2 for x in frac0]
        frac1 = [x / 2 for x in frac1]
        
        # Args specifying a change of (1, 1, 1) should correspond to a change of 
        # (bbox[0]/2, bbox[1]/2, bbox[2]/2)
        self.starting_pos = [a * b for a, b in zip(frac0, bbox)]
        self.ending_pos = [a * b for a, b in zip(frac1, bbox)]

        print("{} - {}: pan, position {} to {}".format(self.frame0, self.frame1, starting_frac, ending_frac))

    def _key(self, id_interpolator, id_key, name, val):
        result  = "[interpolator/{}/keys/{}]\n".format(id_interpolator, id_key)
        result += "type=1\n"
        result += "l0=1\n"
        result += "l0_name=Render View:1\n"
        result += "l1=1\n"
        result += "l1_name=Render View:1\n"
        result += "l2=0\n"
        result += "l2_name=obj_trans_{}\n".format(name)
        result += "val={}\n".format(val)
        return result

    def keys(self, frame, id_interpolator, id_key, current_keys, state):
        if self.duration > 0:
            t = interpolation_parameter(frame, self.frame0, self.frame1)
            eased = ease_in_ease_out_quadratic(t)
            # Use `b - a`` instead of `a - b`` because the keys move the object (volumes) in the direction
            # opposite to the camera movement.
            change = [b - a for a, b in zip(self.ending_pos, self.starting_pos)]
            pos_eased = [a + eased * b for a, b in zip(self.starting_pos, change)]
        else:
            pos_eased = [b - a for a, b in zip(self.ending_pos, self.starting_pos)]

        result =  self._key(id_interpolator, id_key, "x", pos_eased[0])
        result += self._key(id_interpolator, id_key + 1, "y", pos_eased[1])
        result += self._key(id_interpolator, id_key + 2, "z", pos_eased[2])

        return current_keys + result

    def key_count(self, frame):
        return 3

def centerCamera_cmd(state, args):
    validate_cmd_args("centerCamera", ["duration", "at"], args)
    animators = state["animators"]
    fps = state["fps"]
    current_time = state["current_time"]
    current_pos = [0, 0, 0]
    if "camera_current_position" in state:
        current_pos = state["camera_current_position"]

    starting_time = current_time
    duration = args["duration"]
    starting_pos = current_pos
    if not "at" in args:
        print("Invalid 'centerCamera' command: no 'at' argument")
        sys.exit()
    ending_pos = args["at"]
    bbox = state["bbox_overall"]
    panner = Panner(starting_time, duration, starting_pos, ending_pos, bbox, fps)
    animators["camera_translation"].append(panner)

    state["camera_current_position"] = ending_pos
    state["max_time"] = current_time + duration

class Zoomer:
    def __init__(self, starting_time, duration, starting_zoom, ending_zoom, fps):
        self.starting_time = starting_time
        self.duration = duration
        self.frame0 = frame_from_time(starting_time, fps)
        self.frame1 = frame_from_time(starting_time + duration, fps)

        zoom_to_scale = 1 / 100
        self.starting_scale = starting_zoom * zoom_to_scale
        self.ending_scale = ending_zoom * zoom_to_scale

        print("{} - {}: zoom, {} to {}".format(self.frame0, self.frame1, starting_zoom, ending_zoom))

    def keys(self, frame, id_interpolator, id_key, current_keys, state):
        if self.duration > 0:
            t = interpolation_parameter(frame, self.frame0, self.frame1)
            eased = ease_in_ease_out_quadratic(t)
            scale_eased = self.starting_scale + eased * (self.ending_scale - self.starting_scale)
        else:
            scale_eased = self.ending_scale

        result  = "[interpolator/{}/keys/{}]\n".format(id_interpolator, id_key)
        result += "type=1\n"
        result += "l0=1\n"
        result += "l0_name=Render View:1\n"
        result += "l1=1\n"
        result += "l1_name=Render View:1\n"
        result += "l2=0\n"
        result += "l2_name=scale\n"
        result += "val={}\n".format(scale_eased)

        return current_keys + result

    def key_count(self, frame):
        return 1

def zoomCamera_cmd(state, args):
    validate_cmd_args("zoomCamera", ["duration", "to"], args)
    animators = state["animators"]
    fps = state["fps"]
    current_time = state["current_time"]

    current_zoom = 100
    if "camera_current_zoom" in state:
        current_zoom = state["camera_current_zoom"]

    starting_time = current_time
    duration = args["duration"]
    starting_zoom = current_zoom
    if not "to" in args:
        print("Invalid 'zoomCamera' command: no 'to' argument")
        sys.exit()
    ending_zoom = args["to"]
    zoomer = Zoomer(starting_time, duration, starting_zoom, ending_zoom, fps)
    animators["camera_zoom"].append(zoomer)

    state["camera_current_zoom"] = ending_zoom

    state["max_time"] = current_time + duration

class Fader:
    def __init__(self, full_names, starting_time, duration, starting_alpha, ending_alpha, fps):
        self.names = full_names
        self.starting_time = starting_time
        self.duration = duration
        self.frame0 = frame_from_time(starting_time, fps)
        self.frame1 = frame_from_time(starting_time + duration, fps)
        self.starting_alpha = starting_alpha
        self.ending_alpha = ending_alpha

        if self.starting_alpha < self.ending_alpha:
            self.starting_alpha = 0
            self.ending_alpha = 1
        elif self.starting_alpha > self.ending_alpha:
            self.starting_alpha = 1
            self.ending_alpha = 0
        elif self.starting_alpha == 0:
            self.starting_alpha = 0
            self.ending_alpha = 0
        else:
            self.starting_alpha = 1
            self.ending_alpha = 1

        print("{} - {}: fade {}, alpha {} to {}".format(self.frame0, self.frame1, self.names, self.starting_alpha, self.ending_alpha))

    def keys(self, frame, id_interpolator, id_key, current_keys, state):
        visible = 1
        if self.starting_alpha == 0 and self.ending_alpha == 0:
            visible = 0
        elif frame < self.frame0 and self.starting_alpha == 0:
            visible = 0
        elif frame > self.frame1 and self.ending_alpha == 0:
            visible = 0

        result = ""
        for i in range(len(self.names)):
            result += "[interpolator/{}/keys/{}]\n".format(id_interpolator, id_key + i)
            result += "type=3\n"
            result += "l0=1\n"
            result += "l0_name=Render View:1\n"
            result += "l1=2\n"
            result += "l1_name={}\n".format(self.names[i])
            result += "l2=0\n"
            result += "l2_name=display\n"
            result += "val={}\n".format(visible)

        t = interpolation_parameter(frame, self.frame0, self.frame1)

        alpha = self.starting_alpha
        if self.starting_alpha < self.ending_alpha:
            eased = ease_in_cubic(t)
            alpha = self.starting_alpha + eased * (self.ending_alpha - self.starting_alpha)
        elif self.starting_alpha > self.ending_alpha:
            eased = ease_out_cubic(t)
            alpha = self.starting_alpha + eased * (self.ending_alpha - self.starting_alpha)

        for i in range(len(self.names)):
            result += "[interpolator/{}/keys/{}]\n".format(id_interpolator, id_key + len(self.names) + i)
            result += "type=1\n"
            result += "l0=1\n"
            result += "l0_name=Render View:1\n"
            result += "l1=2\n"
            result += "l1_name={}\n".format(self.names[i])
            result += "l2=0\n"
            l2_name = "alpha" if self.names[i].startswith("volumes") else "transparency"
            result += f"l2_name={l2_name}\n"
            result += "val={}\n".format(alpha)

        return current_keys + result

    def key_count(self, frame):
        return 2 * len(self.names)

def flash_cmd(state, args):
    validate_cmd_args("flash", ["advanceTime", "duration", "ramp", "volume", "meshes", "offset"], args)
    animators = state["animators"]
    fps = state["fps"]
    current_time = state["current_time"]

    if "volume" not in args and "meshes" not in args:
        print("The 'flash' command must have a 'volume' or 'meshes' argument")
        sys.exit()

    advance_time = 0
    duration = 2

    if "volume" in args:
        full_vol_name = args["volume"]
        if "flash_volume_current_advance_time" in state:
            advance_time = state["flash_volume_current_advance_time"]
        if "advanceTime" in args:
            advance_time = args["advanceTime"]
        if "flash_volume_current_duration" in state:
            duration = state["flash_volume_current_duration"]
        if "duration" in args:
            duration = args["duration"]
        ramp = 0.5
        if "flash_volume_current_ramp" in state:
            ramp = state["flash_volume_current_ramp"]
        if "ramp" in args:
            ramp = args["ramp"]

        starting_time = current_time
        fader1 = Fader([full_vol_name], starting_time, duration=ramp, starting_alpha=0, ending_alpha=1, fps=fps)
        starting_time += ramp
        mid_duration = duration - 2 * ramp
        fader2 = Fader([full_vol_name], starting_time, duration=mid_duration, starting_alpha=1, ending_alpha=1, fps=fps)
        starting_time += mid_duration
        fader3 = Fader([full_vol_name], starting_time, duration=ramp, starting_alpha=1, ending_alpha=0, fps=fps)

        if not full_vol_name in animators:
            animators[full_vol_name] = []
        animators[full_vol_name] += [fader1, fader2, fader3]

        state["flash_volume_current_advance_time"] = advance_time
        state["flash_volume_current_duration"] = duration
        state["flash_volume_current_ramp"] = ramp

    elif "meshes" in args:
        meshes_name = args["meshes"]
        count = len(state["meshes"][meshes_name])
        meshes_names = [f"{meshes_name}.{i}" for i in range(count)]

        if "flash_meshes_current_advance_time" in state:
            advance_time = state["flash_meshes_current_advance_time"]
        if "advanceTime" in args:
            advance_time = args["advanceTime"]
        if "flash_meshes_current_duration" in state:
            duration = state["flash_meshes_current_duration"]
        if "duration" in args:
            duration = args["duration"]

        # Stagger the fading of the meshes in the group, with start times differing by `offset`.
        offset = 0
        if count > 1:
            offset = (duration / 2) / (count - 1) 
        if "offset" in args:
            offset = args["offset"]

        one_frame = 1 / fps
        one_frame *= 2
        offset = max(offset, one_frame)

        ramp = min(duration / 4, 0.25)
        ramp = max(ramp, one_frame)
        
        starting_time = current_time
        ending_time = starting_time + duration
        starting_last_ramp = ending_time - ramp
        for mesh_name in meshes_names:
            fader1 = Fader([mesh_name], starting_time, duration=ramp, starting_alpha=0, ending_alpha=1, fps=fps)
            duration2 = starting_last_ramp - (starting_time + ramp)
            fader2 = Fader([mesh_name], starting_time + ramp, duration=duration2, starting_alpha=1, ending_alpha=1, fps=fps)
            fader3 = Fader([mesh_name], starting_last_ramp, duration=ramp, starting_alpha=1, ending_alpha=0, fps=fps)
            starting_time += offset

            if not mesh_name in animators:
                animators[mesh_name] = []
            animators[mesh_name] += [fader1, fader2, fader3]

        state["flash_meshes_current_advance_time"] = advance_time
        state["flash_meshes_current_duration"] = duration

    state["current_time"] += advance_time
    state["max_time"] = current_time + duration

def fade_cmd(state, args):
    validate_cmd_args("fade", ["duration", "startingAlpha", "endingAlpha", "volume", "meshes"], args)
    animators = state["animators"]
    fps = state["fps"]
    current_time = state["current_time"]

    if "volume" not in args and "meshes" not in args:
        print("The 'fade' command must have a 'volume' or 'meshes' argument")
        sys.exit()
    if "volume" in args:
        full_name = args["volume"]
        full_names = [full_name]
    else:
        full_name = args["meshes"]
        count = len(state["meshes"][full_name])
        full_names = [f"{full_name}.{i}" for i in range(count)]

    duration = 1
    if "duration" in args:
        duration = args["duration"]
    starting_alpha = 1
    if "startingAlpha" in args:
        starting_alpha = args["startingAlpha"]
    starting_alpha = max(0, starting_alpha)
    starting_alpha = min(1, starting_alpha)
    ending_alpha = 0
    if "endingAlpha" in args:
        ending_alpha = args["endingAlpha"]
    ending_alpha = max(0, ending_alpha)
    ending_alpha = min(1, ending_alpha)

    starting_time = current_time
    fader = Fader(full_names, starting_time, duration, starting_alpha, ending_alpha, fps)
    animators[full_name].append(fader)

    state["max_time"] = current_time + duration

def parse_cmd(step):
    if not isinstance(step, list) or len(step) != 2:
        print(invalid_line_msg(step))
        print("Invalid animation command structure")
        print(proper_cmd_structure())
        sys.exit()
    cmd_name = step[0]
    if not isinstance(cmd_name, str):
        print(invalid_line_msg(step))
        print("Invalid animation command name: '{}'".format(to_json_quotes(cmd_name)))
        print(proper_cmd_structure())
        sys.exit()
    args = step[1]
    if not isinstance(args, dict):
        print(invalid_line_msg(step))
        print("Invalid animation command arguments: '{}'".format(to_json_quotes(args)))
        print(proper_cmd_structure())
        sys.exit()
    # The Python function implementing command `x` must be named `x_cmd`.  The `_cmd` suffix simplifies  
    # printing all the supported commands when an erroneous command is parsed.
    cmd_name += "_cmd"
    if cmd_name in globals():
        cmd = globals()[cmd_name]
        return (cmd, args)
    else:
        print("Invalid animation step:\n  {}".format(step))
        print("Unrecognized animation command: '{}'".format(cmd_name_public(cmd_name)))
        print("Supported animation commands: {}".format(", ".join(supported_cmds())))
        sys.exit()

def remove_comments(file):
    output = ""
    with open(file) as f:
        for line in f:
            line_stripped = line.lstrip()
            if line_stripped.startswith("#") or line_stripped.startswith("//"):
                # Replace a comment line with a blank line, so the line count stays the same
                # in error messages.
                output += "\n"
            else:
                output += line
    return output

def parse_json(json_input_file):
    try:
        json_data = json.loads(remove_comments(json_input_file))
        return json_data
    except json.JSONDecodeError as exc:
        print("Error reading JSON, line {}, column {}: {}".format(exc.lineno, exc.colno, exc.msg))
        # TODO: guess_extraneous_comma(json_input_file)
        sys.exit()

def get_num_frames(animators, fps):
    max_time = 0
    for animator_list in animators.values():
        for animator in animator_list:
            time = animator.starting_time + animator.duration
            max_time = max(max_time, time)
    # Add one for the frame at 0.
    num = frame_from_time(max_time, fps) + 1
    return num

def get_vol_int_attr(attrs, name):
    val = 0
    if name in attrs:
        val = attrs[name]
        if not isinstance(val, int):
            val = val[0]
    return val

def get_vol_bbox(path):
    dx = dy = dz = 0
    with h5py.File(path, "r") as f:
        attrs = f["Channels"].attrs
        dx = get_vol_int_attr(attrs, "width")
        dy = get_vol_int_attr(attrs, "height")
        dz = get_vol_int_attr(attrs, "frames")
    return (dx, dy, dz)  

def init_state(fps):
    state = {}
    state["fps"] = fps
    state["current_time"] = 0
    return state

def add_volumes(input, state, json_data, default_channel):
    if not "volumes" in json_data:
        print("Invalid JSON: no 'volumes' section")
        sys.exit()

    json_anim = json_data["volumes"]
    if not isinstance(json_anim, dict):
        print("Invalid JSON: 'volumes' must be a dictionary of volume names and sources")
        sys.exit()

    json_volumes = json_data["volumes"]

    source_base = ""
    if "source" in json_volumes:
        source_base = json_volumes["source"]
    input_dir = os.path.dirname(input)

    volumes = {}
    for key, value in json_volumes.items():
        if key != "source":
            full_vol_name = "volumes." + key
            if type(value) == list:
                vol_file = value[0]
                channel = value[1]
            else:
                vol_file = value
                channel = default_channel
            vol_path = os.path.join(source_base, vol_file)
            volumes[full_vol_name] = (vol_path, channel)
    state["volumes"] = volumes

    bbox_overall = (0, 0, 0)
    for vol_name, vol_tuple in volumes.items():
        vol_path, channel = vol_tuple
        vol_path = os.path.join(input_dir, vol_path)
        bbox = get_vol_bbox(vol_path)
        bbox_overall = (max(bbox[0], bbox_overall[0]), max(bbox[1], bbox_overall[1]), max(bbox[2], bbox_overall[2]))
    state["bbox_overall"] = bbox_overall

    print("bbox overall: {}".format(bbox_overall))

def add_meshes(input, state, json_data):
    if not "meshes" in json_data:
        return

    json_anim = json_data["meshes"]
    if not isinstance(json_anim, dict):
        print("Invalid JSON: 'meshes' must be a dictionary of mesh names and sources")
        sys.exit()

    json_meshes = json_data["meshes"]

    source_base = ""
    if "source" in json_meshes:
        source_base = json_meshes["source"]

    meshes = {}
    for key, value in json_meshes.items():
        if key != "source":
            meshes_group_name = "meshes." + key
            if type(value) == str:
                if "." in value:
                    value = value.split(".")[0]
                value = [int(value)]
            meshes_group = []
            for id in value:
                if not type(id) == int:
                    print(f"In \"meshes.{key}\" skipping \"{id}\" which is not an integer ID")
                    continue

                # TODO: Handle OBJ files in addition to SWC files.
                mesh_file = f"{id}.swc"

                mesh_path = os.path.join(source_base, mesh_file)
                meshes_group.append(mesh_path)
            meshes[meshes_group_name] = meshes_group
    state["meshes"] = meshes

    '''
    # TODO: Account for the (unlikely?) possibility that a mesh extends outside the volume and affects the bounding box.
    bbox_overall = (0, 0, 0)
    input_dir = os.path.dirname(input)
    for mesh_name, mesh_path in meshes.items():
        mesh_path = os.path.join(input_dir, mesh_path)
        bbox = get_mesh_bbox(mesh_path)
        bbox_overall = (max(bbox[0], bbox_overall[0]), max(bbox[1], bbox_overall[1]), max(bbox[2], bbox_overall[2]))
    state["bbox_overall"] = bbox_overall
    '''

def add_animators(state, json_data, fps):
    if not "animation" in json_data:
        print("Invalid JSON: no 'animation' section")
        sys.exit()

    json_anim = json_data["animation"]
    if not isinstance(json_anim, list):
        print("Invalid JSON: 'animation' must be a list of commands")
        sys.exit()

    animators = {}
    animators["camera_rotation"] = []
    animators["camera_translation"] = []
    animators["camera_zoom"] = []
    animated = list(state["volumes"].keys())
    if "meshes" in state:
        animated += list(state["meshes"].keys())
    for name in animated:
        animators[name] = []
    state["animators"] = animators

    for step in json_anim:
        cmd, args = parse_cmd(step)
        cmd(state, args)

    max_time = state["max_time"]
    '''
    # TODO: Make certain this old code is really not needed.
    for name in animated:
        if len(animators[name]) == 0:
            # A volume not mentioned in any commands should be visible all the time.
            animators[name] = [Fader([name], 0, max_time, 1, 1, fps)]
    '''

def describe_header():
    result = "ver_major=2\n"
    result += "ver_minor=19\n"
    result += "ticks=2\n"
    result += "[memory\ settings]\n"
    result += "mem\ swap=1\n"
    result += "graphics\ mem=10000\n"
    result += "large\ data\ size=1000\n"
    result += "force\ brick\ size=512\n"
    result += "up\ time=100\n"
    result += "update\ order=1\n"
    return result

def get_color(i):
    colors = [
        (255,   65,    40), # (165,   54,     0, ), # orange
        (247,   37,   251), # (179,   45,     181), # pink
        (  0,  114,   178), # blue
        (144,  136,    39), # yellow
        ( 21,  142,    63), # (52,    142,    83 ), # green
        (  5,   60,   255) # dark blue
    ]
    colors = [(c[0]/255.0, c[1]/255.0, c[2]/255.0) for c in colors]
    return colors[i % len(colors)]

def describe_volumes(state):
    num = len(state["volumes"])
    result = "[data]\n"
    result += "[data/volume]\n"
    result += "num={}\n".format(num)
    i = 0
    for full_vol_name, vol_tuple in state["volumes"].items():
        vol_path, channel = vol_tuple

        # VVDViewer seems to accept only absolute paths and paths that start with "./"
        # So even relative paths like "../elsewhere" need to be "./../elsewhere", oddly.
        if not os.path.isabs(vol_path):
            vol_path = os.path.join(".", vol_path)

        # On Windows, the output of os.path.join does not seem to work for paths in
        # VVDViewer project files.  But forward slashes do work.
        vol_path = vol_path.replace(os.sep, "/")

        result += "[data/volume/{}]\n".format(i)
        result += "name={}\n".format(full_vol_name)
        result += "path={}\n".format(vol_path)
        result += "cur_chan={}\n".format(channel)
        result += "[data/volume/{}/properties]\n".format(i)
        result += "display=1\n"
        color = get_color(i)
        result += "color={} {} {}\n".format(color[0], color[1], color[2])
        result += "shading=1\n"

        result += "3dgamma=0.6\n"
        result += "enable_alpha=1\n"
        result += "alpha=0.850476\n"
        result += "samplerate=0.27\n"
        result += "gamma=0.250000 0.250000 0.250000\n"

        i += 1

    return result

def describe_meshes(state):
    if not "meshes" in state:
        return ""

    meshes = state["meshes"]
    meshes_decollated = []
    i = 0
    for meshes_group_name, meshes_group in meshes.items():
        for j in range(len(meshes_group)):
            mesh_name = f"{meshes_group_name}.{j}"
            meshes_decollated.append((mesh_name, meshes_group[j], i))
        i += 1

    num = len(meshes_decollated)
    result = "[data/mesh]\n"
    result += "num={}\n".format(num)
    i = 0
    for mesh_name, mesh_path, color_index in meshes_decollated:

        # VVDViewer seems to accept only absolute paths and paths that start with "./"
        # So even relative paths like "../elsewhere" need to be "./../elsewhere", oddly.
        if not os.path.isabs(mesh_path):
            if not mesh_path.startswith("./"):
                mesh_path = os.path.join(".", mesh_path)

        # On Windows, the output of os.path.join does not seem to work for paths in
        # VVDViewer project files.  But forward slashes do work.
        mesh_path = mesh_path.replace(os.sep, "/")

        result += "[data/mesh/{}]\n".format(i)
        result += "name={}\n".format(mesh_name)
        result += "path={}\n".format(mesh_path)
        result += "[data/mesh/{}/properties]\n".format(i)
        result += "display=1\n"
        result += "lighting=1\n"
        color = get_color(color_index)
        result += "diffuse={} {} {}\n".format(color[0], color[1], color[2])
        result += "shininess=30\n"
        result += "alpha=1\n"
        result += "gamma=1.000000 1.000000 1.000000\n"
        result += "brightness=1.000000 1.000000 1.000000\n"
        result += "hdr=0.000000 0.000000 0.000000\n"
        result += "levels=1.000000 1.000000 1.000000\n"
        result += "sync_r=0\n"
        result += "sync_g=0\n"
        result += "sync_b=0\n"
        result += "shadow=1\n"
        result += "shadow_darkness=0.6\n"
        result += "radius_scale=1\n"

        i += 1

    return result

def describe_views(state):
    volumes = state["volumes"]
    meshes = []
    if "meshes" in state:
        for meshes_group_name, meshes_group in state["meshes"].items():
            for i in range(len(meshes_group)):
                meshes.append(f"{meshes_group_name}.{i}")
    result  = "[views]\n"
    result += "num=1\n"
    result += "[views/0]\n"

    result += "[views/0/layers]\n"
    result += "num={}\n".format(len(volumes) + len(meshes))
    items = list(volumes.items())
    for i in range(len(items)):
        result += "[views/0/layers/{}]\n".format(i)
        result += "type=5\n"
        result += "name=Group {}\n".format(i)
        result += "id={}\n".format(i)
        result += "[views/0/layers/{}/volumes]\n".format(i)
        result += "num=1\n"
        name = items[i][0]
        result += "vol_0={}\n".format(name)
    for i in range(len(meshes)):
        name = meshes[i]
        result += "[views/0/layers/{}]\n".format(i + len(volumes))
        result += "type=3\n"
        result += "name={}\n".format(name)

    result += "[views/0/properties]\n"

    default_zoom = 100
    state["camera_current_zoom"] = default_zoom
    zoom_to_scale = 1 / 100
    result += "scale={}\n".format(default_zoom * zoom_to_scale)

    '''
    # TODO: Add an option for enabling mesh/volume depth occlusion with the following:
    result += "volmethod=2\n"
    '''

    return result

def describe_interpolators(state, fps):
    animators = state["animators"]
    num_frames = get_num_frames(animators, fps)

    print("total frames: {}".format(num_frames))

    num_interpolators = num_frames
    result  = "[interpolator]\n"
    result += "max_id={}\n".format(num_interpolators)
    result += "num={}\n".format(num_interpolators)

    for frame in range(num_frames):
        id_interpolator = frame
        id_key = 0
        keys = ""
        for name, animator_list in animators.items():
            indices = []
            afters = []
            n = len(animator_list)
            for i in range(n):
                animator = animator_list[i]
                f0 = frame_from_time(animator.starting_time, fps)
                f1 = frame_from_time(animator.starting_time + animator.duration, fps)
                before_first = (i == 0 and frame < f0)
                within = (f0 <= frame and frame <= f1)
                # When the frame is between two animators, use the later one.  This case is not triggered too often
                # because the animators are sorted and looping will break earlier in other cases.
                between = (frame < f0) and not within
                if before_first or within or between:
                    indices.append(i)

                # For some animators (e.g., orbits, which are rotations), the value from the animator's final frame
                # must continue to take effect after that frame. But behavior is most intuitive if these inactive
                # animators are applied in reverse order, after the active animators. Without that ordering, it 
                # would not be possible to give the most intuitive behavior for nested animators (overlapping in time).
                # See the comments in the `Orbiter.keys()` function.

                after_last = (f1 < frame) and not within
                if after_last:
                    afters.append((i, f1))

            afters = sorted(afters, reverse=True, key=lambda x: x[1])
            for a in afters:
                indices.append(a[0])

            for i in indices:
                animator = animator_list[i]
                # Pass in the current keys and get back the current keys plus new keys.
                # This approach allows changing of the current keys (e.g,, for nested orbiting).
                keys = animator.keys(frame, id_interpolator, id_key, keys, state)
                id_key += animator.key_count(frame)

        result += "[interpolator/{}]\n".format(frame)
        result += "id={}\n".format(frame)
        result += "t={}\n".format(frame)
        # Not sure what this means...
        result += "type=0\n"

        result += "[interpolator/{}/keys]\n".format(frame)
        result += "num={}\n".format(id_key)

        result += keys

    return result

def describe_project(input, json_data, default_channel):
    # TODO: Support "fps" in the JSON.
    fps = 30

    state = init_state(fps)
    add_volumes(input, state, json_data, default_channel)
    add_meshes(input, state, json_data)
    add_animators(state, json_data, fps)

    # For keys at N frames, there need to be N `[interpolator/<i>]` statements, 0 < i < N.
    # Each `[interpolator/<i>]` section has a `t=<frame>` statement for the specific <frame>.
    # Then each `[interpolator/<i>]` section has a `[interpolator/<i>/keys]` subsection.
    # The ``[interpolator/<i>/keys]` subsection starts with a `num=<M>` statement for the M things that
    # need to be keyed at this frame.
    # Then it has a `[interpolator/<i>/keys/<j>]` subsection, 0 < j < M, for those keys.

    result = describe_header()
    result += describe_volumes(state)
    result += describe_meshes(state)
    result += describe_views(state)
    result += describe_interpolators(state, fps)

    return result

# Builds a very simple neuVid description (JSON) file from the volumes in `input_dir`.
def collect_volumes(input_dir, output_dir_rel, count=-1):
    result = {
        "volumes": {
            "source": output_dir_rel
        },
        "animation": [
        ]
    }

    paths_and_names = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            split = os.path.splitext(file)
            if len(split) == 2 and split[1].lower() == ".h5j":
                path = os.path.join(root, file)
                path = path.split(input_dir)[1]
                if path[0] == os.sep:
                    path = path[1:]
                name = path.split(os.sep)[0]
                paths_and_names.append((path, name))
    paths_and_names = sorted(paths_and_names, key=lambda x: x[0])
    if count > 0:
        paths_and_names = paths_and_names[:count]

    for path, name in paths_and_names:
        result["volumes"][name] = path

    add_args = True
    for path, name in paths_and_names:
        if add_args:
            add_args = False
            cmd = ["flash", {"volume": "volumes." + name, "ramp": 0.5, "duration": 4, "advanceTime": 1}]
        else:
            cmd = ["flash", {"volume": "volumes." + name}]
        result["animation"].append(cmd)

    return result

if __name__ == "__main__":
    report_version()
    
    parser = argparse.ArgumentParser()
    parser.set_defaults(input="")
    parser.add_argument("--input", "-i", dest="input", help="path to input (H5J file directory, or JSON file")
    parser.set_defaults(count=-1)
    parser.add_argument("--count", "-c", type=int, dest="count", help="limit on the number of files to load")
    parser.add_argument("--output", "-o", dest="output", help="path to output VVDViewer project file (.vrp)")
    parser.set_defaults(channel=0)
    parser.add_argument("--channel", "-ch", type=int, dest="channel", help="default channel from the H5J file")

    args = parser.parse_args()

    if os.path.isdir(args.input):
        print("Using input directory: {}".format(args.input))
        output = args.output
        if not output:
            output = args.input
            if output.endswith(os.sep):
                output = output[:-1]
            output += ".json"
        if args.count > 0:
            print("Limiting to count: {}".format(args.count))
        print("Using output file: {}".format(output))

        input_dir = os.path.abspath(args.input)
        output_dir = os.path.dirname(output)
        output_dir_rel = os.path.relpath(input_dir, output_dir)
        json_data = collect_volumes(input_dir, output_dir_rel, args.count)
        json_str = formatted(json_data)
        with open(output, "w") as f:
            f.write(json_str)
    else:
        print("Using input file: {}".format(args.input))
        output = args.output
        if not output:
            output = os.path.splitext(args.input)[0] + ".vrp"
        print("Using output file: {}".format(output))

        print("Using default channel: {}".format(args.channel))

        json_data = parse_json(args.input)
        project = describe_project(args.input, json_data, args.channel)
        with open(output, "w") as f:
            f.write(project)
