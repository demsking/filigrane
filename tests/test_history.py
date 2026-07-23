"""Unit tests for HistoryManager presets and recent files."""

from filigrane.core.history import HistoryManager


def test_history_manager_recent_files(tmp_path, monkeypatch):
  monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
  mgr = HistoryManager()

  mgr.add_recent_pdf("/path/doc1.pdf")
  mgr.add_recent_pdf("/path/doc2.pdf")

  assert mgr.recent_pdf_files[0] == "/path/doc2.pdf"
  assert mgr.recent_pdf_files[1] == "/path/doc1.pdf"

  # Reload from file
  mgr2 = HistoryManager()
  assert mgr2.recent_pdf_files[0] == "/path/doc2.pdf"


def test_history_presets(tmp_path, monkeypatch):
  monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
  mgr = HistoryManager()

  assert "Confidential" in mgr.presets
  preset = mgr.get_preset("Confidential")
  assert preset is not None
  assert preset.text_config.text == "CONFIDENTIAL"


def test_history_save_custom_preset(tmp_path, monkeypatch):
  monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
  mgr = HistoryManager()

  custom_settings = mgr.get_preset("Confidential")
  custom_settings.text_config.text = "TOP SECRET"
  mgr.save_preset("My Custom Preset", custom_settings)

  # Check in-memory preset
  saved = mgr.get_preset("My Custom Preset")
  assert saved is not None
  assert saved.text_config.text == "TOP SECRET"

  # Reload from disk
  mgr2 = HistoryManager()
  reloaded = mgr2.get_preset("My Custom Preset")
  assert reloaded is not None
  assert reloaded.text_config.text == "TOP SECRET"


def test_history_delete_custom_preset(tmp_path, monkeypatch):
  monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
  mgr = HistoryManager()

  # Default presets cannot be deleted
  assert mgr.is_custom_preset("Confidential") is False
  assert mgr.delete_preset("Confidential") is False
  assert "Confidential" in mgr.presets

  # Save a custom preset
  custom_settings = mgr.get_preset("Draft")
  mgr.save_preset("Custom Draft", custom_settings)
  assert mgr.is_custom_preset("Custom Draft") is True
  assert "Custom Draft" in mgr.presets

  # Delete custom preset
  assert mgr.delete_preset("Custom Draft") is True
  assert "Custom Draft" not in mgr.presets
  assert mgr.get_preset("Custom Draft") is None

  # Reload from disk and verify it remains deleted
  mgr2 = HistoryManager()
  assert "Custom Draft" not in mgr2.presets
