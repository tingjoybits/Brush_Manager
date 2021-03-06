# ##### BEGIN GPL LICENSE BLOCK #####
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENCE BLOCK #####

import bpy
import os
import sys
import subprocess
import json
import bpy.utils.previews
from bpy.app.handlers import persistent
from bpy.types import Operator, Menu, Panel, PropertyGroup, AddonPreferences, Scene, WindowManager, BlendData
from bpy.props import *
import rna_keymap_ui
from bl_ui import space_toolsystem_common, space_toolsystem_toolbar

try:
    Addon_Name = __name__.split('.')[1]
except IndexError:
    Addon_Name = __name__


def prefs():
    return bpy.context.preferences.addons[Addon_Name].preferences


MODE = None
UI_MODE = False
START_FAV_LOADED = {}
FAV_SETTINGS_LOADED = {}
IS_INIT_SMEAR = {}

SET_DEFAULT_ICONS = {}
CURRENT_MODE_CATEGORY = {}

BRUSHES_SCULPT_NAMES = [
    'Blob', 'Clay', 'Clay Strips', 'Clay Thumb', 'Cloth',
    'Crease', 'Draw Face Sets', 'Draw Sharp', 'Elastic Deform',
    'Fill/Deepen', 'Flatten/Contrast', 'Grab', 'Inflate/Deflate',
    'Layer', 'Mask', 'Multi-plane Scrape', 'Nudge', 'Pinch/Magnify',
    'Pose', 'Rotate', 'Scrape/Peaks', 'SculptDraw', 'Simplify',
    'Slide Relax', 'Smooth', 'Snake Hook', 'Thumb'
]
BRUSHES_IPAINT_NAMES = ['Clone', 'Fill', 'Mask', 'Smear', 'Soften', 'TexDraw']

BRUSHES_GPAINT_NAMES = [
    'Airbrush', 'Eraser Hard', 'Eraser Point', 'Eraser Soft',
    'Eraser Stroke', 'Fill Area', 'Ink Pen', 'Ink Pen Rough', 'Marker Bold',
    'Marker Chisel', 'Pen', 'Pencil', 'Pencil Soft', 'Tint'
]
# print([b.name for b in bpy.data.brushes if b.use_paint_weight])
BRUSHES_WPAINT_NAMES = [
    'Add', 'Average', 'Blur', 'Darken', 'Draw', 'Lighten', 'Mix', 'Multiply', 'Subtract',
    'Smear Weight'
]
BRUSHES_VPAINT_NAMES = [
    'Add', 'Average', 'Blur', 'Darken', 'Draw', 'Lighten', 'Mix', 'Multiply', 'Subtract',
    'Smear Vertex',
]
# use_vertex_grease_pencil
BRUSHES_GVERTEX_NAMES = [
    'Vertex Average', 'Vertex Blur', 'Vertex Draw', 'Vertex Replace', 'Vertex Smear'
]


def collect_tools(mode):
    b_tools = []
    o_tools = []
    tools = space_toolsystem_toolbar.VIEW3D_PT_tools_active.tools_from_context(None, mode)
    for item in tools:
        if item is None:
            continue
        if type(item) is tuple:
            for subitem in item:
                o_tools.append(subitem.label)
            continue
        if item.idname.startswith("builtin_brush"):
            b_tools.append(item.label)
        else:
            o_tools.append(item.label)
    b_tools.sort()
    return b_tools, o_tools


BRUSHES_SCULPT, TOOLS_SCULPT = collect_tools('SCULPT')
BRUSHES_IPAINT, TOOLS_IPAINT = collect_tools('PAINT_TEXTURE')
BRUSHES_GPAINT, TOOLS_GPAINT = collect_tools('PAINT_GPENCIL')
BRUSHES_WPAINT, TOOLS_WPAINT = collect_tools('PAINT_WEIGHT')
BRUSHES_VPAINT, TOOLS_VPAINT = collect_tools('PAINT_VERTEX')
BRUSHES_GVERTEX, TOOLS_GVERTEX = collect_tools('VERTEX_GPENCIL')


def evaluate_brush_tools(brushes, mode=''):
    if not mode:
        mode = MODE
    brush_tool_names = []
    for t_label in brushes:
        found = False
        if mode == 'SCULPT':
            if t_label == 'Draw':
                brush_tool_names.append((t_label, 'SculptDraw'))
                continue
            for brush in BRUSHES_SCULPT_NAMES:
                if brush.split('/')[0] == t_label:
                    brush_tool_names.append((t_label, brush))
                    found = True
                    break
            if not found:
                brush_tool_names.append((t_label, t_label))
        elif mode == 'PAINT_TEXTURE':
            if t_label == 'Draw':
                brush_tool_names.append((t_label, 'TexDraw'))
                continue
            brush_tool_names.append((t_label, t_label))
        elif mode == 'PAINT_WEIGHT':
            if t_label == 'Smear':
                brush_tool_names.append((t_label, 'Smear Weight'))
                continue
            brush_tool_names.append((t_label, t_label))
        elif mode == 'PAINT_VERTEX':
            if t_label == 'Smear':
                brush_tool_names.append((t_label, 'Smear Vertex'))
                continue
            brush_tool_names.append((t_label, t_label))
        elif mode == 'VERTEX_GPENCIL':
            brush_tool_names.append((t_label, 'Vertex ' + t_label))
        else:
            brush_tool_names.append((t_label, t_label))
    return brush_tool_names


def update_pref_def_brush(self, context, mode=''):
    if not mode:
        mode = self.pref_tabs
    # props = context.window_manager.brush_manager_props
    default_brushes = get_default_brushes_list(mode=mode)
    pref_def_brushes = get_pref_default_brush_props(mode=mode)
    icons_path = get_icons_path(mode)
    if not self.modes.Modes[mode].get('has_themes'):
        icons_path = os.path.join(icons_path, 'custom_icons')
    for brush in default_brushes:
        if pref_def_brushes.get(brush):
            if not SET_DEFAULT_ICONS.get(mode):
                continue
            set_custom_icon(context, icons_path, brush)
            continue
        try:
            bpy.data.brushes[brush].use_custom_icon = False
            # bpy.data.brushes[brush].icon_filepath = ''
        except KeyError:
            pass
    update_brush_list(self, context)


def update_pref_def_s_brush(self, context):
    update_pref_def_brush(self, context, mode='SCULPT')


def update_pref_def_wp_brush(self, context):
    update_pref_def_brush(self, context, mode='PAINT_WEIGHT')


def update_pref_def_vp_brush(self, context):
    update_pref_def_brush(self, context, mode='PAINT_VERTEX')


def update_pref_def_gv_brush(self, context):
    update_pref_def_brush(self, context, mode='VERTEX_GPENCIL')


class BM_Modes:
    in_modes = [
        'SCULPT',
        'PAINT_TEXTURE',
        'PAINT_WEIGHT',
        'PAINT_VERTEX',
        'PAINT_GPENCIL',
        'VERTEX_GPENCIL',
    ]

    def __init__(self, context_mode=''):
        if MODE:
            self.mode = MODE
        else:
            self.mode = 'SCULPT'
        if UI_MODE:
            self.mode = 'PAINT_TEXTURE'
        if context_mode != '':
            self.mode = context_mode
        self.mode_prefixes = {
            'SCULPT': 's',
            'PAINT_TEXTURE': 'ip',
            'PAINT_WEIGHT': 'wp',
            'PAINT_VERTEX': 'vp',
            'PAINT_GPENCIL': 'gp',
            'VERTEX_GPENCIL': 'gv'
        }
        self.Modes = dict(
            SCULPT={
                'tool_settings': 'sculpt',  # context.tool_settings
                'brush_tool': 'sculpt_tool',
                'brush_use_mode': 'use_paint_sculpt',
                'fav_settings': 'bm_favorite_list_settings',
                'fav_store': 'bm_sculpt_fav_list_store',
                'icons_folder': 'icon_themes',
                'has_themes': True,
                'def_brushes_tool_list': BRUSHES_SCULPT,
                'other_tools_list': TOOLS_SCULPT,
                'def_brush_names': BRUSHES_SCULPT_NAMES,
                'is_split_tools': False,
                'use_custom_icons': True,
                'default_custom_icons': 'default_brushes_custom_icon',
            },
            PAINT_TEXTURE={
                'tool_settings': 'image_paint',
                'brush_tool': 'image_tool',
                'brush_use_mode': 'use_paint_image',
                'fav_settings': 'bm_paint_favorite_settings',
                'fav_store': 'bm_paint_fav_list_store',
                'icons_folder': 'paint_icons',
                'has_themes': False,
                'def_brushes_tool_list': BRUSHES_IPAINT,
                'other_tools_list': TOOLS_IPAINT,
                'def_brush_names': BRUSHES_IPAINT_NAMES,
                'is_split_tools': False,
                'use_custom_icons': False,
                'default_custom_icons': False,
            },
            PAINT_GPENCIL={
                'tool_settings': 'gpencil_paint',
                'brush_tool': 'gpencil_tool',
                'brush_use_mode': 'use_paint_grease_pencil',
                'fav_settings': 'bm_gpaint_favorite_settings',
                'fav_store': 'bm_gpaint_fav_list_store',
                'icons_folder': 'gpaint_icons',
                'has_themes': False,
                'def_brushes_tool_list': BRUSHES_GPAINT,
                'other_tools_list': TOOLS_GPAINT,
                'def_brush_names': BRUSHES_GPAINT_NAMES,
                'is_split_tools': True,  # if brush tool has more default brushes than one
                'use_custom_icons': False,
                'default_custom_icons': False,
            },
            PAINT_WEIGHT={
                'tool_settings': 'weight_paint',
                'brush_tool': 'weight_tool',
                'brush_use_mode': 'use_paint_weight',
                'fav_settings': 'bm_wpaint_favorite_settings',
                'fav_store': 'bm_wpaint_fav_list_store',
                'icons_folder': 'wpaint_icons',
                'has_themes': False,
                'def_brushes_tool_list': BRUSHES_WPAINT,
                'other_tools_list': TOOLS_WPAINT,
                'def_brush_names': BRUSHES_WPAINT_NAMES,
                'is_split_tools': True,
                'use_custom_icons': True,
                'default_custom_icons': 'default_wp_brushes_custom_icon',
            },
            PAINT_VERTEX={
                'tool_settings': 'vertex_paint',
                'brush_tool': 'vertex_tool',
                'brush_use_mode': 'use_paint_vertex',
                'fav_settings': 'bm_vpaint_favorite_settings',
                'fav_store': 'bm_vpaint_fav_list_store',
                'icons_folder': 'vpaint_icons',
                'has_themes': False,
                'def_brushes_tool_list': BRUSHES_VPAINT,
                'other_tools_list': TOOLS_VPAINT,
                'def_brush_names': BRUSHES_VPAINT_NAMES,
                'is_split_tools': True,
                'use_custom_icons': True,
                'default_custom_icons': 'default_vp_brushes_custom_icon',
            },
            VERTEX_GPENCIL={
                'tool_settings': 'gpencil_vertex_paint',
                'brush_tool': 'gpencil_vertex_tool',
                'brush_use_mode': 'use_vertex_grease_pencil',
                'fav_settings': 'bm_gvertex_favorite_settings',
                'fav_store': 'bm_gvertex_fav_list_store',
                'icons_folder': 'vpaint_icons',
                'has_themes': False,
                'def_brushes_tool_list': BRUSHES_GVERTEX,
                'other_tools_list': TOOLS_GVERTEX,
                'def_brush_names': BRUSHES_GVERTEX_NAMES,
                'is_split_tools': False,
                'use_custom_icons': True,
                'default_custom_icons': 'default_gv_brushes_custom_icon',
            },
        )
        for im in self.in_modes:
            m = self.mode_prefixes.get(im)
            similar_props = {
                'pref_brush': 'default_' + m + '_brush_',
                'pref_tool': m + '_tool_brush_',
                'pref_other_tool': m + '_tool_',
                'use_startup_favorites': 'use_' + m + '_startup_favorites',
                'path_to_startup_favorites': 'path_to_' + m + '_startup_favorites',
                'brush_library': m + '_brush_library',
                'wide_popup_layout': 'wide_' + m + '_popup_layout',
                'wide_popup_layout_size': 'wide_' + m + '_popup_layout_size',
                'popup_max_tool_columns': 'popup_' + m + '_max_tool_columns',
                'popup_width': 'popup_' + m + '_width',
                'preview_frame_scale': 'preview_' + m + '_frame_scale',
                'popup_items_scale': 'popup_' + m + '_items_scale',
            }
            self.Modes[im].update(similar_props)

    def popup_items_scale(self):
        prefs = bpy.context.preferences.addons[Addon_Name].preferences
        return eval('prefs.' + self.Modes[self.mode].get('popup_items_scale'))

    def preview_frame_scale(self):
        prefs = bpy.context.preferences.addons[Addon_Name].preferences
        return eval('prefs.' + self.Modes[self.mode].get('preview_frame_scale'))

    def popup_width(self):
        prefs = bpy.context.preferences.addons[Addon_Name].preferences
        return eval('prefs.' + self.Modes[self.mode].get('popup_width'))

    def popup_max_tool_columns(self):
        prefs = bpy.context.preferences.addons[Addon_Name].preferences
        return eval('prefs.' + self.Modes[self.mode].get('popup_max_tool_columns'))

    def wide_popup_layout_size(self):
        prefs = bpy.context.preferences.addons[Addon_Name].preferences
        return eval('prefs.' + self.Modes[self.mode].get('wide_popup_layout_size'))

    def wide_popup_layout(self):
        prefs = bpy.context.preferences.addons[Addon_Name].preferences
        return eval('prefs.' + self.Modes[self.mode].get('wide_popup_layout'))

    def tool_settings(self, context):
        ts = context.tool_settings
        return eval('ts.' + self.Modes[self.mode].get('tool_settings'))

    def brush_tool(self, brush):
        return eval('brush.' + self.Modes[self.mode].get('brush_tool'))

    def brush_use_mode(self, brush):
        return eval('brush.' + self.Modes[self.mode].get('brush_use_mode'))

    def def_brushes_tool_list(self):
        return self.Modes[self.mode].get('def_brushes_tool_list')

    def def_brushes_list(self):
        if not self.mode:
            return None
        if self.Modes[self.mode].get('is_split_tools'):
            return self.Modes[self.mode].get('def_brush_names')
        return [b for t, b in evaluate_brush_tools(self.def_brushes_tool_list(), self.mode)]

    def pref_brush(self):
        return self.Modes[self.mode].get('pref_brush')

    def pref_tool(self, t_type='brush'):
        if t_type == 'brush':
            return self.Modes[self.mode].get('pref_tool')
        elif t_type == 'other':
            return self.Modes[self.mode].get('pref_other_tool')

    def brush_tool_enum_items(self):
        enum_items = []
        for brush in bpy.data.brushes:
            if self.brush_use_mode(brush):
                enum_items = brush.bl_rna.properties[
                    self.Modes[self.mode].get('brush_tool')].enum_items
                break
        return enum_items

    def use_startup_favorites(self):
        prefs = bpy.context.preferences.addons[Addon_Name].preferences
        return eval('prefs.' + self.Modes[self.mode].get('use_startup_favorites'))

    def path_to_startup_favorites(self):
        prefs = bpy.context.preferences.addons[Addon_Name].preferences
        return eval('prefs.' + self.Modes[self.mode].get('path_to_startup_favorites'))

    def icons_path(self):
        prefs = bpy.context.preferences.addons[Addon_Name].preferences
        folder = self.Modes[self.mode].get('icons_folder')
        icons_path = get_icon_themes_path(folder)
        if self.Modes[self.mode].get('has_themes'):
            icons_path = os.path.join(icons_path, prefs.brush_icon_theme)
        return icons_path

    def fav_settings(self):
        if not self.mode:
            return None
        scene = bpy.context.scene
        return eval('scene.' + self.Modes[self.mode].get('fav_settings'))

    def fav_store(self):
        if not self.mode:
            return None
        wm = bpy.context.window_manager
        return eval('wm.' + self.Modes[self.mode].get('fav_store'))

    def library_path(self):
        prefs = bpy.context.preferences.addons[Addon_Name].preferences
        return eval('prefs.' + self.Modes[self.mode].get('brush_library'))


def text_lookup(find_string, source_text):
    if source_text.find(find_string) != -1:
        return True
    else:
        return False


def get_b_files(directory):
    if directory and os.path.exists(directory):
        b_files = []
        for fn in os.listdir(directory):
            if fn.lower().endswith(".blend"):
                b_files.append(fn)
    return b_files


def get_brushes_in_files(directory, b_files):
    brushes = []
    for name in b_files:
        filepath = os.path.join(directory, name)
        with bpy.data.libraries.load(filepath) as (data_from, data_to):
            for brush in data_from.brushes:
                brushes.append(brush)
    return brushes


def get_library_directory(context):
    props = context.window_manager.brush_manager_props
    prefs = bpy.context.preferences.addons[Addon_Name].preferences
    modes = BM_Modes()
    lib_path = modes.library_path()
    directory = os.path.join(lib_path, props.lib_categories)
    return directory


def get_active_brush(context):
    modes = BM_Modes()
    ts = modes.tool_settings(context)
    return ts.brush


def check_brush_type(brush, mode=''):
    if mode == '':
        mode = bpy.context.mode
    modes = BM_Modes(mode)
    return modes.brush_use_mode(brush)


def get_append_brushes(directory, b_files, default_brushes=False):
    brushes_append = []
    brushes_in_files = get_brushes_in_files(directory, b_files)
    def_brushes = get_default_brushes_list()
    for brush in brushes_in_files:
        if brush in def_brushes and not default_brushes:
            continue
        try:
            if not check_brush_type(bpy.data.brushes[brush], MODE):
                continue
        except KeyError:
                continue
        brushes_append.append(brush)
    brushes_append = list(set(brushes_append))
    brushes_append.sort()
    return brushes_append


def get_copy_number(name):
    name_digits = []
    brushes = get_current_file_brushes(MODE)
    check_name = '.'.join(name.split('.')[0:-1])
    if check_name == '':
        check_name = name
    for b in brushes:
        if b.startswith(check_name) and\
                len(check_name) == len('.'.join(b.split('.')[0:-1])):
            if b.split('.')[-1].isdigit():
                name_digits.append(b)
    name_digits.sort()
    if name_digits:
        return name_digits[-1]
    return False


def auto_rename(name):
    digits = '001'
    copy_number = get_copy_number(name)
    if copy_number:
        name = copy_number
    if name.split(".")[-1].isdigit():
        zeroes = ''
        for i in range(len(name.split('.')[-1])):
            if int(name.split('.')[-1][i]) > 0:
                digits = zeroes + str(int(name.split('.')[-1]) + 1)
                break
            else:
                zeroes += '0'
        return '.'.join(name.split('.')[0:-1]) + '.' + digits
    else:
        return name + '.' + digits


