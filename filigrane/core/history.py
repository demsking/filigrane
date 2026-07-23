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

gi.require_version("GLib", "2.0")
from gi.repository import GLib  # noqa: E402

from filigrane.core.watermark import WatermarkSettings  # noqa: E402
from filigrane.utils.logger import get_logger  # noqa: E402

logger = get_logger()

DEFAULT_PRESETS: dict[str, dict[str, Any]] = {
  "Confidential": {
    "type": "text",
    "text_config": {
      "text": "CONFIDENTIAL",
      "font_family": "Sans",
      "font_size": 48.0,
      "bold": True,
      "italic": False,
      "underline": False,
      "color": [0.8, 0.1, 0.1],
      "opacity": 0.4,
      "rotation": -45.0,
      "position": "center",
      "margin_x": 20.0,
      "margin_y": 20.0,
      "custom_x": 50.0,
      "custom_y": 50.0,
      "align": "center",
    },
  },
  "Draft": {
    "type": "text",
    "text_config": {
      "text": "DRAFT",
      "font_family": "Sans",
      "font_size": 56.0,
      "bold": True,
      "italic": True,
      "underline": False,
      "color": [0.3, 0.3, 0.8],
      "opacity": 0.35,
      "rotation": -30.0,
      "position": "center",
      "margin_x": 20.0,
      "margin_y": 20.0,
      "custom_x": 50.0,
      "custom_y": 50.0,
      "align": "center",
    },
  },
  "Sample": {
    "type": "text",
    "text_config": {
      "text": "SAMPLE ONLY",
      "font_family": "Serif",
      "font_size": 42.0,
      "bold": True,
      "italic": False,
      "underline": False,
      "color": [0.2, 0.6, 0.2],
      "opacity": 0.4,
      "rotation": -45.0,
      "position": "tiled",
      "margin_x": 20.0,
      "margin_y": 20.0,
      "custom_x": 50.0,
      "custom_y": 50.0,
      "align": "center",
    },
  },
}


class HistoryManager:
  """Manages application recent settings, presets, and recent files."""

  def __init__(self) -> None:
    config_dir = Path(GLib.get_user_config_dir()) / "filigrane"
    config_dir.mkdir(parents=True, exist_ok=True)
    self.history_file = config_dir / "history.json"

    self.recent_pdf_files: list[str] = []
    self.recent_image_files: list[str] = []
    self.last_settings: WatermarkSettings = WatermarkSettings()
    self.presets: dict[str, dict[str, Any]] = dict(DEFAULT_PRESETS)

    self.load()

  def load(self) -> None:
    """Load history data from file."""
    if not self.history_file.exists():
      return

    try:
      with open(self.history_file, encoding="utf-8") as f:
        data = json.load(f)
        self.recent_pdf_files = data.get("recent_pdf_files", [])[:10]
        self.recent_image_files = data.get("recent_image_files", [])[:10]

        if "last_settings" in data:
          self.last_settings = WatermarkSettings.from_dict(data["last_settings"])

        if "presets" in data and isinstance(data["presets"], dict):
          self.presets.update(data["presets"])
    except Exception as e:
      logger.warning(f"Failed loading history file: {e}")

  def save(self) -> None:
    """Save history data to file."""
    try:
      data = {
        "recent_pdf_files": self.recent_pdf_files[:10],
        "recent_image_files": self.recent_image_files[:10],
        "last_settings": self.last_settings.to_dict(),
        "presets": self.presets,
      }
      with open(self.history_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    except Exception as e:
      logger.warning(f"Failed saving history file: {e}")

  def add_recent_pdf(self, path: str) -> None:
    """Add PDF path to recent files list."""
    if not path:
      return
    if path in self.recent_pdf_files:
      self.recent_pdf_files.remove(path)
    self.recent_pdf_files.insert(0, path)
    self.recent_pdf_files = self.recent_pdf_files[:10]
    self.save()

  def add_recent_image(self, path: str) -> None:
    """Add image path to recent watermark images list."""
    if not path:
      return
    if path in self.recent_image_files:
      self.recent_image_files.remove(path)
    self.recent_image_files.insert(0, path)
    self.recent_image_files = self.recent_image_files[:10]
    self.save()

  def save_preset(self, name: str, settings: WatermarkSettings) -> None:
    """Save a custom user watermark preset."""
    self.presets[name] = settings.to_dict()
    self.save()

  def get_preset(self, name: str) -> WatermarkSettings | None:
    """Retrieve a watermark preset by name."""
    if name in self.presets:
      return WatermarkSettings.from_dict(self.presets[name])
    return None

  def is_custom_preset(self, name: str) -> bool:
    """Check if a preset is a custom user preset."""
    return name in self.presets and name not in DEFAULT_PRESETS

  def delete_preset(self, name: str) -> bool:
    """Delete a custom user watermark preset. Return True if deleted."""
    if self.is_custom_preset(name):
      del self.presets[name]
      self.save()
      return True
    return False
