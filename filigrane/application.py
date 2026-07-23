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
from collections.abc import Sequence
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gio", "2.0")

from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402

from filigrane import __app_id__  # noqa: E402
from filigrane.config import ConfigManager  # noqa: E402
from filigrane.core.history import HistoryManager  # noqa: E402
from filigrane.ui.about import show_about_dialog  # noqa: E402
from filigrane.ui.preferences import PreferencesDialog  # noqa: E402
from filigrane.ui.window import FiligraneWindow  # noqa: E402
from filigrane.utils.logger import get_logger, setup_logging  # noqa: E402

logger = get_logger()


class FiligraneApplication(Adw.Application):
  """Primary application class managing lifecycles and GNOME desktop integration."""

  def __init__(self) -> None:
    super().__init__(
      application_id=__app_id__,
      flags=Gio.ApplicationFlags.HANDLES_OPEN,
    )
    self.config_mgr = ConfigManager()
    self.history_mgr = HistoryManager()
    self.main_window: FiligraneWindow | None = None

    setup_logging(self.config_mgr.get_string("log-level"))

  def do_startup(self) -> None:
    """Initialize application components, style manager, and global actions."""
    Adw.Application.do_startup(self)

    # Register local data icon search path if available (for development mode)
    display = Gdk.Display.get_default()
    if display:
      icon_theme = Gtk.IconTheme.get_for_display(display)
      dev_icons_dir = Path(__file__).resolve().parent.parent / "data" / "icons"
      if dev_icons_dir.exists():
        icon_theme.add_search_path(str(dev_icons_dir))

    # Apply Theme Preference
    style_mgr = Adw.StyleManager.get_default()
    theme_pref = self.config_mgr.get_string("theme-preference")
    if theme_pref == "light":
      style_mgr.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
    elif theme_pref == "dark":
      style_mgr.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
    else:
      style_mgr.set_color_scheme(Adw.ColorScheme.DEFAULT)

    # Setup Simple Actions
    self._create_action("new-window", self._on_new_window_action, ["<Primary>n"])
    self._create_action("about", self._on_about_action)
    self._create_action("preferences", self._on_preferences_action)
    self._create_action("quit", self._on_quit_action, ["<Primary>q"])

    # Accels for window shortcuts
    self.set_accels_for_action("app.preferences", ["<Primary>comma"])

  def do_activate(self) -> None:
    """Activate main application window."""
    if not self.main_window:
      self.main_window = FiligraneWindow(
        app=self,
        config_mgr=self.config_mgr,
        history_mgr=self.history_mgr,
      )
    self.main_window.present()

  def do_open(self, files: Sequence[Gio.File], n_files: int, hint: str) -> None:
    """Handle opening files passed via GNOME Files 'Open With', command-line, or portal."""
    self.do_activate()
    paths = [p for f in files if (p := f.get_path()) is not None]
    if paths and self.main_window:
      self.main_window.open_file(paths[0])

  def _create_action(self, name: str, callback: Callable[..., None], accels: list[str] | None = None) -> None:
    action = Gio.SimpleAction.new(name, None)
    action.connect("activate", callback)
    self.add_action(action)
    if accels:
      self.set_accels_for_action(f"app.{name}", accels)

  def _on_new_window_action(self, action: Gio.SimpleAction, param: None) -> None:
    win = FiligraneWindow(
      app=self,
      config_mgr=self.config_mgr,
      history_mgr=self.history_mgr,
    )
    win.present()

  def _on_about_action(self, action: Gio.SimpleAction, param: None) -> None:
    if self.main_window:
      show_about_dialog(self.main_window)

  def _on_preferences_action(self, action: Gio.SimpleAction, param: None) -> None:
    if self.main_window:
      on_changed = (
        self.main_window.sidebar.refresh_presets
        if hasattr(self.main_window, "sidebar") and hasattr(self.main_window.sidebar, "refresh_presets")
        else None
      )
      dialog = PreferencesDialog(
        self.config_mgr,
        history_mgr=self.history_mgr,
        on_presets_changed=on_changed,
      )
      dialog.present(self.main_window)

  def _on_quit_action(self, action: Gio.SimpleAction, param: None) -> None:
    if self.main_window:
      self.main_window.close()
    else:
      self.quit()