def append_brushes_from_a_file(filepath, default_brushes=False, duplicates='SKIP'):
    brushes = []
    brushes_to_rename = []
    duplicates_list = []
    def_brushes = get_default_brushes_list(mode=MODE)
    with bpy.data.libraries.load(filepath) as (data_from, data_to):
        for brush in data_from.brushes:
            if brush in def_brushes and not default_brushes:
                continue
            if brush not in bpy.data.brushes:
                data_to.brushes.append(brush)
                brushes.append(brush)
                continue
            elif duplicates == 'OVERWRITE':
                bpy.data.brushes.remove(bpy.data.brushes[brush], do_unlink=True)
                data_to.brushes.append(brush)
            elif duplicates == 'RENAME':
                b = bpy.data.brushes[brush]
                b.name = b.name + " {ORIGINAL}"
                data_to.brushes.append(brush)
                brushes_to_rename.append(brush)
                continue
            # !! Append even if the same brush is already exists
            brushes.append(brush)
    for br in brushes_to_rename:
        name = auto_rename(br)
        bpy.data.brushes[br].name = name
        brushes.append(name)
        bpy.data.brushes[br + " {ORIGINAL}"].name = br
    return brushes


def append_brushes_to_current_file(directory):
    brushes_in_files = []
    b_files = get_b_files(directory)
    for name in b_files:
        filepath = os.path.join(directory, name)
        brushes_in_files += append_brushes_from_a_file(filepath)
    return brushes_in_files


def set_first_preview_item(context, brushes_list, wm_enum_prop='main'):
    wm = context.window_manager
    props = wm.brush_manager_props

    props.skip_brush_set = True

    try:
        if wm_enum_prop == 'main':
            wm.brushes_in_files = brushes_list[0]
        if wm_enum_prop == 'fav':
            wm.brushes_in_favorites = brushes_list[0]
    except (TypeError, IndexError) as e:
        props.skip_brush_set = False


UPDATE_ICONS = False


def update_category(self, context):
    wm = bpy.context.window_manager
    props = wm.brush_manager_props
    if props.lib_categories == 'Default' and\
            context.mode == 'SCULPT' and not UI_MODE:
        create_default_sculpt_tools()
    set_ui_mode(context)
    update_brush_list(self, context)
    update_fav_list(self, context)
    if context.mode == 'SCULPT' and not UI_MODE:
        set_toggle_default_icons(context)


def update_brush_list(self, context):
    create_default_smear_tools()
    main_brushes = get_main_list_brushes(context)
    set_first_preview_item(context, main_brushes)
    b_preview_coll = preview_brushes_coll["main"]
    b_preview_coll.my_previews_dir = ""


def update_fav_list(self, context):
    fav_brushes = get_favorite_brushes()
    set_first_preview_item(context, fav_brushes, wm_enum_prop='fav')
    b_preview_coll = preview_brushes_coll["favorites"]
    b_preview_coll.my_previews_dir = ""


def lib_category_folders(self, context):
    prefs = context.preferences.addons[Addon_Name].preferences
    modes = BM_Modes()
    lib_path = modes.library_path()
    default_list = ['Default', 'Current File']
    folders = get_folders_contains_files(lib_path, ".blend")
    folders_list = default_list + folders

    return [(name, name, "") for name in folders_list]


class WM_OT_Set_Category(Operator):
    bl_label = 'BM Set Category'
    bl_idname = 'bm.set_brushes_category'
    bl_description = "Select the category for the brushes preview"
    bl_options = {'UNDO'}

    lib_category: EnumProperty(
        name='Category',
        items=lib_category_folders,
        description='The library category that contain the list of brushes existing in the blender file data'
    )

    def execute(self, context):
        wm = bpy.context.window_manager
        props = wm.brush_manager_props
        props.lib_categories = self.lib_category

        return {'FINISHED'}


def filter_brushes_type(brushes_list, mode=''):
    filter_brushes = []
    for b in brushes_list:
        try:
            if not check_brush_type(bpy.data.brushes[b], mode):
                continue
        except KeyError:
            continue
        filter_brushes.append(b)
    filter_brushes = list(set(filter_brushes))
    filter_brushes.sort()
    return filter_brushes


def get_appended_to_current_brushes(category, directory):
    brushes_added = append_brushes_to_current_file(directory)
    brushes = filter_brushes_type(brushes_added, MODE)
    if len(brushes) == 0:
        b_files = get_b_files(directory)
        brushes = get_append_brushes(directory, b_files)
    return brushes


def get_default_brushes_list(list_type='brushes', mode=''):
    if mode != '':
        modes = BM_Modes(mode)
    else:
        modes = BM_Modes()
    if list_type == 'brushes':
        brushes = modes.def_brushes_list()
        return brushes
    if list_type == 'init_tools' or list_type == 'tools':
        enum_items = modes.brush_tool_enum_items()
    if list_type == 'sculpt_tools':
        modes.mode = 'SCULPT'
        enum_items = modes.brush_tool_enum_items()
    if list_type == 'init_tools':
        init_tools = dict([(b.identifier, b.name) for b in enum_items])
        return init_tools
    if list_type == 'tools' or list_type == 'sculpt_tools':
        tools = [t.identifier for t in enum_items]
        tools.sort()
        return tools


def check_vertex_paint_brushes():
    try:
        check = bpy.context.preferences.experimental.use_sculpt_vertex_colors
    except AttributeError:
        check = False
    if get_app_version() >= 2.90 and check:
        return True
    return False


def get_current_file_brushes(mode=''):
    brushes = []
    try:
        for brush in bpy.data.brushes:
            try:
                if not check_brush_type(brush, mode):
                    continue
                if brush.name == 'Paint' and not check_vertex_paint_brushes():
                    continue
                brushes.append(brush.name)
            except AttributeError:
                continue
    except AttributeError:
        pass
    brushes.sort()
    return brushes


def get_brushes_from_preview_enums(enum_items, list_type='brushes'):
    brushes_list = []
    icons = []
    for name1, name2, blank, iconid, index in enum_items:
        brushes_list.append(name1)
        icons.append(iconid)
    if list_type == 'icons':
        return icons
    return brushes_list


def get_main_list_brushes(context, list_type='brushes'):
    b_preview_coll = preview_brushes_coll["main"]
    directory = get_library_directory(context)
    b_preview_coll.my_previews_dir = directory
    main_preview_enums = b_preview_coll.my_previews
    if list_type == 'full':
        return main_preview_enums
    return get_brushes_from_preview_enums(main_preview_enums, list_type)


def get_favorite_brushes(list_type='brushes'):
    b_preview_coll = preview_brushes_coll["favorites"]
    preview_enums = b_preview_coll.my_previews
    b_preview_coll.my_previews_dir = "favorites"
    return get_brushes_from_preview_enums(preview_enums, list_type)


def add_to_fav_active_current_brush(context, brushes_list):
    active_brush = get_active_brush(context)
    if not active_brush or active_brush.name in brushes_list:
        return brushes_list
    brushes_list.append(active_brush.name)
    brushes_list.sort()
    return brushes_list


def clear_favorites_list():
    b_preview_coll = preview_brushes_coll["favorites"]
    if b_preview_coll.my_previews_dir != "favorites":
        return None
    enum_items = []
    if len(b_preview_coll.my_previews) > 0:
        b_preview_coll.my_previews.clear()
    b_preview_coll.my_previews = enum_items


def clear_Default_list():
    props = bpy.context.window_manager.brush_manager_props
    b_preview_coll = preview_brushes_coll["main"]
    if props.lib_categories != "Default":
        return None
    enum_items = []
    if len(b_preview_coll.my_previews) > 0:
        b_preview_coll.my_previews.clear()
    b_preview_coll.my_previews = enum_items


def get_app_version():
    version = str(bpy.app.version[0]) + '.' + str(bpy.app.version[1])
    return float(version)


def save_brushes_to_file(brushes_data, filepath, relative_path_remap=False):
    data_blocks = {
        *brushes_data,
        # *bpy.data.textures,
        *bpy.data.node_groups
    }
    if get_app_version() >= 2.90:
        path_remap = 'NONE'
        if relative_path_remap:
            path_remap = 'RELATIVE_ALL'
        try:
            bpy.data.libraries.write(
                filepath, data_blocks, fake_user=True, path_remap=path_remap)
            return None
        except TypeError:
            pass
    bpy.data.libraries.write(
        filepath, data_blocks, fake_user=True, relative_remap=relative_path_remap
    )


def get_folders_contains_files(root_folder_path, file_extension=".blend"):
    folders_list = []
    if not root_folder_path or not os.path.isdir(root_folder_path):
        return folders_list
    for folder in os.listdir(root_folder_path):
        if not os.path.isdir(os.path.join(root_folder_path, folder)):
            continue
        for fn in os.listdir(os.path.join(root_folder_path, folder)):
            if fn.lower().endswith(file_extension):
                folders_list.append(folder)
                break
    return folders_list


def filter_brushes_by_name(brushes_list, name):
    props = bpy.context.window_manager.brush_manager_props
    filtered_brushes_list = []
    for brush in brushes_list:
        if not props.search_case_sensitive:
            if not text_lookup(name.lower(), brush.lower()):
                continue
        else:
            if not text_lookup(name, brush):
                continue
        filtered_brushes_list.append(brush)
    filtered_brushes_list.sort()
    return filtered_brushes_list


def get_icon_themes_path(folder_name='icon_themes'):
    current_file_dir = os.path.dirname(__file__)
    icon_themes_path = os.path.join(current_file_dir, folder_name)
    return icon_themes_path


def get_icons_path(mode=''):
    if mode == '':
        mode = MODE
    modes = BM_Modes(mode)
    return modes.icons_path()


def set_brush_icon_themes(self, context):
    current_file_dir = os.path.dirname(__file__)
    icon_themes_path = get_icon_themes_path()
    default_list = []
    folders = get_folders_contains_files(icon_themes_path, ".png")
    folders_list = folders + default_list
    folders_list.sort()

    return [(name, name, "") for name in folders_list]


def set_active_tool(tool_name):
    if UI_MODE:
        area_type = 'IMAGE_EDITOR'
    else:
        area_type = 'VIEW_3D'
    for area in bpy.context.screen.areas:
        if area.type == area_type:
            override = bpy.context.copy()
            override["space_data"] = area.spaces[0]
            override["area"] = area
            bpy.ops.wm.tool_set_by_id(override, name=tool_name)


def get_icon_name(context, brush_name):
    brush = bpy.data.brushes[brush_name]
    modes = BM_Modes()
    mode = MODE
    if not MODE:
        mode = context.mode
    if modes.Modes[mode].get('is_split_tools'):
        return brush.name.lower() + '.png'
    else:
        return modes.brush_tool(brush).lower() + '.png'


def create_thumbnail_icon(context, brush_name, b_preview_coll):
    icons_path = get_icons_path()
    icon_name = get_icon_name(context, brush_name)
    filepath = os.path.join(icons_path, icon_name)
    if not os.path.isfile(filepath):
        modes = BM_Modes()
        if modes.Modes[MODE].get('is_split_tools'):
            for b in modes.Modes[MODE].get('def_brush_names'):
                if text_lookup(b.split(' ')[0], bpy.data.brushes[brush_name].name):
                    icon_name = bpy.data.brushes[b].name.lower() + '.png'
                    break
        if not os.path.isfile(os.path.join(icons_path, icon_name)):
            icon_name = modes.brush_tool(bpy.data.brushes[brush_name]).lower() + '.png'
        if not os.path.isfile(os.path.join(icons_path, icon_name)):
            icon_name = 'NA_brush.png'
        filepath = os.path.join(icons_path, icon_name)
    thumb = b_preview_coll.load(MODE + '_' + brush_name, filepath, 'IMAGE')
    return thumb.icon_id


def create_enum_list(context, brushes, b_preview_coll, update_icon=False):
    global UPDATE_ICONS
    if UPDATE_ICONS or update_icon:
        update_icon = True
        b_preview_coll.clear()
    icons_path = get_icons_path()
    enum_items = []
    for index, brush in enumerate(brushes):
        try:
            check = bpy.data.brushes[brush]
        except KeyError:
            continue
        if update_icon:
            icon = False
        else:
            if UI_MODE:
                icon = b_preview_coll.get('PAINT_TEXTURE' + '_' + brush)
            else:
                icon = b_preview_coll.get(context.mode + '_' + brush)
        if not icon:
            if bpy.data.brushes[brush].use_custom_icon:
                filepath = bpy.data.brushes[brush].icon_filepath
                if os.path.isfile(bpy.path.abspath(filepath)):
                    thumb = bpy.data.brushes[brush].preview.icon_id
                else:
                    thumb = create_thumbnail_icon(context, brush, b_preview_coll)
            else:
                thumb = create_thumbnail_icon(context, brush, b_preview_coll)
        else:
            if UI_MODE:
                thumb = b_preview_coll['PAINT_TEXTURE' + '_' + brush].icon_id
            else:
                thumb = b_preview_coll[context.mode + '_' + brush].icon_id
        enum_items.append((brush, brush, "", thumb, index))
    return enum_items


def reset_all_default_brushes(context):
    if contex.mode != 'SCULPT':
        return None
    props = context.window_manager.brush_manager_props
    def_brushes = get_sorted_default_brushes()
    active_brush = get_active_brush(context)
    for brush in def_brushes:
        try:
            set_brush_tool(None, context, bpy.data.brushes[brush])
        except KeyError:
            pass
        bpy.ops.brush.reset()
        if props.set_default_brushes_custom_icon:
            bpy.data.brushes[brush].use_custom_icon = True
    set_brush_tool(None, context, active_brush)


def create_default_sculpt_tools():
    if bpy.context.mode != 'SCULPT' or UI_MODE:
        return None
    props = bpy.context.window_manager.brush_manager_props
    if bpy.data.scenes[0].name == 'Empty':
        return None
    active_brush = bpy.context.tool_settings.sculpt.brush
    try:
        bpy.context.tool_settings.sculpt.brush = bpy.data.brushes['Clay']
    except KeyError:
        pass
    init_tools = get_default_brushes_list(list_type='init_tools')
    sculpt_tools = get_default_brushes_list(list_type='sculpt_tools')
    current_brushes = get_current_file_brushes()
    current_tools = []
    for brush in current_brushes:
        current_tools.append(bpy.data.brushes[brush].sculpt_tool)
        if brush == 'Multiplane Scrape':
            bpy.data.brushes[brush].name = 'Multi-plane Scrape'
    for tool in sculpt_tools:
        if tool in current_tools:
            continue
        # print('INIT TOOL:', tool)
        if init_tools.get(tool) not in BRUSHES_SCULPT and\
                not check_vertex_paint_brushes():
            continue
        # print('SET INIT TOOL:', init_tools.get(tool))
        set_active_tool("builtin_brush." + init_tools.get(tool))
        bpy.ops.brush.reset()
    try:
        tool_name = init_tools.get(active_brush.sculpt_tool)
    except AttributeError:
        return None
    if tool_name:
        set_active_tool("builtin_brush." + tool_name)
    bpy.context.tool_settings.sculpt.brush = active_brush


def create_default_smear_tools():
    global IS_INIT_SMEAR
    if bpy.context.mode != 'PAINT_WEIGHT' and bpy.context.mode != 'PAINT_VERTEX':
        return None
    if IS_INIT_SMEAR.get(bpy.context.mode):
        return None
    props = bpy.context.window_manager.brush_manager_props
    if bpy.data.scenes[0].name == 'Empty':
        return None

    toolhelper = space_toolsystem_common.ToolSelectPanelHelper
    space_type = bpy.context.space_data.type
    tool_active_id = getattr(
        toolhelper._tool_active_from_context(bpy.context, space_type),
        "idname", None,
    )
    set_active_tool("builtin_brush." + 'Smear')
    c_brushes = get_current_file_brushes()
    smear_name = 'Smear ' + bpy.context.mode.split('_')[-1].capitalize()
    for b in c_brushes:
        if bpy.data.brushes[b].name == smear_name:
            break
        if bpy.data.brushes[b].name.split('.')[0] == 'Smear' and ((
                bpy.data.brushes[b].name.split('.')[-1] == '001') or (
                bpy.data.brushes[b].name.split('.')[-1] == '002') or (
                bpy.data.brushes[b].name.split('.')[-1] == '003')):
            bpy.data.brushes[b].name = smear_name
            IS_INIT_SMEAR[bpy.context.mode] = True
            break
    set_active_tool(tool_active_id)


def check_current_file_brush_icons():
    brushes = get_current_file_brushes()
    for brush in brushes:
        if not bpy.data.brushes[brush].use_custom_icon:
            continue
        filepath = bpy.data.brushes[brush].icon_filepath
        if os.path.isfile(bpy.path.abspath(filepath)):
            continue
        bpy.data.brushes[brush].use_custom_icon = False


def load_startup_favorites(list_type='SCULPT'):
    prefs = bpy.context.preferences.addons[Addon_Name].preferences
    modes = BM_Modes(list_type)
    if not modes.use_startup_favorites():
        return None
    if get_favorite_brushes():
        return None
    path = modes.path_to_startup_favorites()
    if not os.path.isfile(path):
        return None
    if os.path.basename(path).split('.')[-1] != 'blend':
        return None
    b_preview_fav = preview_brushes_coll["favorites"]
    b_preview_fav.my_previews_dir = "favorites"
    append_brushes_from_a_file(path, default_brushes=True)
    brushes_in_file = get_append_brushes(
        os.path.dirname(path), b_files=[os.path.basename(path)],
        default_brushes=True
    )
    brushes_in_file.sort()
    enum_items = create_enum_list(bpy.context, brushes_in_file, b_preview_fav)
    b_preview_fav.my_previews = enum_items
    global START_FAV_LOADED
    START_FAV_LOADED[list_type] = True
    return True


def handler_check(handler, function_name):
    if len(handler) <= 0:
        return False
    for i, h in enumerate(handler):
        func = str(handler[i]).split(' ')[1]
        if func == function_name:
            return True
    return False


