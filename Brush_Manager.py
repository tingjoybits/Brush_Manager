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
import bpy.utils.previews
from bpy.app.handlers import persistent
from bpy.types import Operator, Menu, Panel, PropertyGroup, AddonPreferences, Scene, WindowManager, BlendData
from bpy.props import *   # StringProperty, EnumProperty, BoolProperty, FloatProperty

Addon_Name = __name__.split('.')[1]


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
    lib_path = prefs.brush_library
    directory = os.path.join(lib_path, props.lib_categories)
    return directory


def get_append_brushes(directory, b_files, exclude_default=True):
    brushes_append = []
    brushes_in_files = get_brushes_in_files(directory, b_files)
    default_brushes = get_default_brushes_list()
    for brush in brushes_in_files:
        if brush in default_brushes and exclude_default:
            continue
        try:
            if not bpy.data.brushes[brush].use_paint_sculpt:
                continue
        except KeyError:
                continue
        brushes_append.append(brush)
        brushes_append = list(set(brushes_append))
        brushes_append.sort()
    return brushes_append

# ================================================================


def append_brushes_from_a_file(filepath):
    brushes = []
    def_brushes = get_default_brushes_list()
    with bpy.data.libraries.load(filepath) as (data_from, data_to):
        for brush in data_from.brushes:
            if brush not in bpy.data.brushes:
                data_to.brushes.append(brush)
                brushes.append(brush)
                continue
            if brush in def_brushes:
                continue
            # !! Append even if the same brush is already exists
            brushes.append(brush)
    return brushes


def append_brushes_to_current_file(directory):
    b_files = get_b_files(directory)
    for name in b_files:
        filepath = os.path.join(directory, name)
        brushes_in_file = append_brushes_from_a_file(filepath)
    return brushes_in_file


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


def update_category(self, context):
    wm = bpy.context.window_manager
    props = wm.brush_manager_props
    if props.lib_categories == 'Default':
        create_default_sculpt_tools()
    update_brush_list(self, context)
    set_toggle_default_icons(context)


def update_brush_list(self, context):
    main_brushes = get_main_list_brushes(context)
    set_first_preview_item(context, main_brushes)
    b_preview_coll = preview_brushes_coll["main"]
    b_preview_coll.my_previews_dir = ""


def filter_sculpt_brushes(brushes_list):
    sculpt_brushes = []
    for b in brushes_list:
        try:
            if not bpy.data.brushes[b].use_paint_sculpt:
                continue
        except KeyError:
            continue
        sculpt_brushes.append(b)
    sculpt_brushes = list(set(sculpt_brushes))
    sculpt_brushes.sort()
    return sculpt_brushes


def get_appended_to_current_brushes(category, directory):
    brushes_added = append_brushes_to_current_file(directory)
    brushes = filter_sculpt_brushes(brushes_added)
    if len(brushes) == 0:
        b_files = get_b_files(directory)
        brushes = get_append_brushes(directory, b_files)
    return brushes


def get_default_brushes_list(list_type='brushes'):
    brushes = [
        'Blob', 'Clay', 'Clay Strips', 'Clay Thumb', 'Cloth',
        'Crease', 'Draw Face Sets', 'Draw Sharp', 'Elastic Deform',
        'Fill/Deepen', 'Flatten/Contrast', 'Grab', 'Inflate/Deflate',
        'Layer', 'Mask', 'Multi-plane Scrape', 'Nudge', 'Pinch/Magnify',
        'Pose', 'Rotate', 'Scrape/Peaks', 'SculptDraw', 'Simplify',
        'Slide Relax', 'Smooth', 'Snake Hook', 'Thumb'
    ]
    def_s_tools = [
        'BLOB', 'CLAY', 'CLAY_STRIPS', 'CLAY_THUMB', 'CLOTH', 'CREASE',
        'DRAW_FACE_SETS', 'DRAW_SHARP', 'ELASTIC_DEFORM', 'FILL', 'FLATTEN',
        'GRAB', 'INFLATE', 'LAYER', 'MASK', 'MULTIPLANE_SCRAPE', 'NUDGE',
        'PINCH', 'POSE', 'ROTATE', 'SCRAPE', 'DRAW', 'SIMPLIFY', 'TOPOLOGY',
        'SMOOTH', 'SNAKE_HOOK', 'THUMB'
    ]
    if list_type == 'brushes':
        return brushes
    if list_type == 'def_s_tools':
        return def_s_tools
    if list_type == 'slot_brushes':
        tool_slots = bpy.context.tool_settings.sculpt.tool_slots
        slot_brushes = []
        for i, ts in enumerate(tool_slots):
            if i == 0:
                continue
            slot_brushes.append(ts.brush.name)
        slot_brushes.sort()
        return slot_brushes
    if list_type == 'init_tools' or list_type == 'sculpt_tools':
        enum_items = []
        for brush in bpy.data.brushes:
            if brush.use_paint_sculpt:
                enum_items = brush.bl_rna.properties['sculpt_tool'].enum_items
                break
    if list_type == 'init_tools':
        init_tools = dict([(b.identifier, b.name) for b in enum_items])
        return init_tools
    if list_type == 'sculpt_tools':
        sculpt_tools = [t.identifier for t in enum_items]
        sculpt_tools.sort()
        return sculpt_tools
    return brushes


