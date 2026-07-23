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
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GLib", "2.0")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

from filigrane.core.preview import PreviewRenderer  # noqa: E402
from filigrane.core.watermark import WatermarkSettings  # noqa: E402
from filigrane.utils.i18n import _  # noqa: E402
from filigrane.utils.logger import get_logger  # noqa: E402

logger = get_logger()


class PreviewWidget(Gtk.Box):
  """Interactive preview canvas and navigation bar for PDF documents."""

  def __init__(self, **kwargs: Any) -> None:
    super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0, **kwargs)

    self.renderer = PreviewRenderer()
    self.current_page: int = 0
    self.zoom_level: float = 1.0  # 1.0 = 100%
    self.is_fit_mode: bool = True
    self.settings: WatermarkSettings = WatermarkSettings()
    self._update_timeout_id: int = 0

    # Main viewport / scrolled area
    self.scrolled_window = Gtk.ScrolledWindow.new()
    self.scrolled_window.set_hexpand(True)
    self.scrolled_window.set_vexpand(True)
    self.scrolled_window.set_overlay_scrolling(True)
    self.scrolled_window.connect("notify::allocated-width", self._on_viewport_resized)
    self.scrolled_window.connect("notify::allocated-height", self._on_viewport_resized)
    self.append(self.scrolled_window)

    # Container for picture
    self.picture_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
    self.picture_box.set_halign(Gtk.Align.FILL)
    self.picture_box.set_valign(Gtk.Align.FILL)
    self.picture_box.set_hexpand(True)
    self.picture_box.set_vexpand(True)
    self.picture_box.set_margin_top(16)
    self.picture_box.set_margin_bottom(16)
    self.picture_box.set_margin_start(16)
    self.picture_box.set_margin_end(16)
    self.scrolled_window.set_child(self.picture_box)

    # Overlay Stack for Preview Picture vs Error Placeholder
    self.preview_stack = Gtk.Stack.new()
    self.preview_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
    self.preview_stack.set_hexpand(True)
    self.preview_stack.set_vexpand(True)
    self.picture_box.append(self.preview_stack)

    # Gtk.Picture for high resolution page rendering
    self.picture = Gtk.Picture.new()
    self.picture.set_content_fit(Gtk.ContentFit.FILL)
    self.picture.set_can_shrink(True)
    self.picture.add_css_class("card")

    # AspectFrame to strictly lock PDF sheet ratio under zoom and window resize/maximize
    self.aspect_frame = Gtk.AspectFrame.new(0.5, 0.5, 0.7727, False)
    self.aspect_frame.set_hexpand(True)
    self.aspect_frame.set_vexpand(True)
    self.aspect_frame.set_child(self.picture)
    self.preview_stack.add_named(self.aspect_frame, "page")

    # Error status page fallback
    self.error_status = Adw.StatusPage.new()
    self.error_status.set_icon_name("dialog-warning-symbolic")
    self.error_status.set_title(_("Preview Unavailable"))
    self.error_status.set_description(_("Unable to render page preview. Please check document integrity or settings."))
    self.preview_stack.add_named(self.error_status, "error")

    self.preview_stack.set_visible_child_name("page")

    # Bottom Control Bar
    self.control_bar = Gtk.CenterBox.new()
    self.control_bar.add_css_class("toolbar")
    self.control_bar.set_margin_top(4)
    self.control_bar.set_margin_bottom(8)
    self.control_bar.set_margin_start(12)
    self.control_bar.set_margin_end(12)
    self.append(self.control_bar)

    # Navigation Controls (Left/Start)
    nav_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 4)
    self.control_bar.set_start_widget(nav_box)

    self.btn_prev = Gtk.Button.new_from_icon_name("go-previous-symbolic")
    self.btn_prev.set_tooltip_text(_("Previous Page"))
    self.btn_prev.connect("clicked", self._on_prev_page)
    nav_box.append(self.btn_prev)

    self.lbl_total_pages = Gtk.Label.new("1 / 1")
    self.lbl_total_pages.set_margin_start(6)
    self.lbl_total_pages.set_margin_end(6)
    nav_box.append(self.lbl_total_pages)

    self.btn_next = Gtk.Button.new_from_icon_name("go-next-symbolic")
    self.btn_next.set_tooltip_text(_("Next Page"))
    self.btn_next.connect("clicked", self._on_next_page)
    nav_box.append(self.btn_next)

    # Zoom Controls (Right)
    zoom_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 4)
    self.control_bar.set_end_widget(zoom_box)

    self.btn_zoom_out = Gtk.Button.new_from_icon_name("zoom-out-symbolic")
    self.btn_zoom_out.set_tooltip_text(_("Zoom Out"))
    self.btn_zoom_out.connect("clicked", self._on_zoom_out)
    zoom_box.append(self.btn_zoom_out)

    self.lbl_zoom = Gtk.Label.new("100%")
    self.lbl_zoom.set_margin_start(4)
    self.lbl_zoom.set_margin_end(4)
    zoom_box.append(self.lbl_zoom)

    self.btn_zoom_in = Gtk.Button.new_from_icon_name("zoom-in-symbolic")
    self.btn_zoom_in.set_tooltip_text(_("Zoom In"))
    self.btn_zoom_in.connect("clicked", self._on_zoom_in)
    zoom_box.append(self.btn_zoom_in)

    self.btn_zoom_fit = Gtk.Button.new_from_icon_name("zoom-fit-best-symbolic")
    self.btn_zoom_fit.set_tooltip_text(_("Fit Page"))
    self.btn_zoom_fit.connect("clicked", self._on_zoom_fit)
    zoom_box.append(self.btn_zoom_fit)

  def load_document(self, file_path: str) -> bool:
    """Load a PDF document into preview renderer."""
    success = self.renderer.set_document(file_path)
    if success:
      self.current_page = 0
      total = max(1, self.renderer.total_pages)
      self.lbl_total_pages.set_text(f"1 / {total}")
      self.is_fit_mode = True
      self._fit_to_viewport()
      self.queue_update_preview()
    else:
      self.clear_document()
    return success

  def clear_document(self) -> None:
    """Clear currently loaded PDF document from preview renderer."""
    self.renderer.close_document()
    self.current_page = 0
    self.lbl_total_pages.set_text("1 / 1")
    self.preview_stack.set_visible_child_name("error")

  def update_settings(self, new_settings: WatermarkSettings) -> None:
    """Update active watermark configuration and refresh preview."""
    self.settings = new_settings
    self.queue_update_preview()

  def queue_update_preview(self) -> None:
    """Debounce preview update to avoid UI lag during slider changes."""
    if self._update_timeout_id > 0:
      GLib.source_remove(self._update_timeout_id)
    self._update_timeout_id = GLib.timeout_add(50, self._do_update_preview)

  def do_size_allocate(self, width: int, height: int, baseline: int) -> None:
    Gtk.Box.do_size_allocate(self, width, height, baseline)
    if self.is_fit_mode and self.renderer.total_pages > 0:
      if abs(width - getattr(self, "_last_w", 0)) > 4 or abs(height - getattr(self, "_last_h", 0)) > 4:
        self._last_w = width
        self._last_h = height
        self._fit_to_viewport()
        self.queue_update_preview()

  def _fit_to_viewport(self) -> None:
    """Calculate and set zoom level to fit document comfortably in the scrolled viewport."""
    if self.renderer.total_pages == 0:
      return

    sw_w = max(100, self.scrolled_window.get_width() - 128)
    sw_h = max(100, self.scrolled_window.get_height() - 128)
    orig_w, orig_h = self.renderer.get_page_size(self.current_page)

    if orig_w > 0 and orig_h > 0 and sw_w > 50 and sw_h > 50:
      fit_w = sw_w / orig_w
      fit_h = sw_h / orig_h
      best_scale = min(fit_w, fit_h) * 0.96
      self.zoom_level = max(0.2, min(3.0, round(best_scale, 2)))

  def _on_viewport_resized(self, *args: Any) -> None:
    """Auto-adjust preview size when window/viewport is resized or maximized in fit mode."""
    if self.renderer.total_pages > 0:
      self._fit_to_viewport()
      self.queue_update_preview()

  def _do_update_preview(self) -> bool:
    self._update_timeout_id = 0
    if self.renderer.total_pages == 0:
      self.preview_stack.set_visible_child_name("error")
      return False

    try:
      orig_w, orig_h = self.renderer.get_page_size(self.current_page)
      if orig_w > 0 and orig_h > 0:
        ratio = float(orig_w) / float(orig_h)
        self.aspect_frame.set_ratio(ratio)

      if self.is_fit_mode:
        self.picture_box.set_halign(Gtk.Align.FILL)
        self.picture_box.set_valign(Gtk.Align.FILL)
        self.aspect_frame.set_size_request(-1, -1)
        self.picture.set_size_request(-1, -1)
        self._fit_to_viewport()
      else:
        self.picture_box.set_halign(Gtk.Align.CENTER)
        self.picture_box.set_valign(Gtk.Align.CENTER)
        disp_w = max(1, int(orig_w * self.zoom_level))
        disp_h = max(1, int(orig_h * self.zoom_level))
        self.aspect_frame.set_size_request(disp_w, disp_h)
        self.picture.set_size_request(disp_w, disp_h)

      texture = self.renderer.render_page_texture(self.current_page, self.settings, scale_factor=self.zoom_level)
      if texture:
        self.picture.set_paintable(texture)
        self.preview_stack.set_visible_child_name("page")
      else:
        self.preview_stack.set_visible_child_name("error")
    except Exception:
      self.preview_stack.set_visible_child_name("error")

    self._update_nav_buttons()
    return False

  def _update_nav_buttons(self) -> None:
    total = max(1, self.renderer.total_pages)
    self.btn_prev.set_sensitive(self.current_page > 0)
    self.btn_next.set_sensitive(self.current_page < total - 1)
    current = self.current_page + 1 if self.renderer.total_pages > 0 else 1
    self.lbl_total_pages.set_text(f"{current} / {total}")
    self.lbl_zoom.set_text(f"{int(self.zoom_level * 100)}%")

  def prev_page(self) -> None:
    if self.renderer.total_pages > 0 and self.current_page > 0:
      self.current_page -= 1
      self.queue_update_preview()

  def next_page(self) -> None:
    if self.renderer.total_pages > 0 and self.current_page < self.renderer.total_pages - 1:
      self.current_page += 1
      self.queue_update_preview()

  def first_page(self) -> None:
    if self.renderer.total_pages > 0 and self.current_page != 0:
      self.current_page = 0
      self.queue_update_preview()

  def last_page(self) -> None:
    if self.renderer.total_pages > 0 and self.current_page != self.renderer.total_pages - 1:
      self.current_page = self.renderer.total_pages - 1
      self.queue_update_preview()

  def zoom_in(self) -> None:
    if self.renderer.total_pages == 0:
      return
    self.is_fit_mode = False
    if self.zoom_level < 3.0:
      self.zoom_level = min(3.0, round(self.zoom_level + 0.25, 2))
      self.queue_update_preview()

  def zoom_out(self) -> None:
    if self.renderer.total_pages == 0:
      return
    self.is_fit_mode = False
    if self.zoom_level > 0.25:
      self.zoom_level = max(0.25, round(self.zoom_level - 0.25, 2))
      self.queue_update_preview()

  def zoom_fit(self) -> None:
    if self.renderer.total_pages == 0:
      return
    self.is_fit_mode = True
    self._fit_to_viewport()
    self.queue_update_preview()

  def _on_prev_page(self, btn: Gtk.Button | None = None) -> None:
    self.prev_page()

  def _on_next_page(self, btn: Gtk.Button | None = None) -> None:
    self.next_page()

  def _on_zoom_in(self, btn: Gtk.Button | None = None) -> None:
    self.zoom_in()

  def _on_zoom_out(self, btn: Gtk.Button | None = None) -> None:
    self.zoom_out()

  def _on_zoom_fit(self, btn: Gtk.Button | None = None) -> None:
    self.zoom_fit()
