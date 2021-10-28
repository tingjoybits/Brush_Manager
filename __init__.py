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
import sys
import importlib

bl_info = {
    "name": "Brush Manager",
    "description": "Manage and organize of the brushes library",
    "author": "TingJoyBits",
    "blender": (2, 83, 0),
    "version": (1, 2, 9),
    "location": "Properties Editor > Active Tool tab > Brushes Panel",
    "doc_url": "https://github.com/tingjoybits/Brush_Manager",
    "category": "Interface"
}

modules = [
    'Brush_Manager'
]

modules_full_names = {}
for m in modules:
    modules_full_names[m] = ('{}.{}'.format(__name__, m))

for mf in modules_full_names.values():
    if mf in sys.modules:
        importlib.reload(sys.modules[mf])
    else:
        globals()[mf] = importlib.import_module(mf)
        setattr(globals()[mf], 'modules', modules_full_names)


def register():
    for mf in modules_full_names.values():
        if mf in sys.modules:
            if hasattr(sys.modules[mf], 'register'):
                sys.modules[mf].register()


def unregister():
    for mf in modules_full_names.values():
        if mf in sys.modules:
            if hasattr(sys.modules[mf], 'unregister'):
                sys.modules[mf].unregister()


if __name__ == "__main__":
    register()
