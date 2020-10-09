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
from bpy.props import *
import rna_keymap_ui

try:
    Addon_Name = __name__.split('.')[1]
except IndexError:
    Addon_Name = __name__


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


def get_active_brush(context):
    if context.mode == 'SCULPT':
        return context.tool_settings.sculpt.brush


def check_brush_type(brush, mode=''):
    if mode == '':
        mode = bpy.context.mode
    if mode == 'SCULPT':
        return brush.use_paint_sculpt


def get_append_brushes(directory, b_files, exclude_default=True):
    brushes_append = []
    brushes_in_files = get_brushes_in_files(directory, b_files)
    default_brushes = get_default_brushes_list()
    for brush in brushes_in_files:
        if brush in default_brushes and exclude_default:
            continue
        try:
            if not check_brush_type(bpy.data.brushes[brush]):
                continue
        except KeyError:
                continue
        brushes_append.append(brush)
        brushes_append = list(set(brushes_append))
        brushes_append.sort()
    return brushes_append


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


UPDATE_ICONS = False


def update_category(self, context):
    wm = bpy.context.window_manager
    props = wm.brush_manager_props
    if props.lib_categories == 'Default' and\
            context.mode == 'SCULPT':
        create_default_sculpt_tools()
    update_brush_list(self, context)
    update_fav_list(self, context)
    set_toggle_default_icons(context)


def update_brush_list(self, context):
    main_brushes = get_main_list_brushes(context)
    set_first_preview_item(context, main_brushes)
    b_preview_coll = preview_brushes_coll["main"]
    b_preview_coll.my_previews_dir = ""


def update_fav_list(self, context):
    fav_brushes = get_favorite_brushes()
    set_first_preview_item(context, fav_brushes, wm_enum_prop='fav')
    b_preview_coll = preview_brushes_coll["favorites"]
    b_preview_coll.my_previews_dir = ""


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
    brushes = filter_brushes_type(brushes_added)
    if len(brushes) == 0:
        b_files = get_b_files(directory)
        brushes = get_append_brushes(directory, b_files)
    return brushes


BRUSHES_SCULPT = [
    'Blob', 'Clay', 'Clay Strips', 'Clay Thumb', 'Cloth',
    'Crease', 'Draw Face Sets', 'Draw Sharp', 'Elastic Deform',
    'Fill/Deepen', 'Flatten/Contrast', 'Grab', 'Inflate/Deflate',
    'Layer', 'Mask', 'Multi-plane Scrape', 'Nudge', 'Pinch/Magnify',
    'Pose', 'Rotate', 'Scrape/Peaks', 'SculptDraw', 'Simplify',
    'Slide Relax', 'Smooth', 'Snake Hook', 'Thumb'
]
DEF_SCULPT_TOOLS = [
    'BLOB', 'CLAY', 'CLAY_STRIPS', 'CLAY_THUMB', 'CLOTH', 'CREASE',
    'DRAW_FACE_SETS', 'DRAW_SHARP', 'ELASTIC_DEFORM', 'FILL', 'FLATTEN',
    'GRAB', 'INFLATE', 'LAYER', 'MASK', 'MULTIPLANE_SCRAPE', 'NUDGE',
    'PINCH', 'POSE', 'ROTATE', 'SCRAPE', 'DRAW', 'SIMPLIFY', 'TOPOLOGY',
    'SMOOTH', 'SNAKE_HOOK', 'THUMB'
]


def get_default_brushes_list(list_type='brushes'):
    brushes = []
    def_tools = []
    if MODE == 'SCULPT':
        brushes = BRUSHES_SCULPT
        def_tools = DEF_SCULPT_TOOLS
    if list_type == 'brushes':
        return brushes
    if list_type == 'def_tools':
        return def_tools
    if list_type == 'slot_brushes':
        tool_slots = bpy.context.tool_settings.sculpt.tool_slots
        slot_brushes = []
        for i, ts in enumerate(tool_slots):
            if i == 0:
                continue
            slot_brushes.append(ts.brush.name)
        slot_brushes.sort()
        return slot_brushes
    if list_type == 'init_tools' or list_type == 'tools' or list_type == 'sculpt_tools':
        enum_items = []
        for brush in bpy.data.brushes:
            if (MODE == 'SCULPT' or list_type == 'sculpt_tools') and brush.use_paint_sculpt:
                enum_items = brush.bl_rna.properties['sculpt_tool'].enum_items
                break
    if list_type == 'init_tools':
        init_tools = dict([(b.identifier, b.name) for b in enum_items])
        return init_tools
    if list_type == 'tools' or list_type == 'sculpt_tools':
        tools = [t.identifier for t in enum_items]
        tools.sort()
        return tools
    return brushes


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
    enum_iconless = []
    edit = []
    for name1, name2, blank, iconid, index in enum_items:
        brushes_list.append(name1)
        icons.append(iconid)
        enum_iconless.append((name1, name2, '', index))
        if list_type == 'edit':
            edit.append((name1, '', '', 'REMOVE', index))
        if list_type == 'add':
            edit.append((name1, '', '', 'ADD', index))
    if list_type == 'icons':
        return icons
    if list_type == 'enum':
        return enum_iconless
    if list_type == 'edit' or list_type == 'add':
        return edit
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


