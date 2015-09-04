# BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Matalogue",
    "description": " Catalogue of node trees in the toolbar to switch between quickly",
    "author": "Greg Zaal",
    "version": (1, 0),
    "blender": (2, 75, 0),
    "location": "Node Editor > Tools",
    "warning": "",
    "wiki_url": "https://github.com/gregzaal/Matalogue",
    "tracker_url": "https://github.com/gregzaal/Matalogue/issues",
    "category": "Node"}

import bpy


'''
TODOs:
    Option to list only visible layers
    Show list of groups
    Assign material to selected objects
    Recenter view (don't change zoom) (add preference to disable) - talk to devs about making space_data.edit_tree.view_center editable
    User preference for which panels are collapsed/expanded by default
    Create new material and optionally...
        assign to selected objects
        duplicate from active
'''


class MatalogueSettings(bpy.types.PropertyGroup):
    expand_mat_options = bpy.props.BoolProperty(
        name="Options",
        default=False,
        description="Show settings for controlling which materials are listed")

    selected_only = bpy.props.BoolProperty(
        name="Selected Objects Only",
        default=False,
        description="Only show materials used by objects that are selected")

    all_scenes = bpy.props.BoolProperty(
        name="All Scenes",
        default=False,
        description="Show materials from all the scenes (not just the current one). (\"Selected Objects Only\" must be disabled)")

    show_zero_users = bpy.props.BoolProperty(
        name="0-User Materials",
        default=False,
        description="Also show materials that have no users. (\"All Scenes\" must be enabled)")


#####################################################################
# Functions
#####################################################################

def material_in_cur_scene(mat):
    scene = bpy.context.scene
    for obj in scene.objects:
        if obj.name != "Matalogue Dummy Object":
            for slot in obj.material_slots:
                if slot.material == mat:
                    return True
    return False

def material_on_sel_obj(mat):
    selection = bpy.context.selected_objects
    for obj in selection:
        if obj.name != "Matalogue Dummy Object":
            for slot in obj.material_slots:
                if slot.material == mat:
                    return True
    return False

def get_materials():
    settings = bpy.context.window_manager.matalogue_settings
    materials = []
    for mat in bpy.data.materials:
        conditions = [
            (settings.show_zero_users or mat.users),
            (settings.all_scenes or material_in_cur_scene(mat)),
            (not settings.selected_only or material_on_sel_obj(mat)),
            not mat.library,  # don't allow editing of linked library materials - TODO make this optional (can help to be able to look at the nodes, even if you can't edit it)
            mat.vray.ntree]
        if all(conditions):
            materials.append(mat)

    return materials

def dummy_object(delete=False):
    ''' Return the existing dummy object, or create one if it doesn't exist. '''
    scene = bpy.context.scene

    if delete:
        for obj in scene.objects:
            if "Matalogue Dummy Object" in obj.name:
                scene.objects.unlink(obj)
        return "DONE"
    
    dummy = None
    previous_dummy = [obj for obj in bpy.data.objects if obj.name == "Matalogue Dummy Object"]
    if previous_dummy:
        dummy = previous_dummy[0]
    else:
        m = bpy.data.meshes.new("Matalogue Dummy Mesh")
        dummy = bpy.data.objects.new("Matalogue Dummy Object", m)

    if dummy not in list(obj for obj in scene.objects):
        scene.objects.link(dummy)

    dummy.select = True
    scene.objects.active = dummy

    if len(dummy.material_slots) == 0:
        bpy.ops.object.material_slot_add()
        
    return dummy


#####################################################################
# Operators
#####################################################################

class TLGoToMat(bpy.types.Operator):

    'Show the nodes for this material'
    bl_idname = 'matalogue.goto_mat'
    bl_label = 'Go To Material'
    mat = bpy.props.StringProperty(default = "")

    def execute(self, context):
        dummy_object(delete=True)
        scene = context.scene
        context.space_data.tree_type = 'VRayNodeTreeMaterial'
        context.space_data.shader_type = 'OBJECT'
        mat = bpy.data.materials[self.mat]

        objs_with_mat = 0
        active_set = False
        for obj in scene.objects:
            obj_materials = [slot.material for slot in obj.material_slots]
            if mat in obj_materials:
                objs_with_mat += 1
                obj.select = True
                if not active_set:  # set first object as active
                    active_set = True
                    scene.objects.active = obj
                    if mat != obj.active_material:
                        for i, x in enumerate(obj.material_slots):
                            if x.material == mat:
                                obj.active_material_index = i
                                break
            else:
                obj.select = False

        if objs_with_mat == 0:
            self.report({'WARNING'}, "No objects in this scene use '" + mat.name + "' material")
            dummy = dummy_object()
            slot = dummy.material_slots[0]
            slot.material = mat

        return {'FINISHED'}


class TLGoToLight(bpy.types.Operator):

    'Show the nodes for this material'
    bl_idname = 'matalogue.goto_light'
    bl_label = 'Go To Material'
    light = bpy.props.StringProperty(default = "")
    world = bpy.props.BoolProperty(default = False)

    def execute(self, context):
        #print ("Light1=",self.light)
        dummy_object(delete=True)
        scene = context.scene
        context.space_data.tree_type = 'VRayNodeTreeLight'
        if self.world:
            context.space_data.tree_type = 'VRayNodeTreeWorld'
            context.space_data.shader_type = 'WORLD'
        else:
            context.space_data.shader_type = 'OBJECT'
            light = bpy.data.objects[self.light]
            scene.objects.active = light
            #print ("Light2=",light)

        return {'FINISHED'}