def get_current_file_brushes():
    brushes = []
    try:
        for brush in bpy.data.brushes:
            try:
                if brush.use_paint_sculpt:
                    brushes.append(brush.name)
            except AttributeError:
                continue
    except AttributeError:
        pass
    brushes.sort()
    return brushes


def get_brushes_from_preview_enums(enum_items):
    brushes_list = []
    for name1, name2, blank, iconid, index in enum_items:
        brushes_list.append(name1)
    return brushes_list


def get_main_list_brushes(context):
    b_preview_coll = preview_brushes_coll["main"]
    directory = get_library_directory(context)
    b_preview_coll.my_previews_dir = directory
    main_preview_enums = b_preview_coll.my_previews
    brushes_list = get_brushes_from_preview_enums(main_preview_enums)
    return brushes_list


def get_favorite_brushes():
    b_preview_coll = preview_brushes_coll["favorites"]
    preview_enums = b_preview_coll.my_previews
    b_preview_coll.my_previews_dir = "favorites"
    brushes_list = get_brushes_from_preview_enums(preview_enums)
    return brushes_list


def add_to_fav_active_current_brush(context, brushes_list):
    active_brush = context.tool_settings.sculpt.brush
    if not active_brush:
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
    brushes = get_sorted_default_brushes()
    if len(b_preview_coll.my_previews) > 0:
        b_preview_coll.my_previews.clear()
    enum_items = create_enum_list(bpy.context, brushes, b_preview_coll, update_icon=True)
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


def lib_category_folders(self, context):
    prefs = context.preferences.addons[Addon_Name].preferences
    lib_path = prefs.brush_library
    default_list = ['Default', 'Current File']
    folders = get_folders_contains_files(lib_path, ".blend")
    folders_list = default_list + folders

    return [(name, name, "") for name in folders_list]


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


def get_icon_themes_path():
    current_file_dir = os.path.dirname(__file__)
    icon_themes_path = os.path.join(current_file_dir, 'icon_themes')
    return icon_themes_path


def get_icons_path():
    prefs = bpy.context.preferences.addons[Addon_Name].preferences
    props = bpy.context.window_manager.brush_manager_props
    icon_themes_path = get_icon_themes_path()
    icons_path = os.path.join(icon_themes_path, prefs.brush_icon_theme)
    return icons_path


def set_brush_icon_themes(self, context):
    current_file_dir = os.path.dirname(__file__)
    icon_themes_path = get_icon_themes_path()
    default_list = []
    folders = get_folders_contains_files(icon_themes_path, ".png")
    folders_list = folders + default_list
    folders_list.sort()

    return [(name, name, "") for name in folders_list]


def set_active_tool(tool_name):
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            override = bpy.context.copy()
            override["space_data"] = area.spaces[0]
            override["area"] = area
            bpy.ops.wm.tool_set_by_id(override, name=tool_name)


def initialize_default_brush(tool_name, s_tool, def_stools):
    try:
        check = bpy.context.preferences.experimental.use_sculpt_vertex_colors
    except AttributeError:
        check = False
    if get_app_version() >= 2.90 and not check:
        if s_tool not in def_stools:
            return None
    set_active_tool("builtin_brush." + tool_name)


def create_thumbnail_icon(brush_name, b_preview_coll):
    icons_path = get_icons_path()
    icon_name = bpy.data.brushes[brush_name].sculpt_tool.lower() + '.png'
    filepath = os.path.join(icons_path, icon_name)
    if not os.path.isfile(filepath):
        icon_name = 'NA_brush.png'
        filepath = os.path.join(icons_path, icon_name)
    thumb = b_preview_coll.load(brush_name, filepath, 'IMAGE')
    return thumb


def create_enum_list(context, brushes, b_preview_coll, update_icon=False):
    icons_path = get_icons_path()
    enum_items = []
    for index, brush in enumerate(brushes):
        try:
            check = bpy.data.brushes[brush]
        except KeyError:
            continue
        if update_icon:
            icon = False
            b_preview_coll.clear()
        else:
            icon = b_preview_coll.get(brush)
        if not icon:
            if bpy.data.brushes[brush].use_custom_icon:
                filepath = bpy.data.brushes[brush].icon_filepath
                if os.path.isfile(filepath):
                    thumb = bpy.data.brushes[brush].preview
                else:
                    thumb = create_thumbnail_icon(brush, b_preview_coll)
            else:
                thumb = create_thumbnail_icon(brush, b_preview_coll)
        else:
            thumb = b_preview_coll[brush]
        enum_items.append((brush, brush, "", thumb.icon_id, index))
    return enum_items


def reset_all_default_brushes(context):
    props = context.window_manager.brush_manager_props
    def_brushes = get_sorted_default_brushes()
    active_brush = context.tool_settings.sculpt.brush
    for brush in def_brushes:
        try:
            context.tool_settings.sculpt.brush = bpy.data.brushes[brush]
        except KeyError:
            pass
        bpy.ops.brush.reset()
        if props.set_default_brushes_custom_icon:
            bpy.data.brushes[brush].use_custom_icon = True
    context.tool_settings.sculpt.brush = active_brush


