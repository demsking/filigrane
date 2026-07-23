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
import os
import threading
from pathlib import Path

import gi

from filigrane import __app_id__

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gio", "2.0")
gi.require_version("Pango", "1.0")

from collections.abc import Callable  # noqa: E402
from typing import Any  # noqa: E402

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Pango  # noqa: E402

from filigrane.config import ConfigManager  # noqa: E402
from filigrane.core.history import HistoryManager  # noqa: E402
from filigrane.core.pdf_processor import PDFProcessor  # noqa: E402
from filigrane.core.watermark import WatermarkSettings, WatermarkType  # noqa: E402
from filigrane.ui.preview_widget import PreviewWidget  # noqa: E402
from filigrane.ui.progress_dialog import ProgressDialog  # noqa: E402
from filigrane.ui.shortcuts import show_shortcuts_dialog  # noqa: E402
from filigrane.ui.sidebar import Sidebar  # noqa: E402
from filigrane.utils.file_utils import (  # noqa: E402
  get_default_output_filename,
  is_valid_pdf_file,
  resolve_file_path,
)
from filigrane.utils.i18n import _  # noqa: E402
from filigrane.utils.logger import get_logger  # noqa: E402

logger = get_logger()


class FiligraneWindow(Adw.ApplicationWindow):
  """Main application window following GNOME Human Interface Guidelines (HIG)."""

  def __init__(
    self,
    app: Adw.Application,
    config_mgr: ConfigManager,
    history_mgr: HistoryManager,
    **kwargs: Any,
  ) -> None:
    super().__init__(application=app, **kwargs)

    self.config_mgr = config_mgr
    self.history_mgr = history_mgr
    self.export_cancel_event = threading.Event()
    self.progress_dialog: ProgressDialog | None = None
    self._is_modified = False
    self._doc_actions: list[Gio.SimpleAction] = []

    self.set_title(_("Filigrane"))
    self.set_icon_name(__app_id__)

    # Restore window geometry
    w = max(600, self.config_mgr.get_int("window-width"))
    h = max(700, self.config_mgr.get_int("window-height"))
    self.set_default_size(w, h)
    if self.config_mgr.get_boolean("is-maximized"):
      self.maximize()

    # Toast Overlay wrapper
    self.toast_overlay = Adw.ToastOverlay.new()
    self.set_content(self.toast_overlay)

    # Split View (Sidebar + Content)
    self.split_view = Adw.OverlaySplitView.new()
    self.split_view.set_collapsed(False)
    self.split_view.set_sidebar_width_fraction(0.35)
    self.split_view.set_min_sidebar_width(320)
    self.toast_overlay.set_child(self.split_view)

    # Sidebar Toolbar View & Header Bar
    self.sidebar_toolbar_view = Adw.ToolbarView.new()
    self.sidebar_header_bar = Adw.HeaderBar.new()
    self.sidebar_header_bar.set_show_start_title_buttons(False)
    self.sidebar_header_bar.set_show_end_title_buttons(False)
    self.sidebar_toolbar_view.add_top_bar(self.sidebar_header_bar)

    # Sidebar Component
    self.sidebar = Sidebar(
      history_mgr=self.history_mgr,
      config_mgr=self.config_mgr,
      on_settings_changed=self._on_settings_changed,
      on_file_changed=self._on_file_changed,
    )
    self.sidebar_toolbar_view.set_content(self.sidebar)
    self.split_view.set_sidebar(self.sidebar_toolbar_view)

    # Content Toolbar View & Header Bar
    self.content_toolbar_view = Adw.ToolbarView.new()
    self.header_bar = Adw.HeaderBar.new()

    # Centered app title widget
    self.window_title = Adw.WindowTitle.new(_("Filigrane"), "")
    self.header_bar.set_title_widget(self.window_title)

    # Document title box packed at left/start of header bar (label + tooltip + close icon button)
    self.doc_title_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 4)
    self.doc_title_box.set_valign(Gtk.Align.CENTER)
    self.doc_title_box.set_margin_start(12)
    self.doc_title_box.set_visible(False)

    self.doc_title_label = Gtk.Label.new("")
    self.doc_title_label.add_css_class("heading")
    self.doc_title_label.set_ellipsize(Pango.EllipsizeMode.END)
    self.doc_title_box.append(self.doc_title_label)

    self.btn_close_doc = Gtk.Button.new_from_icon_name("window-close-symbolic")
    self.btn_close_doc.add_css_class("flat")
    self.btn_close_doc.add_css_class("circular")
    self.btn_close_doc.set_valign(Gtk.Align.CENTER)
    self.btn_close_doc.set_tooltip_text(_("Close Document"))
    self.btn_close_doc.connect("clicked", self._on_close_doc_clicked)
    self.doc_title_box.append(self.btn_close_doc)

    self.header_bar.pack_start(self.doc_title_box)
    self.content_toolbar_view.add_top_bar(self.header_bar)

    # Open PDF Button
    self.btn_add_pdf = Gtk.Button.new_from_icon_name("document-open-symbolic")
    self.btn_add_pdf.set_tooltip_text(_("Open PDF File"))
    self.btn_add_pdf.connect("clicked", self._on_header_add_pdf)

    # Primary Menu
    self._setup_primary_menu()

    # Layout state helper
    self._sidebar_header_active = False
    self._update_header_and_sidebar_layout(False)

    # Export Button (placed before App Menu button)
    self._setup_export_btn_css()
    self.btn_export = Gtk.Button.new_with_label(_("Export"))
    self.btn_export.add_css_class("suggested-action")
    self.btn_export.add_css_class("rounded-export-btn")
    self.btn_export.set_tooltip_text(_("Apply watermark and export PDF"))
    self.btn_export.connect("clicked", self._on_export_clicked)
    self.btn_export.set_sensitive(False)
    self.btn_export.set_visible(False)
    self.header_bar.pack_end(self.btn_export)

    # Main Content Stack (Status Page vs Preview Widget)
    self.content_stack = Gtk.Stack.new()
    self.content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
    self.content_toolbar_view.set_content(self.content_stack)
    self.split_view.set_content(self.content_toolbar_view)

    # Empty State Status Page
    self.status_page = Adw.StatusPage.new()
    self.status_page.set_icon_name("document-open-symbolic")
    self.status_page.set_title(_("Add a Watermark to a PDF"))
    self.status_page.set_description(_("Drag &amp; drop a PDF file here"))

    btn_content = Adw.ButtonContent.new()
    btn_content.set_icon_name("document-open-symbolic")
    btn_content.set_label(_("Open PDF File"))

    btn_open_status = Gtk.Button.new()
    btn_open_status.set_child(btn_content)
    btn_open_status.add_css_class("pill")
    btn_open_status.add_css_class("suggested-action")
    btn_open_status.set_halign(Gtk.Align.CENTER)
    btn_open_status.set_valign(Gtk.Align.CENTER)
    btn_open_status.connect("clicked", self._on_header_add_pdf)
    self.status_page.set_child(btn_open_status)
    self.content_stack.add_named(self.status_page, "status")

    # Preview Widget Component
    self.preview_widget = PreviewWidget()
    self.content_stack.add_named(self.preview_widget, "preview")
    self.content_stack.set_visible_child_name("status")

    # Setup Window Keyboard Shortcuts & Actions
    self._setup_window_actions()

    # Setup Window Drag & Drop Target
    self._setup_drag_and_drop()

    # Connect window close event to save geometry
    self.connect("close-request", self._on_close_request)

  def _setup_window_actions(self) -> None:
    self._doc_actions = []

    def _on_show_shortcuts(action: Gio.SimpleAction, param: None) -> None:
      show_shortcuts_dialog(self)

    # File / Document Actions
    self._create_win_action("open", lambda a, p: self._on_header_add_pdf(self.btn_add_pdf), ["<Primary>o"])
    action_export = self._create_win_action(
      "export", lambda a, p: self._on_export_clicked(self.btn_export), ["<Primary>e", "<Primary>s"]
    )
    action_close = self._create_win_action(
      "close-doc", lambda a, p: self._on_close_doc_clicked(self.btn_close_doc), ["<Primary>w"]
    )
    action_open_with = self._create_win_action("open-with", self._on_open_pdf_with, ["<Primary><Shift>o"])
    action_print = self._create_win_action("print", self._on_print_pdf, ["<Primary>p"])
    self._create_win_action(
      "show-help-overlay",
      _on_show_shortcuts,
      ["<Primary>question", "<Primary>slash", "F1"],
    )

    # Navigation Actions
    action_prev = self._create_win_action(
      "prev-page", lambda a, p: self.preview_widget.prev_page(), ["Page_Up", "<Primary>Page_Up"]
    )
    action_next = self._create_win_action(
      "next-page", lambda a, p: self.preview_widget.next_page(), ["Page_Down", "<Primary>Page_Down"]
    )
    action_first = self._create_win_action("first-page", lambda a, p: self.preview_widget.first_page(), ["Home"])
    action_last = self._create_win_action("last-page", lambda a, p: self.preview_widget.last_page(), ["End"])

    # Zoom Actions
    action_zoom_in = self._create_win_action(
      "zoom-in", lambda a, p: self.preview_widget.zoom_in(), ["<Primary>plus", "<Primary>equal", "<Primary>KP_Add"]
    )
    action_zoom_out = self._create_win_action(
      "zoom-out", lambda a, p: self.preview_widget.zoom_out(), ["<Primary>minus", "<Primary>KP_Subtract"]
    )
    action_zoom_fit = self._create_win_action("zoom-fit", lambda a, p: self.preview_widget.zoom_fit(), ["<Primary>0"])

    self._doc_actions = [
      action_export,
      action_close,
      action_open_with,
      action_print,
      action_prev,
      action_next,
      action_first,
      action_last,
      action_zoom_in,
      action_zoom_out,
      action_zoom_fit,
    ]
    self._set_doc_actions_enabled(False)

  def _create_win_action(self, name: str, callback: Callable[..., None], accels: list[str] | None = None) -> Gio.SimpleAction:
    action = Gio.SimpleAction.new(name, None)
    action.connect("activate", callback)
    self.add_action(action)
    app = self.get_application()
    if app and accels:
      app.set_accels_for_action(f"win.{name}", accels)
    return action

  def _set_doc_actions_enabled(self, enabled: bool) -> None:
    for action in self._doc_actions:
      action.set_enabled(enabled)

  def _setup_primary_menu(self) -> None:
    menu = Gio.Menu.new()

    sec_file = Gio.Menu.new()
    sec_file.append(_("New Window"), "app.new-window")
    sec_file.append(_("Open PDF"), "win.open")
    menu.append_section(None, sec_file)

    sec_tools = Gio.Menu.new()
    sec_tools.append(_("Open PDF With…"), "win.open-with")
    sec_tools.append(_("Print PDF…"), "win.print")
    menu.append_section(None, sec_tools)

    sec_app = Gio.Menu.new()
    sec_app.append(_("Preferences"), "app.preferences")
    sec_app.append(_("Keyboard Shortcuts"), "win.show-help-overlay")
    sec_app.append(_("About Filigrane"), "app.about")
    menu.append_section(None, sec_app)

    self.menu_btn = Gtk.MenuButton.new()
    self.menu_btn.set_icon_name("open-menu-symbolic")
    self.menu_btn.set_menu_model(menu)
    self.menu_btn.set_primary(True)
    self.menu_btn.set_tooltip_text(_("Main Menu"))

  def _update_header_and_sidebar_layout(self, has_files: bool) -> None:
    self.split_view.set_show_sidebar(has_files)
    self.doc_title_box.set_visible(has_files)
    self.window_title.set_visible(not has_files)
    self.header_bar.set_title_widget(self.window_title)
    self._set_doc_actions_enabled(has_files)

    if has_files:
      if not self._sidebar_header_active:
        if self.btn_add_pdf.get_parent():
          self.btn_add_pdf.unparent()
        self.sidebar_header_bar.pack_start(self.btn_add_pdf)

        if self.menu_btn.get_parent():
          self.menu_btn.unparent()
        self.sidebar_header_bar.pack_end(self.menu_btn)

        self._sidebar_header_active = True
      self.btn_add_pdf.set_visible(True)
    else:
      self.btn_add_pdf.set_visible(False)
      if self.btn_add_pdf.get_parent():
        self.btn_add_pdf.unparent()

      if self.menu_btn.get_parent():
        self.menu_btn.unparent()
      self.header_bar.pack_start(self.menu_btn)

      self._sidebar_header_active = False

  def _setup_drag_and_drop(self) -> None:
    drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
    drop_target.connect("drop", self._on_file_dropped)
    self.add_controller(drop_target)

  def _on_file_dropped(self, target: Gtk.DropTarget, value: GObject.Value, x: float, y: float) -> bool:
    if isinstance(value, Gio.File):
      path = value.get_path()
      if path:
        self.open_file(path)
        return True
    return False

  def open_file(self, path: str) -> None:
    """Open and load a single PDF path from command line, file manager, or drag & drop."""
    abs_p = resolve_file_path(path)
    if not abs_p or not is_valid_pdf_file(abs_p):
      self.show_toast(_("No valid PDF file provided"))
      return

    if self._is_modified and self.sidebar.loaded_pdf_file:
      alert = Adw.AlertDialog.new(
        _("Open New Document?"),
        _("You have unsaved watermark settings changes. Opening a new document will discard these changes."),
      )
      alert.add_response("cancel", _("Cancel"))
      alert.add_response("open", _("Open Document"))
      alert.set_response_appearance("open", Adw.ResponseAppearance.DESTRUCTIVE)
      alert.set_default_response("cancel")
      alert.set_close_response("cancel")

      def _on_response(dialog: Adw.AlertDialog, response: str) -> None:
        if response == "open":
          self._is_modified = False
          self.sidebar.set_pdf_file(abs_p)
          self.history_mgr.add_recent_pdf(abs_p)

      alert.connect("response", _on_response)
      alert.present(self)
      return

    self.sidebar.set_pdf_file(abs_p)
    self.history_mgr.add_recent_pdf(abs_p)

  def _on_file_changed(self, file_path: str | None) -> None:
    self._is_modified = False
    if file_path:
      success = self.preview_widget.load_document(file_path)
      if success:
        file_url = GLib.filename_to_uri(file_path)
        self.content_stack.set_visible_child_name("preview")
        self.btn_export.set_sensitive(True)
        self.btn_export.set_visible(True)
        self.doc_title_label.set_text(Path(file_path).name)
        self.doc_title_label.set_tooltip_text(file_url)
        self.doc_title_box.set_tooltip_text(file_url)
        self._update_header_and_sidebar_layout(True)
      else:
        self.content_stack.set_visible_child_name("status")
        self.btn_export.set_sensitive(False)
        self.btn_export.set_visible(False)
        self.doc_title_label.set_text("")
        self.doc_title_label.set_tooltip_text("")
        self.doc_title_box.set_tooltip_text("")
        self._update_header_and_sidebar_layout(False)
    else:
      self.preview_widget.clear_document()
      self.content_stack.set_visible_child_name("status")
      self.btn_export.set_sensitive(False)
      self.btn_export.set_visible(False)
      self.doc_title_label.set_text("")
      self.doc_title_label.set_tooltip_text("")
      self.doc_title_box.set_tooltip_text("")
      self._update_header_and_sidebar_layout(False)

  def _on_settings_changed(self, settings: WatermarkSettings) -> None:
    self.preview_widget.update_settings(settings)
    if self.sidebar.loaded_pdf_file:
      if settings.type == WatermarkType.IMAGE:
        self._is_modified = bool(settings.image_config.image_path)
      else:
        self._is_modified = bool(settings.text_config.text and settings.text_config.text.strip())

  def _on_close_doc_clicked(self, btn: Gtk.Button | None = None) -> None:
    if self._is_modified and self.sidebar.loaded_pdf_file:
      alert = Adw.AlertDialog.new(
        _("Close Document?"),
        _("You have unsaved watermark settings changes. Are you sure you want to close this document?"),
      )
      alert.add_response("cancel", _("Cancel"))
      alert.add_response("close", _("Close Document"))
      alert.set_response_appearance("close", Adw.ResponseAppearance.DESTRUCTIVE)
      alert.set_default_response("cancel")
      alert.set_close_response("cancel")

      def _on_response(dialog: Adw.AlertDialog, response: str) -> None:
        if response == "close":
          self._is_modified = False
          self.sidebar.set_pdf_file(None)

      alert.connect("response", _on_response)
      alert.present(self)
    else:
      self._is_modified = False
      self.sidebar.set_pdf_file(None)

  def _on_header_add_pdf(self, btn: Gtk.Button) -> None:
    self.sidebar._on_add_pdf_clicked(btn)

  def _on_open_pdf_with(self, action: Gio.SimpleAction | None = None, param: Any = None) -> None:
    file_path = self.sidebar.loaded_pdf_file
    if not file_path or not os.path.exists(file_path):
      self.show_toast(_("No PDF file open"))
      return

    gfile = Gio.File.new_for_path(file_path)
    try:
      launcher = Gtk.FileLauncher.new(gfile)
      launcher.set_always_ask(True)
      launcher.launch(self, None, self._on_open_with_finish)
    except Exception as e:
      logger.warning(f"FileLauncher failed, falling back to launch_default_for_uri: {e}")
      try:
        Gio.AppInfo.launch_default_for_uri(GLib.filename_to_uri(file_path), None)
      except Exception as err:
        logger.error(f"Failed to open PDF with external app: {err}")
        self.show_toast(_("Failed to open PDF with external app"))

  def _on_open_with_finish(self, source_object: Gtk.FileLauncher, result: Gio.AsyncResult) -> None:
    try:
      source_object.launch_finish(result)
    except Exception as e:
      logger.debug(f"Open PDF With callback: {e}")

  def _on_print_pdf(self, action: Gio.SimpleAction | None = None, param: Any = None) -> None:
    file_path = self.sidebar.loaded_pdf_file
    poppler_doc = self.preview_widget.renderer._poppler_doc
    if not file_path or not poppler_doc:
      self.show_toast(_("No PDF file open"))
      return

    print_op = Gtk.PrintOperation.new()
    settings: WatermarkSettings = self.sidebar.settings

    def _on_begin_print(operation: Gtk.PrintOperation, context: Gtk.PrintContext) -> None:
      operation.set_n_pages(poppler_doc.get_n_pages())

    def _on_draw_page(operation: Gtk.PrintOperation, context: Gtk.PrintContext, page_nr: int) -> None:
      cr = context.get_cairo_context()
      poppler_page = poppler_doc.get_page(page_nr)
      w, h = poppler_page.get_size()

      page_w = context.get_width()
      page_h = context.get_height()
      scale_x = page_w / w if w > 0 else 1.0
      scale_y = page_h / h if h > 0 else 1.0
      scale = min(scale_x, scale_y)

      cr.save()
      cr.scale(scale, scale)
      poppler_page.render(cr)
      self.preview_widget.renderer._render_watermark_overlay(cr, w, h, settings)
      cr.restore()

    print_op.connect("begin-print", _on_begin_print)
    print_op.connect("draw-page", _on_draw_page)
    try:
      print_op.run(Gtk.PrintOperationAction.PRINT_DIALOG, self)
    except Exception as e:
      logger.error(f"Failed to print PDF: {e}")
      self.show_toast(_("Failed to print PDF"))

  def _on_export_clicked(self, btn: Gtk.Button) -> None:
    input_file = self.sidebar.loaded_pdf_file
    if not input_file:
      return

    dialog = Gtk.FileDialog.new()
    dialog.set_title(_("Export Watermarked PDF"))

    default_dir = self.config_mgr.get_string("default-output-dir")
    if default_dir and os.path.exists(default_dir):
      dialog.set_initial_folder(Gio.File.new_for_path(default_dir))

    default_name = get_default_output_filename(input_file)
    dialog.set_initial_name(default_name)

    filter_pdf = Gtk.FileFilter.new()
    filter_pdf.set_name("PDF File")
    filter_pdf.add_mime_type("application/pdf")
    filters = Gio.ListStore.new(Gtk.FileFilter)
    filters.append(filter_pdf)
    dialog.set_filters(filters)

    dialog.save(self, None, self._on_export_save_location_selected)

  def _on_export_save_location_selected(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
    try:
      file_target = dialog.save_finish(result)
      if file_target:
        out_path = file_target.get_path()
        if out_path:
          self._start_export(out_path)
    except Exception:
      pass

  def _start_export(self, output_path: str) -> None:
    input_file = self.sidebar.loaded_pdf_file
    if not input_file:
      return

    self.export_cancel_event.clear()
    self.progress_dialog = ProgressDialog(self, on_cancel=self._cancel_export)
    self.progress_dialog.show()

    settings = self.sidebar.settings

    def _worker() -> None:
      try:
        PDFProcessor.apply_watermark(
          input_path=input_file,
          output_path=output_path,
          settings=settings,
          progress_callback=self._update_export_progress,
          cancel_event=self.export_cancel_event,
        )
        GLib.idle_add(self._on_export_success, output_path)
      except Exception as e:
        logger.error(f"Export error: {e}")
        GLib.idle_add(self._on_export_failed, str(e))

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

  def _update_export_progress(self, fraction: float, message: str) -> None:
    if self.progress_dialog:
      self.progress_dialog.update(fraction, message)

  def _cancel_export(self) -> None:
    self.export_cancel_event.set()

  def _on_export_success(self, output_path: str) -> bool:
    if self.progress_dialog:
      self.progress_dialog.close()
      self.progress_dialog = None
    self._is_modified = False
    self.show_toast(_("Export completed successfully!"))
    return False

  def _on_export_failed(self, error_message: str) -> bool:
    if self.progress_dialog:
      self.progress_dialog.close()
      self.progress_dialog = None

    if "cancelled" in error_message.lower():
      self.show_toast(_("Export cancelled"))
    else:
      alert = Adw.AlertDialog.new(_("Export Failed"), error_message)
      alert.add_response("ok", _("OK"))
      alert.present(self)
    return False

  def show_toast(self, message: str) -> None:
    """Display Libadwaita toast message overlay."""
    toast = Adw.Toast.new(message)
    toast.set_timeout(3)
    self.toast_overlay.add_toast(toast)

  def _save_window_state(self) -> None:
    w, h = self.get_default_size()
    self.config_mgr.set_int("window-width", w)
    self.config_mgr.set_int("window-height", h)
    self.config_mgr.set_boolean("is-maximized", self.is_maximized())
    self.history_mgr.last_settings = self.sidebar.settings
    self.history_mgr.save()

  def _on_close_request(self, window: Gtk.Window) -> bool:
    if self._is_modified and self.sidebar.loaded_pdf_file:
      alert = Adw.AlertDialog.new(
        _("Quit Filigrane?"),
        _("You have unsaved watermark settings changes. Are you sure you want to quit?"),
      )
      alert.add_response("cancel", _("Cancel"))
      alert.add_response("quit", _("Quit Without Saving"))
      alert.set_response_appearance("quit", Adw.ResponseAppearance.DESTRUCTIVE)
      alert.set_default_response("cancel")
      alert.set_close_response("cancel")

      def _on_response(dialog: Adw.AlertDialog, response: str) -> None:
        if response == "quit":
          self._is_modified = False
          self.close()

      alert.connect("response", _on_response)
      alert.present(self)
      return True

    self._save_window_state()
    return False

  def _setup_export_btn_css(self) -> None:
    display = Gdk.Display.get_default()
    if not display:
      return
    css = """
    .rounded-export-btn {
      border-radius: 20px;
    }
    """
    provider = Gtk.CssProvider.new()
    provider.load_from_string(css)
    Gtk.StyleContext.add_provider_for_display(
      display,
      provider,
      Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