def initialize_brush_manager_ui(props, b_preview_coll):
    if not handler_check(bpy.app.handlers.load_post, "brush_manager_on_file_load"):
        bpy.app.handlers.load_post.append(brush_manager_on_file_load)
    if not handler_check(bpy.app.handlers.depsgraph_update_pre, "brush_manager_pre_dp_update"):
        bpy.app.handlers.depsgraph_update_pre.append(brush_manager_pre_dp_update)
    if not handler_check(bpy.app.handlers.save_pre, "brush_manager_pre_save"):
        bpy.app.handlers.save_pre.append(brush_manager_pre_save)
    if not handler_check(bpy.app.handlers.save_post, "brush_manager_post_save"):
        bpy.app.handlers.save_post.append(brush_manager_post_save)
    if not handler_check(bpy.app.handlers.undo_pre, "brush_manager_pre_undo"):
        bpy.app.handlers.undo_pre.append(brush_manager_pre_undo)
    if not handler_check(bpy.app.handlers.undo_post, "brush_manager_post_undo"):
        bpy.app.handlers.undo_post.append(brush_manager_post_undo)

    prefs = bpy.context.preferences.addons[Addon_Name].preferences
    props.brush_manager_init = True
    if bpy.data.scenes[0].name == 'Empty':
        props.manager_empty_init = True
    b_preview_coll.my_previews_dir = ""
    global MODE
    if UI_MODE:
        MODE = 'PAINT_TEXTURE'
    else:
        MODE = bpy.context.mode
    clear_favorites_list()
    clear_Default_list()
    create_default_sculpt_tools()
    create_default_smear_tools()
    check_current_file_brush_icons()
    load_favorites_in_mode()
    modes = BM_Modes()
    if modes.Modes[MODE].get('use_custom_icons') and not UI_MODE:
        is_icons = eval('prefs.' + modes.Modes[MODE].get('default_custom_icons'))
        if is_icons and not props.set_default_brushes_custom_icon:
            props.set_default_brushes_custom_icon = True
    if prefs.selected_brush_custom_icon and not props.set_selected_brush_custom_icon:
        props.set_selected_brush_custom_icon = True
    if prefs.force_brush_custom_icon and not props.set_force_brush_custom_icon:
        props.set_force_brush_custom_icon = True
    switch_icons()
    update_tools_popup(None, bpy.context)
    update_brush_tools_popup(None, bpy.context)


def preview_brushes_in_folders(self, context):
    prefs = context.preferences.addons[Addon_Name].preferences
    props = context.window_manager.brush_manager_props
    enum_items = []
    if context is None:
        return enum_items
    b_preview_coll = preview_brushes_coll["main"]
    if props.lib_categories == '':
        props.lib_categories = 'Default'
    selected_category_name = props.lib_categories

    directory = get_library_directory(context)
    if directory == b_preview_coll.my_previews_dir:
        return b_preview_coll.my_previews

    elif selected_category_name == 'Default':
        brushes = get_sorted_default_brushes(MODE)
    elif selected_category_name == 'Current File':
        brushes = get_current_file_brushes(MODE)
    elif selected_category_name:
        brushes = get_appended_to_current_brushes(selected_category_name, directory)
    props.post_undo_last = False

    if props.search_in_category:
        brushes = filter_brushes_by_name(brushes, str(props.search_bar.decode("utf-8")))
        brushes.sort()
    enum_items = create_enum_list(context, brushes, b_preview_coll)
    b_preview_coll.my_previews_dir = directory
    b_preview_coll.my_previews = enum_items
    return b_preview_coll.my_previews


def preview_brushes_in_favorites(self, context):
    enum_items = []
    if context is None:
        return enum_items

    list_dir = "favorites"
    b_preview_coll = preview_brushes_coll["favorites"]
    if b_preview_coll.my_previews_dir == list_dir:
        return b_preview_coll.my_previews

    brushes = get_favorite_brushes()
    enum_items = create_enum_list(context, brushes, b_preview_coll)
    b_preview_coll.my_previews_dir = list_dir
    b_preview_coll.my_previews = enum_items
    global UPDATE_ICONS
    UPDATE_ICONS = False
    return b_preview_coll.my_previews


def SelectBrushError(self, context):
    msg = "Selected Brush has been deleted or renamed, removing..."
    print("Brush Manager Error: " + msg)
    self.layout.label(text=msg)


def set_brush_tool(self, context, brush):
    modes = BM_Modes()
    init_tools = get_default_brushes_list(list_type='init_tools')

    tool_name = init_tools.get(modes.brush_tool(brush))
    if not hasattr(self, 'no_tool'):
        set_active_tool("builtin_brush." + tool_name)
    else:
        if not self.no_tool:
            set_active_tool("builtin_brush." + tool_name)
    tool_settings_mode = modes.tool_settings(context)
    tool_settings_mode.brush = brush


def set_brush_from_lib_list(self, context):
    props = context.window_manager.brush_manager_props
    if props.skip_brush_set:
        props.skip_brush_set = False
        return None
    if hasattr(self, 'brush'):
        selected_brush = self.brush
    else:
        selected_brush = context.window_manager.brushes_in_files
    try:
        set_brush_tool(self, context, bpy.data.brushes[selected_brush])
    except KeyError:
        context.window_manager.popup_menu(SelectBrushError, title="Error", icon="INFO")
        update_brush_list(self, context)
        return None
    if bpy.data.brushes[selected_brush].use_custom_icon and not props.set_force_brush_custom_icon:
        return None
    if props.set_selected_brush_custom_icon and MODE == 'SCULPT':
        icons_path = get_icons_path()
        set_custom_icon(context, icons_path, selected_brush)
    return None


def set_brush_from_fav_list(self, context):
    props = context.window_manager.brush_manager_props
    if props.skip_brush_set:
        props.skip_brush_set = False
        return None
    selected_brush = context.window_manager.brushes_in_favorites
    try:
        set_brush_tool(self, context, bpy.data.brushes[selected_brush])
    except KeyError:
        context.window_manager.popup_menu(SelectBrushError, title="Error", icon="INFO")
        remove_active_brush_favorite(self, context)
        return None
    if bpy.data.brushes[selected_brush].use_custom_icon and not props.set_force_brush_custom_icon:
        return None
    if props.set_selected_brush_custom_icon and MODE == 'SCULPT':
        icons_path = get_icons_path()
        set_custom_icon(context, icons_path, selected_brush)
    return None


def set_brush_from_fav_popup(self, context):
    props = context.window_manager.brush_manager_props
    if hasattr(self, 'brush'):
        selected_brush = self.brush
    else:
        selected_brush = context.window_manager.fav_brush_popup
    try:
        set_brush_tool(self, context, bpy.data.brushes[selected_brush])
    except KeyError:
        context.window_manager.popup_menu(SelectBrushError, title="Error", icon="INFO")
        remove_active_brush_favorite(self, context, fav_type='popup')
        return None
    if bpy.data.brushes[selected_brush].use_custom_icon and not props.set_force_brush_custom_icon:
        return None
    if props.set_selected_brush_custom_icon and MODE == 'SCULPT':
        icons_path = get_icons_path()
        set_custom_icon(context, icons_path, selected_brush)
    return None


def set_custom_icon(context, icons_path, brush_name):
    try:
        brush = bpy.data.brushes[brush_name]
    except (KeyError, AttributeError) as e:
        return False
    icon_name = get_icon_name(context, brush_name)
    filepath = os.path.join(icons_path, icon_name)
    if not os.path.isfile(filepath):
        modes = BM_Modes()
        if modes.Modes[MODE].get('is_split_tools'):
            for b in modes.Modes[MODE].get('def_brush_names'):
                if text_lookup(b.split(' ')[0], bpy.data.brushes[brush_name].name):
                    icon_name = bpy.data.brushes[b].name.lower() + '.png'
                    break
        if not os.path.isfile(os.path.join(icons_path, icon_name)):
            icon_name = modes.brush_tool(bpy.data.brushes[brush_name]).lower() + '.png'
        if not os.path.isfile(os.path.join(icons_path, icon_name)):
            icon_name = 'NA_brush.png'
        filepath = os.path.join(icons_path, icon_name)
    brush.use_custom_icon = True
    brush.icon_filepath = filepath


class WM_OT_Select_Brush(Operator):
    bl_label = 'Select Brush'
    bl_idname = 'bm.select_brush'
    bl_description = "Select brush to make it active"
    bl_options = {'UNDO'}

    brush: bpy.props.StringProperty()
    from_list: bpy.props.StringProperty()
    no_tool: bpy.props.BoolProperty()

    def execute(self, context):
        if self.from_list == 'add_brush_popup':
            set_brush_from_lib_list(self, context)
        else:
            set_brush_from_fav_popup(self, context)

        if prefs().close_popup_on_select:
            popup_close()
        return {'FINISHED'}


class WM_OT_Set_Select_Brush(Operator):
    bl_label = 'Select Brush'
    bl_idname = 'bm.set_brush'
    bl_description = "Select brush to make it active"
    # bl_options = {'UNDO'}

    brush: bpy.props.StringProperty()
    from_list: bpy.props.StringProperty()

    def execute(self, context):
        if self.from_list == 'add_brush_popup':
            set_brush_from_lib_list(self, context)
        else:
            set_brush_from_fav_popup(self, context)

        if prefs().close_popup_on_select:
            popup_close()
        return {'FINISHED'}


def update_pref_apply_theme_to_def(self, context):
    global SET_DEFAULT_ICONS
    modes = BM_Modes()
    mode = prefs().pref_tabs
    if (context.mode not in modes.in_modes) or\
            context.mode != mode:
        is_icons = eval('self.' + modes.Modes[mode].get('default_custom_icons'))
        if is_icons:
            SET_DEFAULT_ICONS[mode] = True
        else:
            SET_DEFAULT_ICONS[mode] = False
        return None
    mode = context.mode
    props = context.window_manager.brush_manager_props
    is_icons = eval('self.' + modes.Modes[mode].get('default_custom_icons'))
    if is_icons:
        SET_DEFAULT_ICONS[mode] = True
        props.set_default_brushes_custom_icon = True
    else:
        SET_DEFAULT_ICONS[mode] = False
        props.set_default_brushes_custom_icon = False
        set_toggle_default_icons(context, switch=True)
        update_category(self, context)


def update_pref_apply_theme_to_selected(self, context):
    prefs = context.preferences.addons[Addon_Name].preferences
    props = context.window_manager.brush_manager_props
    if not props.set_selected_brush_custom_icon and prefs.selected_brush_custom_icon:
        props.set_selected_brush_custom_icon = True
    if props.set_selected_brush_custom_icon and not prefs.selected_brush_custom_icon:
        props.set_selected_brush_custom_icon = False


def update_pref_force_apply_theme_to_sel(self, context):
    prefs = context.preferences.addons[Addon_Name].preferences
    props = context.window_manager.brush_manager_props
    if not props.set_force_brush_custom_icon and prefs.force_brush_custom_icon:
        props.set_force_brush_custom_icon = True
    if props.set_force_brush_custom_icon and not prefs.force_brush_custom_icon:
        props.set_force_brush_custom_icon = False

    if prefs.force_brush_custom_icon and not prefs.selected_brush_custom_icon:
        prefs.selected_brush_custom_icon = True


def update_force_theme_to_brush(self, context):
    props = context.window_manager.brush_manager_props
    if props.set_force_brush_custom_icon and not props.set_selected_brush_custom_icon:
        props.set_selected_brush_custom_icon = True


def update_brush_tools_popup(self, context):
    prefs = context.preferences.addons[Addon_Name].preferences
    props = context.window_manager.brush_manager_props
    if prefs.brush_tools and not props.show_brush_tools:
        props.show_brush_tools = True
    if not prefs.brush_tools and props.show_brush_tools:
        props.show_brush_tools = False


def update_tools_popup(self, context):
    prefs = context.preferences.addons[Addon_Name].preferences
    props = context.window_manager.brush_manager_props
    if prefs.popup_tools and not props.popup_tools_switch:
        props.popup_tools_switch = True
    if not prefs.popup_tools and props.popup_tools_switch:
        props.popup_tools_switch = False


LOADING_SETTINGS = False


def set_toggle_default_icons(context, switch=False, mode='', force=False):
    if mode == '':
        mode = MODE
    if context.mode not in BM_Modes.in_modes and not force:
        return None
    modes = BM_Modes()
    if not modes.Modes[mode].get('use_custom_icons') and LOADING_SETTINGS:
        return None
    global SET_DEFAULT_ICONS
    prefs = context.preferences.addons[Addon_Name].preferences
    props = context.window_manager.brush_manager_props
    if modes.Modes[mode].get('has_themes'):
        icon_themes_path = get_icon_themes_path()
        icons_path = os.path.join(icon_themes_path, prefs.brush_icon_theme)
    else:
        icon_themes_path = get_icon_themes_path(modes.icons_path())
        icons_path = os.path.join(icon_themes_path, 'custom_icons')
    default_brushes = get_sorted_default_brushes(mode)
    if props.set_default_brushes_custom_icon and not switch:
        for brush in default_brushes:
            set_custom_icon(context, icons_path, brush)
        SET_DEFAULT_ICONS[mode] = True
    elif switch:
        for brush in default_brushes:
            if bpy.data.brushes[brush].use_custom_icon:
                bpy.data.brushes[brush].use_custom_icon = False
            # bpy.data.brushes[brush].icon_filepath = ''
        SET_DEFAULT_ICONS[mode] = False


def update_default_icons(self, context):
    modes = BM_Modes()
    mode = context.mode
    global SET_DEFAULT_ICONS
    if mode not in modes.in_modes:
        if self.set_default_brushes_custom_icon:
            SET_DEFAULT_ICONS[prefs().pref_tabs] = True
        else:
            SET_DEFAULT_ICONS[prefs().pref_tabs] = False
        return None
    if self.set_default_brushes_custom_icon and\
            not modes.Modes[mode].get('use_custom_icons'):  # context.mode != 'SCULPT':
        SET_DEFAULT_ICONS[mode] = True
        return None
    if not self.set_default_brushes_custom_icon and\
            not modes.Modes[mode].get('use_custom_icons'):
        SET_DEFAULT_ICONS[mode] = False
    set_toggle_default_icons(context)


def update_icon_theme(self, context):
    props = context.window_manager.brush_manager_props
    props.lib_categories = "Current File"
    is_theme = props.set_default_brushes_custom_icon
    popup_close()
    if props.set_default_brushes_custom_icon:
        props.set_default_brushes_custom_icon = False
    global UPDATE_ICONS
    UPDATE_ICONS = True
    update_category(self, context)
    if is_theme:
        props.set_default_brushes_custom_icon = True


def remove_fav_brush(self, context, remove_brushes):
    b_preview_coll = preview_brushes_coll["favorites"]
    if b_preview_coll.my_previews_dir != "favorites":
        return None
    brushes = get_favorite_brushes()
    for b in remove_brushes:
        try:
            brushes.remove(b)
        except ValueError:
            # msg = "Brush Manager: Nothing to remove"
            # self.report({'ERROR'}, msg)
            return None
    enum_items = create_enum_list(context, brushes, b_preview_coll)
    b_preview_coll.my_previews = enum_items


def remove_active_brush_favorite(self, context, fav_type='preview'):
    if fav_type == 'preview':
        active_brush = context.window_manager.brushes_in_favorites
    if fav_type == 'popup':
        active_brush = get_active_brush(context).name
    remove_fav_brush(self, context, [active_brush])


def get_pref_default_brush_props(list_type='', mode=''):
    prefs = bpy.context.preferences.addons[Addon_Name].preferences
    if mode == '':
        mode = MODE

    modes = BM_Modes(mode)
    if list_type == 'tools':
        props_list = [pr for pr in prefs.__annotations__ if pr.startswith(modes.pref_tool())]
    elif list_type == 'other_tools':
        props_list = [pr for pr in prefs.__annotations__ if pr.startswith(modes.pref_tool('other'))]
    else:
        props_list = [pr for pr in prefs.__annotations__ if pr.startswith(modes.pref_brush())]
        b_tools = dict(evaluate_brush_tools(modes.def_brushes_tool_list(), mode))

    props_values = []
    for pr in props_list:
        b_name = prefs.bl_rna.properties[pr].name
        if list_type == 'tools' or list_type == 'other_tools':
            exec("props_values.append((b_name, prefs." + pr + "))")
        else:
            if modes.Modes[mode].get('is_split_tools'):
                exec("props_values.append((b_name, prefs." + pr + "))")
            else:
                exec("props_values.append((b_tools.get(b_name), prefs." + pr + "))")
    props_values = dict(props_values)
    return props_values


def get_pref_custom_def_brush_props(list_type=''):
    if list_type != 'SCULPT':
        return []
    prefs = bpy.context.preferences.addons[Addon_Name].preferences
    custom_props_list = [pr for pr in prefs.__annotations__ if pr.startswith("add_def_brush_")]
    props_values = []
    for pr in custom_props_list:
        exec("if prefs." + pr + " != '': props_values.append(prefs." + pr + ")")
    return props_values


def get_pref_default_brushes(list_type=''):
    default_brushes = get_default_brushes_list(mode=list_type)
    pref_def_brushes = get_pref_default_brush_props(mode=list_type)
    pref_custom_def_brushes = get_pref_custom_def_brush_props(list_type)
    brushes_include = []
    for brush in default_brushes:
        if not pref_def_brushes.get(brush):
            continue
        brushes_include.append(brush)
    brushes_include = brushes_include + pref_custom_def_brushes
    return brushes_include


def get_sorted_default_brushes(list_type=''):
    default_brushes = get_pref_default_brushes(list_type)
    default_brushes = filter_brushes_type(default_brushes, list_type)
    current_brushes = get_current_file_brushes(list_type)
    if list_type == 'SCULPT':
        tools = get_default_brushes_list(list_type='sculpt_tools')
    else:
        tools = get_default_brushes_list(list_type='tools')
    modes = BM_Modes(list_type)
    for brush in current_brushes:
        tool = modes.brush_tool(bpy.data.brushes[brush])
        if tool in tools:
            continue
        default_brushes.append(brush)
    return default_brushes


class WM_OT_Add_to_the_Favorites(Operator):
    bl_label = 'Add to the Favorites'
    bl_idname = 'bm.add_brush_to_favorites'
    bl_description = "Add the active brush to the favorites list"

    def execute(self, context):
        b_preview_coll = preview_brushes_coll["favorites"]
        if b_preview_coll.my_previews_dir != "favorites":
            return {'FINISHED'}
        brushes_list = get_favorite_brushes()
        brushes = add_to_fav_active_current_brush(context, brushes_list)
        enum_items = create_enum_list(context, brushes, b_preview_coll)
        b_preview_coll.my_previews = enum_items
        return {'FINISHED'}


class WM_OT_Append_List_to_the_Favorites(Operator):
    bl_label = 'Append the Category List to the Favorites'
    bl_idname = 'bm.append_list_to_favorites'
    bl_description = "Append the current preview brushes list to the Favorites"

    def execute(self, context):
        b_preview_fav = preview_brushes_coll["favorites"]
        b_preview_main = preview_brushes_coll["main"]
        if b_preview_fav.my_previews_dir != "favorites":
            return {'FINISHED'}
        main_preview_enums = b_preview_main.my_previews
        main_brushes = get_brushes_from_preview_enums(main_preview_enums)
        fav_brushes = get_favorite_brushes()
        brushes = list(set(main_brushes + fav_brushes))
        brushes.sort()
        enum_items = create_enum_list(context, brushes, b_preview_fav)
        b_preview_fav.my_previews = enum_items
        return {'FINISHED'}