def create_default_sculpt_tools():
    props = bpy.context.window_manager.brush_manager_props
    if bpy.data.scenes[0].name == 'Empty':
        return None
    active_brush = bpy.context.tool_settings.sculpt.brush
    init_tools = get_default_brushes_list(list_type='init_tools')
    sculpt_tools = get_default_brushes_list(list_type='sculpt_tools')
    current_brushes = get_current_file_brushes()
    current_tools = []
    def_stools = get_default_brushes_list(list_type='def_s_tools')
    for brush in current_brushes:
        current_tools.append(bpy.data.brushes[brush].sculpt_tool)
        if brush == 'Multiplane Scrape':
            bpy.data.brushes[brush].name = 'Multi-plane Scrape'
    for tool in sculpt_tools:
        if tool in current_tools:
            continue
        # print('INIT TOOL:', tool)
        initialize_default_brush(init_tools.get(tool), tool, def_stools)
        bpy.ops.brush.reset()
    tool_name = init_tools.get(active_brush.sculpt_tool)
    set_active_tool("builtin_brush." + tool_name)
    bpy.context.tool_settings.sculpt.brush = active_brush


def check_current_file_brush_icons():
    brushes = get_current_file_brushes()
    for brush in brushes:
        if not bpy.data.brushes[brush].use_custom_icon:
            continue
        filepath = bpy.data.brushes[brush].icon_filepath
        if os.path.isfile(filepath):
            continue
        bpy.data.brushes[brush].use_custom_icon = False


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
    clear_favorites_list()
    clear_Default_list()
    create_default_sculpt_tools()
    check_current_file_brush_icons()
    if prefs.default_brushes_custom_icon and not props.set_default_brushes_custom_icon:
        props.set_default_brushes_custom_icon = True
    if prefs.selected_brush_custom_icon and not props.set_selected_brush_custom_icon:
        props.set_selected_brush_custom_icon = True
    if prefs.force_brush_custom_icon and not props.set_force_brush_custom_icon:
        props.set_force_brush_custom_icon = True


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
        brushes = get_sorted_default_brushes()
    elif selected_category_name == 'Current File':
        brushes = get_current_file_brushes()
    elif selected_category_name:
        brushes = get_appended_to_current_brushes(selected_category_name, directory)
    props.post_undo_last = False

    if props.search_in_category:
        brushes = filter_brushes_by_name(brushes, str(props.search_bar.decode("utf-8")))  # utf-8
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
    return b_preview_coll.my_previews


def SelectBrushError(self, context):
    msg = "Selected Brush has been deleted or renamed, removing..."
    print("Brush Manager Error: " + msg)
    self.layout.label(text=msg)


def set_brush_from_lib_list(self, context):
    props = context.window_manager.brush_manager_props
    if props.skip_brush_set:
        props.skip_brush_set = False
        return None
    selected_brush = context.window_manager.brushes_in_files
    try:
        context.tool_settings.sculpt.brush = bpy.data.brushes[selected_brush]
    except KeyError:
        context.window_manager.popup_menu(SelectBrushError, title="Error", icon="INFO")
        update_brush_list(self, context)
        return None
    if bpy.data.brushes[selected_brush].use_custom_icon and not props.set_force_brush_custom_icon:
        return None
    if props.set_selected_brush_custom_icon:
        icons_path = get_icons_path()
        set_custom_icon(icons_path, selected_brush)
    return None


def set_brush_from_fav_list(self, context):
    props = context.window_manager.brush_manager_props
    if props.skip_brush_set:
        props.skip_brush_set = False
        return None
    selected_brush = context.window_manager.brushes_in_favorites
    try:
        context.tool_settings.sculpt.brush = bpy.data.brushes[selected_brush]
    except KeyError:
        context.window_manager.popup_menu(SelectBrushError, title="Error", icon="INFO")
        remove_active_brush_favorite(self, context)
        return None
    if bpy.data.brushes[selected_brush].use_custom_icon and not props.set_force_brush_custom_icon:
        return None
    if props.set_selected_brush_custom_icon:
        icons_path = get_icons_path()
        set_custom_icon(icons_path, selected_brush)
    return None


def set_custom_icon(icons_path, brush_name):
    try:
        brush = bpy.data.brushes[brush_name]
    except (KeyError, AttributeError) as e:
        return False
    icon_name = brush.sculpt_tool.lower() + '.png'
    filepath = os.path.join(icons_path, icon_name)
    if not os.path.isfile(filepath):
        icon_name = 'NA_brush.png'
        filepath = os.path.join(icons_path, icon_name)
    brush.use_custom_icon = True
    brush.icon_filepath = filepath


def update_pref_apply_theme_to_def(self, context):
    prefs = context.preferences.addons[Addon_Name].preferences
    props = context.window_manager.brush_manager_props
    if not props.set_default_brushes_custom_icon and prefs.default_brushes_custom_icon:
        props.set_default_brushes_custom_icon = True
    if props.set_default_brushes_custom_icon and not prefs.default_brushes_custom_icon:
        props.set_default_brushes_custom_icon = False


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


