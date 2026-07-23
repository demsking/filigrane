"""Unit tests for PreferencesDialog preset management."""

from filigrane.config import ConfigManager
from filigrane.core.history import HistoryManager
from filigrane.ui.preferences import PreferencesDialog


def test_preferences_dialog_preset_group(tmp_path, monkeypatch):
  monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
  config_mgr = ConfigManager()
  history_mgr = HistoryManager()
  history_mgr.history_file = tmp_path / "history.json"
  history_mgr.presets = {"Confidential": {}, "Draft": {}, "Sample": {}}

  cb_called = False

  def on_changed():
    nonlocal cb_called
    cb_called = True

  dialog = PreferencesDialog(
    config_manager=config_mgr,
    history_mgr=history_mgr,
    on_presets_changed=on_changed,
  )

  # Initially no custom presets, empty row rendered
  assert len(dialog._preset_rows) == 1
  assert dialog._preset_rows[0].get_title() == "No Custom Presets"

  # Save a custom preset
  custom_settings = history_mgr.get_preset("Draft")
  history_mgr.save_preset("Company Secret", custom_settings)

  # Refresh preferences preset group
  dialog._refresh_presets_group()
  assert len(dialog._preset_rows) == 1
  assert dialog._preset_rows[0].get_title() == "Company Secret"

  # Delete custom preset via history_mgr and call refresh
  history_mgr.delete_preset("Company Secret")
  dialog._refresh_presets_group()
  assert len(dialog._preset_rows) == 1
  assert dialog._preset_rows[0].get_title() == "No Custom Presets"