def get_favorite_brushes_popup(self, context):
    return get_favorite_brushes(list_type='enum')
    # return preview_brushes_coll["favorites"].my_previews


def add_to_fav_active_current_brush(context, brushes_list):
    active_brush = get_active_brush(context)
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
    # brushes = get_sorted_default_brushes()
    enum_items = []
    if len(b_preview_coll.my_previews) > 0:
        b_preview_coll.my_previews.clear()
    # enum_items = create_enum_list(bpy.context, brushes, b_preview_coll, update_icon=True)
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


def get_icon_themes_path(folder_name='icon_themes'):
    current_file_dir = os.path.dirname(__file__)
    icon_themes_path = os.path.join(current_file_dir, folder_name)
    return icon_themes_path


def get_icons_path():
    prefs = bpy.context.preferences.addons[Addon_Name].preferences
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


def get_icon_name(context, brush_name):
    if context.mode == 'SCULPT':
        return bpy.data.brushes[brush_name].sculpt_tool.lower() + '.png'


def create_thumbnail_icon(context, brush_name, b_preview_coll):
    icons_path = get_icons_path()
    icon_name = get_icon_name(context, brush_name)
    filepath = os.path.join(icons_path, icon_name)
    if not os.path.isfile(filepath):
        icon_name = 'NA_brush.png'
        filepath = os.path.join(icons_path, icon_name)
    thumb = b_preview_coll.load(context.mode + '_' + brush_name, filepath, 'IMAGE')
    return thumb


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
            icon = b_preview_coll.get(context.mode + '_' + brush)
        if not icon:
            if bpy.data.brushes[brush].use_custom_icon:
                filepath = bpy.data.brushes[brush].icon_filepath
                if os.path.isfile(bpy.path.abspath(filepath)):
                    thumb = bpy.data.brushes[brush].preview.icon_id
                else:
                    thumb = create_thumbnail_icon(context, brush, b_preview_coll).icon_id
            else:
                thumb = create_thumbnail_icon(context, brush, b_preview_coll).icon_id
        else:
            thumb = b_preview_coll[context.mode + '_' + brush].icon_id
        enum_items.append((brush, brush, "", thumb, index))
    return enum_items


def reset_all_default_brushes(context):
    props = context.window_manager.brush_manager_props
    def_brushes = get_sorted_default_brushes()
    active_brush = get_active_brush(context)
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
    if bpy.context.mode != 'SCULPT':
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
    sculpt_tools = get_default_brushes_list(list_type='tools')
    current_brushes = get_current_file_brushes()
    current_tools = []
    def_stools = get_default_brushes_list(list_type='def_tools')
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
    try:
        tool_name = init_tools.get(active_brush.sculpt_tool)
    except AttributeError:
        return None
    if tool_name:
        set_active_tool("builtin_brush." + tool_name)
    bpy.context.tool_settings.sculpt.brush = active_brush


def check_current_file_brush_icons():
    brushes = get_current_file_brushes()
    for brush in brushes:
        if not bpy.data.brushes[brush].use_custom_icon:
            continue
        filepath = bpy.data.brushes[brush].icon_filepath
        if os.path.isfile(bpy.path.abspath(filepath)):
            continue
        bpy.data.brushes[brush].use_custom_icon = False


SCULPT_START_FAV_LOADED = False