def set_toggle_default_icons(context, switch=False):
    prefs = context.preferences.addons[Addon_Name].preferences
    props = context.window_manager.brush_manager_props
    icon_themes_path = get_icon_themes_path()
    icons_path = os.path.join(icon_themes_path, prefs.brush_icon_theme)
    default_brushes = get_sorted_default_brushes(list_type='pref')
    if props.set_default_brushes_custom_icon and not switch:
        for brush in default_brushes:
            set_custom_icon(icons_path, brush)
    else:
        for brush in default_brushes:
            bpy.data.brushes[brush].use_custom_icon = False
            bpy.data.brushes[brush].icon_filepath = ''


def update_default_icons(self, context):
    set_toggle_default_icons(context)


def update_icon_theme(self, context):
    props = context.window_manager.brush_manager_props
    props.lib_categories = "Default"
    set_toggle_default_icons(context)
    clear_Default_list()
    update_brush_list(self, context)


def update_pref_def_brush(self, context):
    props = context.window_manager.brush_manager_props
    default_brushes = get_default_brushes_list()
    pref_def_brushes = get_pref_default_brush_props()
    for brush in default_brushes:
        if pref_def_brushes.get(brush):
            if not props.set_default_brushes_custom_icon:
                continue
            icons_path = get_icons_path()
            set_custom_icon(icons_path, brush)
            continue
        try:
            bpy.data.brushes[brush].use_custom_icon = False
            bpy.data.brushes[brush].icon_filepath = ''
        except KeyError:
            pass
    update_brush_list(self, context)


def remove_active_brush_favorite(self, context):
    b_preview_coll = preview_brushes_coll["favorites"]
    if b_preview_coll.my_previews_dir != "favorites":
        return {'FINISHED'}
    active_brush = context.window_manager.brushes_in_favorites
    brushes = get_favorite_brushes()
    try:
        brushes.remove(active_brush)
    except ValueError:
        msg = "Brush Manager: Nothing to remove"
        self.report({'ERROR'}, msg)
        return {'FINISHED'}
    enum_items = create_enum_list(context, brushes, b_preview_coll)
    b_preview_coll.my_previews = enum_items


def get_pref_default_brush_props():
    prefs = bpy.context.preferences.addons[Addon_Name].preferences
    props_list = [pr for pr in prefs.__annotations__ if pr.startswith("default_brush_")]
    props_values = []
    for pr in props_list:
        b_name = prefs.__annotations__.get(pr)[1].get('name')
        exec("props_values.append((b_name, prefs." + pr + "))")
    props_values = dict(props_values)
    return props_values


def get_pref_custom_def_brush_props():
    prefs = bpy.context.preferences.addons[Addon_Name].preferences
    custom_props_list = [pr for pr in prefs.__annotations__ if pr.startswith("add_def_brush_")]
    props_values = []
    for pr in custom_props_list:
        exec("if prefs." + pr + " != '': props_values.append(prefs." + pr + ")")
    return props_values


def get_pref_default_brushes():
    default_brushes = get_default_brushes_list()
    pref_def_brushes = get_pref_default_brush_props()
    pref_custom_def_brushes = get_pref_custom_def_brush_props()
    brushes_include = []
    for brush in default_brushes:
        if not pref_def_brushes.get(brush):
            continue
        brushes_include.append(brush)
    brushes_include = brushes_include + pref_custom_def_brushes
    return brushes_include


def get_sorted_default_brushes(list_type='pref'):
    if list_type == 'def':
        default_brushes = get_default_brushes_list()
    else:
        default_brushes = get_pref_default_brushes()
    default_brushes = filter_sculpt_brushes(default_brushes)
    sculpt_tools = get_default_brushes_list(list_type='sculpt_tools')
    current_brushes = get_current_file_brushes()
    for brush in current_brushes:
        sculpt_tool = bpy.data.brushes[brush].sculpt_tool
        if sculpt_tool in sculpt_tools:
            continue
        default_brushes.append(brush)
    return default_brushes


class WM_OT_Add_to_the_Favorites(Operator):
    bl_label = 'Add to the Favorites'
    bl_idname = 'add_brush_to_favorites.op'
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
    bl_label = 'Append a List to the Favorites'
    bl_idname = 'wm.append_list_to_favorites'
    bl_description = "Append the current preview brushes list to the Favorites"

    def execute(self, context):
        b_preview_fav = preview_brushes_coll["favorites"]
        b_preview_main = preview_brushes_coll["main"]
        if b_preview_fav.my_previews_dir != "favorites":
            return {'FINISHED'}
        main_preview_enums = b_preview_main.my_previews
        main_brushes = get_brushes_from_preview_enums(main_preview_enums)
        fav_brushes = get_favorite_brushes()
        brushes = main_brushes + fav_brushes
        brushes.sort()
        enum_items = create_enum_list(context, brushes, b_preview_fav)
        b_preview_fav.my_previews = enum_items
        return {'FINISHED'}


