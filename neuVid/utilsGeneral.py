# General utilty code.

import bpy

def newObject(name, data=None):
    obj = bpy.data.objects.new(name=name, object_data=data)
    if bpy.app.version < (2, 80, 0):
        bpy.context.scene.objects.link(obj)
    else:
        bpy.context.scene.collection.objects.link(obj)
    return obj