class WM_OT_Append_from_a_File_to_Favorites(Operator):
    bl_label = 'Load Brushes'
    bl_idname = 'bm.append_from_a_file_to_favorites'
    bl_description = "Append the brushes library from a file to the Favorites"

    default_brushes: bpy.props.BoolProperty(
        name="Default Brushes",
        default=True,
        description="Include/Exclude the default brushes in the appending list",
    )
    duplicates: EnumProperty(
        name="Duplicates",
        items=[
            ("RENAME", "Auto Rename", 'Auto rename the copyied brush if already exist'),
            ("OVERWRITE", "Overwrite", 'Overwrite if already exist'),
            ("SKIP", "Skip", 'Skip if already exist'),
        ],
        default="SKIP"
    )
    directory: bpy.props.StringProperty(
        subtype="DIR_PATH"
    )
    filename: bpy.props.StringProperty(
        subtype="FILE_NAME"
    )
    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH"
    )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        if not self.filepath.endswith(".blend"):
            msg = "Selected file has to be a .blend file"
            self.report({'ERROR'}, msg)

            return {'FINISHED'}

        modes = BM_Modes()
        ts = modes.tool_settings(context)
        active_brush_name = ts.brush.name

        b_preview_fav = preview_brushes_coll["favorites"]
        b_preview_fav.my_previews_dir = "favorites"
        brushes_in_file = append_brushes_from_a_file(
            self.filepath,
            default_brushes=self.default_brushes,
            duplicates=self.duplicates
        )
        fav_brushes = get_favorite_brushes()
        brushes = list(set(brushes_in_file + fav_brushes))
        brushes.sort()
        enum_items = create_enum_list(context, brushes, b_preview_fav)
        b_preview_fav.my_previews = enum_items
        ts.brush = bpy.data.brushes[active_brush_name]

        msg = "Brushes loaded from: " + self.filepath
        self.report({'INFO'}, msg)

        return {'FINISHED'}


class WM_OT_Remove_Active_Favorite(Operator):
    bl_label = 'Remove the Active Favorite'
    bl_idname = 'bm.remove_active_brush_favorite'
    bl_description = "Remove the Active Brush from the favorites list"

    def execute(self, context):
        wm = context.window_manager
        brushes = get_favorite_brushes()
        if len(brushes) == 0:
            return {'FINISHED'}
        remove_active_brush_favorite(self, context)
        set_first_preview_item(context, brushes, wm_enum_prop='fav')
        return {'FINISHED'}


class WM_OT_Remove_Active_Popup_Favorite(Operator):
    bl_label = 'Remove the Active Favorite'
    bl_idname = 'bm.remove_active_popup_favorite'
    bl_description = "Remove the Active Brush from the favorites list"

    def execute(self, context):
        wm = context.window_manager
        brushes = get_favorite_brushes()
        if len(brushes) == 0:
            return {'FINISHED'}
        remove_active_brush_favorite(self, context, fav_type='popup')
        set_first_preview_item(context, brushes, wm_enum_prop='fav')
        return {'FINISHED'}


class WM_OT_Clear_Favorites(Operator):
    bl_label = 'Clear The Favorites'
    bl_idname = 'bm.clear_favorites'
    bl_description = "Remove all Brushes from the favorites list"

    def execute(self, context):
        brushes = get_favorite_brushes()
        set_first_preview_item(context, brushes, wm_enum_prop='fav')
        clear_favorites_list()
        return {'FINISHED'}


class WM_OT_Delete_Zero_User_Brushes(Operator):
    bl_label = 'Delete All Zero User Brushes'
    bl_idname = 'bm.delete_unused_brushes'
    bl_description = "Delete all zero user brushes data"

    def execute(self, context):
        remove_brushes = []
        for brush in bpy.data.brushes:
            if not check_brush_type(brush, MODE):
                continue
            if brush.users > 0:
                continue
            remove_brushes.append(brush.name)
            bpy.data.brushes.remove(brush, do_unlink=True)
        fav_brushes = get_favorite_brushes()
        remove_favorites = [b for b in remove_brushes if b in fav_brushes]
        remove_fav_brush(self, context, remove_favorites)
        set_first_preview_item(context, fav_brushes, wm_enum_prop='fav')
        props = context.window_manager.brush_manager_props
        props.lib_categories = 'Default'
        update_brush_list(self, context)
        self.report({'INFO'}, "Zero user brushes data has been deleted")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class WM_OT_Delete_Active_Brush_Data(Operator):
    bl_label = 'Delete the Active Brush Data'
    bl_idname = 'bm.delete_active_brush'
    bl_description = "Delete the active brush from the current file data"

    def execute(self, context):
        active_brush_data = get_active_brush(context)
        if not active_brush_data:
            return {'FINISHED'}
        brush_name = active_brush_data.name
        fav_brushes = get_favorite_brushes()
        if brush_name in fav_brushes:
            remove_fav_brush(self, context, [brush_name])
            set_first_preview_item(context, fav_brushes, wm_enum_prop='fav')
        bpy.data.brushes.remove(active_brush_data, do_unlink=True)
        update_brush_list(self, context)

        self.report({'INFO'}, "\"" + brush_name + "\" brush data has been deleted")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class WM_OT_Refresh_Category_List(Operator):
    bl_label = 'Refresh the Category List'
    bl_idname = 'bm.update_category_list'
    bl_description = "Update the brushes list in the selected library category"

    def execute(self, context):
        global UPDATE_ICONS
        UPDATE_ICONS = True
        update_category(self, context)

        return {'FINISHED'}


class WM_OT_Save_Favorites(Operator):
    bl_label = 'Save Brushes'
    bl_idname = 'bm.save_favorites'
    bl_description = "Save the favorites list of brushes to a .blend file"

    relative_remap: bpy.props.BoolProperty(
        name="Remap Relative",
        default=True,
        description="Remap relative paths when saving to a different directory",
    )
    default_brushes: bpy.props.BoolProperty(
        name="Default Brushes",
        default=True,
        description="Include/Exclude the default brushes in the saving list",
    )
    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH"
    )

    def execute(self, context):
        if self.filepath.endswith(".blend"):
            blend_filepath = self.filepath
        else:
            blend_filepath = self.filepath + ".blend"
        brushes_list = get_favorite_brushes()
        def_brushes = get_default_brushes_list()
        brushes_data = []
        brushes_failed = ''
        for b in brushes_list:
            if b in def_brushes and not self.default_brushes:
                continue
            try:
                if check_brush_type(bpy.data.brushes[b], MODE):
                    brushes_data.append(bpy.data.brushes[b])
            except KeyError:
                brushes_failed = brushes_failed + ' ' + '\"' + b + '\",'
        if brushes_failed != '':
            msg = "Save Brushes Error:" + brushes_failed + " data does not found."
            self.report({'ERROR'}, msg)
            return {'FINISHED'}
        save_brushes_to_file(brushes_data, blend_filepath, relative_path_remap=self.relative_remap)
        update_brush_list(self, context)
        msg = "Brushes Saved to: " + blend_filepath
        self.report({'INFO'}, msg)

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


def get_fav_list_type(mode, list_type):
    try:
        modes = BM_Modes(mode)
        if list_type == 'SETTINGS':
            return modes.fav_settings()
        elif list_type == 'STORE':
            return modes.fav_store()
    except AttributeError:
        return None


def load_saved_favorites_list(mode='SCULPT', list_type='SETTINGS'):
    global FAV_SETTINGS_LOADED
    global START_FAV_LOADED
    fav_list = get_fav_list_type(mode, list_type)
    if fav_list is None:
        return None
    b_preview_fav = preview_brushes_coll["favorites"]
    b_preview_fav.my_previews_dir == "favorites"
    brushes = [i.name for i in fav_list]
    enum_items = create_enum_list(bpy.context, brushes, b_preview_fav)
    b_preview_fav.my_previews = enum_items

    FAV_SETTINGS_LOADED[mode] = True
    if brushes:
        START_FAV_LOADED[mode] = True
    return brushes


class BM_Favorite_list_settings(PropertyGroup):
    name: StringProperty(name="Brush name")


class WM_OT_Load_Favorites_from_current_file(Operator):
    bl_label = 'Load the Favorites from the Current File'
    bl_idname = 'bm.load_favorites_from_current_file'
    bl_description = "Load the favorites list of brushes from the current file"

    def execute(self, context):
        brushes = get_favorite_brushes()
        set_first_preview_item(context, brushes, wm_enum_prop='fav')
        clear_favorites_list()
        load_saved_favorites_list(MODE, 'SETTINGS')

        return {'FINISHED'}


class WM_OT_Load_Startup_Favorites(Operator):
    bl_label = 'Load the Startup Favorites'
    bl_idname = 'bm.load_startup_favorites'
    bl_description = "Load the Startup Favorites list from the specified file in the add-on preferences"

    def execute(self, context):
        brushes = get_favorite_brushes()
        set_first_preview_item(context, brushes, wm_enum_prop='fav')
        clear_favorites_list()
        load_startup_favorites(MODE)
        return {'FINISHED'}


def store_favorites_list(mode='SCULPT', list_type='SETTINGS'):
    fav_list = get_fav_list_type(mode, list_type)
    if fav_list is None:
        return None
    brushes_list = get_favorite_brushes()
    fav_list.clear()
    for b in brushes_list:
        item = fav_list.add()
        item.name = b
        if list_type == 'SETTINGS':
            bpy.data.brushes[b].use_fake_user = True


class WM_OT_Save_Favorites_to_current_file(Operator):
    bl_label = 'Save the Favorites to the Current File'
    bl_idname = 'bm.save_favorites_to_current_file'
    bl_description = "Save the favorites list of brushes to the current file"

    def execute(self, context):
        store_favorites_list(MODE, 'SETTINGS')
        self.report({'INFO'}, "Favorites List Saved")

        return {'FINISHED'}


class WM_OT_Save_Active_Brush(Operator):
    bl_label = 'Save Brush'
    bl_idname = 'bm.save_active_brush'
    bl_description = "Save the active brush to a .blend file"

    relative_remap: bpy.props.BoolProperty(
        name="Remap Relative",
        default=True,
        description="Remap relative paths when saving to a different directory",
    )
    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH"
    )

    def execute(self, context):
        if self.filepath.endswith(".blend"):
            blend_filepath = self.filepath
        else:
            blend_filepath = self.filepath + ".blend"
        brushes_data = [get_active_brush(context)]
        save_brushes_to_file(brushes_data, blend_filepath, relative_path_remap=self.relative_remap)
        update_brush_list(self, context)
        msg = "Brush \"" + brushes_data[0].name + "\" Saved to: " + blend_filepath
        self.report({'INFO'}, msg)

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class WM_OT_Open_Category_Folder(Operator):
    bl_idname = "bm.category_folder"
    bl_label = "Open Category Folder"
    bl_description = "Open the selected category folder in the file browser"

    def execute(self, context):
        directory = get_library_directory(context)

        if sys.platform == "win32":
            os.startfile(directory)
        else:
            if sys.platform == "darwin":
                command = "open"
            else:
                command = "xdg-open"
            subprocess.call([command, directory])

        return {'FINISHED'}


class WM_OT_Reset_All_Default_Brushes(Operator):
    bl_label = 'Reset the Default Brushes'
    bl_idname = 'bm.reset_default_brushes'
    bl_description = "Return all properties of brushes in the Default list to their defaults"

    def execute(self, context):
        reset_all_default_brushes(context)

        self.report({'INFO'}, "Brushes has been returned to their defaults")

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


def icon_directory_paths(self, context):
    paths = []
    paint_icons_path = os.path.join(get_icon_themes_path('paint_icons'), 'custom_icons')
    gpaint_icons_path = os.path.join(get_icon_themes_path('gpaint_icons'), 'custom_icons')
    wpaint_icons_path = os.path.join(get_icon_themes_path('wpaint_icons'), 'custom_icons')
    vpaint_icons_path = os.path.join(get_icon_themes_path('vpaint_icons'), 'custom_icons')
    paths.append((paint_icons_path, 'paint_icons', ''))
    paths.append((gpaint_icons_path, 'gpaint_icons', ''))
    paths.append((wpaint_icons_path, 'wpaint_icons', ''))
    paths.append((vpaint_icons_path, 'vpaint_icons', ''))
    icon_themes_path = get_icon_themes_path()
    folders = get_folders_contains_files(icon_themes_path, ".png")
    for folder in folders:
        paths.append((os.path.join(icon_themes_path, folder), folder, ''))
    return paths


def theme_icons_for_custom_icon(self, context):
    files = []
    if not os.path.isdir(self.path):
        return files
    for file in os.listdir(self.path):
        if not os.path.isfile(os.path.join(self.path, file)):
            continue
        if file.lower().endswith('.png'):
            files.append((file, file, ""))
    return files


class WM_OT_Apply_Icon_to_Active_Brush(Operator):
    bl_label = 'Apply an Icon to the Active Brush'
    bl_idname = 'bm.set_icon_to_active_brush'
    bl_description = "Set custom icon from existing themes to the active brush"

    path: EnumProperty(
        name='Theme',
        items=icon_directory_paths
    )
    icon: EnumProperty(
        name='Icon',
        items=theme_icons_for_custom_icon
    )

    def execute(self, context):
        filepath = os.path.join(self.path, self.icon)
        active_brush = get_active_brush(context)
        if not active_brush:
            return {'FINISHED'}
        active_brush.use_custom_icon = True
        active_brush.icon_filepath = filepath
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class WM_MT_BrushManager_Ops(Menu):
    bl_label = "Preview Operations"
    bl_idname = "VIEW3D_MT_Sculpt_brush_manager_menu"

    def draw(self, context):
        prefs = context.preferences.addons[Addon_Name].preferences
        props = context.window_manager.brush_manager_props
        layout = self.layout
        if prefs.move_add_to_favorite_op:
            layout.operator('bm.add_brush_to_favorites', icon='ADD')
        layout.operator("bm.append_list_to_favorites", icon='APPEND_BLEND')
        layout.operator("bm.edit_brushes_from_category_popup", icon='SHORTDISPLAY')
        if (context.space_data.type == 'VIEW_3D' and context.region.type == 'WINDOW'):
            layout.separator()
            if prefs.hide_header:
                layout.prop(props, "popup_tools_switch", text='Show Tools')
                layout.prop(props, "show_brush_tools")
                layout.operator("bm.settings_popup", icon='PREFERENCES')
                layout.separator()
        else:
            if MODE == 'SCULPT' and not prefs.sculpt_hide_preview:
                layout.operator("bm.add_to_favorites_popup", icon='PRESET_NEW')
            layout.separator()
            layout.operator("bm.settings_popup", icon='PREFERENCES')
            layout.separator()
        layout.operator("bm.set_icon_to_active_brush", icon='FILE_IMAGE')
        layout.separator()
        layout.operator("bm.save_favorites_to_current_file", icon='FILE_TICK')
        layout.operator("bm.load_favorites_from_current_file", icon='FILE_BLEND')
        modes = BM_Modes()
        if modes.use_startup_favorites():
            layout.operator("bm.load_startup_favorites", icon='FILE_BLEND')
        layout.operator("bm.save_active_brush", text='Save the Active Brush to a File', icon='FILE')
        layout.operator("bm.save_favorites", text='Save the Favorites to a File', icon='EXPORT')
        layout.operator("bm.append_from_a_file_to_favorites", text='Append from a File to the Favorites', icon='IMPORT')
        layout.separator()
        if context.mode == 'SCULPT' and not UI_MODE:
            layout.operator("bm.reset_default_brushes", icon='PRESET')
            layout.separator()
        layout.operator("bm.delete_active_brush", icon='TRASH')
        layout.operator("bm.delete_unused_brushes", icon='TRASH')
        layout.separator()
        if (context.space_data.type == 'VIEW_3D' and context.region.type == 'WINDOW') or UI_MODE:
            layout.prop(props, "edit_favorites")
            layout.operator("bm.remove_active_popup_favorite", icon='REMOVE')
        else:
            if MODE == 'SCULPT' and not prefs.sculpt_hide_preview:  # != PAINT_GPENCIL
                layout.operator("bm.edit_favorites_list_popup", icon='LONGDISPLAY')
            layout.operator("bm.remove_active_brush_favorite", icon='REMOVE')
        layout.operator("bm.clear_favorites", icon='X')


def delete_fav_brush_list_update(self, context):
    brush_name = self.brush_name
    brushes = get_favorite_brushes()
    if len(brushes) == 0:
        return None
    remove_fav_brush(self, context, [brush_name])
    set_first_preview_item(context, brushes, wm_enum_prop='fav')


class BrushManager_Properties(PropertyGroup):

    lib_categories: EnumProperty(
        name='Category',
        items=lib_category_folders,
        description='The library category that contain the list of brushes existing in the blender file data',
        # update=update_category
    )
    brush_manager_init: BoolProperty(
        name="Brush Manager Init",
        description='',
        default=False
    )
    manager_empty_init: BoolProperty(
        name="Brush Manager Init on Empty scene",
        description='',
        default=False
    )
    skip_brush_set: BoolProperty(
        name="Skip Brush Set",
        description='Skip Brush Set on update',
        default=False
    )
    search_in_category: BoolProperty(
        name="Search",
        description='Turn on/off the search filter for the current category',
        default=False,
        update=update_category
    )
    search_bar: StringProperty(
        name='Search Filter',
        description='Text input field of the search filter',
        subtype='BYTE_STRING',
        options={'TEXTEDIT_UPDATE'},
        update=update_brush_list
    )
    search_case_sensitive: BoolProperty(
        name="Search Case Sesitivity",
        description='Use the search filter case sensitive',
        default=False,
        update=update_brush_list
    )
    WindowManager.brushes_in_files = EnumProperty(
        items=preview_brushes_in_folders,
        update=set_brush_from_lib_list
    )
    WindowManager.brushes_in_favorites = EnumProperty(
        items=preview_brushes_in_favorites,
        update=set_brush_from_fav_list
    )
    set_default_brushes_custom_icon: BoolProperty(
        name="Toggle Theme in the Default Brushes",
        default=False,
        description="Apply/Remove theme for custom icons of all default brushes",
        update=update_default_icons
    )
    set_selected_brush_custom_icon: BoolProperty(
        name="Auto Apply Theme to the Selected Brush",
        default=False,
        description="Apply theme to custom icon of the selected brush from library list",
        # update=update_sel_brush_custom_icon
    )
    set_force_brush_custom_icon: BoolProperty(
        name="Force to Apply Theme to the Selected Brush",
        default=False,
        description="Force to apply theme to the selected brush if custom icon is already exists",
        update=update_force_theme_to_brush
    )
    post_undo_last: BoolProperty(
        name="last post undo",
        default=False
    )
    update_after_save: BoolProperty(
        name="update after save",
        default=False
    )
    edit_favorites: BoolProperty(
        name="Edit the Favorites List",
        default=False
    )
    popup_tools_switch: BoolProperty(
        name='Show Tools',
        default=False
    )
    show_brush_tools: BoolProperty(
        name='Show Brush Tools',
        default=False
    )