class WM_OT_Append_from_a_File_to_Favorites(Operator):
    bl_label = 'Load Brushes'
    bl_idname = 'wm.append_from_a_file_to_favorites'
    bl_description = "Append the brushes library from a file to the Favorites"

    exclude_default_brushes: bpy.props.BoolProperty(
        name="Exclude the Default Brushes",
        default=False,
        description="Exclude the default brushes from the list",
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

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def execute(self, context):
        if not self.filepath.endswith(".blend"):
            msg = "Selected file has to be a .blend file"
            self.report({'ERROR'}, msg)

            return {'FINISHED'}

        b_preview_fav = preview_brushes_coll["favorites"]
        b_preview_fav.my_previews_dir = "favorites"
        append_brushes_from_a_file(self.filepath)
        brushes_in_file = get_append_brushes(
            self.directory, b_files=[self.filename],
            exclude_default=self.exclude_default_brushes
        )
        fav_brushes = get_favorite_brushes()
        brushes = brushes_in_file + fav_brushes
        brushes.sort()
        enum_items = create_enum_list(context, brushes, b_preview_fav)
        b_preview_fav.my_previews = enum_items
        msg = "Brushes loaded from: " + self.filepath
        self.report({'INFO'}, msg)

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class WM_OT_Remove_Active_Favorite(Operator):
    bl_label = 'Remove the Active Favorite'
    bl_idname = 'wm.remove_active_brush_favorite'
    bl_description = "Remove the Active Brush from the favorites list"

    def execute(self, context):
        wm = context.window_manager
        brushes = get_favorite_brushes()
        if len(brushes) == 0:
            return {'FINISHED'}
        remove_active_brush_favorite(self, context)
        set_first_preview_item(context, brushes, wm_enum_prop='fav')
        return {'FINISHED'}


class WM_OT_Clear_Favorites(Operator):
    bl_label = 'Clear The Favorites'
    bl_idname = 'wm.clear_favorites'
    bl_description = "Remove all Brushes from the favorites list"

    def execute(self, context):
        wm = context.window_manager
        brushes = get_favorite_brushes()
        set_first_preview_item(context, brushes, wm_enum_prop='fav')
        clear_favorites_list()
        return {'FINISHED'}


class WM_OT_Delete_Zero_User_Brushes(Operator):
    bl_label = 'Delete All Zero User Brushes'
    bl_idname = 'wm.delete_unused_brushes'
    bl_description = "Delete all zero user brushes data"

    def execute(self, context):
        for brush in bpy.data.brushes:
            if not brush.use_paint_sculpt:
                continue
            if brush.users > 0:
                continue
            bpy.data.brushes.remove(brush, do_unlink=True)
        props = context.window_manager.brush_manager_props
        props.lib_categories = 'Default'
        update_brush_list(self, context)

        self.report({'INFO'}, "Zero user brushes data has been deleted")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class WM_OT_Delete_Active_Brush_Data(Operator):
    bl_label = 'Delete the Active Brush Data'
    bl_idname = 'wm.delete_active_brush'
    bl_description = "Delete the active brush from the current file data"

    def execute(self, context):
        active_brush_data = context.tool_settings.sculpt.brush
        if not active_brush_data:
            return {'FINISHED'}
        brush_name = active_brush_data.name
        bpy.data.brushes.remove(active_brush_data, do_unlink=True)
        update_brush_list(self, context)

        self.report({'INFO'}, "\"" + brush_name + "\" brush data has been deleted")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class WM_OT_Refresh_Category_List(Operator):
    bl_label = 'Refresh the Category List'
    bl_idname = 'wm.update_category_list'
    bl_description = "Update the brushes list in the selected library category"

    def execute(self, context):
        update_category(self, context)

        return {'FINISHED'}


class WM_OT_Save_Favorites(Operator):
    bl_label = 'Save Brushes'
    bl_idname = 'wm.save_favorites'
    bl_description = "Save the favorites list of brushes to a .blend file"

    relative_remap: bpy.props.BoolProperty(
        name="Remap Relative",
        default=True,
        description="Remap relative paths when saving to a different directory",
    )
    exclude_default_brushes: bpy.props.BoolProperty(
        name="Exclude the Default Brushes",
        default=False,
        description="Exclude the default brushes from the list",
    )
    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH"
    )

    @classmethod
    def poll(cls, context):
        return context.object is not None

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
            if b in def_brushes and self.exclude_default_brushes:
                continue
            try:
                if bpy.data.brushes[b].use_paint_sculpt:
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


