"""Unit tests for ConfigManager fallback configuration."""

from filigrane.config import ConfigManager


def test_config_manager_defaults(tmp_path, monkeypatch):
  monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
  cfg = ConfigManager()

  assert cfg.get_string("theme-preference") in ["system", "light", "dark"]
  assert cfg.get_boolean("overwrite-behavior") is False

  cfg.set_string("default-output-dir", "/tmp/watermarked")
  assert cfg.get_string("default-output-dir") == "/tmp/watermarked"

  # Verify persistence
  cfg2 = ConfigManager()
  assert cfg2.get_string("default-output-dir") == "/tmp/watermarked"