class BM_Side_Panel:
    def draw(self, context, layout):
        prefs = context.preferences.addons[Addon_Name].preferences
        props = context.window_manager.brush_manager_props

        layout = self.layout
        row = layout.row()
        row = row.row(align=True)
        modes = BM_Modes()
        preview_frame_scale = modes.preview_frame_scale()
        if MODE == 'SCULPT':
            row.prop(props, "lib_categories", text='')
        else:
            row.operator_menu_enum('bm.set_brushes_category', 'lib_category', text=props.lib_categories)
        if props.lib_categories != 'Default' and props.lib_categories != 'Current File':
            row.operator('bm.category_folder', text='', icon='FILE_FOLDER')
        row.operator('bm.update_category_list', text='', icon='FILE_REFRESH')
        row.prop(props, "search_in_category", text='', icon='VIEWZOOM')
        if props.search_in_category:
            row = layout.row()
            row.prop(props, "search_bar", text='')
            row.prop(props, "search_case_sensitive", text='', icon='SMALL_CAPS')
        row = layout.row(align=True)
        if MODE == 'SCULPT' and not prefs.sculpt_hide_preview:
            row.template_icon_view(
                context.window_manager, "brushes_in_files", show_labels=True,
                scale=preview_frame_scale, scale_popup=prefs.preview_items_scale)
            row.template_icon_view(
                context.window_manager, "brushes_in_favorites", show_labels=True,
                scale=preview_frame_scale, scale_popup=prefs.preview_items_scale)
            row = row.row(align=True)
            row.scale_y = preview_frame_scale
            if not prefs.move_add_to_favorite_op:
                row.operator('bm.add_brush_to_favorites', text='', icon='ADD')
            row.menu("VIEW3D_MT_Sculpt_brush_manager_menu", icon='DOWNARROW_HLT', text="")
        else:
            preview_brushes_in_folders(self, context)
            preview_brushes_in_favorites(self, context)
            row.scale_y = preview_frame_scale
            row.operator("bm.add_to_favorites_popup", text='Select/Add', icon='PRESET_NEW')
            row.operator("bm.edit_favorites_list_popup", text='Favorites', icon='SOLO_ON')  # SOLO_ON LONGDISPLAY
            if not prefs.move_add_to_favorite_op:
                row.operator('bm.add_brush_to_favorites', text='', icon='ADD')
            row.menu("VIEW3D_MT_Sculpt_brush_manager_menu", icon='DOWNARROW_HLT', text="")


def init_bm_panel(self):
    global MODE
    global UI_MODE
    BM_Initialization()
    if bpy.context.mode != MODE and not UI_MODE:
        props = bpy.context.window_manager.brush_manager_props
        store_favorites_list(MODE, 'STORE')
        CURRENT_MODE_CATEGORY[MODE] = props.lib_categories
        pre_mode = MODE
        MODE = bpy.context.mode
        if UI_MODE:
            MODE = 'PAINT_TEXTURE'
        if CURRENT_MODE_CATEGORY.get(MODE):
            props.lib_categories = CURRENT_MODE_CATEGORY.get(MODE)
        else:
            props.lib_categories = 'Default'
        switching_modes(pre_mode)
        update_brush_list(self, bpy.context)
        update_fav_list(self, bpy.context)


class BM_PT_Brush_Manager(Panel):
    bl_label = "Brush Manager"
    bl_idname = "VIEW3D_PT_brush_manager"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = "VIEW3D_PT_tools_brush_select"

    @classmethod
    def poll(cls, context):
        if context.mode in BM_Modes.in_modes:
            return True
        else:
            return False

    def __init__(self):
        init_bm_panel(self)

    def draw(self, context):
        layout = self.layout
        BM_Side_Panel.draw(self, context, layout)


class GPENCIL_PT_Brush_Manager(Panel):
    bl_label = "Brush Manager"
    bl_idname = "VIEW3D_PT_brush_manager_gpencil"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = "VIEW3D_PT_tools_grease_pencil_brush_select"

    @classmethod
    def poll(cls, context):
        if context.mode == 'PAINT_GPENCIL':
            return True

    def __init__(self):
        init_bm_panel(self)

    def draw(self, context):
        layout = self.layout
        BM_Side_Panel.draw(self, context, layout)


class GPENCILVP_PT_Brush_Manager(Panel):
    bl_label = "Brush Manager"
    bl_idname = "VIEW3D_PT_brush_manager_gpencil_vertex_paint"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = "VIEW3D_PT_tools_grease_pencil_vertex_paint_select"

    @classmethod
    def poll(cls, context):
        if context.mode == 'VERTEX_GPENCIL':
            return True

    def __init__(self):
        init_bm_panel(self)

    def draw(self, context):
        layout = self.layout
        BM_Side_Panel.draw(self, context, layout)


panels = (
    BM_PT_Brush_Manager,
    GPENCIL_PT_Brush_Manager,
    GPENCILVP_PT_Brush_Manager,
)


def update_panel(self, context):
    for panel in panels:
        if "bl_rna" in panel.__dict__:
            bpy.utils.unregister_class(panel)

    for panel in panels:
        prefs = context.preferences.addons[Addon_Name].preferences
        if prefs.ui_panel_closed:
            panel.bl_options = {'DEFAULT_CLOSED'}  # {'HIDE_HEADER'} {'DEFAULT_CLOSED'}
        bpy.utils.register_class(panel)


def draw_keymaps(self, context, layout):
    box = layout.box()
    row = box.row()
    row.label(text="Keymaps:", icon="KEYINGSET")
    row.prop(self, "persistent_keymaps")

    col = box.column()

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    old_km_name = ""
    get_kmi_l = []
    for km_add, kmi_add in addon_keymaps:
        for km_con in kc.keymaps:
            if km_add.name == km_con.name:
                km = km_con
                break

        for kmi_con in km.keymap_items:
            if kmi_add.idname == kmi_con.idname:
                if kmi_add.name == kmi_con.name:
                    get_kmi_l.append((km, kmi_con))

    get_kmi_l = sorted(set(get_kmi_l), key=get_kmi_l.index)

    for km, kmi in get_kmi_l:
        if not km.name == old_km_name:
            col.label(text=str(km.name), icon="DOT")
        col.context_pointer_set("keymap", km)
        rna_keymap_ui.draw_kmi([], kc, km, kmi, col, 0)
        col.separator()
        old_km_name = km.name


def draw_similar_settings(self, context, layout, mode=''):
    modes = BM_Modes()
    props = dict(
        preview_frame_scale=dict(
            label="Preview Frame Row Size:",
            prop=modes.Modes[mode].get('preview_frame_scale')
        ),
        popup_items_scale=dict(
            label="Popup Button List Size:",
            prop=modes.Modes[mode].get('popup_items_scale')
        ),
        wide_popup_layout=dict(
            prop=modes.Modes[mode].get('wide_popup_layout')
        ),
        wide_popup_layout_size=dict(
            prop=modes.Modes[mode].get('wide_popup_layout_size')
        ),
        popup_width=dict(
            label="Popup Window Width:",
            prop=modes.Modes[mode].get('popup_width')
        ),
        popup_max_tool_columns=dict(
            label="Popup Max Tool Columns:",
            prop=modes.Modes[mode].get('popup_max_tool_columns')
        ),
    )
    prop_col = layout.column()
    box = prop_col.box()
    col = box.column(align=True)
    col.label(text="Specify a path to a folder containing sub-folders with your brushes mode collections in *.blend files.")
    col = box.column(align=True)
    col.label(text="Brush Library Path:")
    col.prop(self, modes.Modes[mode].get('brush_library'))

    row = box.row()
    row.prop(self, modes.Modes[mode].get('use_startup_favorites'))
    row = box.row()
    row.enabled = eval('self.' + modes.Modes[mode].get('use_startup_favorites'))
    row.prop(self, modes.Modes[mode].get('path_to_startup_favorites'), text='')

    row = box.row()
    if self.show_UI:
        row.prop(self, "show_UI", icon='TRIA_DOWN', toggle=True)
        draw_assign_next = False
        popup_width_enable = not eval('self.' + modes.Modes[mode].get('wide_popup_layout'))
        for pr in props:
            if not draw_assign_next:
                row = box.row()
                if pr == 'popup_width':
                    row.enabled = popup_width_enable
            if props[pr].get('label'):
                row.label(text=props[pr].get('label'))
            elif not draw_assign_next:
                row.prop(self, props[pr].get('prop'))
                draw_assign_next = True
                continue
            row = row.row(align=True)
            row.scale_x = 0.96
            row.prop(self, props[pr].get('prop'), text='')
            op = row.operator("bm.assign_to_similar", text='', icon='CHECKMARK')
            op.prop = pr
            op.mode = mode
            draw_assign_next = False
            if pr == 'preview_frame_scale' and mode == 'SCULPT':
                row = box.row()
                row.label(text="Preview Brush Size:")
                row.prop(self, "preview_items_scale", text='')
            if pr == 'popup_max_tool_columns' and mode == 'SCULPT':
                row = box.row()
                row.label(text="Brush Icon Theme:")
                row.prop(self, "brush_icon_theme", text='')
    else:
        row.prop(self, "show_UI", icon='TRIA_RIGHT', toggle=True)

    is_split_tools = modes.Modes[mode].get('is_split_tools')

    bm = modes.mode_prefixes.get(mode)
    box = layout.box()

    row = box.row()
    if self.show_tools:
        row.prop(self, "show_tools", icon='TRIA_DOWN', toggle=True)
        # row.label(text="Tools:")
        row = box.row(align=True)
        grid = row.grid_flow(even_columns=True, even_rows=True, columns=3, align=True)  # row_major=True,
        o_tools = modes.Modes[mode].get('other_tools_list')
        for o_tool in o_tools:
            t = o_tool.replace(' ', '')
            t = t.replace('-', '')
            grid.prop(self, bm + '_tool_' + t, text=o_tool, icon='TOOL_SETTINGS', toggle=True)

        row = box.row(align=True)
        box.label(text="Default Brushes List:")
        row = box.row(align=True)
        grid = row.grid_flow(columns=3, align=True)
        if is_split_tools:
            brushes = modes.Modes[mode].get('def_brush_names')
        else:
            brushes = modes.Modes[mode].get('def_brushes_tool_list')

        for brush in brushes:
            b = brush.replace(' ', '')
            b = b.replace('-', '')
            if not is_split_tools:
                try:
                    exec("if self.default_" + bm + "_brush_" + b + " != '': pass")
                    grow = grid.row(align=True)
                    grow.prop(self, 'default_' + bm + '_brush_' + b, toggle=True)
                    grow.prop(self, bm + '_tool_brush_' + b, text='', icon='BRUSHES_ALL', toggle=True)
                except AttributeError:
                    continue
            else:
                try:
                    exec("if self.default_" + bm + "_brush_" + b + " != '': pass")
                    grid.prop(self, 'default_' + bm + '_brush_' + b, toggle=True)
                except AttributeError:
                    continue
        if not is_split_tools:
            return prop_col, box
        row = box.row(align=True)
        row.label(text="Brush Tools:")
        row = box.row(align=True)
        grid = row.grid_flow(columns=4, align=True)
        b_tools = modes.Modes[mode].get('def_brushes_tool_list')
        for b_tool in b_tools:
            b = b_tool.replace(' ', '')
            b = b.replace('-', '')
            grid.prop(self, bm + '_tool_brush_' + b, text=b_tool, icon='BRUSHES_ALL', toggle=True)
    else:
        row.prop(self, "show_tools", icon='TRIA_RIGHT', toggle=True)

    return prop_col, box


def draw_preferences(self, context, layout):
    # prefs = context.preferences.addons[Addon_Name].preferences
    # layout = self.layout
    row = layout.row()
    if self.show_common:
        row.prop(self, "show_common", icon='TRIA_DOWN', toggle=True)

        box = layout.box()
        row = box.row()
        grid = row.grid_flow(columns=2, align=True)
        grid.prop(self, "hide_header")
        grid.prop(self, "move_add_to_favorite_op")
        grid.prop(self, "ui_panel_closed")
        grid.prop(self, "save_favorites_list")
        grid.prop(self, "close_popup_on_select")
        grid.prop(self, "popup_tools")
        grid.prop(self, "brush_tools")
        grid.prop(self, "hide_annotate_tools")
    else:
        row.prop(self, "show_common", icon='TRIA_RIGHT', toggle=True)

    row = layout.row()
    if self.show_keymaps:
        row.prop(self, "show_keymaps", icon='TRIA_DOWN', toggle=True)
        draw_keymaps(self, context, layout)
    else:
        row.prop(self, "show_keymaps", icon='TRIA_RIGHT', toggle=True)

    row = layout.row(align=True)
    row.prop(self, "pref_tabs", expand=True)

    modes = BM_Modes()
    if self.pref_tabs in modes.in_modes:
        prop_col, tools_box = draw_similar_settings(self, context, layout, mode=self.pref_tabs)
    if self.pref_tabs == 'SCULPT':
        box = prop_col.box()
        grid = box.grid_flow(columns=2, align=True)
        grid.prop(self, "default_brushes_custom_icon")
        grid.prop(self, "selected_brush_custom_icon")
        row = grid.row()
        row.enabled = self.selected_brush_custom_icon
        row.prop(self, "force_brush_custom_icon")
        grid.prop(self, "sculpt_hide_preview")
        grid.prop(self, "switch_mode_on_save")

        wm = bpy.context.window_manager
        box = tools_box
        row = box.row(align=True)
        row.label(text="Custom Default Brush Slots:")
        row.prop(self, "default_brushes_custom_slots", text="")
        row.operator("bm.refresh_brushes_data_list", icon='FILE_REFRESH')
        row = box.row(align=True)
        grid = row.grid_flow(columns=3, align=True)
        for i in range(self.default_brushes_custom_slots):
            grid.prop_search(self, 'add_def_brush_' + str(i), wm, "bm_brushes_data_list", text="")
    if self.pref_tabs == 'PAINT_WEIGHT':
        box = prop_col.box()
        grid = box.grid_flow(columns=2, align=True)
        grid.prop(self, "default_wp_brushes_custom_icon")
        # 'default_custom_icons': 'default_wp_brushes_custom_icon',
    if self.pref_tabs == 'PAINT_VERTEX':
        box = prop_col.box()
        grid = box.grid_flow(columns=2, align=True)
        grid.prop(self, "default_vp_brushes_custom_icon")
    if self.pref_tabs == 'VERTEX_GPENCIL':
        box = prop_col.box()
        grid = box.grid_flow(columns=2, align=True)
        grid.prop(self, "default_gv_brushes_custom_icon")

    row = layout.row(align=True)
    row.operator("bm.save_pref_settings", icon='EXPORT')
    row.operator("bm.load_pref_settings", icon='IMPORT')


class PREF_OT_assign_to_similar_settings(Operator):
    bl_label = 'Assign to Similar'
    bl_idname = 'bm.assign_to_similar'
    bl_description = "Assign the current value to similar settings in other modes"

    prop: StringProperty()
    mode: StringProperty()

    def execute(self, context):
        prefs = context.preferences.addons[Addon_Name].preferences
        modes = BM_Modes()
        mode_prop = modes.Modes[self.mode].get(self.prop)
        value = eval('prefs.' + mode_prop)
        for m in modes.in_modes:
            mode_prop = modes.Modes[m].get(self.prop)
            exec("prefs." + mode_prop + " = value")

        return {'FINISHED'}