class WM_OT_Save_Active_Brush(Operator):
    bl_label = 'Save Brush'
    bl_idname = 'wm.save_active_brush'
    bl_description = "Save the active brush to a .blend file"

    relative_remap: bpy.props.BoolProperty(
        name="Remap Relative",
        default=True,
        description="Remap relative paths when saving to a different directory",
    )
    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH"
    )

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def execute(self, context):
        if self.filepath.endswith(".blend"):
            blend_filepath = self.filepath
        else:
            blend_filepath = self.filepath + ".blend"
        brushes_data = [context.tool_settings.sculpt.brush]
        save_brushes_to_file(brushes_data, blend_filepath, relative_path_remap=self.relative_remap)
        update_brush_list(self, context)
        msg = "Brush \"" + brushes_data[0].name + "\" Saved to: " + blend_filepath
        self.report({'INFO'}, msg)

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class WM_OT_Open_Category_Folder(Operator):
    bl_idname = "wm.category_folder"
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
    bl_label = 'Reset All Default Brushes'
    bl_idname = 'wm.reset_default_brushes'
    bl_description = "Return all brushes settings from the Default list to their defaults"

    def execute(self, context):
        reset_all_default_brushes(context)

        self.report({'INFO'}, "Brushes has been returned to their defaults")

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


def theme_icons_for_custom_icon(self, context):
    directory = os.path.join(get_icon_themes_path(), self.theme)
    files = []
    if not directory or not os.path.isdir(directory):
        return files
    for file in os.listdir(directory):
        if not os.path.isfile(os.path.join(directory, file)):
            continue
        if file.lower().endswith('.png'):
            files.append((file, file, ""))
    return files


class WM_OT_Apply_Icon_to_Active_Brush(Operator):
    bl_label = 'Apply an Icon to the Active Brush'
    bl_idname = 'wm.set_icon_to_active_brush'
    bl_description = "Set custom icon from existing themes to the active brush"

    theme: EnumProperty(
        name='Theme',
        items=set_brush_icon_themes
    )
    icon: EnumProperty(
        name='Icon',
        items=theme_icons_for_custom_icon
    )

    def execute(self, context):
        directory = os.path.join(get_icon_themes_path(), self.theme)
        filepath = os.path.join(directory, self.icon)
        active_brush = context.tool_settings.sculpt.brush
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
            layout.operator('add_brush_to_favorites.op', icon='ADD')
        layout.operator("wm.append_list_to_favorites", icon='APPEND_BLEND')
        layout.separator()
        layout.prop(props, "set_default_brushes_custom_icon")
        layout.prop(props, "set_selected_brush_custom_icon")
        row = layout.row()
        row.enabled = props.set_selected_brush_custom_icon
        row.prop(props, "set_force_brush_custom_icon")
        layout.operator("wm.set_icon_to_active_brush", icon='FILE_IMAGE')
        layout.separator()
        layout.operator("wm.save_active_brush", text='Save the Active Brush to a File', icon='FILE_BLANK')
        layout.operator("wm.save_favorites", text='Save the Favorites to a File', icon='EXPORT')
        layout.operator("wm.append_from_a_file_to_favorites", text='Append from a File to the Favorites', icon='IMPORT')
        layout.separator()
        layout.operator("wm.reset_default_brushes", icon='PRESET')
        layout.separator()
        layout.operator("wm.delete_active_brush", icon='TRASH')
        layout.operator("wm.delete_unused_brushes", icon='TRASH')
        layout.separator()
        layout.operator("wm.remove_active_brush_favorite", icon='REMOVE')
        layout.operator("wm.clear_favorites", icon='X')


class Manager_Scene_Properties(PropertyGroup):

    lib_categories: EnumProperty(
        name='Category',
        items=lib_category_folders,
        description='The library category that contain the list of brushes existing in the blender file data',
        update=update_category
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
    )
    set_force_brush_custom_icon: BoolProperty(
        name="Force to Apply Theme to the Selected Brush",
        default=False,
        description="Force to apply theme to the selected brush if custom icon is already exists",
        update=update_force_theme_to_brush
    )
    exclude_default_brushes: BoolProperty(
        name="Exclude the Default Brushes",
        default=False,
        description="Exclude the default brushes from the list",
    )
    post_undo_last: BoolProperty(
        name="last post undo",
        default=False
    )
    update_after_save: BoolProperty(
        name="update after save",
        default=False
    )


