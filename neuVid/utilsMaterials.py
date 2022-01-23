# Utilities related to materials.

import bpy
import os.path

def handleMaterialAttributeNodesException(mat, data_path, exc):
    if data_path == "alpha" or data_path == "diffuse_color":
        raise RuntimeError("Material '{}' was not set up with nodes corresponding to 2.79 attributes".format(mat.name)) from exc
    else:
        raise exc
   
def getMaterialValue(mat, data_path):
    if bpy.app.version < (2, 80, 0):
        return getattr(mat, data_path)
    else:
        try:
            return mat.node_tree.nodes[data_path].outputs[0].default_value
        except KeyError as exc:
            handleMaterialAttributeNodesException(mat, data_path, exc)

def setMaterialValue(mat, data_path, value):
    if bpy.app.version < (2, 80, 0):
        setattr(mat, data_path, value)
    else:
        try:
            if data_path == "diffuse_color" and len(value) == 3:
                value = value + (1, )
            mat.node_tree.nodes[data_path].outputs[0].default_value = value
        except KeyError as exc:
            handleMaterialAttributeNodesException(mat, data_path, exc)

def insertMaterialKeyframe(mat, data_path, frame):
    if bpy.app.version < (2, 80, 0):
        mat.keyframe_insert(data_path, frame=frame)
    else:
        try:
            mat.node_tree.nodes[data_path].outputs[0].keyframe_insert("default_value", frame=frame)
        except KeyError as exc:
            handleMaterialAttributeNodesException(mat, data_path, exc)

# `data_path` should be "alpha  " or "diffuse_color"
def getMaterialFcurve(mat, data_path):
    animation_data = None
    if bpy.app.version < (2, 80, 0):
        animation_data = mat.animation_data
        full_data_path = data_path
    else:
        if mat.node_tree:
            animation_data = mat.node_tree.animation_data
            full_data_path = 'nodes["{}"].outputs[0].default_value'.format(data_path)
    if animation_data and animation_data.action.fcurves:
        return animation_data.action.fcurves.find(full_data_path)
    return None

def setupMaterialAttributeNodes(mat):
    if bpy.app.version < (2, 80, 0):
        return (None, None)
    else:
        matNodes = mat.node_tree.nodes

        alphaNode = matNodes.new("ShaderNodeValue")
        alphaNode.name = "alpha"
        alphaNode.label = "alpha"
        alphaNode.outputs["Value"].default_value = 1

        diffuseColorNode = matNodes.new("ShaderNodeRGB")
        diffuseColorNode.name = "diffuse_color"
        diffuseColorNode.label = "diffuse_color"

        return (alphaNode, diffuseColorNode)

def setupAlphaScaledSpecular(mat):
    matNodes = mat.node_tree.nodes
    matLinks = mat.node_tree.links

    alphaNode = matNodes["alpha"]
    bsdfNode = matNodes["Principled BSDF"]

    # Specular highlights seem to stay too strong as alpha decreases.  With Blender 2.79,
    # the solution was to use the Material `specular_alpha` attribute, but it no longer exists.
    # So pull the specular value out into its own node...
    specNode = matNodes.new("ShaderNodeValue")
    specNode.name = "specular_intensity"
    specNode.outputs["Value"].default_value = 0.5

    # ...and scale its output by the alpha node...
    alphaXSpecNode = matNodes.new("ShaderNodeMath")
    alphaXSpecNode.name = "alphaXSpecNode"
    alphaXSpecNode.operation = "MULTIPLY"
    matLinks.new(alphaNode.outputs["Value"], alphaXSpecNode.inputs[0])
    matLinks.new(specNode.outputs["Value"], alphaXSpecNode.inputs[1])

    # ...before sending that value to the BSDF node as the new specular value.
    matLinks.new(alphaXSpecNode.outputs["Value"], bsdfNode.inputs["Specular"])

