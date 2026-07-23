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
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk  # noqa: E402

from filigrane.application import FiligraneApplication  # noqa: E402
from filigrane.config import ConfigManager  # noqa: E402
from filigrane.core.history import HistoryManager  # noqa: E402
from filigrane.ui.shortcuts import show_shortcuts_dialog  # noqa: E402
from filigrane.ui.window import FiligraneWindow  # noqa: E402


def test_show_shortcuts_dialog() -> None:
  app = Adw.Application.new("io.gitlab.demsking.filigrane.testshortcuts1", Gio.ApplicationFlags.NON_UNIQUE)
  app.register()
  win = Gtk.Window(application=app)
  dialog = show_shortcuts_dialog(win)
  assert dialog is not None
  assert isinstance(dialog, Gtk.ShortcutsWindow)
  assert dialog.get_transient_for() == win


def test_window_shortcut_actions() -> None:
  app = FiligraneApplication()
  app.register()
  config_mgr = ConfigManager()
  history_mgr = HistoryManager()
  win = FiligraneWindow(app=app, config_mgr=config_mgr, history_mgr=history_mgr)

  actions = [
    "open",
    "export",
    "close-doc",
    "open-with",
    "print",
    "show-help-overlay",
    "prev-page",
    "next-page",
    "first-page",
    "last-page",
    "zoom-in",
    "zoom-out",
    "zoom-fit",
  ]
  for act_name in actions:
    assert win.has_action(act_name), f"Action win.{act_name} missing on FiligraneWindow"

  assert win.lookup_action("export").get_enabled() is False
  assert win.lookup_action("close-doc").get_enabled() is False
  assert win.lookup_action("open-with").get_enabled() is False
  assert win.lookup_action("print").get_enabled() is False
  assert win.lookup_action("show-help-overlay").get_enabled() is True
  assert app.has_action("new-window") is True
