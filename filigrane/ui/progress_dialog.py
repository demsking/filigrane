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
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GLib", "2.0")
gi.require_version("Pango", "1.0")
from gi.repository import Adw, GLib, Gtk, Pango  # noqa: E402

from filigrane.utils.i18n import _  # noqa: E402


class ProgressDialog:
  """Non-blocking export progress window with progress bar and cancel button."""

  def __init__(self, parent_window: Gtk.Window, on_cancel: Callable[[], None]) -> None:
    self.parent = parent_window
    self.on_cancel_callback = on_cancel

    self.window = Adw.Window.new()
    self.window.set_transient_for(parent_window)
    self.window.set_modal(True)
    self.window.set_default_size(420, 200)
    self.window.set_resizable(False)
    self.window.set_deletable(False)

    toolbar_view = Adw.ToolbarView.new()
    self.window.set_content(toolbar_view)

    header_bar = Adw.HeaderBar.new()
    header_bar.set_show_start_title_buttons(False)
    header_bar.set_show_end_title_buttons(False)
    toolbar_view.add_top_bar(header_bar)

    title = Gtk.Label.new(_("Exporting Watermarked PDF"))
    title.add_css_class("title")
    header_bar.set_title_widget(title)

    vbox = Gtk.Box.new(Gtk.Orientation.VERTICAL, 16)
    vbox.set_margin_start(24)
    vbox.set_margin_end(24)
    vbox.set_margin_top(20)
    vbox.set_margin_bottom(24)
    vbox.set_valign(Gtk.Align.CENTER)
    toolbar_view.set_content(vbox)

    self.status_label = Gtk.Label.new(_("Preparing export..."))
    self.status_label.set_halign(Gtk.Align.START)
    self.status_label.set_ellipsize(Pango.EllipsizeMode.END)
    vbox.append(self.status_label)

    self.progress_bar = Gtk.ProgressBar.new()
    self.progress_bar.set_fraction(0.0)
    vbox.append(self.progress_bar)

    btn_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 8)
    btn_box.set_halign(Gtk.Align.END)
    vbox.append(btn_box)

    self.btn_cancel = Gtk.Button.new_with_label(_("Cancel"))
    self.btn_cancel.add_css_class("destructive-action")
    self.btn_cancel.connect("clicked", self._on_cancel_clicked)
    btn_box.append(self.btn_cancel)

  def show(self) -> None:
    """Present progress dialog."""
    self.window.present()

  def close(self) -> None:
    """Close progress dialog."""
    self.window.close()

  def update(self, fraction: float, message: str) -> None:
    """Update progress bar fraction (0.0 to 1.0) and status message safely on GTK main thread."""

    def _do_update() -> bool:
      self.progress_bar.set_fraction(max(0.0, min(1.0, fraction)))
      self.status_label.set_text(message)
      return False

    GLib.idle_add(_do_update)

  def _on_cancel_clicked(self, widget: Gtk.Button) -> None:
    self.btn_cancel.set_sensitive(False)
    self.status_label.set_text(_("Cancelling operation..."))
    self.on_cancel_callback()