def newBasicMaterial(name, color=None):
    mat = bpy.data.materials.new(name=name)
    if bpy.app.version < (2, 80, 0):
        mat.use_transparency = True
        if color:
            mat.diffuse_color = color[0:3]
    else:
        # The best compromise for transparency seems to be what the UI calls "Alpha Hashed" blend mode
        # ("HASHED"). It avoids strange depth-sorting artifacts that occur with "Alpha Blend" ("BLEND").
        # It looks a bit noisy with the relatively low number of samples necessary for good performance
        # but that speckled noise is acceptable for the main way we use transparency, to make objects
        # fade on and off.  Note that the situation is different for silhouettes, so they use different
        # settings.
        mat.blend_method = "HASHED"
        mat.shadow_method = "HASHED"

        mat.use_nodes = True
        matNodes = mat.node_tree.nodes
        matLinks = mat.node_tree.links

        alphaNode, diffuseColorNode = setupMaterialAttributeNodes(mat)        
        bsdfNode = matNodes["Principled BSDF"]
        bsdfNode.inputs["Roughness"].default_value = 0.25

        bsdfNode.inputs["Specular Tint"].default_value = 0.75

        if color:
            diffuseColorNode.outputs["Color"].default_value = color[0:4]

        matLinks.new(diffuseColorNode.outputs["Color"], bsdfNode.inputs["Base Color"])
        matLinks.new(alphaNode.outputs["Value"], bsdfNode.inputs["Alpha"])

        setupAlphaScaledSpecular(mat)
    return mat

# The source is a path to an image file (e.g., .png) or a movie file (e.g., .avi).
def newShadelessImageMaterial(name, source):
    mat = bpy.data.materials.new(name=name)
    if bpy.app.version < (2, 80, 0):
        mat.use_shadeless = True
        mat.use_transparency = True
        mat.use_shadows = False
        mat.use_cast_shadows = False
        mat.use_transparent_shadows = False

        tex = bpy.data.textures.new("Texture." + name, type="IMAGE")
        img = bpy.data.images.load(source)
        tex.image = img

        # The following settings improve the sharpness of the image somewhat.
        tex.use_interpolation = False
        tex.use_mipmap = False
        tex.filter_type = "BOX"
        tex.filter_size = 0.1

        mtex = mat.texture_slots.add()
        mtex.texture = tex
        mtex.mapping = "FLAT"
        mtex.texture_coords = "UV"

        if img.source == "MOVIE":
            duration = img.frame_duration
            # Due to a bug in Blender, a movie image's `frame_duration` must be called twice
            # to get the correct value.
            duration = img.frame_duration
            tex.image_user.frame_duration = duration

            tex.image_user.frame_offset = 0
            tex.image_user.use_auto_refresh = True
    else:
        mat.blend_method = "HASHED"
        mat.shadow_method = "NONE"

        mat.use_nodes = True
        matNodes = mat.node_tree.nodes
        matLinks = mat.node_tree.links

        matNodes.remove(matNodes["Principled BSDF"])

        # TODO: use diffuseColorNode to tint the image/movie?
        alphaNode, diffuseColorNode = setupMaterialAttributeNodes(mat)

        texImageNode = mat.node_tree.nodes.new("ShaderNodeTexImage")
        texImageNode.name = "texImage"
        # It seems to be necessary to have an absolute path to the image/movie.
        texImageNode.image = bpy.data.images.load(os.path.abspath(source))

        if texImageNode.image.source == "MOVIE":
            duration = texImageNode.image.frame_duration
            # Due to a bug in Blender, a movie image's `frame_duration` must be called twice
            # to get the correct value.
            duration = texImageNode.image.frame_duration
            texImageNode.image_user.frame_duration = duration

            texImageNode.image_user.frame_offset = 0
            texImageNode.image_user.use_auto_refresh = True

        backgroundNode = matNodes.new("ShaderNodeBsdfTransparent")
        backgroundNode.name = "background"

        lightPathNode = matNodes.new("ShaderNodeLightPath")
        lightPathNode.name = "lightPath"

        alphaXLightPathNode = matNodes.new("ShaderNodeMath")
        alphaXLightPathNode.name = "alphaXLightPath"
        alphaXLightPathNode.operation = "MULTIPLY"
        alphaXLightPathNode.use_clamp = True
        matLinks.new(lightPathNode.outputs["Is Camera Ray"], alphaXLightPathNode.inputs[0])
        matLinks.new(alphaNode.outputs["Value"], alphaXLightPathNode.inputs[1])

        mixNode = matNodes.new("ShaderNodeMixShader")
        mixNode.name = "mix"
        matLinks.new(alphaXLightPathNode.outputs["Value"], mixNode.inputs["Fac"])
        matLinks.new(backgroundNode.outputs["BSDF"], mixNode.inputs[1])
        matLinks.new(texImageNode.outputs["Color"], mixNode.inputs[2])

        outputNode = matNodes["Material Output"]
        matLinks.new(mixNode.outputs["Shader"], outputNode.inputs["Surface"])
    return mat

