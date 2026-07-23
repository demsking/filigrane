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
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from filigrane.config import ConfigManager  # noqa: E402
from filigrane.core.history import HistoryManager  # noqa: E402
from filigrane.utils.i18n import _  # noqa: E402


class PreferencesDialog(Adw.PreferencesDialog):
  """Preferences dialog managing user settings."""

  def __init__(
    self,
    config_manager: ConfigManager,
    history_mgr: HistoryManager | None = None,
    on_presets_changed: Callable[[], None] | None = None,
    **kwargs: Any,
  ) -> None:
    super().__init__(**kwargs)
    self.config = config_manager
    self.history_mgr = history_mgr
    self.on_presets_changed = on_presets_changed
    self._preset_rows: list[Adw.ActionRow] = []
    self.set_title(_("Preferences"))

    # General Page
    page = Adw.PreferencesPage.new()
    page.set_title(_("General"))
    page.set_icon_name("preferences-system-symbolic")
    self.add(page)

    # Security Group
    sec_group = Adw.PreferencesGroup.new()
    sec_group.set_title(_("Document Security &amp; Protection"))
    page.add(sec_group)

    # Protect PDF Switch
    self.protect_switch = Adw.SwitchRow.new()
    self.protect_switch.set_title(_("Protect Saved PDFs against Editing"))
    self.protect_switch.set_subtitle(_("Lock document modifications with AES-256 security permissions"))
    self.protect_switch.set_active(self.config.get_boolean("protect-pdf"))
    self.protect_switch.connect("notify::active", self._on_protect_changed)
    sec_group.add(self.protect_switch)

    # Protection Mode Combo
    self.protection_mode_combo = Adw.ComboRow.new()
    self.protection_mode_combo.set_title(_("Protection Mode"))
    model_mode = Gtk.StringList.new(
      [
        _("Standard (Vector AES-256)"),
        _("Maximum (Flattened Anti-Tamper)"),
      ]
    )
    self.protection_mode_combo.set_model(model_mode)
    current_mode = self.config.get_string("protection-mode")
    mode_idx = 1 if current_mode == "flatten_and_restrict" else 0
    self.protection_mode_combo.set_selected(mode_idx)
    self.protection_mode_combo.connect("notify::selected", self._on_protection_mode_changed)
    sec_group.add(self.protection_mode_combo)

    # Allow Printing Switch
    self.print_switch = Adw.SwitchRow.new()
    self.print_switch.set_title(_("Allow Printing"))
    self.print_switch.set_subtitle(_("Permit high-resolution printing of watermarked documents"))
    self.print_switch.set_active(self.config.get_boolean("allow-printing"))
    self.print_switch.connect("notify::active", self._on_print_permission_changed)
    sec_group.add(self.print_switch)

    # Interface Group
    ui_group = Adw.PreferencesGroup.new()
    ui_group.set_title(_("Appearance &amp; Performance"))
    page.add(ui_group)

    # Theme Preference
    self.theme_combo = Adw.ComboRow.new()
    self.theme_combo.set_title(_("Color Scheme"))
    model_theme = Gtk.StringList.new([_("System Default"), _("Light"), _("Dark")])
    self.theme_combo.set_model(model_theme)
    current_theme = self.config.get_string("theme-preference")
    theme_idx = 0 if current_theme == "system" else (1 if current_theme == "light" else 2)
    self.theme_combo.set_selected(theme_idx)
    self.theme_combo.connect("notify::selected", self._on_theme_changed)
    ui_group.add(self.theme_combo)

    # Preview Quality
    self.quality_combo = Adw.ComboRow.new()
    self.quality_combo.set_title(_("Preview Quality"))
    model_quality = Gtk.StringList.new([_("Low (Fast)"), _("Medium (Balanced)"), _("High (Crisp)")])
    self.quality_combo.set_model(model_quality)
    current_q = self.config.get_string("preview-quality")
    q_idx = 0 if current_q == "low" else (2 if current_q == "high" else 1)
    self.quality_combo.set_selected(q_idx)
    self.quality_combo.connect("notify::selected", self._on_quality_changed)
    ui_group.add(self.quality_combo)

    # Presets Group
    self.preset_group = Adw.PreferencesGroup.new()
    self.preset_group.set_title(_("Custom Watermark Presets"))
    page.add(self.preset_group)
    self._refresh_presets_group()

  def _refresh_presets_group(self) -> None:
    for row in self._preset_rows:
      self.preset_group.remove(row)
    self._preset_rows.clear()

    if not self.history_mgr:
      return

    custom_preset_names = [name for name in self.history_mgr.presets if self.history_mgr.is_custom_preset(name)]

    if not custom_preset_names:
      empty_row = Adw.ActionRow.new()
      empty_row.set_title(_("No Custom Presets"))
      empty_row.set_subtitle(_("Saved custom presets will appear here."))
      empty_row.set_sensitive(False)
      self.preset_group.add(empty_row)
      self._preset_rows.append(empty_row)
      return

    for preset_name in custom_preset_names:
      row = Adw.ActionRow.new()
      row.set_title(preset_name)
      preset_data = self.history_mgr.presets[preset_name]
      p_type = str(preset_data.get("type", "text")).capitalize()
      row.set_subtitle(_("{type} Watermark").format(type=p_type))

      btn_delete = Gtk.Button.new_from_icon_name("user-trash-symbolic")
      btn_delete.set_tooltip_text(_("Delete Preset"))
      btn_delete.set_valign(Gtk.Align.CENTER)
      btn_delete.add_css_class("flat")
      btn_delete.connect("clicked", self._on_delete_preset_clicked, preset_name)

      row.add_suffix(btn_delete)
      self.preset_group.add(row)
      self._preset_rows.append(row)

  def _on_delete_preset_clicked(self, btn: Gtk.Button, preset_name: str) -> None:
    root = self.get_root()
    dialog = Adw.MessageDialog.new(
      root if isinstance(root, Gtk.Window) else None,
      _("Delete Watermark Preset"),
      _('Are you sure you want to delete the preset "{name}"?').format(name=preset_name),
    )
    dialog.add_response("cancel", _("Cancel"))
    dialog.add_response("delete", _("Delete"))
    dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
    dialog.set_default_response("cancel")
    dialog.set_close_response("cancel")

    def _on_response(dlg: Adw.MessageDialog, response: str) -> None:
      if response == "delete" and self.history_mgr:
        self.history_mgr.delete_preset(preset_name)
        self._refresh_presets_group()
        if self.on_presets_changed:
          self.on_presets_changed()

    dialog.connect("response", _on_response)
    dialog.present()

  def _on_protect_changed(self, widget: Adw.SwitchRow, param: Any) -> None:
    self.config.set_boolean("protect-pdf", widget.get_active())

  def _on_protection_mode_changed(self, widget: Adw.ComboRow, param: Any) -> None:
    idx = widget.get_selected()
    mode_val = "flatten_and_restrict" if idx == 1 else "restrict_editing"
    self.config.set_string("protection-mode", mode_val)

  def _on_print_permission_changed(self, widget: Adw.SwitchRow, param: Any) -> None:
    self.config.set_boolean("allow-printing", widget.get_active())

  def _on_theme_changed(self, widget: Adw.ComboRow, param: Any) -> None:
    idx = widget.get_selected()
    values = ["system", "light", "dark"]
    if idx < len(values):
      self.config.set_string("theme-preference", values[idx])
      style_mgr = Adw.StyleManager.get_default()
      if values[idx] == "light":
        style_mgr.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
      elif values[idx] == "dark":
        style_mgr.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
      else:
        style_mgr.set_color_scheme(Adw.ColorScheme.DEFAULT)

  def _on_quality_changed(self, widget: Adw.ComboRow, param: Any) -> None:
    idx = widget.get_selected()
    values = ["low", "medium", "high"]
    if idx < len(values):
      self.config.set_string("preview-quality", values[idx])
