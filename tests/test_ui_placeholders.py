"""Tests for UI placeholder views and empty states."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk  # noqa: E402

from filigrane.core.history import HistoryManager  # noqa: E402
from filigrane.ui.preview_widget import PreviewWidget  # noqa: E402
from filigrane.ui.sidebar import Sidebar  # noqa: E402


def test_sidebar_document_queue_and_image_placeholder() -> None:
  """Test sidebar active document updates and image row placeholder UI states."""
  app = Gtk.Application.new(None, Gio.ApplicationFlags.NON_UNIQUE)
  app.register()

  history_mgr = HistoryManager()
  sidebar = Sidebar(
    history_mgr=history_mgr,
    on_settings_changed=lambda s: None,
    on_file_changed=lambda f: None,
  )

  # Check empty active document initialization
  assert sidebar.loaded_pdf_file is None

  # Dynamically set active PDF file
  sidebar.set_pdf_file("/path/to/doc1.pdf")
  assert sidebar.loaded_pdf_file == "/path/to/doc1.pdf"

  sidebar.set_pdf_file(None)
  assert sidebar.loaded_pdf_file is None

  # Check image row UI initialization
  assert sidebar.img_file_row is not None
  assert sidebar.image_drop_zone is not None


def test_sidebar_image_drop_zone() -> None:
  """Test modern image drop zone initialization and UI state changes."""
  history_mgr = HistoryManager()
  sidebar = Sidebar(
    history_mgr=history_mgr,
    on_settings_changed=lambda s: None,
    on_file_changed=lambda f: None,
  )

  assert sidebar.image_drop_zone is not None
  assert sidebar.image_drop_zone.has_css_class("image-drop-card")

  # Initially empty image path
  assert sidebar.settings.image_config.image_path == ""
  child = sidebar.image_drop_zone.get_first_child()
  assert isinstance(child, Gtk.Box)

  # Simulate clearing image
  sidebar._on_clear_image_clicked(Gtk.Button.new())
  assert sidebar.settings.image_config.image_path == ""


def test_sidebar_position_controls_visibility() -> None:
  """Test that custom X/Y position inputs are hidden by default when preset is Center."""
  history_mgr = HistoryManager()
  sidebar = Sidebar(
    history_mgr=history_mgr,
    on_settings_changed=lambda s: None,
    on_file_changed=lambda f: None,
  )

  # Custom X and Y should be hidden by default (preset is Center)
  assert sidebar.spin_custom_x.get_visible() is False
  assert sidebar.spin_custom_y.get_visible() is False
  assert sidebar.spin_margin_x.get_visible() is True
  assert sidebar.spin_margin_y.get_visible() is True

  # Select Custom X/Y position preset (index 6)
  sidebar.combo_pos.set_selected(6)
  assert sidebar.spin_custom_x.get_visible() is True
  assert sidebar.spin_custom_y.get_visible() is True
  assert sidebar.spin_margin_x.get_visible() is False
  assert sidebar.spin_margin_y.get_visible() is False

  # Switch back to Center position preset (index 0)
  sidebar.combo_pos.set_selected(0)
  assert sidebar.spin_custom_x.get_visible() is False
  assert sidebar.spin_custom_y.get_visible() is False
  assert sidebar.spin_margin_x.get_visible() is True
  assert sidebar.spin_margin_y.get_visible() is True


def test_sidebar_save_custom_preset(tmp_path, monkeypatch) -> None:
  """Test saving a custom preset via sidebar."""
  monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
  history_mgr = HistoryManager()
  sidebar = Sidebar(
    history_mgr=history_mgr,
    on_settings_changed=lambda s: None,
    on_file_changed=lambda f: None,
  )

  sidebar.entry_text.set_text("INTERNAL REVIEW")
  sidebar.save_custom_preset("Internal Review")

  assert "Internal Review" in history_mgr.presets
  saved_preset = history_mgr.get_preset("Internal Review")
  assert saved_preset is not None
  assert saved_preset.text_config.text == "INTERNAL REVIEW"


def test_preview_widget_placeholders() -> None:
  """Test PreviewWidget placeholder stack initialization and left-aligned pagination bar."""
  widget = PreviewWidget()
  assert widget.preview_stack is not None
  assert widget.error_status is not None
  assert widget.control_bar.get_start_widget() is not None
  assert hasattr(widget, "btn_prev")
  assert hasattr(widget, "btn_next")
  assert hasattr(widget, "lbl_total_pages")
  assert not hasattr(widget, "page_spin")
  assert not hasattr(widget, "btn_first")
  assert not hasattr(widget, "btn_last")


def test_window_status_page_placeholder() -> None:
  """Test main window status page empty state and button constraint."""
  from filigrane.config import ConfigManager
  from filigrane.ui.window import FiligraneWindow

  app = Adw.Application.new("io.gitlab.demsking.filigrane.test", Gio.ApplicationFlags.NON_UNIQUE)
  app.register()

  config_mgr = ConfigManager()
  history_mgr = HistoryManager()
  win = FiligraneWindow(app=app, config_mgr=config_mgr, history_mgr=history_mgr)

  assert win.status_page is not None
  child_btn = win.status_page.get_child()
  assert isinstance(child_btn, Gtk.Button)
  assert child_btn.get_halign() == Gtk.Align.CENTER
  assert child_btn.get_valign() == Gtk.Align.CENTER
  assert win.doc_title_box is not None
  assert win.btn_close_doc is not None


def test_window_unsaved_changes_on_close() -> None:
  """Test window unsaved changes state tracking and close request intercept."""
  from filigrane.config import ConfigManager
  from filigrane.core.watermark import WatermarkSettings
  from filigrane.ui.window import FiligraneWindow

  app = Adw.Application.new("io.gitlab.demsking.filigrane.testclose", Gio.ApplicationFlags.NON_UNIQUE)
  app.register()

  config_mgr = ConfigManager()
  history_mgr = HistoryManager()
  win = FiligraneWindow(app=app, config_mgr=config_mgr, history_mgr=history_mgr)

  assert win._is_modified is False
  # Close request when not modified returns False
  assert win._on_close_request(win) is False

  # Simulate loaded file and settings change
  win.sidebar.loaded_pdf_file = "/path/to/test.pdf"
  win._on_settings_changed(WatermarkSettings())

  assert win._is_modified is True
  # Close request when modified returns True (intercepted for confirmation)
  assert win._on_close_request(win) is True

  # In TEXT mode, empty text means not modified
  empty_text_settings = WatermarkSettings()
  empty_text_settings.text_config.text = ""
  win._on_settings_changed(empty_text_settings)
  assert win._is_modified is False

  # In IMAGE mode, empty image_path means not modified
  from filigrane.core.watermark import WatermarkType

  image_settings = WatermarkSettings(type=WatermarkType.IMAGE)
  win._on_settings_changed(image_settings)
  assert win._is_modified is False

  # In IMAGE mode, image_path set means modified
  image_settings.image_config.image_path = "/path/to/logo.png"
  win._on_settings_changed(image_settings)
  assert win._is_modified is True

  # Export success resets modified state
  win._on_export_success("/path/to/out.pdf")
  assert win._is_modified is False
  assert win._on_close_request(win) is False


def test_preferences_dialog(tmp_path, monkeypatch) -> None:
  """Test PreferencesDialog initialization without removed export rows."""
  monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
  from filigrane.config import ConfigManager
  from filigrane.ui.preferences import PreferencesDialog

  Adw.init()
  cfg = ConfigManager()
  dialog = PreferencesDialog(config_manager=cfg)

  assert hasattr(dialog, "protect_switch")
  assert hasattr(dialog, "theme_combo")
  assert not hasattr(dialog, "output_dir_row")
  assert not hasattr(dialog, "overwrite_switch")
  assert not hasattr(dialog, "remember_dir_switch")