def newGlowingMaterial(name, color):
    mat = bpy.data.materials.new(name=name)
    if bpy.app.version < (2, 80, 0):
        if color:
            mat.diffuse_color = color[0:3]
        mat.use_transparency = True

        # Make it "glow" like it is emitting light, which really just gives it
        # a brighter version of its color.
        mat.emit = 0.5
        mat.specular_intensity = 0
    else:
        # The transparency settings that work well with `newBasicMaterial` work well here, too.
        mat.blend_method = "HASHED"
        mat.shadow_method = "HASHED"

        mat.use_nodes = True
        matNodes = mat.node_tree.nodes
        matLinks = mat.node_tree.links

        alphaNode, diffuseColorNode = setupMaterialAttributeNodes(mat)
        bsdfNode = matNodes["Principled BSDF"]

        matLinks.new(diffuseColorNode.outputs["Color"], bsdfNode.inputs["Base Color"])
        matLinks.new(diffuseColorNode.outputs["Color"], bsdfNode.inputs["Emission"])
        matLinks.new(alphaNode.outputs["Value"], bsdfNode.inputs["Alpha"])

        bsdfNode.inputs["Emission Strength"].default_value = 0.5
        if color:
            diffuseColorNode.outputs["Color"].default_value = color[0:4]

        setupAlphaScaledSpecular(mat)
    return mat