class BrushManager_Preferences(AddonPreferences):

    bl_idname = Addon_Name

    modes = BM_Modes()
    tabs_items = []
    for m in modes.in_modes:
        if m.split('_')[-1] != m.split('_')[0]:
            tab_name = (
                m.split('_')[-1].capitalize() + (
                    " " + m.split('_')[0].capitalize()
                ))
        else:
            tab_name = m.capitalize()
        tabs_items.append((m, tab_name, ''))
    del tab_name

    pref_tabs: EnumProperty(
        name='Add-on Settings Tabs',
        items=tabs_items,
        description='Select a settings tab',
        default='SCULPT',
    )
    wide_items = [
        ('225', 'Tiny', ''),
        ('250', 'Smaller', ''),
        ('300', 'Small', ''),
        ('350', 'Medium', ''),
        ('425', 'Big', ''),
        ('475', 'Bigger', ''),
        ('525', 'Large', ''),
        ('600', 'Largest', ''),
    ]
    for m in modes.in_modes:
        prop = modes.Modes[m].get('brush_library')
        description = 'The main library folder containing sub-folders with the *.blend files of this mode brushes'
        exec(
            prop + ": StringProperty("
            "name='', subtype='DIR_PATH',"
            "description=description)"
        )
        prop = modes.Modes[m].get('use_startup_favorites')
        name = "Use Startup Favorites"
        description = "Automatically load the Favorites list from the specified file if that list is empty in the current file"
        exec(
            prop + ": BoolProperty("
            "name=name, default=False,"
            "description=description)"
        )
        prop = modes.Modes[m].get('path_to_startup_favorites')
        name = "Path to the Mode Startup Favorites List"
        description = 'The path to the .blend file that contains a list of brushes for the Mode Favorites'
        exec(
            prop + ": StringProperty("
            "name=name, subtype='FILE_PATH',"
            "description=description)"
        )
        prop = modes.Modes[m].get('preview_frame_scale')
        name = "Preview Frame Row Size"
        description = 'Scale the size of the preview frames row on the Brushes Manager UI panel'
        exec(
            prop + ": FloatProperty("
            "name=name, min=1, max=6.5, default=2,"
            "description=description)"
        )
        prop = modes.Modes[m].get('popup_items_scale')
        name = "Popup Button List Size"
        description = 'Scale the size of icon and button in the popup list'
        exec(
            prop + ": FloatProperty("
            "name=name, min=1, max=5, default=1.8,"
            "description=description)"
        )
        prop = modes.Modes[m].get('popup_width')
        name = "Popup Window Width"
        description = 'Scale the size of the popup window width'
        exec(
            prop + ": IntProperty("
            "name=name, min=100, soft_min=100, max=600, soft_max=600, default=180,"
            "description=description)"
        )
        prop = modes.Modes[m].get('popup_max_tool_columns')
        name = "Popup Max Tool Columns"
        description = 'Set a maximum number of the columns for tools in the popup window'
        exec(
            prop + ": IntProperty("
            "name=name, min=1, soft_min=1, max=12, soft_max=12, default=4,"
            "description=description)"
        )
        prop = modes.Modes[m].get('wide_popup_layout')
        name = 'Wide Popup Layout'
        description = 'Let Tools to show on the right side of the popup layout'
        exec(
            prop + ": BoolProperty("
            "name=name, default=False,"
            "description=description)"
        )
        prop = modes.Modes[m].get('wide_popup_layout_size')
        name = 'Wide Popup Layout Size'
        description = 'Scale the size of the popup layout'
        exec(
            prop + ": EnumProperty("
            "name=name, items=wide_items, default='350',"
            "description=description)"
        )
        prop = modes.Modes[m].get('wide_popup_layout_size')
        name = 'Wide Popup Layout Size'
        description = 'Scale the size of the popup layout'
        exec(
            prop + ": EnumProperty("
            "name=name, items=wide_items, default='350',"
            "description=description)"
        )
    del name
    del prop
    del description
    #////////////////////////
    ui_panel_closed: BoolProperty(
        name="UI Panel Default Closed",
        default=False,
        description="Register the UI panel closed by default. In order to use it properly startup file have to use factory settings for that panel",
        update=update_panel
    )
    preview_items_scale: FloatProperty(
        name="Preview Items Size",
        min=1,
        max=7,
        default=2.8,
        description='Scale the size of icon in the brushes preview list'
    )
    hide_header: BoolProperty(
        name="Hide Header in the Popup Window",
        default=False,
        description="Hide header buttons in the popup window and move them into the Menu"
    )
    move_add_to_favorite_op: BoolProperty(
        name="Move \'Add to the Favorites\' into Menu",
        default=False,
        description="Move the \'Add to the Favorites\' operator from UI panel into own menu."
    )
    brush_icon_theme: EnumProperty(
        name='Icon Theme',
        items=set_brush_icon_themes,
        description="Select a theme for the brushes preview and custom icons",
        update=update_icon_theme
    )
    default_brushes_custom_icon: BoolProperty(
        name="Apply Custom Icon Theme",
        default=False,
        description="On launch every brush with the default name will have themed custom icon turned on.\
 These brushes could be specified in the add-on preference settings",
        update=update_pref_apply_theme_to_def
    )
    default_wp_brushes_custom_icon: BoolProperty(
        name="Apply Custom Icons",
        default=False,
        description="On launch every brush with the default name will have themed custom icon turned on.\
 These brushes could be specified in the add-on preference settings",
        update=update_pref_apply_theme_to_def
    )
    default_vp_brushes_custom_icon: BoolProperty(
        name="Apply Custom Icons",
        default=False,
        description="On launch every brush with the default name will have themed custom icon turned on.\
 These brushes could be specified in the add-on preference settings",
        update=update_pref_apply_theme_to_def
    )
    default_gv_brushes_custom_icon: BoolProperty(
        name="Apply Custom Icons",
        default=False,
        description="On launch every brush with the default name will have themed custom icon turned on.\
 These brushes could be specified in the add-on preference settings",
        update=update_pref_apply_theme_to_def
    )
    selected_brush_custom_icon: BoolProperty(
        name="Auto Apply Theme to the Selected Brush",
        default=False,
        description="Allows for the Brush Manager to automatically\
 apply a custom icon to the selected brush from any category list if it has not applied yet.",
        update=update_pref_apply_theme_to_selected
    )
    force_brush_custom_icon: BoolProperty(
        name="Force to Apply Theme to the Selected Brush",
        default=False,
        description="Allows for the Brush Manager a force to set a custom icon\
 to the selected brush even if it has been applied already.",
        update=update_pref_force_apply_theme_to_sel
    )
    save_favorites_list: BoolProperty(
        name="Save Favorites List to the Current File",
        default=False,
        description="On Save include the favorites brushes in the current file data and memorize the current favorites list"
    )
    sculpt_hide_preview: BoolProperty(
        name="Hide Preview Frame",
        default=False,
        description="Hide brush preview frame, make UI layout the same look, as its like in other modes"
    )
    switch_mode_on_save: BoolProperty(
        name="Switch Mode on Save",
        default=False,
        description="Switch to the Object Mode on save if currently in the Sculpt Mode.\
 Useful if you want to avoid of the undo limitation when opening the current file leading directly into the Sculpt Mode",
    )
    popup_tools: BoolProperty(
        name='Show Tools in Popup',
        description='Show tools by default in the popup window',
        default=False,
        update=update_tools_popup
    )
    brush_tools: BoolProperty(
        name='Brush Tools in Popup',
        description='Show brush tools by default in the popup window',
        default=False,
        update=update_brush_tools_popup
    )
    hide_annotate_tools: BoolProperty(
        name='Hide Annotate Tools in Popup',
        description='Hide Annotate tools in the tools list of the popup window',
        default=True
    )
    show_common: BoolProperty(
        name='Common',
        description='Show Common settings',
        default=False,
    )
    show_UI: BoolProperty(
        name='UI',
        description='Show UI settings',
        default=False,
    )
    show_keymaps: BoolProperty(
        name='Keymaps',
        description='Show keymap settings',
        default=False,
    )
    show_tools: BoolProperty(
        name='Tools and Brushes',
        description='Show tool and brush settings',
        default=False,
    )
    persistent_keymaps: BoolProperty(
        name='Persistent Keymaps',
        description='Keep the same keymap settings for the app templates',
        default=True,
    )
    close_popup_on_select: BoolProperty(
        name='Close Popup on Tool Select',
        description='Close popup windows when brush or tool have been selected',
        default=True,
    )
    for bm_mode in modes.in_modes:
        is_split_tools = modes.Modes[bm_mode].get('is_split_tools')
        if is_split_tools:
            brushes = modes.Modes[bm_mode].get('def_brush_names')
        else:
            brushes = modes.Modes[bm_mode].get('def_brushes_tool_list')
        bm = modes.mode_prefixes.get(bm_mode)
        for brush in brushes:
            b = brush.replace(' ', '')
            b = b.replace('-', '')
            default_brush = 'default_' + bm + '_brush_' + b  # str(i)
            if modes.Modes[bm_mode].get('use_custom_icons'):
                func = 'update_pref_def_' + bm + '_brush'
                exec(default_brush + ': BoolProperty(name="' + brush + '", default = True, update=' + func + ')')
            else:
                exec(default_brush + ': BoolProperty(name="' + brush + '", default = True, update=update_brush_list)')
            update_brush_list
            if is_split_tools:
                continue
            tool_brush = bm + '_tool_brush_' + b
            exec(tool_brush + ': BoolProperty(name="' + brush + '", default = True)')
        o_tools = modes.Modes[bm_mode].get('other_tools_list')
        for o_tool in o_tools:
            b = o_tool.replace(' ', '')
            b = b.replace('-', '')
            other_tool = bm + '_tool_' + b
            exec(other_tool + ': BoolProperty(name="' + o_tool + '", default = True)')
        if not is_split_tools:
            continue
        b_tools = modes.Modes[bm_mode].get('def_brushes_tool_list')
        for b_tool in b_tools:
            b = b_tool.replace(' ', '')
            b = b.replace('-', '')
            tool_brush = bm + '_tool_brush_' + b
            exec(tool_brush + ': BoolProperty(name="' + b_tool + '", default = True)')
    del b
    del other_tool
    del tool_brush
    del func
    del brushes
    del b_tools
    del o_tools
    del is_split_tools
    del bm

    default_brushes_custom_slots: IntProperty(
        name="Custom Default Brush Slots",
        min=3,
        max=12,
        default=3,
        description="Number of slots down below for the custom Default brush"
    )
    name = "Custom Default Brush"
    description = "Slot for other brushes that are not exists in the Default Brushes list.\
 Brush Manager will treat it as a Default brush that initialy will be listed in the\
 Default category on a file load if it exists in the loaded data"
    for i in range(12):
        exec("add_def_brush_" + str(i) + ": StringProperty(name='" + name + "', description='" + description + "')")

    def draw(self, context):
        # prefs = context.preferences.addons[Addon_Name].preferences
        layout = self.layout
        draw_preferences(self, context, layout)


class PREF_OT_Refresh_Brushes_Data_List(Operator):
    bl_idname = "bm.refresh_brushes_data_list"
    bl_label = "Refresh Brushes Data"
    bl_description = "Refresh a list of brushes in the current file data"

    def execute(self, context):
        set_brushes_data_collection_items()
        return {'FINISHED'}


def set_brushes_data_collection_items():
    """This is to be called on loading a new file or reloading addons
    """
    try:
        brushes_data_list = bpy.context.window_manager.bm_brushes_data_list
    except AttributeError:
        return None
    modes = BM_Modes('SCULPT')
    brushes_current_file = get_current_file_brushes('SCULPT')
    brushes_default = modes.def_brushes_list()
    brushes_sort = [b for b in brushes_current_file if b not in brushes_default]
    brushes_data_list.clear()
    for name in brushes_sort:
        item = brushes_data_list.add()
        item.name = name


def brush_manager_pre_undo(scene):
    try:
        b_preview_coll = preview_brushes_coll["main"]
    except KeyError:
        return None
    b_preview_undo = preview_brushes_coll["undo"]
    b_preview_undo.my_previews = b_preview_coll.my_previews

    b_preview_fav = preview_brushes_coll["favorites"]
    b_preview_undof = preview_brushes_coll["undofav"]
    b_preview_undof.my_previews = b_preview_fav.my_previews


def brush_manager_post_undo(scene):
    try:
        props = bpy.context.window_manager.brush_manager_props
    except AttributeError:
        return None
    if not props.brush_manager_init:
        return None
    if bpy.context.mode != 'SCULPT' and not props.post_undo_last and MODE == 'SCULPT':
        props.post_undo_last = True
        bpy.ops.sculpt.sculptmode_toggle()
        create_default_sculpt_tools()
        bpy.ops.sculpt.sculptmode_toggle()
        set_toggle_default_icons(bpy.context)

    b_preview_coll = preview_brushes_coll["main"]
    b_preview_undo = preview_brushes_coll["undo"]
    b_preview_coll.my_previews = b_preview_undo.my_previews
    b_preview_coll.my_previews_dir = ""

    b_preview_fav = preview_brushes_coll["favorites"]
    b_preview_undof = preview_brushes_coll["undofav"]
    b_preview_fav.my_previews = b_preview_undof.my_previews
    b_fav = get_favorite_brushes()
    b_preview_fav.my_previews_dir = ""


@persistent
def brush_manager_on_file_load(dummy):
    global FAV_SETTINGS_LOADED
    global START_FAV_LOADED
    global IS_INIT_SMEAR
    # global SET_DEFAULT_ICONS
    global MODE
    global UI_MODE
    FAV_SETTINGS_LOADED.clear()
    START_FAV_LOADED.clear()
    IS_INIT_SMEAR.clear()
    MODE = None
    UI_MODE = False
    try:
        check = bpy.context.window_manager.bm_brushes_data_list
    except AttributeError:
        return None
    set_brushes_data_collection_items()
    clear_favorites_list()
    clear_Default_list()


def brush_manager_pre_save(dummy):
    prefs = bpy.context.preferences.addons[Addon_Name].preferences
    props = bpy.context.window_manager.brush_manager_props
    for mode in BM_Modes.in_modes:
        if SET_DEFAULT_ICONS.get(mode):
            set_toggle_default_icons(bpy.context, switch=True, mode=mode, force=True)
        if prefs.save_favorites_list:
            store_favorites_list(mode, 'SETTINGS')
    if bpy.context.mode == 'SCULPT' and prefs.switch_mode_on_save:
        bpy.ops.sculpt.sculptmode_toggle()


def brush_manager_post_save(dummy):
    bpy.context.window_manager.brush_manager_props.update_after_save = True


def brush_manager_pre_dp_update(dummy):
    props = bpy.context.window_manager.brush_manager_props
    if not props.update_after_save:
        return None
    props.update_after_save = False
    if props.set_default_brushes_custom_icon or SET_DEFAULT_ICONS.get(bpy.context.mode):
        set_toggle_default_icons(bpy.context, mode=bpy.context.mode)


class Brushes_Data_Collection(PropertyGroup):
    name: StringProperty(name="Custom Default Brush")


def BM_Initialization():
    props = bpy.context.window_manager.brush_manager_props
    b_preview_coll = preview_brushes_coll["main"]
    if bpy.data.scenes[0].name == 'Empty' and props.manager_empty_init is True:
        return None
    if bpy.data.scenes[0].name != 'Empty' and props.brush_manager_init is True:
        return None
    initialize_brush_manager_ui(props, b_preview_coll)


def load_favorites_in_mode():
    loaded = False
    if not FAV_SETTINGS_LOADED.get(MODE):
        loaded = load_saved_favorites_list(MODE, 'SETTINGS')
    if not START_FAV_LOADED.get(MODE):
        create_default_sculpt_tools()
        if not loaded:
            loaded = load_startup_favorites(MODE)
    if not loaded:
        load_saved_favorites_list(MODE, 'STORE')


def set_ui_mode(context, from_ui='refresh'):
    global UI_MODE
    try:
        if context.space_data.ui_mode == 'PAINT':
            UI_MODE = True
    except AttributeError:
        UI_MODE = False
        return False


def switch_icons(pre_mode=''):
    global SET_DEFAULT_ICONS
    global SET_SELECTED_ICON
    props = bpy.context.window_manager.brush_manager_props
    modes = BM_Modes()

    if pre_mode and modes.Modes[pre_mode].get('use_custom_icons'):
        is_icons = eval('prefs().' + modes.Modes[pre_mode].get('default_custom_icons'))
        if is_icons:
            set_toggle_default_icons(bpy.context, switch=True, mode=pre_mode)
            SET_DEFAULT_ICONS[pre_mode] = True

    if not modes.Modes[MODE].get('use_custom_icons'):
        if props.set_default_brushes_custom_icon:
            props.set_default_brushes_custom_icon = False
            SET_DEFAULT_ICONS[MODE] = True

    if modes.Modes[MODE].get('use_custom_icons') and not UI_MODE:
        is_icons = eval('prefs().' + modes.Modes[MODE].get('default_custom_icons'))
        if SET_DEFAULT_ICONS.get(MODE) or is_icons:
            props.set_default_brushes_custom_icon = True
        else:
            props.set_default_brushes_custom_icon = False


def switching_modes(pre_mode=''):
    load_favorites_in_mode()
    if pre_mode:
        switch_icons(pre_mode)
    else:
        switch_icons()


def draw_favorite_brushes(layout, context):
    space_type = context.space_data.type
    toolhelper = space_toolsystem_common.ToolSelectPanelHelper
    tool_active_id = getattr(
        toolhelper._tool_active_from_context(context, space_type),
        "idname", None,)
    fav_brushes = get_favorite_brushes()
    for brush in fav_brushes:
        row = layout.row(align=True)
        row.alignment = 'EXPAND'
        is_active = is_active_brush(context, brush)
        if MODE == 'SCULPT':
            op = row.operator("bm.set_brush", text=brush, emboss=True, depress=is_active)
            op.brush = brush
            op.from_list = "fav_brush_popup"
        else:
            if MODE == 'PAINT_GPENCIL':
                if not tool_active_id.startswith("builtin_brush"):
                    op = row.operator(
                        "bm.select_brush", text='',
                        icon='GREASEPENCIL', depress=is_active)
                    op.brush = brush
                    op.from_list = "fav_brush_popup"
                    op.no_tool = True
            op = row.operator("bm.select_brush", text=brush, depress=is_active)
            op.brush = brush
            op.from_list = "fav_brush_popup"
            op.no_tool = False


def draw_remove_fav_brushes(layout, context):
    fav_brushes = get_favorite_brushes()
    for brush in fav_brushes:
        op = layout.operator("bm.remove_from_favorites", icon='REMOVE', text='', emboss=True)
        op.brush_name = brush


def popup_close():
    bpy.context.window.screen = bpy.context.window.screen


def tool_updated():
    if Popup_Close:
        popup_close()
    return 0.2


Popup_Close = False


def get_tools_for_popup(context, mode=''):
    prefs = context.preferences.addons[Addon_Name].preferences
    props = context.window_manager.brush_manager_props
    brush_tool_items = []
    other_tool_items = []
    if mode == '':
        mode = context.mode
    tools = space_toolsystem_toolbar.VIEW3D_PT_tools_active.tools_from_context(context, mode)
    brush_tools = get_pref_default_brush_props(list_type='tools')
    other_tools = get_pref_default_brush_props(list_type='other_tools')
    for item in tools:
        if item is None:
            continue
        if type(item) is tuple:
            for sub_item in item:
                if not props.popup_tools_switch:
                    continue
                if sub_item.idname.startswith("builtin.annotate") and\
                        prefs.hide_annotate_tools:
                    continue
                if other_tools.get(sub_item.label):
                    other_tool_items.append(sub_item)
            continue
        if item.idname.startswith("builtin_brush"):
            if not props.show_brush_tools:
                continue
            if not brush_tools.get(item.label):
                continue
            brush_tool_items.append(item)
            continue
        if not props.popup_tools_switch:
            continue
        if other_tools.get(item.label):
            other_tool_items.append(item)
    return brush_tool_items, other_tool_items


def draw_popup_tools(layout, items, tool_active_id):
    toolhelper = space_toolsystem_common.ToolSelectPanelHelper
    for item in items:
        icon_value = toolhelper._icon_value_from_icon_handle(item.icon)
        is_active = (item.idname == tool_active_id)
        layout.operator(
            "wm.tool_set_by_id",
            # text=item.label,
            text="",
            depress=is_active,
            icon_value=icon_value,
        ).name = item.idname


