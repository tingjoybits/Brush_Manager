**Brushes Manager** is an add-on for Blender that helps you to create custom brushes, store them in a file and organize the library of various categories of brushes.
It also has themes for brushes preview and this add-on makes easy to apply a new themed icon for your newly created brush and for existing brushes as well.

Support Blender version: **2.83+**

# Installation

- [**Download**](https://github.com/tingjoybits/Brush_Manager/releases/download/1.1.2a/Brush_Manager112a.zip)<- file
- Open Blender and select Edit->Preferences
- Click Add-ons category and then 'Install...' button
- Select the downloaded file
- Check the 'Brush Manager' option in the add-ons dialog

[![Installation](images/brush_manager_installation640x360.png)](https://drive.google.com/file/d/1eJ54uitBehOi_Xy4-lGUeZvVKPQ0EdO5/preview)

# Overview

**Main UI Panel:**
![Panel](images/brush_manager_panel.png)

**Main UI Panel with the search filter turned on:**
![Search](images/brush_manager_search_panel.png)

**Menu of the Brush Manager with various operations:**
![Menu](images/brush_manager_menu.png)

**Add-on Preferences:**
![Preferences](images/brush_manager_preferences.png)

**Icon Themes:**
![Themes](images/brush_manager_themes.png)

# Change Log:

**Brush Manager 1.1.2**
- Added new Preference setting '*Popup Window Width*' that scale the size of the popup window width.
- Added new Preference setting '*UI Panel Default Closed*' that register the UI panel closed by default. (**Important**) In order to use it properly startup file have to use factory settings for the Brushes panel
- Added new Preference setting to load the Favorites at startup from the specified file if that list is empty in the loading file
- New menu popup operator '*Add to the Favorites from the Category List*' that helps you to pick specific brushes from the popup Category list to append them to the Favorites list
- New menu option '*Edit the Favorites List*' that displays remove button next to the favorite brushes. That way you can quickly remove unnecessary brushes from the list 
- Fixed custom icon being ignored if it has relative file path.
- Improved the Refresh button that refreshes category list icons and now for the Favorites list also
- Other small fixes

![](images/preferences112.png)
![](images/bm_ops_menu112.png)

*'Add to the Favorites from the Category List'* popup and *Edit the Favorites List*:

![](images/add_from_category.png)
![](images/edit_favorites_popup.png)

**Brush Manager 1.0.9**

* Fix 'Paint' brush listing in 2.90 if experimental feature is turned off for the Sculpt Vertex Colors
* Other small fixes

**Brush Manager 1.0.8**

* Moved keymap for popup into the 'Sculpt' mode section. Now you can assign 'Spacebar' key only for Sculpt mode to override Preference keymap setting and it will not interfere with other modes that uses Spacebar Action ( Play, Tools, Search )
* Added keymap menu to the add-on preferences from within Blender Keymap settings.
![addon_keymap](images/bm_keymap_pref_sign.png) 

**Brush Manager 1.0.7**

* New function added to save the Favorites list to the current file. (On Save include the favorites brushes in the current file data and memorize the current favorites list)
* Small fixes.

Menu operations added:

![save_load_menu|277x355](images/save_load_menu.png) 

That way you can save the list state on demand if new preference setting has not been turned on.

Preference setting for auto saving the favorites list on file save:

![save_fav_pref|482x396](images/save_fav_pref.png)

**Brush Manager 1.0.5**

- First implementation of the Popup menu with a hotkey (Alt + Space)( I'm still looking forward towards Blender 2.90 release. I hope there will be a new possibility in python API for a better version of the brushes palette.)

![Popup](images/brush_manager_popup.png)

Here you can change the hotkey if it has already using by another add-on:
![Popup_hotkey](images/bm_popup_hotkey.png)

New Preference setting:

![Popup_setting](images/bm_popup_setting.png)

**Support the Developer:**

You can support me here https://gum.co/zLBPz Thanks!
