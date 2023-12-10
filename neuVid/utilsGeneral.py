# General utilty code.

import os

def report_version():
    ver_paths = []
    cwd = os.path.dirname(os.path.realpath(__file__))
    pcwd = os.path.dirname(cwd)

    # For running the script directly in Blender.
    ver_path = os.path.join(pcwd, "VERSION")
    ver_paths.append(ver_path)

    # For bundles built with Nuitka `--include-data-files=../VERSION=VERSION`.
    ver_path = os.path.join(cwd, "VERSION")
    ver_paths.append(ver_path)

    ver = ""
    for ver_path in ver_paths:
        if os.path.exists(ver_path):
            try:
                with open(ver_path) as ver_file:
                    ver = ver_file.read().strip()
                    print("neuVid {}".format(ver))
                    break
            except:
                pass
    return ver

def newObject(name, data=None):
    import bpy
    obj = bpy.data.objects.new(name=name, object_data=data)
    if bpy.app.version < (2, 80, 0):
        bpy.context.scene.objects.link(obj)
    else:
        bpy.context.scene.collection.objects.link(obj)
    return obj