class POPUP_OT_Tools_and_Brushes(Operator):
    bl_label = 'Brush Manager Popup Menu'
    bl_idname = 'bm.tools_and_brushes_popup'

    timer = True

    def __del__(self):
        global UI_MODE
        UI_MODE = False
        global Popup_Close
        Popup_Close = False
        if prefs().close_popup_on_select and not self.timer:
            bpy.app.timers.unregister(tool_updated)

    def __init__(self):
        self.active_tool = None
        if prefs().close_popup_on_select:
            self.timer = bpy.app.timers.register(tool_updated)

    def execute(self, context):
        modes = BM_Modes()
        space = context.space_data.type
        if space == 'VIEW_3D' and (context.mode in modes.in_modes) or\
                (context.space_data.ui_mode == 'PAINT'):
            prefs = context.preferences.addons[Addon_Name].preferences
            props = context.window_manager.brush_manager_props
            set_ui_mode(context, 'popup')
            BM_Initialization()
            global MODE
            global CURRENT_MODE_CATEGORY
            if context.mode != MODE or UI_MODE:
                store_favorites_list(MODE, 'STORE')
                if not UI_MODE:
                    CURRENT_MODE_CATEGORY[MODE] = props.lib_categories
                else:
                    props.lib_categories = 'Default'
                preMode = MODE
                if UI_MODE:
                    MODE = 'PAINT_TEXTURE'
                else:
                    MODE = context.mode
                if CURRENT_MODE_CATEGORY.get(MODE) and not UI_MODE:
                    props.lib_categories = CURRENT_MODE_CATEGORY.get(MODE)
                else:
                    props.lib_categories = 'Default'
                switching_modes(preMode)
                update_brush_list(self, context)
                update_fav_list(self, context)
            if modes.wide_popup_layout():
                layout_width = int(modes.wide_popup_layout_size())
            else:
                layout_width = modes.popup_width()
            return context.window_manager.invoke_popup(self, width=layout_width)
        else:
            return {'CANCELLED'}

    def draw_header(self, context, layout):
        props = context.window_manager.brush_manager_props
        layout.emboss = 'NONE'
        col_one = layout.column()
        col_two = layout.column()
        row = col_one.row()
        row.prop(props, "popup_tools_switch", text='', icon='TOOL_SETTINGS')
        row.prop(props, "show_brush_tools", text='', icon='BRUSHES_ALL')
        row.operator("bm.settings_popup", text='', icon='PREFERENCES')
        row = row.row()  # align=True
        row.label(text=' ')
        row.menu("VIEW3D_MT_Sculpt_brush_manager_menu", icon='DOWNARROW_HLT', text="")

    def draw(self, context):
        prefs = context.preferences.addons[Addon_Name].preferences
        props = context.window_manager.brush_manager_props
        wm = bpy.context.window_manager

        layout = self.layout
        tools = get_tools_for_popup(context, MODE)
        modes = BM_Modes()
        popup_items_scale = modes.popup_items_scale()
        preview_frame_scale = modes.preview_frame_scale()
        if ((not props.popup_tools_switch and not props.show_brush_tools) or (
                not tools[0] and not tools[1])) and\
                modes.wide_popup_layout():
            layout_width = int(modes.wide_popup_layout_size())
            n = modes.popup_max_tool_columns()
            units = (layout_width / (n * 5.35 + 18.6))
            if (units - round(units, 1)) > 0:
                units = round(units, 1) + 0.05
            layout.ui_units_x = units
            del n

        if not prefs.hide_header:
            header = layout.row()
            self.draw_header(context, header)
        mainrow = layout.row()

        col_one = mainrow.column()
        if modes.wide_popup_layout():
            col_one.ui_units_x = 5
            col_two = mainrow.column()
        row = col_one.row(align=True)
        if MODE == 'SCULPT':
            row.prop(props, "lib_categories", text='')
        else:
            row.operator_menu_enum('bm.set_brushes_category', 'lib_category', text=props.lib_categories)
        if props.lib_categories != 'Default' and props.lib_categories != 'Current File':
            row.operator('bm.category_folder', text='', icon='FILE_FOLDER')
        row.operator('bm.update_category_list', text='', icon='FILE_REFRESH')
        row.prop(props, "search_in_category", text='', icon='VIEWZOOM')
        if props.search_in_category:
            row = col_one.row(align=True)
            row.prop(props, "search_bar", text='')
            row.prop(props, "search_case_sensitive", text='', icon='SMALL_CAPS')
        row = col_one.row(align=True)
        if MODE == 'SCULPT' and not prefs.sculpt_hide_preview:
            if not prefs.sculpt_hide_preview:
                prow = row.row(align=True)
                prow.scale_x = 0.91
                prow.template_icon_view(
                    wm, "brushes_in_files", show_labels=True,
                    scale=preview_frame_scale, scale_popup=prefs.preview_items_scale)
        else:
            preview_brushes_in_folders(self, context)
        row = row.row(align=True)
        row.scale_y = preview_frame_scale
        row.operator("bm.add_to_favorites_popup", text='Select/Add', icon='PRESET_NEW')
        if not prefs.move_add_to_favorite_op:
            row.operator('bm.add_brush_to_favorites', text='', icon='ADD')
        if prefs.hide_header:
            row.menu("VIEW3D_MT_Sculpt_brush_manager_menu", icon='DOWNARROW_HLT', text="")

        row = col_one.row(align=True)
        col = row.column(align=True)
        enums = preview_brushes_in_favorites(self, context)
        icons = get_favorite_brushes(list_type='icons')
        for i, icon in enumerate(icons):
            col.template_icon(icon_value=icon, scale=popup_items_scale)
        col = row.column(align=True)
        col.scale_y = popup_items_scale

        draw_favorite_brushes(col, context)

        if props.edit_favorites:
            col = row.column(align=True)
            col.scale_y = popup_items_scale

            draw_remove_fav_brushes(col, context)
        #//////////////Tools//////////////
        if not props.popup_tools_switch and not props.show_brush_tools:
            return None
        if not tools[0] and not tools[1]:
            return None

        if modes.wide_popup_layout():
            col = col_two.column(align=False)
        else:
            col = col_one.column(align=False)
        col.scale_y = popup_items_scale

        toolhelper = space_toolsystem_common.ToolSelectPanelHelper
        space_type = context.space_data.type
        tool_active_id = getattr(
            toolhelper._tool_active_from_context(context, space_type),
            "idname", None,
        )
        #///////////////////
        if self.active_tool and prefs.close_popup_on_select:
            if self.active_tool != tool_active_id:
                global Popup_Close
                Popup_Close = True
        else:
            self.active_tool = tool_active_id
        #//////////////////
        if props.show_brush_tools:
            bgrid = col.grid_flow(
                row_major=True, columns=modes.popup_max_tool_columns(),
                even_columns=True, even_rows=True, align=True)
            draw_popup_tools(bgrid, tools[0], tool_active_id)
        if props.popup_tools_switch:
            tgrid = col.grid_flow(
                row_major=True, columns=modes.popup_max_tool_columns(),
                even_columns=True, even_rows=True, align=True)
            draw_popup_tools(tgrid, tools[1], tool_active_id)


class POPUP_OT_Edit_Favorites_Popup(Operator):
    bl_label = 'Edit the Favorites List'
    bl_idname = 'bm.edit_favorites_list_popup'

    def execute(self, context):
        return context.window_manager.invoke_popup(self, width=180)

    def draw(self, context):
        prefs = context.preferences.addons[Addon_Name].preferences
        props = context.window_manager.brush_manager_props
        wm = bpy.context.window_manager
        modes = BM_Modes()
        popup_items_scale = modes.popup_items_scale()
        icons = get_favorite_brushes(list_type='icons')

        layout = self.layout

        row = layout.row(align=True)
        col = row.column(align=True)
        for i, icon in enumerate(icons):
            col.template_icon(icon_value=icon, scale=popup_items_scale)
        col = row.column(align=True)
        col.scale_y = popup_items_scale

        draw_favorite_brushes(col, context)

        col = row.column(align=True)
        col.scale_y = popup_items_scale

        draw_remove_fav_brushes(col, context)


class WM_MT_Edit_from_Category_Ops(Menu):
    bl_label = "Operations"
    bl_idname = "BMANAGER_MT_Edit_Operations_menu"

    def draw(self, context):
        prefs = context.preferences.addons[Addon_Name].preferences
        props = context.window_manager.brush_manager_props
        layout = self.layout
        layout.operator("bm.save_selected_brushes", icon='EXPORT')
        layout.separator()
        op = layout.operator("bm.switch_fake_user", text='Apply Fake User', icon='FAKE_USER_ON')
        op.switch = True
        op = layout.operator("bm.switch_fake_user", text='Remove Fake User', icon='FAKE_USER_OFF')
        op.switch = False
        layout.separator()
        op = layout.operator("bm.switch_custom_icon", text='Turn On Custom Icon', icon='FILE_IMAGE')
        op.switch = True
        op = layout.operator("bm.switch_custom_icon", text='Turn Off Custom Icon', icon='MATPLANE')
        op.switch = False
        layout.separator()
        layout.operator("bm.change_icon_path_in_edit_list", icon='FILEBROWSER')
        layout.separator()
        row = layout.row()
        row.enabled = (props.lib_categories != 'Current File' and props.lib_categories != 'Default')
        row.operator("bm.refresh_brush_data_in_edit_list", icon='UV_SYNC_SELECT')
        layout.separator()
        layout.operator("bm.delete_brush_data_in_edit_list", icon='TRASH')


PICK_EDIT_LIST = []
BRUSHES_IN_CATEGORY = []


class WM_OT_Pick_Brush(Operator):
    bl_label = 'Pick Brush'
    bl_idname = 'bm.pick_brush'
    bl_description = "Select brush to edit"

    brush: bpy.props.StringProperty()

    def execute(self, context):
        global PICK_EDIT_LIST
        if self.brush in PICK_EDIT_LIST:
            PICK_EDIT_LIST = [b for b in PICK_EDIT_LIST if b != self.brush]
        else:
            PICK_EDIT_LIST.append(self.brush)
        return {'FINISHED'}


class WM_OT_Pick_Select_All_Brushes(Operator):
    bl_label = 'Select All'
    bl_idname = 'bm.select_all_brushes_in_edit_list'
    bl_description = "Select all brushes in the edit list"

    def execute(self, context):
        global PICK_EDIT_LIST
        PICK_EDIT_LIST = get_popup_add_list()
        return {'FINISHED'}


class WM_OT_Pick_Deselect_All_Brushes(Operator):
    bl_label = 'Deselect All'
    bl_idname = 'bm.deselect_all_brushes_in_edit_list'
    bl_description = "Deselect all brushes in the edit list"

    def execute(self, context):
        global PICK_EDIT_LIST
        PICK_EDIT_LIST.clear()
        return {'FINISHED'}


class WM_OT_Pick_Invert_Selected_Brushes(Operator):
    bl_label = 'Invert Selection'
    bl_idname = 'bm.invert_selected_brushes_in_edit_list'
    bl_description = "Invert selected brushes in the edit list"

    def execute(self, context):
        global PICK_EDIT_LIST
        PICK_EDIT_LIST = [b for b in get_popup_add_list() if b not in PICK_EDIT_LIST]
        return {'FINISHED'}


class WM_OT_Pick_Delete_Brush_Data(Operator):
    bl_label = 'Delete Brush Data'
    bl_idname = 'bm.delete_brush_data_in_edit_list'
    bl_description = "Delete the selected brushes data in the edit list"

    def execute(self, context):
        global PICK_EDIT_LIST
        global BRUSHES_IN_CATEGORY
        brushes_in_cat = get_popup_add_list()
        remove_brushes = [b for b in brushes_in_cat if b in PICK_EDIT_LIST]
        if not remove_brushes:
            msg = "Brush Manager: Brushes has not been selected."
            self.report({'ERROR'}, msg)
            return {'FINISHED'}
        fav_brushes = get_favorite_brushes()
        remove_favorites = [b for b in remove_brushes if b in fav_brushes]
        remove_fav_brush(self, context, remove_favorites)
        set_first_preview_item(context, fav_brushes, wm_enum_prop='fav')
        BRUSHES_IN_CATEGORY = [
            (n1, n2, b, iid, i)
            for n1, n2, b, iid, i in BRUSHES_IN_CATEGORY
            if n1 not in remove_brushes
        ]
        props = context.window_manager.brush_manager_props
        props.lib_categories = 'Current File'
        for brush in remove_brushes:
            try:
                b = bpy.data.brushes[brush]
            except KeyError:
                continue
            bpy.data.brushes.remove(b, do_unlink=True)
        update_brush_list(self, context)
        return {'FINISHED'}


class WM_OT_Pick_Refresh_Brush_Data(Operator):
    bl_label = 'Refresh Brush Data'
    bl_idname = 'bm.refresh_brush_data_in_edit_list'
    bl_description = (
        "Refresh the selected brushes data and return to the settings from their library files."
        " Works with other than 'Default' or 'Current File' categories"
    )

    def execute(self, context):
        global PICK_EDIT_LIST
        global BRUSHES_IN_CATEGORY
        brushes_in_cat = get_popup_add_list()
        remove_brushes = [b for b in brushes_in_cat if b in PICK_EDIT_LIST]
        if not remove_brushes:
            msg = "Brush Manager: Brushes has not been selected."
            self.report({'ERROR'}, msg)
            return {'FINISHED'}
        modes = BM_Modes()
        ts = modes.tool_settings(context)
        active_brush_name = ts.brush.name
        for brush in remove_brushes:
            try:
                b = bpy.data.brushes[brush]
            except KeyError:
                continue
            bpy.data.brushes.remove(b, do_unlink=True)

        global UPDATE_ICONS
        UPDATE_ICONS = True

        update_brush_list(self, context)
        update_fav_list(self, context)
        preview_brushes_in_folders(self, context)
        preview_brushes_in_favorites(self, context)
        ts.brush = bpy.data.brushes[active_brush_name]
        popup_close()

        return {'FINISHED'}


class WM_OT_Pick_Change_Icon_Path(Operator):
    bl_label = 'Change Icon Folder Path'
    bl_idname = 'bm.change_icon_path_in_edit_list'
    bl_description = "Change a folder path to the same custom icon file name of the selected brushes in the edit list"

    directory: bpy.props.StringProperty(
        subtype="DIR_PATH"
    )

    def __init__(self):
        self.brushes = []

    def invoke(self, context, event):
        global PICK_EDIT_LIST
        brushes_in_cat = get_popup_add_list()
        self.brushes = [b for b in brushes_in_cat if b in PICK_EDIT_LIST]
        if not self.brushes:
            msg = "Brush Manager: Brushes has not been selected."
            self.report({'ERROR'}, msg)
            return {'FINISHED'}
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        for brush in self.brushes:
            try:
                b = bpy.data.brushes[brush]
            except KeyError:
                continue
            file_name = os.path.basename(b.icon_filepath)
            filepath = os.path.join(self.directory, file_name)
            b.icon_filepath = filepath

        global UPDATE_ICONS
        UPDATE_ICONS = True
        update_category(self, context)

        return {'FINISHED'}


class WM_OT_Switch_Custom_Icon(Operator):
    bl_label = 'Switch Custom Icon'
    bl_idname = 'bm.switch_custom_icon'
    bl_description = "Turn on/off custom icons of the selected brushes in the edit list"

    switch: BoolProperty(default=False)

    def execute(self, context):
        global PICK_EDIT_LIST

        brushes_in_cat = get_popup_add_list()
        brushes = [b for b in brushes_in_cat if b in PICK_EDIT_LIST]
        if not brushes:
            msg = "Brush Manager: Brushes has not been selected."
            self.report({'ERROR'}, msg)
            return {'FINISHED'}
        for brush in brushes:
            try:
                b = bpy.data.brushes[brush]
            except KeyError:
                continue
            b.use_custom_icon = self.switch

        global UPDATE_ICONS
        UPDATE_ICONS = True
        update_category(self, context)

        return {'FINISHED'}


class WM_OT_Switch_Fake_User(Operator):
    bl_label = 'Switch Fake User'
    bl_idname = 'bm.switch_fake_user'
    bl_description = "Apply/Remove fake user of the selected brushes in the edit list"

    switch: BoolProperty(default=False)

    def execute(self, context):
        global PICK_EDIT_LIST

        brushes_in_cat = get_popup_add_list()
        brushes = [b for b in brushes_in_cat if b in PICK_EDIT_LIST]
        if not brushes:
            msg = "Brush Manager: Brushes has not been selected."
            self.report({'ERROR'}, msg)
            return {'FINISHED'}
        for brush in brushes:
            try:
                b = bpy.data.brushes[brush]
            except KeyError:
                continue
            b.use_fake_user = self.switch

        return {'FINISHED'}


class WM_OT_Pick_Save_Brushes(Operator):
    bl_label = 'Save Brushes'
    bl_idname = 'bm.save_selected_brushes'
    bl_description = "Save the selected brushes to a .blend file"

    relative_remap: bpy.props.BoolProperty(
        name="Remap Relative",
        default=True,
        description="Remap relative paths when saving to a different directory",
    )
    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH"
    )

    def __init__(self):
        global PICK_EDIT_LIST
        brushes_in_cat = get_popup_add_list()
        self.brushes = [b for b in brushes_in_cat if b in PICK_EDIT_LIST]

    def execute(self, context):
        if self.filepath.endswith(".blend"):
            blend_filepath = self.filepath
        else:
            blend_filepath = self.filepath + ".blend"

        brushes_data = []
        brushes_failed = ''
        for b in self.brushes:
            try:
                if check_brush_type(bpy.data.brushes[b], MODE):
                    brushes_data.append(bpy.data.brushes[b])
            except KeyError:
                brushes_failed = brushes_failed + ' ' + '\"' + b + '\",'
        if brushes_failed != '':
            msg = "Save Brushes Error:" + brushes_failed + " data does not found."
            self.report({'ERROR'}, msg)
            return {'FINISHED'}
        save_brushes_to_file(brushes_data, blend_filepath, relative_path_remap=self.relative_remap)
        update_brush_list(self, context)
        msg = "Brushes Saved to: " + blend_filepath
        self.report({'INFO'}, msg)

        return {'FINISHED'}

    def invoke(self, context, event):
        if not self.brushes:
            msg = "Brush Manager: Nothing to save, or brushes have not been selected."
            self.report({'ERROR'}, msg)
            return {'FINISHED'}
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class POPUP_OT_Edit_Category_Brushes_Popup(Operator):
    bl_label = 'Edit Brushes from Category'
    bl_idname = 'bm.edit_brushes_from_category_popup'

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        global PICK_EDIT_LIST
        PICK_EDIT_LIST.clear()
        update_brush_list(self, context)
        brushes_enum = preview_brushes_in_folders(self, context)
        set_brushes_in_category_list_popup(brushes_enum, exclude_fav=False)
        return context.window_manager.invoke_popup(self, width=355)

    def draw(self, context):
        prefs = context.preferences.addons[Addon_Name].preferences
        props = context.window_manager.brush_manager_props
        wm = bpy.context.window_manager
        modes = BM_Modes()
        popup_items_scale = modes.popup_items_scale()

        brushes = get_popup_add_list(list_type='icons_n_brushes')

        layout = self.layout

        row = layout.row(align=True)
        col = row.column()

        row = col.row(align=True)
        col1 = row.column()
        row1 = col1.row(align=True)
        sr = row1.row(align=True)
        sr.scale_x = 1.65
        sr.prop(props, "search_bar", text='', icon='VIEWZOOM')
        row1.prop(props, "search_case_sensitive", text='', icon='SMALL_CAPS')
        col2 = row.column()
        row2 = col2.row(align=True)
        row2.label(text='')
        row2.operator("bm.select_all_brushes_in_edit_list", text='', icon='CHECKMARK')
        row2.operator("bm.deselect_all_brushes_in_edit_list", text='', icon='CHECKBOX_DEHLT')
        row2.operator("bm.invert_selected_brushes_in_edit_list", text='', icon='SELECT_SUBTRACT')
        sr = row2.row(align=True)
        sr.scale_x = 1.3
        sr.menu("BMANAGER_MT_Edit_Operations_menu")
        col = col.column()
        flow = col.column_flow(columns=2, align=True)
        for brush, icon in brushes:
            row = flow.row(align=True)
            col = row.column(align=True)
            col.template_icon(icon_value=icon, scale=popup_items_scale)
            is_active = True if brush in PICK_EDIT_LIST else False
            col = row.column(align=True)
            col.scale_y = popup_items_scale
            op = col.operator("bm.pick_brush", text=brush, emboss=True, depress=is_active)
            op.brush = brush


class WM_OT_Add_from_Category(Operator):
    bl_label = 'Add'
    bl_idname = 'bm.add_from_category'
    bl_description = "Add brush to the Favorites"

    brush_name: StringProperty()

    def execute(self, context):
        add_to_fav_update(self, context)
        return {'FINISHED'}