class BrushManager_Preferences(AddonPreferences):

    bl_idname = Addon_Name

    brush_library: StringProperty(
        name="",
        subtype='DIR_PATH',
        # default="D:\\Blender\\Brush_Library",
        description='The main library folder containing sub-folders with the *.blend files of sculpt brushes'
    )
    preview_frame_scale: FloatProperty(
        name="Preview Frame Size",
        min=1,
        max=6.5,
        default=2.1,
        description='Scale the size of the preview frames on the Brushes Manager UI panel'
    )
    preview_items_scale: FloatProperty(
        name="Preview Items Size",
        min=1,
        max=7,
        default=2.8,
        description='Scale the size of icon in the brushes preview list'
    )
    move_add_to_favorite_op: BoolProperty(
        name="Move \'Add to the Favorites\' into Menu",
        default=False,
        description="Move the \'Add to the Favorites\' operator from UI panel into own menu. Useful for the preview frame scaling lower than default"
    )
    brush_icon_theme: EnumProperty(
        name='Icon Theme',
        items=set_brush_icon_themes,
        description="Select a theme for the brushes preview and custom icons",
        update=update_icon_theme
    )
    default_brushes_custom_icon: BoolProperty(
        name="Apply Custom Icon Theme to the Default Brushes",
        default=False,
        description="On file load every brush with the default name will have themed custom icon turned on.\
 These brushes could be specified in the add-on preference settings",
        update=update_pref_apply_theme_to_def
    )
    selected_brush_custom_icon: BoolProperty(
        name="Auto Apply Theme to the Selected Brush",
        default=False,
        description="On file load turn on option that is allows for the Brush Manager to automatically\
 apply a custom icon to the selected brush from any category list if it has not applied yet. It can be accessed in the panel menu",
        update=update_pref_apply_theme_to_selected
    )
    force_brush_custom_icon: BoolProperty(
        name="Force to Apply Theme to the Selected Brush",
        default=False,
        description="On file load turn on option that is allows for the Brush Manager a force to set a custom icon\
 to the selected brush even if it has been applied already. It can be accessed in the panel menu",
        update=update_pref_force_apply_theme_to_sel
    )
    switch_mode_on_save: BoolProperty(
        name="Switch Mode on Save",
        default=False,
        description="Switch to the Object Mode on save if currently in the Sculpt Mode.\
 Useful if you want to avoid of the undo limitation when opening the current file leading directly into the Sculpt Mode",
    )
    brushes = get_default_brushes_list()
    for i, brush in enumerate(brushes):
        default_brush = 'default_brush_' + str(i)
        exec(default_brush + ': BoolProperty(name="' + brush + '", default = True, update=update_pref_def_brush)')

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
        prefs = context.preferences.addons[Addon_Name].preferences
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Specify a path to a folder containing sub-folders with your sculpt brushes collections in *.blend files.")
        col = layout.column(align=True)
        col.label(text="Brush Library Path:")
        col.prop(self, "brush_library")
        box = layout.box()
        row = box.row()
        row.label(text="UI Settings:")
        row.prop(self, "move_add_to_favorite_op")
        row = box.row()
        row.label(text="Preview Frame Size:")
        row.prop(self, "preview_frame_scale", text='')
        row = box.row()
        row.label(text="Preview Brush Size:")
        row.prop(self, "preview_items_scale", text='')
        row = box.row()
        row.label(text="Brush Icon Theme:")
        row.prop(self, "brush_icon_theme", text='')
        row = box.row()
        row.prop(self, "default_brushes_custom_icon")
        row = box.row()
        row.prop(self, "selected_brush_custom_icon")
        row = box.row()
        row.enabled = prefs.selected_brush_custom_icon
        row.prop(self, "force_brush_custom_icon")
        row = box.row()
        row.prop(self, "switch_mode_on_save")
        box = layout.box()
        box.label(text="Default Brushes List:")
        row = box.row(align=True)
        grid = row.grid_flow(columns=3, align=True)
        brushes = get_default_brushes_list()
        for i, brush in enumerate(brushes):
            try:
                exec("if self.default_brush_" + str(i) + " != '': pass")
                grid.prop(self, 'default_brush_' + str(i), toggle=True)
            except AttributeError:
                continue
        wm = bpy.context.window_manager
        row = box.row(align=True)
        row.label(text="Custom Default Brush Slots:")
        row.prop(self, "default_brushes_custom_slots", text="")
        row.operator("op.refresh_brushes_data_list", icon='FILE_REFRESH')
        row = box.row(align=True)
        grid = row.grid_flow(columns=3, align=True)
        for i in range(self.default_brushes_custom_slots):
            grid.prop_search(self, 'add_def_brush_' + str(i), wm, "bm_brushes_data_list", text="")


class SCULPT_PT_Brush_Manager(Panel):
    bl_label = "Brush Manager"
    bl_idname = "VIEW3D_PT_brush_manager"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = "VIEW3D_PT_tools_brush_select"

    @classmethod
    def poll(cls, context):
        if context.mode == 'SCULPT':
            return True

    def __init__(self):
        props = bpy.context.window_manager.brush_manager_props
        b_preview_coll = preview_brushes_coll["main"]
        if bpy.data.scenes[0].name == 'Empty' and props.manager_empty_init is True:
            return None
        if bpy.data.scenes[0].name != 'Empty' and props.brush_manager_init is True:
            return None
        initialize_brush_manager_ui(props, b_preview_coll)

    def draw(self, context):
        prefs = context.preferences.addons[Addon_Name].preferences
        props = context.window_manager.brush_manager_props

        layout = self.layout
        row = layout.row()
        row = row.row(align=True)
        row.prop(props, "lib_categories", text='')
        if props.lib_categories != 'Default' and props.lib_categories != 'Current File':
            row.operator('wm.category_folder', text='', icon='FILE_FOLDER')
        row.operator('wm.update_category_list', text='', icon='FILE_REFRESH')
        row.prop(props, "search_in_category", text='', icon='VIEWZOOM')
        if props.search_in_category:
            row = layout.row()
            row.prop(props, "search_bar", text='')
            row.prop(props, "search_case_sensitive", text='', icon='FILE_TEXT')  # FILE_FONT, FILE_TEXT, 'TEXT'
        row = layout.row()
        row.template_icon_view(
            context.window_manager, "brushes_in_files", show_labels=True,
            scale=prefs.preview_frame_scale, scale_popup=prefs.preview_items_scale)  # scale=2,
        row.template_icon_view(
            context.window_manager, "brushes_in_favorites", show_labels=True,
            scale=prefs.preview_frame_scale, scale_popup=prefs.preview_items_scale)
        col = row.column()
        col.menu("VIEW3D_MT_Sculpt_brush_manager_menu", icon='DOWNARROW_HLT', text="")
        if not prefs.move_add_to_favorite_op:
            col.operator('add_brush_to_favorites.op', text='', icon='ADD')


