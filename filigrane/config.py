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
import json
from pathlib import Path
from typing import Any

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gio, GLib  # noqa: E402

from filigrane import __app_id__  # noqa: E402
from filigrane.utils.logger import get_logger  # noqa: E402

logger = get_logger()


class ConfigManager:
  """Manages application settings via GSettings or JSON configuration fallback."""

  def __init__(self) -> None:
    self.app_id = __app_id__
    self.gsettings: Gio.Settings | None = None
    self._fallback_data: dict[str, Any] = {
      "default-output-dir": "",
      "overwrite-behavior": False,
      "remember-last-dir": True,
      "preview-quality": "medium",
      "theme-preference": "system",
      "language": "system",
      "log-level": "INFO",
      "window-width": 985,
      "window-height": 1000,
      "is-maximized": False,
      "protect-pdf": True,
      "protection-mode": "restrict_editing",
      "allow-printing": True,
      "custom-owner-password": "",
    }

    self._config_file = Path(GLib.get_user_config_dir()) / "filigrane" / "settings.json"
    self._init_gsettings()
    if self.gsettings is None:
      self._load_fallback_json()

  def _init_gsettings(self) -> None:
    """Initialize GSettings schema if installed on system."""
    try:
      source = Gio.SettingsSchemaSource.get_default()
      if source and source.lookup(self.app_id, True):
        self.gsettings = Gio.Settings.new(self.app_id)
        logger.debug("Successfully connected to GSettings schema")
    except Exception as e:
      logger.debug(f"GSettings schema not found, using JSON fallback: {e}")
      self.gsettings = None

  def _load_fallback_json(self) -> None:
    """Load settings from JSON fallback file."""
    if self._config_file.exists():
      try:
        with open(self._config_file, encoding="utf-8") as f:
          data = json.load(f)
          self._fallback_data.update(data)
      except Exception as e:
        logger.warning(f"Error loading JSON settings: {e}")

  def _save_fallback_json(self) -> None:
    """Save settings to JSON fallback file."""
    try:
      self._config_file.parent.mkdir(parents=True, exist_ok=True)
      with open(self._config_file, "w", encoding="utf-8") as f:
        json.dump(self._fallback_data, f, indent=2)
    except Exception as e:
      logger.warning(f"Error saving JSON settings: {e}")

  def get_string(self, key: str) -> str:
    """Get string configuration value."""
    if self.gsettings:
      try:
        return str(self.gsettings.get_string(key))
      except Exception:
        pass
    return str(self._fallback_data.get(key, ""))

  def set_string(self, key: str, value: str) -> None:
    """Set string configuration value."""
    if self.gsettings:
      try:
        self.gsettings.set_string(key, value)
        return
      except Exception:
        pass
    self._fallback_data[key] = value
    self._save_fallback_json()

  def get_boolean(self, key: str) -> bool:
    """Get boolean configuration value."""
    if self.gsettings:
      try:
        return bool(self.gsettings.get_boolean(key))
      except Exception:
        pass
    return bool(self._fallback_data.get(key, False))

  def set_boolean(self, key: str, value: bool) -> None:
    """Set boolean configuration value."""
    if self.gsettings:
      try:
        self.gsettings.set_boolean(key, value)
        return
      except Exception:
        pass
    self._fallback_data[key] = value
    self._save_fallback_json()

  def get_int(self, key: str) -> int:
    """Get integer configuration value."""
    if self.gsettings:
      try:
        return int(self.gsettings.get_int(key))
      except Exception:
        pass
    return int(self._fallback_data.get(key, 0))

  def set_int(self, key: str, value: int) -> None:
    """Set integer configuration value."""
    if self.gsettings:
      try:
        self.gsettings.set_int(key, value)
        return
      except Exception:
        pass
    self._fallback_data[key] = value
    self._save_fallback_json()