def load_startup_favorites(list_type='SCULPT'):
    prefs = bpy.context.preferences.addons[Addon_Name].preferences
    if not prefs.use_sculpt_startup_favorites:
        return None
    if get_favorite_brushes():
        return None
    filepath = prefs.path_to_sculpt_startup_favorites
    if not os.path.isfile(filepath):
        return None
    if os.path.basename(filepath).split('.')[-1] != 'blend':
        return None
    b_preview_fav = preview_brushes_coll["favorites"]
    b_preview_fav.my_previews_dir = "favorites"
    append_brushes_from_a_file(filepath)
    brushes_in_file = get_append_brushes(
        os.path.dirname(filepath), b_files=[os.path.basename(filepath)],
        exclude_default=False
    )
    brushes_in_file.sort()
    enum_items = create_enum_list(bpy.context, brushes_in_file, b_preview_fav)
    b_preview_fav.my_previews = enum_items
    global SCULPT_START_FAV_LOADED
    SCULPT_START_FAV_LOADED = True
    return True


def handler_check(handler, function_name):
    if len(handler) <= 0:
        return False
    for i, h in enumerate(handler):
        func = str(handler[i]).split(' ')[1]
        if func == function_name:
            return True
    return False


MODE = 'NONE'


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
    MODE = bpy.context.mode
    clear_favorites_list()
    clear_Default_list()
    create_default_sculpt_tools()
    check_current_file_brush_icons()
    load_favorites_in_mode()
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


def set_brush_tool(context, brush):
    if context.mode == 'SCULPT':
        context.tool_settings.sculpt.brush = brush


def set_brush_from_lib_list(self, context):
    props = context.window_manager.brush_manager_props
    if props.skip_brush_set:
        props.skip_brush_set = False
        return None
    selected_brush = context.window_manager.brushes_in_files
    try:
        set_brush_tool(context, bpy.data.brushes[selected_brush])
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
        set_brush_tool(context, bpy.data.brushes[selected_brush])
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


def set_brush_from_fav_popup(self, context):
    props = context.window_manager.brush_manager_props
    selected_brush = context.window_manager.fav_brush_popup
    try:
        set_brush_tool(context, bpy.data.brushes[selected_brush])
    except KeyError:
        context.window_manager.popup_menu(SelectBrushError, title="Error", icon="INFO")
        remove_active_brush_favorite(self, context, fav_type='popup')
        return None
    if bpy.data.brushes[selected_brush].use_custom_icon and not props.set_force_brush_custom_icon:
        return None
    if props.set_selected_brush_custom_icon:
        icons_path = get_icons_path()
        set_custom_icon(icons_path, selected_brush)
    return None


def set_brush_from_add_fav_popup(self, context):
    props = context.window_manager.brush_manager_props
    selected_brush = self.brushes
    try:
        set_brush_tool(context, bpy.data.brushes[selected_brush])
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
    default_brushes = get_sorted_default_brushes()
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
    props.lib_categories = "Current File"
    global UPDATE_ICONS
    UPDATE_ICONS = True
    update_category(self, context)


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


def remove_fav_brush(self, context, remove_brushes):
    b_preview_coll = preview_brushes_coll["favorites"]
    if b_preview_coll.my_previews_dir != "favorites":
        return {'FINISHED'}
    brushes = get_favorite_brushes()
    for b in remove_brushes:
        try:
            brushes.remove(b)
        except ValueError:
            msg = "Brush Manager: Nothing to remove"
            self.report({'ERROR'}, msg)
            return {'FINISHED'}
    enum_items = create_enum_list(context, brushes, b_preview_coll)
    b_preview_coll.my_previews = enum_items


def remove_active_brush_favorite(self, context, fav_type='preview'):
    if fav_type == 'preview':
        active_brush = context.window_manager.brushes_in_favorites
    if fav_type == 'popup':
        active_brush = context.window_manager.fav_brush_popup
    remove_fav_brush(self, context, [active_brush])


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


def get_pref_default_brushes(list_type=''):
    if list_type == 'SCULPT':
        default_brushes = BRUSHES_SCULPT
    else:
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


def get_sorted_default_brushes():
    mode = bpy.context.mode
    default_brushes = get_pref_default_brushes()
    default_brushes = filter_brushes_type(default_brushes)
    tools = get_default_brushes_list(list_type='tools')
    current_brushes = get_current_file_brushes()
    for brush in current_brushes:
        tool = bpy.data.brushes[brush].sculpt_tool
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
        brushes = main_brushes + fav_brushes
        brushes.sort()
        enum_items = create_enum_list(context, brushes, b_preview_fav)
        b_preview_fav.my_previews = enum_items
        return {'FINISHED'}


