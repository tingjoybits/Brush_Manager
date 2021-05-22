**Brushes Manager** is an add-on for Blender that helps you to create custom brushes, store them in a file and organize the library of various categories of brushes.
It also has themes for brushes preview and this add-on makes easy to apply a new themed icon for your newly created brush and for existing brushes as well.

Support Blender version: **2.83+**

# Installation

- [**DOWNLOAD LATEST RELEASE**](https://github.com/tingjoybits/Brush_Manager/releases/latest/download/Brush_Manager127b.zip)<- file
- Open Blender and select Edit->Preferences
- Click Add-ons category and then 'Install...' button
- Select the downloaded archive file from download link (The archive downloaded from 'Code' button won't work, please use the releases)
- Check the 'Brush Manager' option in the add-ons dialog

[![Installation](images/brush_manager_installation640x360.png)](https://drive.google.com/file/d/1eJ54uitBehOi_Xy4-lGUeZvVKPQ0EdO5/preview)

![Thumb](images/brush_manager_thumbnail.png)

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

# Change Log

**Brush Manager 1.2.7**

- New operator *'Save Favorites to Category'* added to the menu, that saves the favorites list of brushes to the new or existing library category. Shows a small popup window where you can type or select a name of the Category in which the list of brushes is gonna be saved (**Only Latin characters are supported**).
- Added to *'Edit Brushes from Category'* popup editor menu *'Save Brushes to Category'* operation, that saves the selected list of brushes, similar to the operation that has been described above.
- New operator *'Replace the Favorites by the Category List'*, that replaces the Favorites by the current preview brushes of the category list. The quick and easy way to clear and add the category list to the Favorites in one button.
- New preference property *'Display Default Brushes in Categories'*, that shows and use the default brushes in the selected category if contains them. Previously, or when this property being turned off, if the library file would contain any of the default brushes, they will be filtered out of the list.
- New preference property *'Use Preferences Editor for Settings'*, that opens the Preferences Editor for add-on settings instead of popup window. The main difference in functionality between the two is, that in the usual Preferences window is possible to reset properties to their default values.
- New preference property *"Move \'Replace Favorites by Category\' into Menu"*, that moves the *'Replace Favorites by Category'* operator from UI panel into own menu.

This update allows you to use the categories as a quick presets. Now you can quickly save brushes to the new category and then load with the help of the added operators.
Do not forget to check *'Display Default Brushes in Categories'* if you are planing to use the default brushes in your preset libraries.

![](images/new_common_prefs127.png)
![](images/new_pref_ui_prop127.png)
![](images/ui_layout127.png)
![](images/menu_operator127.png)
![](images/edit_category_menu127.png)
![](images/save_favs_to_category127.png)
![](images/add_to_cat_clear_favs127.png)


**Brush Manager 1.2.5**

- New popup editor for the Library Categories. You can access it from the menu with *'Edit Brushes from Category'* operator. Editor window contains the brush list of the corresponding category and a several new operations, that helps you to edit some properties of the selected brushes.
- Operator *'Refresh Brush Data'* for the category editor, that can refresh the selected brushes data and return to the settings of their library files.
- Operator *'Save Brushes'* for the category editor, that helps you to save a specific list of the selected brushes from the active category. Easy way to pick and save some brushes from various appended libraries that could be listed in the Current File category. That way you don't have to mess around with the favorites list.
- Operator *'Delete Brush Data'* for the category editor, that deletes the brush data of the selected brushes.
- Operator *'Change Icon Folder Path'* for the category editor, that changes a folder path to the same custom icon file name of the selected brushes in the edit list. Basically helps you to relocate missing icons to the new path.
- Operator *'Switch Custom Icon'* for the category editor, that turns on/off custom icons of the selected brushes in the edit list.
- Operator *'Switch Fake User'* for the category editor, that can applies/removes fake user of the selected brushes in the edit list.
- New theme icons for **Multires Displacement Smear** in Blender 2.92.
- New options to *'Overwrite', 'Auto Rename'* or *'Skip'* for duplicates while appending from a file to the favorites.
- Appending to the Favorites no longer produce duplicates with the same name.

![](icon_themes/round%20basic/displacement_smear.png)
![](images/appending_duplicates.png)

**Brush Manager 1.2.3a**

- Bring back Custom Brush Slots

**Brush Manager 1.2.3**

- Added support of **Weight Paint**, **Vertex Paint**, **GPencil Vertex Paint** modes.
- Now in the Settings you able to hide a specific non-brush tools in the popup window.
- Now popup window does not depend on Texture Paint context mode if you want to work in the Image Editor Paint mode.
	Its not the best idea, but to have the ability to call popup window from Object mode, for instance, should be there.
- Now the current category of brushes will stay the same for each mode from the moment that you left, while switching modes.
- Better handling of icon assignment while switching modes (If you had stumble upon on unwanted behavior, then updating is recommended).
- Overall code improvement and several small fixes.

**Brush Manager 1.2.0**

- Added Support of **Image Paint** and **Grease Pencil Draw** modes with new UI layout for these modes.
- New Preference Setting '*Hide Preview Frame*' for Sculpt mode, that hides the brush preview frame, to make UI layout the same look, as its like in other modes.
- Preference Setting Layout has been changed and organized with the rolled out sections.
- New Preference Setting '*Persistent Keymaps*' help you keep the same user defined keymaps when the app template has been loaded.
- New Preference Setting '*Hide Annotate Tools in Popup*', now you can hide or unhide Annotate tools in the tools list.
- New Preference Setting '*Close Popup on Tool Select*', if turned on (On by default), then close popup windows when brush or tool have been selected.
- New Brush buttons design that can be added to quick favorites builtin menu. Now they correctly represent active selected brush in the current context.
- Now Brush Manager Preference Settings can be saved in json file and later loaded with the help of new operator buttons, that are located in the preference settings.
- Added search bar filter in '*Add to Favorites from Category List*' popup.
- Added 'Add All the Rest' operator in '*Add to Favorites from Category List*' popup.
- Changed add-on category location in the Preferences from '*Sculpting*' to '*Interface*'.

![](images/Prederences1.2.0_r.png)
![](images/add_from_category1.2.0.png)

**Brush Manager 1.1.7**

- Added Sculpt Tools to the popup window.
- Added new header to the popup window. The header contains three new buttons:
  - '*Tools*' - Show/Hide the sculpt tools.
  - '*Brush Tools*' - Show/Hide the sculpt brush tools.
  - '*Settings*' - Show preference settings of the Brush Manager add-on in a separate window.
- Menu button moved to the Header in the popup window.
- New Preferences settings:
  - '*Hide Header in the Popup Window*' - Hide header buttons in the popup window and move them into the Menu. Buttons will be moved to the Menu and the Menu button to the popup layout.
  - '*Show Tools in Popup*' - Show tools by default in the popup window.
  - '*Brush Tools in Popup*'- Show brush tools by default in the popup window.
  - '*Popup Max Tool Columns*' - Set a maximum number of the columns for tools in the popup window.
  - '*Wide Popup Layout*' - Let Tools to show on the right side of the popup layout.
  - '*Wide Popup Layout Size*' - Scale the size of the popup layout.
- New possibility to hide particular brush tools that have been added to Default Brushes list section of Preference settings.
- Menu buttons '*Apply Custom Icon Theme*', '*Auto Apply Theme to the Selected Brush*' and '*Force to Apply Theme to the Selected Brush*'
 removed from the menu and now can be switched through '*Settings*'.
- Add to the Favorites from the Category List: Exclude brushes from the category list that are already existing in the Favorites, prevents to accidentally append duplicate brushes.
- Fixed unable to select the brush tool if the none - brush tool is currently active.
- Other small fixes.

![](images/wide_popup_medium.png)
![](images/layouts117.png)

**Brush Manager 1.1.5**
- Now properly displays all brushes in the preview category when a corresponding folder contains multiple .blend files

**Brush Manager 1.1.4**
- Updated the Default list of brushes for Blender 2.91. Added to themes new icons for new 'Boundary' and 'Multires Displacement Eraser' sculpt brushes.

![](icon_themes/round%20basic/boundary.png)
![](icon_themes/round%20basic/displacement_eraser.png)
- Added new menu operation that loads the Startup Favorites list from the specified file in the add-on preferences.
- Fixed the Default list when scripts have been reloaded

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
