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
from pathlib import Path
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
gi.require_version("Gio", "2.0")
gi.require_version("GObject", "2.0")
gi.require_version("Pango", "1.0")
from gi.repository import Adw, Gdk, Gio, GObject, Gtk, Pango  # noqa: E402

from filigrane.config import ConfigManager  # noqa: E402
from filigrane.core.history import HistoryManager  # noqa: E402
from filigrane.core.watermark import (  # noqa: E402
  ProtectionMode,
  SecurityConfig,
  WatermarkPosition,
  WatermarkSettings,
  WatermarkType,
)
from filigrane.utils.file_utils import format_file_size, is_valid_image_file  # noqa: E402
from filigrane.utils.i18n import _  # noqa: E402
from filigrane.utils.logger import get_logger  # noqa: E402

logger = get_logger()


class Sidebar(Gtk.Box):
  """Sidebar panel containing all watermark configuration controls."""

  def __init__(
    self,
    history_mgr: HistoryManager,
    on_settings_changed: Callable[[WatermarkSettings], None],
    on_file_changed: Callable[[str | None], None],
    config_mgr: ConfigManager | None = None,
    **kwargs: Any,
  ) -> None:
    super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0, **kwargs)

    self.history_mgr = history_mgr
    self.config_mgr = config_mgr
    self.on_settings_changed_cb = on_settings_changed
    self.on_file_changed_cb = on_file_changed

    self.loaded_pdf_file: str | None = None
    self.settings: WatermarkSettings = WatermarkSettings()
    if self.config_mgr:
      mode_str = self.config_mgr.get_string("protection-mode")
      mode = ProtectionMode.FLATTEN_AND_RESTRICT if mode_str == "flatten_and_restrict" else ProtectionMode.RESTRICT_EDITING
      self.settings.security_config = SecurityConfig(
        enabled=self.config_mgr.get_boolean("protect-pdf"),
        mode=mode,
        allow_printing=self.config_mgr.get_boolean("allow-printing"),
        owner_password=self.config_mgr.get_string("custom-owner-password"),
      )

    # Scrolled container for modern Libadwaita layout
    scrolled = Gtk.ScrolledWindow.new()
    scrolled.set_hexpand(True)
    scrolled.set_vexpand(True)
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    self.append(scrolled)

    page = Adw.PreferencesPage.new()
    scrolled.set_child(page)

    # ----------------------------------------------------
    # Watermark Mode Selector
    # ----------------------------------------------------
    type_group = Adw.PreferencesGroup.new()
    page.add(type_group)

    # Linked ToggleButton mode bar
    mode_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 0)
    mode_box.add_css_class("linked")
    mode_box.set_halign(Gtk.Align.FILL)
    mode_box.set_margin_top(0)
    mode_box.set_margin_bottom(18)

    self.btn_mode_text = Gtk.ToggleButton.new_with_label(_("Text"))
    self.btn_mode_text.set_hexpand(True)
    self.btn_mode_text.set_active(True)

    self.btn_mode_image = Gtk.ToggleButton.new_with_label(_("Image"))
    self.btn_mode_image.set_hexpand(True)
    self.btn_mode_image.set_group(self.btn_mode_text)

    self.btn_mode_text.connect("toggled", self._on_mode_toggled)
    self.btn_mode_image.connect("toggled", self._on_mode_toggled)

    mode_box.append(self.btn_mode_text)
    mode_box.append(self.btn_mode_image)
    type_group.add(mode_box)

    self.type_stack = Gtk.Stack.new()
    self.type_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
    type_group.add(self.type_stack)

    # ----------------------------------------------------
    # Text Watermark Page
    # ----------------------------------------------------
    text_group = Adw.PreferencesGroup.new()
    text_group.set_title(_("Text Parameters"))

    # Text Entry
    self.entry_text = Adw.EntryRow.new()
    self.entry_text.set_title(_("Watermark Text"))
    self.entry_text.set_text(self.settings.text_config.text)
    self.entry_text.connect("changed", self._on_text_param_changed)
    text_group.add(self.entry_text)

    # Font & Size
    self.font_row = Adw.ActionRow.new()
    self.font_row.set_title(_("Font Family"))
    self.font_btn = Gtk.FontDialogButton.new(Gtk.FontDialog.new())
    self.font_btn.set_valign(Gtk.Align.CENTER)
    self.font_btn.connect("notify::font-desc", self._on_font_selected)
    self.font_row.add_suffix(self.font_btn)
    text_group.add(self.font_row)

    self.spin_font_size = Adw.SpinRow.new_with_range(4, 500, 1)
    self.spin_font_size.set_digits(0)
    self.spin_font_size.set_title(_("Font Size"))
    self.spin_font_size.set_value(self.settings.text_config.font_size)
    self.spin_font_size.connect("notify::value", self._on_text_param_changed)
    text_group.add(self.spin_font_size)

    # Styles (Bold, Italic, Underline)
    style_row = Adw.ActionRow.new()
    style_row.set_title(_("Text Style"))
    style_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 4)
    style_box.set_valign(Gtk.Align.CENTER)

    self.toggle_bold = Gtk.ToggleButton.new_with_label("B")
    self.toggle_bold.set_active(self.settings.text_config.bold)
    self.toggle_bold.connect("toggled", self._on_text_param_changed)
    style_box.append(self.toggle_bold)

    self.toggle_italic = Gtk.ToggleButton.new_with_label("I")
    self.toggle_italic.set_active(self.settings.text_config.italic)
    self.toggle_italic.connect("toggled", self._on_text_param_changed)
    style_box.append(self.toggle_italic)

    self.toggle_underline = Gtk.ToggleButton.new_with_label("U")
    self.toggle_underline.set_active(self.settings.text_config.underline)
    self.toggle_underline.connect("toggled", self._on_text_param_changed)
    style_box.append(self.toggle_underline)

    style_row.add_suffix(style_box)
    text_group.add(style_row)

    # Color & Opacity
    color_row = Adw.ActionRow.new()
    color_row.set_title(_("Watermark Color"))
    self.color_btn = Gtk.ColorDialogButton.new(Gtk.ColorDialog.new())
    self.color_btn.set_valign(Gtk.Align.CENTER)
    self.color_btn.connect("notify::rgba", self._on_text_param_changed)
    color_row.add_suffix(self.color_btn)
    text_group.add(color_row)

    self.spin_text_opacity = Adw.SpinRow.new_with_range(0.05, 1.0, 0.05)
    self.spin_text_opacity.set_digits(2)
    self.spin_text_opacity.set_title(_("Opacity"))
    self.spin_text_opacity.set_value(self.settings.text_config.opacity)
    self.spin_text_opacity.connect("notify::value", self._on_text_param_changed)
    text_group.add(self.spin_text_opacity)

    # Rotation
    self.spin_text_rotation = Adw.SpinRow.new_with_range(-180, 180, 5)
    self.spin_text_rotation.set_digits(0)
    self.spin_text_rotation.set_title(_("Rotation Angle (°)"))
    self.spin_text_rotation.set_value(self.settings.text_config.rotation)
    self.spin_text_rotation.connect("notify::value", self._on_text_param_changed)
    text_group.add(self.spin_text_rotation)

    # ----------------------------------------------------
    # Image Watermark Group
    # ----------------------------------------------------
    image_drop_group = Adw.PreferencesGroup.new()
    image_drop_group.set_title(_("Image Parameters"))

    self._setup_drop_zone_css()
    self.image_drop_zone = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
    self.image_drop_zone.add_css_class("image-drop-card")
    self.image_drop_zone.add_css_class("card")

    drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
    drop_target.connect("drop", self._on_image_file_dropped)
    drop_target.connect("notify::current-drop", self._on_image_drop_notify)
    self.image_drop_zone.add_controller(drop_target)

    self._update_image_drop_zone_ui()

    self.img_file_row = self.image_drop_zone
    image_drop_group.add(self.image_drop_zone)

    image_params_group = Adw.PreferencesGroup.new()

    self.spin_img_scale = Adw.SpinRow.new_with_range(0.1, 5.0, 0.1)
    self.spin_img_scale.set_digits(1)
    self.spin_img_scale.set_title(_("Scale Factor"))
    self.spin_img_scale.set_value(self.settings.image_config.scale)
    self.spin_img_scale.connect("notify::value", self._on_img_param_changed)
    image_params_group.add(self.spin_img_scale)

    self.spin_img_opacity = Adw.SpinRow.new_with_range(0.05, 1.0, 0.05)
    self.spin_img_opacity.set_digits(2)
    self.spin_img_opacity.set_title(_("Opacity"))
    self.spin_img_opacity.set_value(self.settings.image_config.opacity)
    self.spin_img_opacity.connect("notify::value", self._on_img_param_changed)
    image_params_group.add(self.spin_img_opacity)

    self.spin_img_rotation = Adw.SpinRow.new_with_range(-180, 180, 5)
    self.spin_img_rotation.set_digits(0)
    self.spin_img_rotation.set_title(_("Rotation Angle"))
    self.spin_img_rotation.set_value(self.settings.image_config.rotation)
    self.spin_img_rotation.connect("notify::value", self._on_img_param_changed)
    image_params_group.add(self.spin_img_rotation)

    self.switch_aspect = Adw.SwitchRow.new()
    self.switch_aspect.set_title(_("Preserve Aspect Ratio"))
    self.switch_aspect.set_active(self.settings.image_config.preserve_aspect)
    self.switch_aspect.connect("notify::active", self._on_img_param_changed)
    image_params_group.add(self.switch_aspect)

    # Add groups to stack
    img_container = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
    img_container.append(image_drop_group)
    img_container.append(image_params_group)

    self.type_stack.add_named(text_group, "text")
    self.type_stack.add_named(img_container, "image")

    # ----------------------------------------------------
    # Placement Group
    # ----------------------------------------------------
    pos_group = Adw.PreferencesGroup.new()
    pos_group.set_title(_("Placement &amp; Alignment"))
    page.add(pos_group)

    self.combo_pos = Adw.ComboRow.new()
    self.combo_pos.set_title(_("Position Preset"))
    pos_model = Gtk.StringList.new(
      [
        _("Center"),
        _("Top Left"),
        _("Top Right"),
        _("Bottom Left"),
        _("Bottom Right"),
        _("Repeat Whole Page (Tiled)"),
        _("Custom X/Y"),
      ]
    )
    self.combo_pos.set_model(pos_model)
    self.combo_pos.connect("notify::selected", self._on_pos_changed)
    pos_group.add(self.combo_pos)

    self.spin_margin_x = Adw.SpinRow.new_with_range(0, 300, 5)
    self.spin_margin_x.set_digits(0)
    self.spin_margin_x.set_title(_("Margin X"))
    self.spin_margin_x.set_value(20.0)
    self.spin_margin_x.connect("notify::value", self._on_pos_changed)
    pos_group.add(self.spin_margin_x)

    self.spin_margin_y = Adw.SpinRow.new_with_range(0, 300, 5)
    self.spin_margin_y.set_digits(0)
    self.spin_margin_y.set_title(_("Margin Y"))
    self.spin_margin_y.set_value(20.0)
    self.spin_margin_y.connect("notify::value", self._on_pos_changed)
    pos_group.add(self.spin_margin_y)

    self.spin_custom_x = Adw.SpinRow.new_with_range(0, 100, 1)
    self.spin_custom_x.set_digits(0)
    self.spin_custom_x.set_title(_("Custom Position X (%)"))
    self.spin_custom_x.set_value(50.0)
    self.spin_custom_x.set_visible(False)
    self.spin_custom_x.connect("notify::value", self._on_pos_changed)
    pos_group.add(self.spin_custom_x)

    self.spin_custom_y = Adw.SpinRow.new_with_range(0, 100, 1)
    self.spin_custom_y.set_digits(0)
    self.spin_custom_y.set_title(_("Custom Position Y (%)"))
    self.spin_custom_y.set_value(50.0)
    self.spin_custom_y.set_visible(False)
    self.spin_custom_y.connect("notify::value", self._on_pos_changed)
    pos_group.add(self.spin_custom_y)

    self._update_pos_visibility()

    # ----------------------------------------------------
    # Document Protection & Security Group
    # ----------------------------------------------------
    security_group = Adw.PreferencesGroup.new()
    security_group.set_title(_("Document Security"))
    page.add(security_group)

    self.switch_security = Adw.SwitchRow.new()
    self.switch_security.set_title(_("Protect Document"))
    self.switch_security.set_active(self.settings.security_config.enabled)
    self.switch_security.connect("notify::active", self._on_security_param_changed)
    security_group.add(self.switch_security)

    self.combo_sec_mode = Adw.ComboRow.new()
    self.combo_sec_mode.set_title(_("Protection Level"))
    model_sec_mode = Gtk.StringList.new(
      [
        _("Standard (Vector)"),
        _("Maximum (Flattened)"),
      ]
    )
    self.combo_sec_mode.set_model(model_sec_mode)
    sec_idx = 1 if self.settings.security_config.mode == ProtectionMode.FLATTEN_AND_RESTRICT else 0
    self.combo_sec_mode.set_selected(sec_idx)
    self.combo_sec_mode.connect("notify::selected", self._on_security_param_changed)
    security_group.add(self.combo_sec_mode)

    # ----------------------------------------------------
    # Presets Group
    # ----------------------------------------------------
    preset_group = Adw.PreferencesGroup.new()
    preset_group.set_title(_("Watermark Presets"))
    page.add(preset_group)

    self.combo_presets = Adw.ComboRow.new()
    self.combo_presets.set_title(_("Load Preset"))
    self._refresh_presets_model()
    self.combo_presets.connect("notify::selected", self._on_preset_selected)
    preset_group.add(self.combo_presets)

    self.btn_save_preset = Adw.ButtonRow.new()
    self.btn_save_preset.set_start_icon_name("document-save-symbolic")
    self.btn_save_preset.set_title(_("Save Current Preset"))
    self.btn_save_preset.set_valign(Gtk.Align.CENTER)
    self.btn_save_preset.set_halign(Gtk.Align.FILL)
    self.btn_save_preset.add_css_class("flat")
    self.btn_save_preset.connect("activated", self._on_save_preset_clicked)

    preset_group.add(self.btn_save_preset)

  def set_pdf_file(self, file_path: str | None) -> None:
    """Update active PDF file."""
    self.loaded_pdf_file = file_path
    self.on_file_changed_cb(self.loaded_pdf_file)

  def _on_add_pdf_clicked(self, btn: Gtk.Button) -> None:
    dialog = Gtk.FileDialog.new()
    dialog.set_title(_("Select PDF Document"))
    filter_pdf = Gtk.FileFilter.new()
    filter_pdf.set_name("PDF File")
    filter_pdf.add_mime_type("application/pdf")

    filters = Gio.ListStore.new(Gtk.FileFilter)
    filters.append(filter_pdf)
    dialog.set_filters(filters)

    root = self.get_root()
    parent_win = root if isinstance(root, Gtk.Window) else None
    dialog.open(parent_win, None, self._on_pdf_selected)

  def _on_pdf_selected(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
    try:
      file_obj = dialog.open_finish(result)
      if file_obj:
        path = file_obj.get_path()
        if path:
          root = self.get_root()
          open_file_fn = getattr(root, "open_file", None)
          if callable(open_file_fn):
            open_file_fn(path)
          else:
            self.set_pdf_file(path)
    except Exception:
      pass

  def _setup_drop_zone_css(self) -> None:
    display = Gdk.Display.get_default()
    if not display:
      return
    css = """
    .image-drop-card {
      border-radius: 12px;
      padding: 20px 16px;
      background-color: #ffffff;
      transition: all 200ms ease-in-out;
      margin-top: 4px;
      margin-bottom: 12px;
    }
    .image-drop-card:hover {
      border-color: @accent_color;
      background-color: #ffffff;
    }
    .image-drop-card.drag-hover {
      border-color: @accent_color;
      border-style: solid;
      background-color: #ffffff;
    }
    """
    provider = Gtk.CssProvider.new()
    provider.load_from_string(css)
    Gtk.StyleContext.add_provider_for_display(
      display,
      provider,
      Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )

  def _update_image_row_ui(self) -> None:
    self._update_image_drop_zone_ui()

  def _update_image_drop_zone_ui(self) -> None:
    while child := self.image_drop_zone.get_first_child():
      self.image_drop_zone.remove(child)

    img_path = self.settings.image_config.image_path
    if img_path and Path(img_path).exists():
      content_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 12)
      content_box.set_valign(Gtk.Align.CENTER)
      content_box.set_margin_start(8)
      content_box.set_margin_end(8)
      content_box.set_margin_top(4)
      content_box.set_margin_bottom(4)

      # Image thumbnail preview
      thumb: Gtk.Widget
      try:
        texture = Gdk.Texture.new_from_filename(img_path)
        pic = Gtk.Picture.new_for_paintable(texture)
        pic.set_content_fit(Gtk.ContentFit.CONTAIN)
        pic.set_size_request(44, 44)
        thumb = pic
      except Exception:
        img = Gtk.Image.new_from_icon_name("image-x-generic-symbolic")
        img.set_pixel_size(36)
        img.add_css_class("accent")
        thumb = img
      content_box.append(thumb)

      # Info box
      info_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 2)
      info_box.set_hexpand(True)
      info_box.set_valign(Gtk.Align.CENTER)

      lbl_name = Gtk.Label.new(Path(img_path).name)
      lbl_name.set_halign(Gtk.Align.START)
      lbl_name.add_css_class("heading")
      lbl_name.set_ellipsize(Pango.EllipsizeMode.END)
      info_box.append(lbl_name)

      try:
        size_bytes = Path(img_path).stat().st_size
        size_str = format_file_size(size_bytes)
      except Exception:
        size_str = ""

      fmt = Path(img_path).suffix.upper().replace(".", "")
      sub_text = f"{fmt} • {size_str}" if size_str else f"{fmt}"
      lbl_sub = Gtk.Label.new(sub_text)
      lbl_sub.set_halign(Gtk.Align.START)
      lbl_sub.add_css_class("caption")
      lbl_sub.add_css_class("dim-label")
      info_box.append(lbl_sub)

      content_box.append(info_box)

      # Action buttons (Change... + Clear)
      action_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 4)
      action_box.set_valign(Gtk.Align.CENTER)

      btn_change = Gtk.Button.new_with_label(_("Change..."))
      btn_change.connect("clicked", self._on_browse_image_clicked)
      action_box.append(btn_change)

      btn_clear = Gtk.Button.new_from_icon_name("user-trash-symbolic")
      btn_clear.add_css_class("flat")
      btn_clear.add_css_class("circular")
      btn_clear.set_valign(Gtk.Align.CENTER)
      btn_clear.set_tooltip_text(_("Clear Image"))
      btn_clear.connect("clicked", self._on_clear_image_clicked)
      action_box.append(btn_clear)

      content_box.append(action_box)

      self.image_drop_zone.append(content_box)
    else:
      content_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 4)
      content_box.set_halign(Gtk.Align.CENTER)
      content_box.set_valign(Gtk.Align.CENTER)
      content_box.set_margin_top(8)
      content_box.set_margin_bottom(8)

      lbl_title = Gtk.Label.new(_("Drop image here"))
      lbl_title.add_css_class("heading")
      lbl_title.set_margin_bottom(2)
      content_box.append(lbl_title)

      lbl_sub = Gtk.Label.new(_("Supports PNG, SVG, or JPEG"))
      lbl_sub.add_css_class("caption")
      lbl_sub.add_css_class("dim-label")
      lbl_sub.set_margin_bottom(12)
      content_box.append(lbl_sub)

      btn_select_content = Adw.ButtonContent.new()
      btn_select_content.set_icon_name("folder-open-symbolic")
      btn_select_content.set_label(_("Select Image..."))

      btn_select = Gtk.Button.new()
      btn_select.set_child(btn_select_content)
      btn_select.add_css_class("suggested-action")
      btn_select.add_css_class("pill")
      btn_select.set_halign(Gtk.Align.CENTER)
      btn_select.connect("clicked", self._on_browse_image_clicked)
      content_box.append(btn_select)

      self.image_drop_zone.append(content_box)

  def _on_image_drop_notify(self, drop_target: Gtk.DropTarget, param: Any) -> None:
    if drop_target.get_current_drop():
      self.image_drop_zone.add_css_class("drag-hover")
    else:
      self.image_drop_zone.remove_css_class("drag-hover")

  def _on_image_file_dropped(self, target: Gtk.DropTarget, value: GObject.Value, x: float, y: float) -> bool:
    if isinstance(value, Gio.File):
      path = value.get_path()
      if path and is_valid_image_file(path):
        self.settings.image_config.image_path = path
        self._update_image_drop_zone_ui()
        self.history_mgr.add_recent_image(path)
        self._emit_settings_changed()
        return True
    return False

  def _on_clear_image_clicked(self, btn: Gtk.Button) -> None:
    self._clearing_image = True
    self.settings.image_config.image_path = ""
    self._update_image_drop_zone_ui()
    self._emit_settings_changed()

  def _on_browse_image_clicked(self, btn: Gtk.Button | None = None) -> None:
    dialog = Gtk.FileDialog.new()
    dialog.set_title(_("Select Watermark Image"))

    filter_img = Gtk.FileFilter.new()
    filter_img.set_name("Image Files (PNG, SVG, JPEG)")
    filter_img.add_mime_type("image/png")
    filter_img.add_mime_type("image/svg+xml")
    filter_img.add_mime_type("image/jpeg")

    filters = Gio.ListStore.new(Gtk.FileFilter)
    filters.append(filter_img)
    dialog.set_filters(filters)

    root = self.get_root()
    parent_win = root if isinstance(root, Gtk.Window) else None
    dialog.open(parent_win, None, self._on_image_selected)

  def _on_image_selected(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
    try:
      file_obj = dialog.open_finish(result)
      if file_obj:
        path = file_obj.get_path()
        if path and is_valid_image_file(path):
          self.settings.image_config.image_path = path
          self._update_image_drop_zone_ui()
          self.history_mgr.add_recent_image(path)
          self._emit_settings_changed()
    except Exception:
      pass

  def _on_mode_toggled(self, btn: Gtk.ToggleButton) -> None:
    if not btn.get_active():
      return
    if self.btn_mode_image.get_active():
      self.type_stack.set_visible_child_name("image")
      self.settings.type = WatermarkType.IMAGE
    else:
      self.type_stack.set_visible_child_name("text")
      self.settings.type = WatermarkType.TEXT
    self._emit_settings_changed()

  def _on_text_param_changed(self, *args: Any) -> None:
    tcfg = self.settings.text_config
    tcfg.text = self.entry_text.get_text()
    tcfg.font_size = self.spin_font_size.get_value()
    tcfg.bold = self.toggle_bold.get_active()
    tcfg.italic = self.toggle_italic.get_active()
    tcfg.underline = self.toggle_underline.get_active()
    tcfg.opacity = self.spin_text_opacity.get_value()
    tcfg.rotation = self.spin_text_rotation.get_value()

    rgba = self.color_btn.get_rgba()
    if rgba:
      tcfg.color = (rgba.red, rgba.green, rgba.blue)

    self._emit_settings_changed()

  def _on_font_selected(self, btn: Gtk.FontDialogButton, param: Any) -> None:
    desc = btn.get_font_desc()
    if desc:
      family = desc.get_family()
      if family:
        self.settings.text_config.font_family = family
      size = desc.get_size()
      if size > 0:
        size_pt = float(size) / (1.0 if desc.get_size_is_absolute() else float(Pango.SCALE))
        self.spin_font_size.set_value(size_pt)
        self.settings.text_config.font_size = size_pt
      self._emit_settings_changed()

  def _on_img_param_changed(self, *args: Any) -> None:
    icfg = self.settings.image_config
    icfg.scale = self.spin_img_scale.get_value()
    icfg.opacity = self.spin_img_opacity.get_value()
    icfg.rotation = self.spin_img_rotation.get_value()
    icfg.preserve_aspect = self.switch_aspect.get_active()
    self._emit_settings_changed()

  def _on_security_param_changed(self, *args: Any) -> None:
    scfg = self.settings.security_config
    scfg.enabled = self.switch_security.get_active()
    idx = self.combo_sec_mode.get_selected()
    scfg.mode = ProtectionMode.FLATTEN_AND_RESTRICT if idx == 1 else ProtectionMode.RESTRICT_EDITING
    self._emit_settings_changed()

  def _update_pos_visibility(self) -> None:
    idx = self.combo_pos.get_selected()
    positions = [
      WatermarkPosition.CENTER,
      WatermarkPosition.TOP_LEFT,
      WatermarkPosition.TOP_RIGHT,
      WatermarkPosition.BOTTOM_LEFT,
      WatermarkPosition.BOTTOM_RIGHT,
      WatermarkPosition.TILED,
      WatermarkPosition.CUSTOM,
    ]
    pos = positions[idx] if idx < len(positions) else WatermarkPosition.CENTER

    if pos == WatermarkPosition.CUSTOM:
      self.spin_margin_x.set_visible(False)
      self.spin_margin_y.set_visible(False)
      self.spin_custom_x.set_visible(True)
      self.spin_custom_y.set_visible(True)
    elif pos == WatermarkPosition.TILED:
      self.spin_margin_x.set_title(_("Pattern Spacing X"))
      self.spin_margin_y.set_title(_("Pattern Spacing Y"))
      self.spin_margin_x.set_visible(True)
      self.spin_margin_y.set_visible(True)
      self.spin_custom_x.set_visible(False)
      self.spin_custom_y.set_visible(False)
    else:
      self.spin_margin_x.set_title(_("Margin X"))
      self.spin_margin_y.set_title(_("Margin Y"))
      self.spin_margin_x.set_visible(True)
      self.spin_margin_y.set_visible(True)
      self.spin_custom_x.set_visible(False)
      self.spin_custom_y.set_visible(False)

  def _on_pos_changed(self, *args: Any) -> None:
    self._update_pos_visibility()
    idx = self.combo_pos.get_selected()
    positions = [
      WatermarkPosition.CENTER,
      WatermarkPosition.TOP_LEFT,
      WatermarkPosition.TOP_RIGHT,
      WatermarkPosition.BOTTOM_LEFT,
      WatermarkPosition.BOTTOM_RIGHT,
      WatermarkPosition.TILED,
      WatermarkPosition.CUSTOM,
    ]
    pos = positions[idx] if idx < len(positions) else WatermarkPosition.CENTER
    mx = self.spin_margin_x.get_value()
    my = self.spin_margin_y.get_value()
    cx = self.spin_custom_x.get_value()
    cy = self.spin_custom_y.get_value()

    self.settings.text_config.position = pos
    self.settings.text_config.margin_x = mx
    self.settings.text_config.margin_y = my
    self.settings.text_config.custom_x = cx
    self.settings.text_config.custom_y = cy

    self.settings.image_config.position = pos
    self.settings.image_config.margin_x = mx
    self.settings.image_config.margin_y = my
    self.settings.image_config.custom_x = cx
    self.settings.image_config.custom_y = cy

    self._emit_settings_changed()

  def refresh_presets(self) -> None:
    """Public interface to refresh the presets model."""
    self._refresh_presets_model()

  def _refresh_presets_model(self) -> None:
    names = list(self.history_mgr.presets.keys())
    model = Gtk.StringList.new(names)
    self.combo_presets.set_model(model)

  def _on_preset_selected(self, combo: Adw.ComboRow, param: Any) -> None:
    idx = combo.get_selected()
    names = list(self.history_mgr.presets.keys())
    if idx < len(names):
      preset_name = names[idx]
      preset_settings = self.history_mgr.get_preset(preset_name)
      if preset_settings:
        self.load_settings(preset_settings)

  def _on_save_preset_clicked(self, btn: Gtk.Button | None = None) -> None:
    """Open dialog to prompt user for custom preset name and save settings."""
    root = self.get_root()

    dialog = Adw.MessageDialog.new(
      root if isinstance(root, Gtk.Window) else None,
      _("Save Watermark Preset"),
      _("Enter a name for this custom watermark configuration:"),
    )
    entry = Gtk.Entry.new()
    entry.set_placeholder_text(_("Preset Name"))
    entry.set_activates_default(True)

    default_name = (
      self.settings.text_config.text
      if self.settings.type == WatermarkType.TEXT
      else (Path(self.settings.image_config.image_path).stem if self.settings.image_config.image_path else _("Custom Preset"))
    )
    if default_name:
      entry.set_text(default_name)

    dialog.set_extra_child(entry)
    dialog.add_response("cancel", _("Cancel"))
    dialog.add_response("save", _("Save"))
    dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
    dialog.set_default_response("save")
    dialog.set_close_response("cancel")

    def _on_response(dlg: Adw.MessageDialog, response: str) -> None:
      if response == "save":
        preset_name = entry.get_text().strip()
        if preset_name:
          self.save_custom_preset(preset_name)

    dialog.connect("response", _on_response)
    dialog.present()

  def save_custom_preset(self, preset_name: str) -> None:
    """Save current settings under preset_name and update UI."""
    self.history_mgr.save_preset(preset_name, self.settings)
    self._refresh_presets_model()
    names = list(self.history_mgr.presets.keys())
    if preset_name in names:
      self.combo_presets.set_selected(names.index(preset_name))

  def load_settings(self, settings: WatermarkSettings) -> None:
    """Apply watermark settings to UI widgets."""
    self.settings = settings
    if settings.type == WatermarkType.IMAGE:
      self.btn_mode_image.set_active(True)
    else:
      self.btn_mode_text.set_active(True)

    self.entry_text.set_text(settings.text_config.text)
    self.spin_font_size.set_value(settings.text_config.font_size)
    if settings.text_config.font_family:
      try:
        font_str = f"{settings.text_config.font_family} {int(settings.text_config.font_size)}"
        desc = Pango.FontDescription.from_string(font_str)
        self.font_btn.set_font_desc(desc)
      except Exception:
        pass
    self.toggle_bold.set_active(settings.text_config.bold)
    self.toggle_italic.set_active(settings.text_config.italic)
    self.toggle_underline.set_active(settings.text_config.underline)
    self.spin_text_opacity.set_value(settings.text_config.opacity)
    self.spin_text_rotation.set_value(settings.text_config.rotation)

    self._update_image_row_ui()
    self.spin_img_scale.set_value(settings.image_config.scale)
    self.spin_img_opacity.set_value(settings.image_config.opacity)
    self.spin_img_rotation.set_value(settings.image_config.rotation)

    self.spin_margin_x.set_value(settings.text_config.margin_x)
    self.spin_margin_y.set_value(settings.text_config.margin_y)
    self.spin_custom_x.set_value(settings.text_config.custom_x)
    self.spin_custom_y.set_value(settings.text_config.custom_y)

    pos_map = {
      WatermarkPosition.CENTER: 0,
      WatermarkPosition.TOP_LEFT: 1,
      WatermarkPosition.TOP_RIGHT: 2,
      WatermarkPosition.BOTTOM_LEFT: 3,
      WatermarkPosition.BOTTOM_RIGHT: 4,
      WatermarkPosition.TILED: 5,
      WatermarkPosition.CUSTOM: 6,
    }
    self.combo_pos.set_selected(pos_map.get(settings.text_config.position, 0))
    self._update_pos_visibility()

    if hasattr(settings, "security_config") and settings.security_config:
      self.switch_security.set_active(settings.security_config.enabled)
      sec_idx = 1 if settings.security_config.mode == ProtectionMode.FLATTEN_AND_RESTRICT else 0
      self.combo_sec_mode.set_selected(sec_idx)

    self._emit_settings_changed()

  def _emit_settings_changed(self) -> None:
    self.on_settings_changed_cb(self.settings)