class WM_OT_Append_from_a_File_to_Favorites(Operator):
    bl_label = 'Load Brushes'
    bl_idname = 'bm.append_from_a_file_to_favorites'
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
            if not check_brush_type(brush):
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
    exclude_default_brushes: bpy.props.BoolProperty(
        name="Exclude the Default Brushes",
        default=False,
        description="Exclude the default brushes from the list",
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
            if b in def_brushes and self.exclude_default_brushes:
                continue
            try:
                if check_brush_type(bpy.data.brushes[b]):
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


def get_fav_list_type(list_type):
    fav_list = None
    try:
        if list_type == 'SCULPT_SETTINGS':
            fav_list = bpy.context.scene.bm_favorite_list_settings
        if list_type == 'SCULPT':
            fav_list = bpy.context.window_manager.bm_sculpt_fav_list_store
        return fav_list
    except AttributeError:
        return None


SCULPT_SETTINGS_LOADED = False


def load_saved_favorites_list(list_type='SCULPT_SETTINGS'):
    global SCULPT_SETTINGS_LOADED
    global SCULPT_START_FAV_LOADED
    fav_list = get_fav_list_type(list_type)
    if fav_list is None:
        return None
    b_preview_fav = preview_brushes_coll["favorites"]
    b_preview_fav.my_previews_dir == "favorites"
    brushes = [i.name for i in fav_list]
    enum_items = create_enum_list(bpy.context, brushes, b_preview_fav)
    b_preview_fav.my_previews = enum_items
    if list_type == 'SCULPT_SETTINGS':
        SCULPT_SETTINGS_LOADED = True
        if brushes:
            SCULPT_START_FAV_LOADED = True
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
        load_saved_favorites_list('SCULPT_SETTINGS')

        return {'FINISHED'}


def store_favorites_list(list_type='SCULPT_SETTINGS'):
    fav_list = get_fav_list_type(list_type)
    if fav_list is None:
        return None
    brushes_list = get_favorite_brushes()
    fav_list.clear()
    for b in brushes_list:
        item = fav_list.add()
        item.name = b
        if list_type.split('_')[-1] == 'SETTINGS':
            bpy.data.brushes[b].use_fake_user = True


class WM_OT_Save_Favorites_to_current_file(Operator):
    bl_label = 'Save the Favorites to the Current File'
    bl_idname = 'bm.save_favorites_to_current_file'
    bl_description = "Save the favorites list of brushes to the current file"

    def execute(self, context):
        store_favorites_list('SCULPT_SETTINGS')
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
        layout.operator("bm.add_to_favorites_popup", icon='PRESET_NEW')
        layout.separator()
        if context.mode == 'SCULPT':
            layout.prop(props, "set_default_brushes_custom_icon")
            layout.prop(props, "set_selected_brush_custom_icon")
            row = layout.row()
            row.enabled = props.set_selected_brush_custom_icon
            row.prop(props, "set_force_brush_custom_icon")
        layout.operator("bm.set_icon_to_active_brush", icon='FILE_IMAGE')
        layout.separator()
        layout.operator("bm.save_favorites_to_current_file", icon='FILE_BLEND')
        layout.operator("bm.load_favorites_from_current_file", icon='FILE_BLEND')
        layout.operator("bm.save_active_brush", text='Save the Active Brush to a File', icon='FILE')
        layout.operator("bm.save_favorites", text='Save the Favorites to a File', icon='EXPORT')
        layout.operator("bm.append_from_a_file_to_favorites", text='Append from a File to the Favorites', icon='IMPORT')
        layout.separator()
        if context.mode == 'SCULPT':
            layout.operator("bm.reset_default_brushes", icon='PRESET')
            layout.separator()
        layout.operator("bm.delete_active_brush", icon='TRASH')
        layout.operator("bm.delete_unused_brushes", icon='TRASH')
        layout.separator()
        if (context.space_data.type == 'VIEW_3D' and context.region.type == 'WINDOW'):
            layout.prop(props, "edit_favorites")
            layout.operator("bm.remove_active_popup_favorite", icon='REMOVE')
        else:
            layout.operator("bm.edit_favorites_list_popup", icon='LONGDISPLAY')
            layout.operator("bm.remove_active_brush_favorite", icon='REMOVE')
        layout.operator("bm.clear_favorites", icon='X')


def edit_favorite_brushes_list(self, context):
    return get_favorite_brushes(list_type='edit')


def delete_fav_brush_list_update(self, context):
    brush_name = context.window_manager.bm_edit_fav_list
    brushes = get_favorite_brushes()
    if len(brushes) == 0:
        return None
    remove_fav_brush(self, context, [brush_name])
    set_first_preview_item(context, brushes, wm_enum_prop='fav')


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
    WindowManager.fav_brush_popup = EnumProperty(
        items=get_favorite_brushes_popup,
        update=set_brush_from_fav_popup
    )
    WindowManager.bm_edit_fav_list = EnumProperty(
        name="Remove",
        description="Remove brush from the Favorites list",
        items=edit_favorite_brushes_list,
        update=delete_fav_brush_list_update
    )
    edit_favorites: BoolProperty(
        name="Edit the Favorites List",
        default=False
    )


class BM_Side_Panel:
    def draw(self, context, layout):
        prefs = context.preferences.addons[Addon_Name].preferences
        props = context.window_manager.brush_manager_props

        layout = self.layout
        row = layout.row()
        row = row.row(align=True)
        row.prop(props, "lib_categories", text='')
        if props.lib_categories != 'Default' and props.lib_categories != 'Current File':
            row.operator('bm.category_folder', text='', icon='FILE_FOLDER')
        row.operator('bm.update_category_list', text='', icon='FILE_REFRESH')
        row.prop(props, "search_in_category", text='', icon='VIEWZOOM')
        if props.search_in_category:
            row = layout.row()
            row.prop(props, "search_bar", text='')
            row.prop(props, "search_case_sensitive", text='', icon='FILE_TEXT')
        row = layout.row()
        row.template_icon_view(
            context.window_manager, "brushes_in_files", show_labels=True,
            scale=prefs.preview_frame_scale, scale_popup=prefs.preview_items_scale)
        row.template_icon_view(
            context.window_manager, "brushes_in_favorites", show_labels=True,
            scale=prefs.preview_frame_scale, scale_popup=prefs.preview_items_scale)
        col = row.column()
        col.menu("VIEW3D_MT_Sculpt_brush_manager_menu", icon='DOWNARROW_HLT', text="")
        if not prefs.move_add_to_favorite_op:
            col.operator('bm.add_brush_to_favorites', text='', icon='ADD')


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
        BM_Initialization()

    def draw(self, context):
        layout = self.layout
        BM_Side_Panel.draw(self, context, layout)


panels = (
    SCULPT_PT_Brush_Manager,
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


class BrushManager_Preferences(AddonPreferences):

    bl_idname = Addon_Name

    brush_library: StringProperty(
        name="",
        subtype='DIR_PATH',
        # default="D:\\Blender\\Brush_Library",
        description='The main library folder containing sub-folders with the *.blend files of sculpt brushes'
    )
    path_to_sculpt_startup_favorites: StringProperty(
        name="Path to the Sculpt Startup Favorites List",
        subtype='FILE_PATH',
        description='The path to the .blend file that contains a list of brushes for the Sculpt Favorites'
    )
    use_sculpt_startup_favorites: BoolProperty(
        name="Use Sculpt Startup Favorites",
        default=False,
        description="Automatically load the Favorites list from the specified file if that list is empty in the current file"
    )
    ui_panel_closed: BoolProperty(
        name="UI Panel Default Closed",
        default=False,
        description="Register the UI panel closed by default. In order to use it properly startup file have to use factory settings for the Brushes panel",
        update=update_panel
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
    popup_items_scale: FloatProperty(
        name="Popup Button List Size",
        min=1,
        max=5,
        default=1.8,
        description='Scale the size of icon and button in the popup list'
    )
    popup_width: IntProperty(
        name="Popup Window Width",
        description='Scale the size of the popup window width',
        min=100, soft_min=100, max=300, soft_max=300, default=180
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
    save_favorites_list: BoolProperty(
        name="Save Favorites List to the Current File",
        default=False,
        description="On Save include the favorites brushes in the current file data and memorize the current favorites list"
    )
    switch_mode_on_save: BoolProperty(
        name="Switch Mode on Save",
        default=False,
        description="Switch to the Object Mode on save if currently in the Sculpt Mode.\
 Useful if you want to avoid of the undo limitation when opening the current file leading directly into the Sculpt Mode",
    )
    # brushes = get_default_brushes_list()
    brushes = BRUSHES_SCULPT
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
        # prefs = context.preferences.addons[Addon_Name].preferences
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
        row.label(text="Popup Button List Size:")
        row.prop(self, "popup_items_scale", text='')
        row = box.row()
        row.label(text="Popup Window Width:")
        row.prop(self, "popup_width", text='')
        row = box.row()
        row.label(text="Brush Icon Theme:")
        row.prop(self, "brush_icon_theme", text='')
        row = box.row()
        row.prop(self, "default_brushes_custom_icon")
        row = box.row()
        row.prop(self, "selected_brush_custom_icon")
        row = box.row()
        row.enabled = self.selected_brush_custom_icon
        row.prop(self, "force_brush_custom_icon")
        row = box.row()
        row.prop(self, "save_favorites_list")
        row = box.row()
        row.prop(self, "ui_panel_closed")
        row = box.row()
        row.prop(self, "switch_mode_on_save")
        box = layout.box()
        row = box.row()
        row.prop(self, "use_sculpt_startup_favorites")
        row = box.row()
        row.enabled = self.use_sculpt_startup_favorites
        row.prop(self, "path_to_sculpt_startup_favorites", text='')

        box = layout.box()
        col = box.column()
        col.label(text="Keymap:", icon="KEYINGSET")

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

        box = layout.box()
        box.label(text="Default Sculpt Brushes List:")
        row = box.row(align=True)
        grid = row.grid_flow(columns=3, align=True)
        # brushes = get_default_brushes_list()
        brushes = BRUSHES_SCULPT
        for i, brush in enumerate(brushes):
            try:
                exec("if self.default_brush_" + str(i) + " != '': pass")
                grid.prop(self, 'default_brush_' + str(i), toggle=True)
            except AttributeError:
                continue
        # wm = bpy.context.window_manager
        row = box.row(align=True)
        row.label(text="Custom Default Brush Slots:")
        row.prop(self, "default_brushes_custom_slots", text="")
        row.operator("bm.refresh_brushes_data_list", icon='FILE_REFRESH')
        row = box.row(align=True)
        grid = row.grid_flow(columns=3, align=True)
        for i in range(self.default_brushes_custom_slots):
            grid.prop_search(self, 'add_def_brush_' + str(i), wm, "bm_brushes_data_list", text="")


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
    brushes_current_file = get_current_file_brushes()
    brushes_default = get_default_brushes_list()
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
    global SCULPT_SETTINGS_LOADED
    global SCULPT_START_FAV_LOADED
    global MODE

    SCULPT_SETTINGS_LOADED = False
    SCULPT_START_FAV_LOADED = False
    MODE = 'NONE'
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
    if prefs.save_favorites_list:
        store_favorites_list('SCULPT_SETTINGS')
    if bpy.context.mode == 'SCULPT' and prefs.switch_mode_on_save:
        bpy.ops.sculpt.sculptmode_toggle()


def brush_manager_post_save(dummy):
    bpy.context.window_manager.brush_manager_props.update_after_save = True


def brush_manager_pre_dp_update(dummy):
    props = bpy.context.window_manager.brush_manager_props
    if not props.update_after_save:
        return None
    props.update_after_save = False
    if props.set_default_brushes_custom_icon:
        set_toggle_default_icons(bpy.context)


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
    global MODE
    loaded = False
    if not SCULPT_SETTINGS_LOADED and MODE == 'SCULPT':
        loaded = load_saved_favorites_list('SCULPT_SETTINGS')
    if not SCULPT_START_FAV_LOADED and MODE == 'SCULPT':
        create_default_sculpt_tools()
        if not loaded:
            loaded = load_startup_favorites(MODE)
    if not loaded:
        load_saved_favorites_list(MODE)


class WM_MT_Favorite_Popup_Menu(Operator):
    bl_label = 'Brush Manager Popup Menu'
    bl_idname = 'view3d.favorite_brushes_popup'

    def execute(self, context):
        space = context.space_data.type
        if space == 'VIEW_3D' and context.mode == 'SCULPT':
            BM_Initialization()
            global MODE
            MODE = context.mode
            prefs = context.preferences.addons[Addon_Name].preferences
            return context.window_manager.invoke_popup(self, width=prefs.popup_width)
        else:
            return {'CANCELLED'}

    def draw(self, context):
        prefs = context.preferences.addons[Addon_Name].preferences
        props = context.window_manager.brush_manager_props
        wm = bpy.context.window_manager

        layout = self.layout
        row = layout.row()
        row = row.row(align=True)
        row.prop(props, "lib_categories", text='')
        if props.lib_categories != 'Default' and props.lib_categories != 'Current File':
            row.operator('bm.category_folder', text='', icon='FILE_FOLDER')
        row.operator('bm.update_category_list', text='', icon='FILE_REFRESH')
        row.prop(props, "search_in_category", text='', icon='VIEWZOOM')
        if props.search_in_category:
            row = layout.row()
            row.prop(props, "search_bar", text='')
            row.prop(props, "search_case_sensitive", text='', icon='FILE_TEXT')
        row = layout.row()
        row.template_icon_view(
            wm, "brushes_in_files", show_labels=True,
            scale=prefs.preview_frame_scale, scale_popup=prefs.preview_items_scale)
        col = row.column()
        col.menu("VIEW3D_MT_Sculpt_brush_manager_menu", icon='DOWNARROW_HLT', text="")
        if not prefs.move_add_to_favorite_op:
            col.operator('bm.add_brush_to_favorites', text='', icon='ADD')

        row = layout.row(align=True)
        col = row.column()
        preview_brushes_in_favorites(self, context)
        icons = get_favorite_brushes(list_type='icons')
        for i, icon in enumerate(icons):
            col.template_icon(icon_value=icon, scale=prefs.popup_items_scale)
        col = row.column(align=False)
        col.scale_y = prefs.popup_items_scale
        col.props_enum(wm, "fav_brush_popup")

        col = row.column(align=False)
        col.scale_y = prefs.popup_items_scale
        if props.edit_favorites:
            col.props_enum(wm, "bm_edit_fav_list")


class WM_MT_Edit_Favorites_Popup(Operator):
    bl_label = 'Edit the Favorites List'
    bl_idname = 'bm.edit_favorites_list_popup'

    def execute(self, context):
        return context.window_manager.invoke_popup(self, width=180)

    def draw(self, context):
        prefs = context.preferences.addons[Addon_Name].preferences
        props = context.window_manager.brush_manager_props
        wm = bpy.context.window_manager
        icons = get_favorite_brushes(list_type='icons')

        layout = self.layout

        row = layout.row(align=True)
        col = row.column()
        for i, icon in enumerate(icons):
            col.template_icon(icon_value=icon, scale=prefs.popup_items_scale)
        col = row.column(align=False)
        col.scale_y = prefs.popup_items_scale
        col.props_enum(wm, "fav_brush_popup")

        col = row.column(align=False)
        col.scale_y = prefs.popup_items_scale
        col.props_enum(wm, "bm_edit_fav_list")


BRUSHES_IN_CATEGORY = []


def set_brushes_in_category_list_popup(brushes_enum):
    full = []
    for name1, name2, blank, iconid, index in brushes_enum:
        full.append((name1, name2, '', iconid, index))
    global BRUSHES_IN_CATEGORY
    BRUSHES_IN_CATEGORY = full


def get_popup_add_list(list_type=''):

    add = []
    icons = []
    enum_iconless = []
    for name1, name2, blank, iconid, index in BRUSHES_IN_CATEGORY:
        enum_iconless.append((name1, name2, '', index))
        icons.append(iconid)
        add.append((name1, '', '', 'ADD', index))
    if list_type == 'enum':
        return enum_iconless
    if list_type == 'icons':
        return icons
    return add


def brushes_in_category(self, context):
    return get_popup_add_list(list_type='enum')


def popup_add_list(self, context):
    return get_popup_add_list()


def add_to_fav_update(self, context):
    global BRUSHES_IN_CATEGORY
    b_preview_coll = preview_brushes_coll["favorites"]
    if b_preview_coll.my_previews_dir != "favorites":
        return None
    brushes_list = get_favorite_brushes()
    brushes_list.append(self.add_list)
    brushes_list.sort()
    enum_items = create_enum_list(context, brushes_list, b_preview_coll)
    b_preview_coll.my_previews = enum_items
    for i, (name1, name2, blank, iconid, index) in enumerate(BRUSHES_IN_CATEGORY):
        if self.add_list == name1:
            BRUSHES_IN_CATEGORY.pop(i)
            self['add_list'] = BRUSHES_IN_CATEGORY[0][-1]


class WM_MT_Add_to_Favorites_Popup(Operator):
    bl_label = 'Add to the Favorites from the Category List'
    bl_idname = 'bm.add_to_favorites_popup'
    bl_description = "Pick brushes from the popup Category list to append them to the Favorites list"

    brushes: EnumProperty(
        name='Brushes',
        items=brushes_in_category,
        update=set_brush_from_add_fav_popup
    )
    add_list: EnumProperty(
        name='Add',
        items=popup_add_list,
        update=add_to_fav_update
    )

    def execute(self, context):
        brushes_enum = get_main_list_brushes(context, list_type='full')
        set_brushes_in_category_list_popup(brushes_enum)
        return context.window_manager.invoke_popup(self, width=300)

    def draw(self, context):
        prefs = context.preferences.addons[Addon_Name].preferences
        props = context.window_manager.brush_manager_props
        wm = bpy.context.window_manager
        icons = get_popup_add_list(list_type='icons')

        layout = self.layout

        row = layout.row(align=True)
        col1 = row.column()
        row1 = col1.row()
        row1.label(text='')
        row1.label(text='')
        row1.label(text='', icon='PRESET_NEW')
        col2 = row.column()
        row2 = col2.row()
        row2.label(text='')
        row2.label(text='')
        row2.label(text='', icon='SOLO_ON')
        row = col1.row(align=True)
        col = row.column()
        for i, icon in enumerate(icons):
            col.template_icon(icon_value=icon, scale=prefs.popup_items_scale)
        col = row.column(align=False)
        col.scale_y = prefs.popup_items_scale
        col.props_enum(self, "brushes")

        col = row.column(align=False)
        col.scale_y = prefs.popup_items_scale
        col.props_enum(self, "add_list")
        #////////////////////////////////
        icons = get_favorite_brushes(list_type='icons')
        row = col2.row(align=True)
        col = row.column()
        for i, icon in enumerate(icons):
            col.template_icon(icon_value=icon, scale=prefs.popup_items_scale)
        col = row.column(align=False)
        col.scale_y = prefs.popup_items_scale
        col.props_enum(wm, "fav_brush_popup")

        col = row.column(align=False)
        col.scale_y = prefs.popup_items_scale
        col.props_enum(wm, "bm_edit_fav_list")


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
    WM_OT_Save_Active_Brush,
    WM_OT_Open_Category_Folder,
    WM_OT_Reset_All_Default_Brushes,
    WM_OT_Apply_Icon_to_Active_Brush,
    WM_MT_BrushManager_Ops,
    PREF_OT_Refresh_Brushes_Data_List,
    SCULPT_PT_Brush_Manager,
    WM_MT_Favorite_Popup_Menu,
    WM_MT_Edit_Favorites_Popup,
    WM_MT_Add_to_Favorites_Popup,
    Brushes_Data_Collection,
    BM_Favorite_list_settings,
    BrushManager_Preferences,
    Manager_Scene_Properties
)

preview_brushes_coll = {}
addon_keymaps = []


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
    wm.brush_manager_props = PointerProperty(type=Manager_Scene_Properties)
    wm.bm_brushes_data_list = CollectionProperty(type=Brushes_Data_Collection)
    wm.bm_sculpt_fav_list_store = CollectionProperty(type=BM_Favorite_list_settings)
    bpy.types.Scene.bm_favorite_list_settings = bpy.props.CollectionProperty(type=BM_Favorite_list_settings)

    winm = bpy.context.window_manager
    keyconf = winm.keyconfigs.addon
    if keyconf:
        keymap = keyconf.keymaps.new(name='Sculpt', space_type='EMPTY', region_type='WINDOW')
        keymap_item = keymap.keymap_items.new("view3d.favorite_brushes_popup", type='SPACE', value='PRESS', alt=True)
        addon_keymaps.append((keymap, keymap_item))

    bpy.app.handlers.load_post.append(brush_manager_on_file_load)
    bpy.app.handlers.save_pre.append(brush_manager_pre_save)
    bpy.app.handlers.save_post.append(brush_manager_post_save)
    bpy.app.handlers.depsgraph_update_pre.append(brush_manager_pre_dp_update)
    bpy.app.handlers.undo_pre.append(brush_manager_pre_undo)
    bpy.app.handlers.undo_post.append(brush_manager_post_undo)
    set_brushes_data_collection_items()
    update_panel(None, bpy.context)


def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

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
    del bpy.types.Scene.bm_favorite_list_settings


if __name__ == "__main__":
    register()