class TLGoToObject(bpy.types.Operator):

    'Show the nodes for this material'
    bl_idname = 'matalogue.goto_object'
    bl_label = 'Go To Material'
    obj = bpy.props.StringProperty(default = "")
    world = bpy.props.BoolProperty(default = False)

    def execute(self, context):
        #print ("self",self.obj)
        dummy_object(delete=True)
        scene = context.scene
        context.space_data.tree_type = 'VRayNodeTreeObject'
        if self.world:
            context.space_data.shader_type = 'WORLD'
        else:
            context.space_data.shader_type = 'OBJECT'
            obj = bpy.data.objects[self.obj]
            scene.objects.active = obj
            #print ("self",self)
            #print ("self.world",self.world)

        return {'FINISHED'}

class TLGoToComp(bpy.types.Operator):

    'Show the nodes for this material'
    bl_idname = 'matalogue.goto_comp'
    bl_label = 'Go To Composite'
    scene = bpy.props.StringProperty(default = "")

    def execute(self, context):
        context.space_data.tree_type = 'CompositorNodeTree'
        scene = bpy.data.scenes[self.scene]
        context.screen.scene = scene

        return {'FINISHED'}


#####################################################################
# UI
#####################################################################

class MatalogueMaterials(bpy.types.Panel):

    bl_label = "Materials"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "TOOLS"
    bl_category = "Trees"

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine[:4] == 'VRAY'

    def draw(self, context):
        settings = context.window_manager.matalogue_settings
        scene = context.scene
        layout = self.layout
        materials = get_materials()

        col = layout.column(align=True)

        for mat in materials:
            name = mat.name
            try:
                icon_val = layout.icon(mat)
            except:
                icon_val = 1
                print ("WARNING [Mat Panel]: Could not get icon value for %s" % name)
            if mat.users:
                op = col.operator('matalogue.goto_mat', text=name, emboss=(mat==context.space_data.id), icon_value=icon_val)
                #op = col.operator('matalogue.goto_mat', text=name,  icon_value=icon_val)
                #print ("mat =",mat)
                op.mat = name
            else:
                row = col.row(align=True)
                op = row.operator('matalogue.goto_mat', text=name, emboss=(mat==context.space_data.id), icon_value=icon_val)
                op.mat = name
                op = row.operator('matalogue.goto_mat', text="", emboss=(mat==context.space_data.id), icon='ERROR')
                op.mat = name

        if not materials:
            col.label("Nothing to show!")

        col = layout.column(align=True)

        box = col.box()
        scol = box.column(align=True)
        scol.prop(settings, 'expand_mat_options', toggle=True, icon='TRIA_DOWN' if settings.expand_mat_options else 'TRIA_RIGHT')
        if settings.expand_mat_options:
            scol.prop(settings, "selected_only")
            r = scol.row()
            r.enabled = not settings.selected_only
            r.prop(settings, "all_scenes")
            r = scol.row()
            r.enabled = (settings.all_scenes and not settings.selected_only)
            r.prop(settings, "show_zero_users")


class MatalogueLighting(bpy.types.Panel):

    bl_label = "Lighting"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "TOOLS"
    bl_category = "Trees"

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine[:4] == 'VRAY'

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        lights = [obj for obj in scene.objects if obj.type == 'LAMP']

        col = layout.column(align=True)

        for light in lights:
            #if light.data.use_nodes:
            if light.data.vray.ntree:
                name = light.name
                op = col.operator('matalogue.goto_light', text=name, emboss=(light.data==context.space_data.id), icon='LAMP_%s' % light.data.type)
                op.light = name
                op.world = False

        if bpy.context.scene.world.vray.ntree:
            op = col.operator('matalogue.goto_light', text="World", emboss=(context.scene.world==context.space_data.id), icon='VRAY_WORLD')
            op.world = True

class MatalogueObject(bpy.types.Panel):

    bl_label = "Object"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "TOOLS"
    bl_category = "Trees"

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine[:4] == 'VRAY'

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        objects = [obj for obj in scene.objects if obj.type == 'MESH']

        col = layout.column(align=True)

        for obj in objects:
            #if light.data.use_nodes:
            if obj.vray.ntree:
                name = obj.name
                op = col.operator('matalogue.goto_object', text=name, emboss=(obj.data==context.space_data.id), icon='VRAY_OBJECT')
                op.obj = name
                op.world = False

      
class MatalogueCompositing(bpy.types.Panel):

    bl_label = "Compositing"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "TOOLS"
    bl_category = "Trees"

    def draw(self, context):
        scenes = bpy.data.scenes
        layout = self.layout

        col = layout.column(align=True)

        for sc in scenes:
            name = sc.name
            op = col.operator('matalogue.goto_comp', text=name, emboss=(sc==context.space_data.id), icon='RENDERLAYERS')
            op.scene = name


#####################################################################
# Registration
#####################################################################

def register():
    bpy.utils.register_module(__name__)

    bpy.types.WindowManager.matalogue_settings = bpy.props.PointerProperty(type=MatalogueSettings)

def unregister():
    del bpy.types.WindowManager.matalogue_settings

    bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()