def newSilhouetteMaterial(name, exp=5):
    mat = bpy.data.materials.new(name=name)
    if bpy.app.version < (2, 80, 0):
        # Enable the transparency of the ROI away from its silhouette.
        mat.use_transparency = True
        mat.alpha = 0.5

        # Do not involve the ROI in any aspect of shadows.
        mat.use_shadows = False
        mat.use_cast_shadows = False
        mat.use_transparent_shadows = False

        if exp > 0:
            # Do not apply lighting to the ROI; just use the silhouette calculation.
            mat.use_shadeless = True

            # Set up the silhouette material for ROIs.

            mat.use_nodes = True
            matNodes = mat.node_tree.nodes
            matLinks = mat.node_tree.links

            matNode = matNodes["Material"]
            outputNode = matNodes["Output"]

            # Make the "Material" node use the non-node material being used
            # to preview in the UI's 3D View, so its animated alpha can be
            # reused as an input to alphaNode, below.  Thus we can preview
            # the animation in the 3D View and also see it in the final render.

            matNode.material = mat

            geomNode = matNodes.new("ShaderNodeGeometry")
            geomNode.name = "geom"

            dotNode = matNodes.new("ShaderNodeVectorMath")
            dotNode.name = "dot"
            dotNode.operation = "DOT_PRODUCT"
            matLinks.new(geomNode.outputs["View"], dotNode.inputs[0])
            matLinks.new(geomNode.outputs["Normal"], dotNode.inputs[1])

            absNode = matNodes.new("ShaderNodeMath")
            absNode.name = "abs"
            absNode.operation = "ABSOLUTE"
            matLinks.new(dotNode.outputs["Value"],absNode.inputs[0])

            negNode = matNodes.new("ShaderNodeMath")
            negNode.name = "neg"
            negNode.operation = "SUBTRACT"
            negNode.inputs[0].default_value = 1
            matLinks.new(absNode.outputs["Value"], negNode.inputs[1])

            powNode = matNodes.new("ShaderNodeMath")
            powNode.name = "pow"
            powNode.operation = "POWER"
            matLinks.new(negNode.outputs["Value"], powNode.inputs[0])
            powNode.inputs[1].default_value = exp

            # Multiply in the animated alpha from the non-node material, above.
            # But note that alpha is the value needed for "SOLID" mode viewport
            # rendering, which is lower.  So scale it up before multiplying with
            # the silhouette alpha.

            alphaGainNode = matNodes.new("ShaderNodeMath")
            alphaGainNode.name = "alphaShift"
            alphaGainNode.operation = "MULTIPLY"
            alphaGainNode.inputs[0].default_value = 6 # 4
            matLinks.new(matNode.outputs["Alpha"], alphaGainNode.inputs[1])

            alphaCombineNode = matNodes.new("ShaderNodeMath")
            alphaCombineNode.name = "alphaCombine"
            alphaCombineNode.operation = "MULTIPLY"
            matLinks.new(alphaGainNode.outputs["Value"], alphaCombineNode.inputs[0])
            matLinks.new(powNode.outputs["Value"], alphaCombineNode.inputs[1])

            matLinks.new(alphaCombineNode.outputs["Value"], outputNode.inputs["Alpha"])
        else:
            # A negative exponent gives simple surface shading instead of the silhouette.
            mat.specular_intensity = 0
    else:
        # We want to see silhouette edges that come from back faces, too.  So turning on
        # what the UI calls the "Alpha Blend" blend method ("BLEND") gives better results
        # than the "Alpha Hashed" blend method ("HASHED").  "BLEND" does not show noise
        # even with a relatively low number of samples, while "HASHED" looks right only
        # with a large number of samples, which hurts peformance.  Note that with "BLEND"
        # for silhouettes, it is important to have `use_backface_culling = False` and
        # `show_transparent_back = True`.
        # But note that a current limitation of Blender's Eevee renderer is that "BLEND"
        # materials are ignored in all passes other than the basic "combined" pass.
        # So for depth compositing, render.py will change theses materials to "HASHED".
        mat.blend_method = "BLEND"
        mat.use_backface_culling = False
        mat.show_transparent_back = True

        mat.shadow_method = "NONE"

        mat.use_nodes = True
        matNodes = mat.node_tree.nodes
        matLinks = mat.node_tree.links

        alphaNode, diffuseColorNode = setupMaterialAttributeNodes(mat)
        
        if exp > 0:
            matNodes.remove(matNodes["Principled BSDF"])
            outputNode = matNodes["Material Output"]

            geomNode = matNodes.new("ShaderNodeNewGeometry")
            geomNode.name = "geom"

            dotNode = matNodes.new("ShaderNodeVectorMath")
            dotNode.name = "dot"
            dotNode.operation = "DOT_PRODUCT"
            matLinks.new(geomNode.outputs["Incoming"], dotNode.inputs[0])
            matLinks.new(geomNode.outputs["Normal"], dotNode.inputs[1])

            absNode = matNodes.new("ShaderNodeMath")
            absNode.name = "abs"
            absNode.operation = "ABSOLUTE"
            matLinks.new(dotNode.outputs["Value"],absNode.inputs[0])

            negNode = matNodes.new("ShaderNodeMath")
            negNode.name = "neg"
            negNode.operation = "SUBTRACT"
            negNode.inputs[0].default_value = 1
            matLinks.new(absNode.outputs["Value"], negNode.inputs[1])

            powNode = matNodes.new("ShaderNodeMath")
            powNode.name = "pow"
            powNode.operation = "POWER"
            matLinks.new(negNode.outputs["Value"], powNode.inputs[0])
            powNode.inputs[1].default_value = exp

            lightPathNode = matNodes.new("ShaderNodeLightPath")
            lightPathNode.name = "lightPath"

            powXLightPathNode = matNodes.new("ShaderNodeMath")
            powXLightPathNode.name = "powXLightPath"
            powXLightPathNode.operation = "MULTIPLY"
            matLinks.new(powNode.outputs["Value"], powXLightPathNode.inputs[0])
            matLinks.new(lightPathNode.outputs["Is Camera Ray"], powXLightPathNode.inputs[1])

            # This increase in the alpha worked well in the 2.79 version, so use it here, too.
            alphaGainNode = matNodes.new("ShaderNodeMath")
            alphaGainNode.name = "alphaGain"
            alphaGainNode.operation = "MULTIPLY"
            alphaGainNode.inputs[0].default_value = 6 # 4
            matLinks.new(alphaNode.outputs["Value"], alphaGainNode.inputs[1])

            alphaXPowXLightPathNode = matNodes.new("ShaderNodeMath")
            alphaXPowXLightPathNode.name = "alphaXPowXLightPath"
            alphaXPowXLightPathNode.operation = "MULTIPLY"
            matLinks.new(powXLightPathNode.outputs["Value"], alphaXPowXLightPathNode.inputs[0])
            matLinks.new(alphaGainNode.outputs["Value"], alphaXPowXLightPathNode.inputs[1])

            backgroundNode = matNodes.new("ShaderNodeBsdfTransparent")
            backgroundNode.name = "background"

            mixNode = matNodes.new("ShaderNodeMixShader")
            mixNode.name = "mix"
            matLinks.new(alphaXPowXLightPathNode.outputs["Value"], mixNode.inputs["Fac"])
            matLinks.new(backgroundNode.outputs["BSDF"], mixNode.inputs[1])
            matLinks.new(diffuseColorNode.outputs["Color"], mixNode.inputs[2])

            matLinks.new(mixNode.outputs["Shader"], outputNode.inputs["Surface"])
        else:
            # A negative exponent gives simple surface shading instead of the silhouette.
            bsdfNode = matNodes["Principled BSDF"]
            matLinks.new(diffuseColorNode.outputs["Color"], bsdfNode.inputs["Base Color"])
            matLinks.new(alphaNode.outputs["Value"], bsdfNode.inputs["Alpha"])
            bsdfNode.inputs["Specular"].default_value = 0
    return mat
