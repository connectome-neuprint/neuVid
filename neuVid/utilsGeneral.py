# General utilty code.

import bpy
import os

def report_version():
    cwd = os.path.dirname(os.path.realpath(__file__))
    pcwd = os.path.dirname(cwd)
    ver_path = os.path.join(pcwd, "VERSION")
    if os.path.exists(ver_path):
        try:
            with open(ver_path) as ver_file:
                ver = ver_file.read().strip()
                print("neuVid {}".format(ver))
        except:
            pass

def newObject(name, data=None):
    obj = bpy.data.objects.new(name=name, object_data=data)
    if bpy.app.version < (2, 80, 0):
        bpy.context.scene.objects.link(obj)
    else:
        bpy.context.scene.collection.objects.link(obj)
    return obj