class WM_OT_Add_from_Category_all_the_rest(Operator):
    bl_label = 'Add All the Rest'
    bl_idname = 'bm.add_from_category_all_the_rest'
    bl_description = "Add all the rest of brushes to the Favorites"

    def execute(self, context):
        add_to_fav_update(self, context, all_the_rest=True)
        return {'FINISHED'}


class WM_OT_Remove_from_Favorites(Operator):
    bl_label = 'Remove'
    bl_idname = 'bm.remove_from_favorites'
    bl_description = "Remove brush from the Favorites"

    brush_name: StringProperty()

    def execute(self, context):
        delete_fav_brush_list_update(self, context)
        return {'FINISHED'}


def set_brushes_in_category_list_popup(brushes_enum, exclude_fav=True):
    full = []
    fav_list = get_favorite_brushes()
    for name1, name2, blank, iconid, index in brushes_enum:
        if name2 in fav_list and exclude_fav:
            continue
        full.append((name1, name2, '', iconid, index))
    global BRUSHES_IN_CATEGORY
    BRUSHES_IN_CATEGORY = full


def get_popup_add_list(list_type=''):
    props = bpy.context.window_manager.brush_manager_props
    add = []
    icons = []
    icons_n_brushes = []
    filter_name = str(props.search_bar.decode("utf-8"))
    for name1, name2, blank, iconid, index in BRUSHES_IN_CATEGORY:
        if filter_name and not props.search_case_sensitive:
            if not text_lookup(filter_name.lower(), name1.lower()):
                continue
        elif filter_name:
            if not text_lookup(filter_name, name1):
                continue
        icons.append(iconid)
        add.append(name1)
        icons_n_brushes.append((name1, iconid))
    if list_type == 'icons':
        return icons
    if list_type == 'icons_n_brushes':
        return icons_n_brushes
    return add


def add_to_fav_update(self, context, all_the_rest=False):
    global BRUSHES_IN_CATEGORY
    b_preview_coll = preview_brushes_coll["favorites"]
    if b_preview_coll.my_previews_dir != "favorites":
        return None
    brushes_list = get_favorite_brushes()
    if not all_the_rest:
        append_brushes = [self.brush_name]
    else:
        append_brushes = get_popup_add_list()
    BRUSHES_IN_CATEGORY = [
        (n1, n2, b, iid, i)
        for n1, n2, b, iid, i in BRUSHES_IN_CATEGORY
        if n1 not in append_brushes
    ]
    brushes_list += append_brushes
    brushes_list.sort()
    enum_items = create_enum_list(context, brushes_list, b_preview_coll)
    b_preview_coll.my_previews = enum_items


def is_active_brush(context, brush_name):
    is_active = False
    ts = context.tool_settings
    brush = get_active_brush(context)
    if hasattr(brush, 'name'):
        is_active = (brush_name == brush.name)
    return is_active


class POPUP_OT_Add_to_Favorites_Popup(Operator):
    bl_label = 'Add to the Favorites from the Category List'
    bl_idname = 'bm.add_to_favorites_popup'
    bl_description = "Pick brushes from the popup Category list to append them to the Favorites list"

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        update_brush_list(self, context)
        brushes_enum = preview_brushes_in_folders(self, context)
        set_brushes_in_category_list_popup(brushes_enum)
        return context.window_manager.invoke_popup(self, width=350)

    def draw(self, context):
        prefs = context.preferences.addons[Addon_Name].preferences
        props = context.window_manager.brush_manager_props
        wm = bpy.context.window_manager
        modes = BM_Modes()
        popup_items_scale = modes.popup_items_scale()
        icons = get_popup_add_list(list_type='icons')

        layout = self.layout

        row = layout.row(align=True)
        col1 = row.column()
        row1 = col1.row(align=True)
        sr = row1.row(align=True)
        sr.scale_x = 1.4
        sr.prop(props, "search_bar", text='', icon='VIEWZOOM')
        row1.prop(props, "search_case_sensitive", text='', icon='SMALL_CAPS')
        row1.operator("bm.add_from_category_all_the_rest", text='', icon='PRESET_NEW')
        col2 = row.column()
        row2 = col2.row()
        row2.label(text='')
        row2.label(text='')
        row2.label(text='', icon='SOLO_ON')
        row = col1.row(align=True)
        col = row.column(align=True)
        for i, icon in enumerate(icons):
            col.template_icon(icon_value=icon, scale=popup_items_scale)
        col = row.column(align=True)
        col.scale_y = popup_items_scale

        space_type = context.space_data.type
        toolhelper = space_toolsystem_common.ToolSelectPanelHelper
        tool_active_id = getattr(
            toolhelper._tool_active_from_context(context, space_type),
            "idname", None,)
        brushes = get_popup_add_list()
        for brush in brushes:
            clrow = col.row(align=True)
            is_active = is_active_brush(context, brush)
            if MODE == 'SCULPT':
                op = clrow.operator("bm.set_brush", text=brush, emboss=True, depress=is_active)
                op.brush = brush
                op.from_list = "add_brush_popup"
            else:
                if MODE == 'PAINT_GPENCIL':
                    if not tool_active_id.startswith("builtin_brush"):
                        op = clrow.operator(
                            "bm.select_brush", text='',
                            icon='GREASEPENCIL', depress=is_active)
                        op.brush = brush
                        op.from_list = "add_brush_popup"
                        op.no_tool = True
                op = clrow.operator("bm.select_brush", text=brush, depress=is_active)
                op.brush = brush
                op.from_list = 'add_brush_popup'
                op.no_tool = False

        col = row.column(align=True)
        col.scale_y = popup_items_scale
        for brush in brushes:
            op = col.operator("bm.add_from_category", icon='ADD', text='', emboss=True)
            op.brush_name = brush
        #////////////////////////////////
        icons = get_favorite_brushes(list_type='icons')
        row = col2.row(align=True)
        col = row.column(align=True)
        for i, icon in enumerate(icons):
            col.template_icon(icon_value=icon, scale=popup_items_scale)
        col = row.column(align=True)
        col.scale_y = popup_items_scale

        draw_favorite_brushes(col, context)

        col = row.column(align=True)
        col.scale_y = popup_items_scale

        draw_remove_fav_brushes(col, context)


class POPUP_OT_Settings_Popup(Operator):
    bl_label = 'Settings'
    bl_idname = 'bm.settings_popup'
    bl_description = "Show preference settings of the Brush Manager add-on"

    def execute(self, context):
        return {'FINISHED'}

    def draw(self, context):
        prefs = bpy.context.preferences.addons[Addon_Name].preferences
        props = context.window_manager.brush_manager_props
        wm = bpy.context.window_manager

        layout = self.layout
        draw_preferences(prefs, context, layout)

        g_prefs = context.preferences
        layout.operator_context = 'EXEC_AREA'

        if g_prefs.use_preferences_save and (not bpy.app.use_userpref_skip_save_on_exit):
            pass
        else:
            # Show '*' to let users know the preferences have been modified.
            layout.operator(
                "wm.save_userpref",
                text="Save Preferences" + (" *" if g_prefs.is_dirty else ""),
            )

    def invoke(self, context, event):
        prefs = context.preferences.addons[Addon_Name].preferences
        if context.mode in BM_Modes.in_modes:
            prefs.pref_tabs = context.mode
        return context.window_manager.invoke_props_dialog(self, width=520)
        # return context.window_manager.invoke_popup(self, width=500)


class PREF_OT_Save_Settings(Operator):
    bl_label = 'Save Settings'
    bl_idname = 'bm.save_pref_settings'
    bl_description = "Save preference settings to the json file"

    def execute(self, context):
        prefs = context.preferences.addons[Addon_Name].preferences
        user_path = bpy.utils.resource_path('USER')
        config_path = os.path.join(user_path, "config")
        json_file = os.path.join(config_path, "BrushManager_settings.json")
        pref_data = {}
        for pr in prefs.__annotations__:
            if pr == 'show_common' or pr == 'pref_tabs':
                continue
            if pr == 'show_keymaps' or pr == 'show_UI' or pr == 'show_tools':
                continue
            pref_data[pr] = eval("prefs." + pr)
        pref_data['keymaps_state'] = get_current_keymaps()

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(pref_data, f, ensure_ascii=False, indent=4)

        msg = "Brush Manager: Settings has been saved to " + json_file
        self.report({'INFO'}, msg)

        return {'FINISHED'}


def load_saved_keymaps(context, load_keymaps):
    keymaps = context.window_manager.keyconfigs.user.keymaps
    for km, kmi in addon_keymaps:
        if not load_keymaps.get(km.name):
            continue
        for i in load_keymaps[km.name]:
            exec('keymaps[km.name].keymap_items[kmi.idname].' + i + ' = load_keymaps[km.name].get(i)')


class PREF_OT_Load_Settings(Operator):
    bl_label = 'Load Settings'
    bl_idname = 'bm.load_pref_settings'
    bl_description = "Load preference settings from saved json file"

    def execute(self, context):
        prefs = context.preferences.addons[Addon_Name].preferences
        user_path = bpy.utils.resource_path('USER')
        config_path = os.path.join(user_path, "config")
        json_file = os.path.join(config_path, "BrushManager_settings.json")
        if not os.path.isfile(json_file):
            msg = "Brush Manager: The settings file does not exist or it have not been saved yet."
            self.report({'WARNING'}, msg)
            return {'FINISHED'}
        global LOADING_SETTINGS
        LOADING_SETTINGS = True
        f = open(json_file)
        pref_data = json.load(f)
        for pr in pref_data:
            value = pref_data.get(pr)
            exec("if hasattr(prefs, pr): prefs." + pr + " = value")
            if pr == 'keymaps_state':
                load_keymaps = pref_data.get(pr)
                load_saved_keymaps(context, load_keymaps)
        f.close()
        LOADING_SETTINGS = False
        msg = "Brush Manager: Settings has been loaded from " + json_file
        self.report({'INFO'}, msg)

        return {'FINISHED'}


classes = (
    WM_OT_Add_to_the_Favorites,
    WM_OT_Append_List_to_the_Favorites,
    WM_OT_Append_from_a_File_to_Favorites,
    WM_OT_Remove_Active_Favorite,
    WM_OT_Remove_Active_Popup_Favorite,
    WM_OT_Clear_Favorites,
    WM_OT_Delete_Zero_User_Brushes,
    WM_OT_Delete_Active_Brush_Data,
    WM_OT_Refresh_Category_List,
    WM_OT_Save_Favorites,
    WM_OT_Save_Favorites_to_current_file,
    WM_OT_Load_Favorites_from_current_file,
    WM_OT_Load_Startup_Favorites,
    WM_OT_Save_Active_Brush,
    WM_OT_Open_Category_Folder,
    WM_OT_Reset_All_Default_Brushes,
    WM_OT_Apply_Icon_to_Active_Brush,
    WM_MT_BrushManager_Ops,
    PREF_OT_Refresh_Brushes_Data_List,
    BM_PT_Brush_Manager,
    GPENCIL_PT_Brush_Manager,
    GPENCILVP_PT_Brush_Manager,
    POPUP_OT_Tools_and_Brushes,
    POPUP_OT_Edit_Favorites_Popup,
    POPUP_OT_Add_to_Favorites_Popup,
    POPUP_OT_Settings_Popup,
    Brushes_Data_Collection,
    BM_Favorite_list_settings,
    BrushManager_Preferences,
    BrushManager_Properties,
    WM_OT_Set_Category,
    WM_OT_Set_Select_Brush,
    WM_OT_Select_Brush,
    WM_OT_Add_from_Category,
    WM_OT_Add_from_Category_all_the_rest,
    WM_OT_Remove_from_Favorites,
    PREF_OT_Save_Settings,
    PREF_OT_Load_Settings,
    PREF_OT_assign_to_similar_settings,
    WM_OT_Pick_Brush,
    POPUP_OT_Edit_Category_Brushes_Popup,
    WM_OT_Pick_Select_All_Brushes,
    WM_OT_Pick_Deselect_All_Brushes,
    WM_OT_Pick_Invert_Selected_Brushes,
    WM_OT_Pick_Delete_Brush_Data,
    WM_OT_Pick_Refresh_Brush_Data,
    WM_OT_Pick_Change_Icon_Path,
    WM_OT_Switch_Custom_Icon,
    WM_OT_Switch_Fake_User,
    WM_OT_Pick_Save_Brushes,
    WM_MT_Edit_from_Category_Ops,
)

preview_brushes_coll = {}
addon_keymaps = []
supported_keymaps = [
    'Sculpt',
    'Image Paint',
    'Weight Paint',
    'Vertex Paint',
    'Grease Pencil Stroke Paint Mode',
    'Grease Pencil Stroke Vertex Mode',
]
bm_keymap_items = {
    'map_type': 'KEYBOARD',
    'type': 'SPACE',
    'any': False,
    'value': 'PRESS',
    'ctrl': False,
    'shift': False,
    'alt': True,
    'oskey': False,
    'repeat': True,
    'key_modifier': 'NONE',
    'active': True,
}
keymaps_state = dict([(km, bm_keymap_items) for km in supported_keymaps])


def register_keymaps():
    addon_keymaps.clear()
    winm = bpy.context.window_manager
    keyconf = winm.keyconfigs.addon
    if keyconf:
        for km in keymaps_state:
            keymap = keyconf.keymaps.new(name=km, space_type='EMPTY', region_type='WINDOW')
            keymap_item = keymap.keymap_items.new(
                "bm.tools_and_brushes_popup", type='SPACE', value='PRESS', alt=True
            )
            for i in keymaps_state[km]:
                exec('keymap_item.' + i + ' = keymaps_state[km].get(i)')
            addon_keymaps.append((keymap, keymap_item))


def unregister_keymaps():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()


def get_current_keymaps():
    stored_keymaps = {}
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    for km in keymaps_state:
        stored_keymaps[km] = {}
        for k in kc.keymaps[km].keymap_items:
            if k.idname == "bm.tools_and_brushes_popup" and k.active:
                for i in keymaps_state[km]:
                    exec('stored_keymaps[km][i] = k.' + i)
    return stored_keymaps


def pre_template_keymaps_save():
    keymaps_state.update(get_current_keymaps())


def register():
    brushes_coll = bpy.utils.previews.new()
    brushes_coll.my_previews_dir = ""
    brushes_coll.my_previews = ()
    preview_brushes_coll["main"] = brushes_coll
    brush_favorites = bpy.utils.previews.new()
    brush_favorites.my_previews_dir = "favorites"
    brush_favorites.my_previews = ()
    preview_brushes_coll["favorites"] = brush_favorites
    brush_undo = bpy.utils.previews.new()
    brush_undo.my_previews_dir = "undo"
    brush_undo.my_previews = ()
    preview_brushes_coll["undo"] = brush_undo
    brush_undof = bpy.utils.previews.new()
    brush_undof.my_previews_dir = "undo"
    brush_undof.my_previews = ()
    preview_brushes_coll["undofav"] = brush_undof

    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    wm = bpy.types.WindowManager
    wm.brush_manager_props = PointerProperty(type=BrushManager_Properties)
    wm.bm_brushes_data_list = CollectionProperty(type=Brushes_Data_Collection)
    wm.bm_sculpt_fav_list_store = CollectionProperty(type=BM_Favorite_list_settings)
    wm.bm_paint_fav_list_store = CollectionProperty(type=BM_Favorite_list_settings)
    wm.bm_gpaint_fav_list_store = CollectionProperty(type=BM_Favorite_list_settings)
    wm.bm_gvertex_fav_list_store = CollectionProperty(type=BM_Favorite_list_settings)
    wm.bm_wpaint_fav_list_store = CollectionProperty(type=BM_Favorite_list_settings)
    wm.bm_vpaint_fav_list_store = CollectionProperty(type=BM_Favorite_list_settings)
    bpy.types.Scene.bm_favorite_list_settings = bpy.props.CollectionProperty(type=BM_Favorite_list_settings)
    bpy.types.Scene.bm_paint_favorite_settings = bpy.props.CollectionProperty(type=BM_Favorite_list_settings)
    bpy.types.Scene.bm_gpaint_favorite_settings = bpy.props.CollectionProperty(type=BM_Favorite_list_settings)
    bpy.types.Scene.bm_gvertex_favorite_settings = bpy.props.CollectionProperty(type=BM_Favorite_list_settings)
    bpy.types.Scene.bm_wpaint_favorite_settings = bpy.props.CollectionProperty(type=BM_Favorite_list_settings)
    bpy.types.Scene.bm_vpaint_favorite_settings = bpy.props.CollectionProperty(type=BM_Favorite_list_settings)

    bpy.app.handlers.load_post.append(brush_manager_on_file_load)
    bpy.app.handlers.save_pre.append(brush_manager_pre_save)
    bpy.app.handlers.save_post.append(brush_manager_post_save)
    bpy.app.handlers.depsgraph_update_pre.append(brush_manager_pre_dp_update)
    bpy.app.handlers.undo_pre.append(brush_manager_pre_undo)
    bpy.app.handlers.undo_post.append(brush_manager_post_undo)
    set_brushes_data_collection_items()
    update_panel(None, bpy.context)
    register_keymaps()


def unregister():
    if prefs().persistent_keymaps:
        pre_template_keymaps_save()

    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)

    for bcoll in preview_brushes_coll.values():
        bpy.utils.previews.remove(bcoll)
    preview_brushes_coll.clear()
    try:
        bpy.app.handlers.load_post.remove(brush_manager_on_file_load)
    except ValueError:
        pass
    try:
        bpy.app.handlers.depsgraph_update_pre.remove(brush_manager_pre_dp_update)
        bpy.app.handlers.save_pre.remove(brush_manager_pre_save)
        bpy.app.handlers.save_post.remove(brush_manager_post_save)
        bpy.app.handlers.undo_pre.remove(brush_manager_pre_undo)
        bpy.app.handlers.undo_post.remove(brush_manager_post_undo)
    except ValueError:
        pass
    del bpy.types.WindowManager.brush_manager_props
    del bpy.types.WindowManager.bm_brushes_data_list
    del bpy.types.WindowManager.bm_sculpt_fav_list_store
    del bpy.types.WindowManager.bm_paint_fav_list_store
    del bpy.types.WindowManager.bm_gpaint_fav_list_store
    del bpy.types.WindowManager.bm_gvertex_fav_list_store
    del bpy.types.WindowManager.bm_wpaint_fav_list_store
    del bpy.types.WindowManager.bm_vpaint_fav_list_store
    del bpy.types.Scene.bm_favorite_list_settings
    del bpy.types.Scene.bm_paint_favorite_settings
    del bpy.types.Scene.bm_gpaint_favorite_settings
    del bpy.types.Scene.bm_gvertex_favorite_settings
    del bpy.types.Scene.bm_wpaint_favorite_settings
    del bpy.types.Scene.bm_vpaint_favorite_settings
    unregister_keymaps()


if __name__ == "__main__":
    register()
