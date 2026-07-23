# Copyright 2026 Sébastien Demanou. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from filigrane.utils.i18n import _  # noqa: E402

SHORTCUTS_UI = f"""
<interface>
  <object class="GtkShortcutsWindow" id="shortcuts_window">
    <property name="modal">True</property>
    <child>
      <object class="GtkShortcutsSection">
        <property name="visible">True</property>
        <property name="max-height">10</property>
        <child>
          <object class="GtkShortcutsGroup">
            <property name="title" translatable="yes">{_("General")}</property>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="accelerator">&lt;Primary&gt;n</property>
                <property name="title" translatable="yes">{_("New Window")}</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="accelerator">&lt;Primary&gt;comma</property>
                <property name="title" translatable="yes">{_("Preferences")}</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="accelerator">&lt;Primary&gt;question</property>
                <property name="title" translatable="yes">{_("Keyboard Shortcuts")}</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="accelerator">&lt;Primary&gt;q</property>
                <property name="title" translatable="yes">{_("Quit")}</property>
              </object>
            </child>
          </object>
        </child>
        <child>
          <object class="GtkShortcutsGroup">
            <property name="title" translatable="yes">{_("Document")}</property>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="accelerator">&lt;Primary&gt;o</property>
                <property name="title" translatable="yes">{_("Open PDF File")}</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="accelerator">&lt;Primary&gt;&lt;Shift&gt;o</property>
                <property name="title" translatable="yes">{_("Open PDF With…")}</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="accelerator">&lt;Primary&gt;p</property>
                <property name="title" translatable="yes">{_("Print PDF…")}</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="accelerator">&lt;Primary&gt;e</property>
                <property name="title" translatable="yes">{_("Export Watermarked PDF")}</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="accelerator">&lt;Primary&gt;w</property>
                <property name="title" translatable="yes">{_("Close Document")}</property>
              </object>
            </child>
          </object>
        </child>
        <child>
          <object class="GtkShortcutsGroup">
            <property name="title" translatable="yes">{_("Zoom")}</property>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="accelerator">&lt;Primary&gt;plus</property>
                <property name="title" translatable="yes">{_("Zoom In")}</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="accelerator">&lt;Primary&gt;minus</property>
                <property name="title" translatable="yes">{_("Zoom Out")}</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="accelerator">&lt;Primary&gt;0</property>
                <property name="title" translatable="yes">{_("Fit Page")}</property>
              </object>
            </child>
          </object>
        </child>
        <child>
          <object class="GtkShortcutsGroup">
            <property name="title" translatable="yes">{_("Navigation")}</property>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="accelerator">Page_Up</property>
                <property name="title" translatable="yes">{_("Previous Page")}</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="accelerator">Page_Down</property>
                <property name="title" translatable="yes">{_("Next Page")}</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="accelerator">Home</property>
                <property name="title" translatable="yes">{_("First Page")}</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="accelerator">End</property>
                <property name="title" translatable="yes">{_("Last Page")}</property>
              </object>
            </child>
          </object>
        </child>
      </object>
    </child>
  </object>
</interface>
"""


def _hide_search_button(widget: Gtk.Widget) -> bool:
  """Recursively find and hide the search toggle button in ShortcutsWindow."""
  if isinstance(widget, Gtk.ToggleButton) and widget.get_icon_name() == "edit-find-symbolic":
    widget.set_visible(False)
    return True
  child = widget.get_first_child()
  while child:
    if _hide_search_button(child):
      return True
    child = child.get_next_sibling()
  return False


def show_shortcuts_dialog(parent: Gtk.Window) -> Gtk.ShortcutsWindow:
  """Create and present the Keyboard Shortcuts dialog for Filigrane."""
  builder = Gtk.Builder.new_from_string(SHORTCUTS_UI, len(SHORTCUTS_UI))
  dialog = builder.get_object("shortcuts_window")
  if isinstance(dialog, Gtk.ShortcutsWindow):
    dialog.set_transient_for(parent)
    _hide_search_button(dialog)
    dialog.present()
    return dialog
  raise RuntimeError("Failed to load GtkShortcutsWindow from Builder XML")