class PREF_OT_Refresh_Brushes_Data_List(Operator):
    bl_idname = "op.refresh_brushes_data_list"
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
    brushes_current_file = get_current_file_brushes()
    brushes_default = get_default_brushes_list()
    brushes_sort = [b for b in brushes_current_file if b not in brushes_default]
    brushes_data_list.clear()
    for name in brushes_sort:
        item = brushes_data_list.add()
        item.name = name


def brush_manager_pre_undo(dummy):
    b_preview_coll = preview_brushes_coll["main"]
    b_preview_undo = preview_brushes_coll["undo"]
    b_preview_undo.my_previews = b_preview_coll.my_previews

    b_preview_fav = preview_brushes_coll["favorites"]
    b_preview_undof = preview_brushes_coll["undofav"]
    b_preview_undof.my_previews = b_preview_fav.my_previews


def brush_manager_post_undo(dummy):
    props = bpy.context.window_manager.brush_manager_props
    if bpy.context.mode != 'SCULPT' and not props.post_undo_last:
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
    if props.set_default_brushes_custom_icon:
        set_toggle_default_icons(bpy.context, switch=True)
    if bpy.context.mode == 'SCULPT' and prefs.switch_mode_on_save:
        bpy.ops.sculpt.sculptmode_toggle()


def brush_manager_post_save(dummy):
    bpy.context.window_manager.brush_manager_props.update_after_save = True


def brush_manager_pre_dp_update(dummy):
    props = bpy.context.window_manager.brush_manager_props
    if not props.update_after_save:
        return None
    props.update_after_save = False
    prefs = bpy.context.preferences.addons[Addon_Name].preferences
    if bpy.context.mode != 'SCULPT' and prefs.switch_mode_on_save:
        bpy.ops.sculpt.sculptmode_toggle()
    if props.set_default_brushes_custom_icon:
        set_toggle_default_icons(bpy.context)


class Brushes_Data_Collection(PropertyGroup):
    name: StringProperty(name="Custom Default Brush")


classes = (
    WM_OT_Add_to_the_Favorites,
    WM_OT_Append_List_to_the_Favorites,
    WM_OT_Append_from_a_File_to_Favorites,
    WM_OT_Remove_Active_Favorite,
    WM_OT_Clear_Favorites,
    WM_OT_Delete_Zero_User_Brushes,
    WM_OT_Delete_Active_Brush_Data,
    WM_OT_Refresh_Category_List,
    WM_OT_Save_Favorites,
    WM_OT_Save_Active_Brush,
    WM_OT_Open_Category_Folder,
    WM_OT_Reset_All_Default_Brushes,
    WM_OT_Apply_Icon_to_Active_Brush,
    WM_MT_BrushManager_Ops,
    PREF_OT_Refresh_Brushes_Data_List,
    SCULPT_PT_Brush_Manager,
    Brushes_Data_Collection,
    BrushManager_Preferences,
    Manager_Scene_Properties
)

preview_brushes_coll = {}


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    wm = bpy.types.WindowManager
    wm.brush_manager_props = PointerProperty(type=Manager_Scene_Properties)
    wm.bm_brushes_data_list = CollectionProperty(type=Brushes_Data_Collection)

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

    bpy.app.handlers.load_post.append(brush_manager_on_file_load)
    bpy.app.handlers.save_pre.append(brush_manager_pre_save)
    bpy.app.handlers.save_post.append(brush_manager_post_save)
    bpy.app.handlers.depsgraph_update_pre.append(brush_manager_pre_dp_update)
    bpy.app.handlers.undo_pre.append(brush_manager_pre_undo)
    bpy.app.handlers.undo_post.append(brush_manager_post_undo)
    set_brushes_data_collection_items()


def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)

    for bcoll in preview_brushes_coll.values():
        bpy.utils.previews.remove(bcoll)
    preview_brushes_coll.clear()
    try:
        bpy.app.handlers.load_post.remove(brush_manager_on_file_load)
        bpy.app.handlers.depsgraph_update_pre.remove(brush_manager_pre_dp_update)
        bpy.app.handlers.save_pre.remove(brush_manager_pre_save)
        bpy.app.handlers.save_pre.remove(brush_manager_post_save)
        bpy.app.handlers.undo_pre.remove(brush_manager_pre_undo)
        bpy.app.handlers.undo_post.remove(brush_manager_post_undo)
    except ValueError:
        pass
    del bpy.types.WindowManager.brush_manager_props
    del bpy.types.WindowManager.bm_brushes_data_list


if __name__ == "__main__":
    register()