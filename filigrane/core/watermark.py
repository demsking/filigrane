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
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any


class WatermarkType(Enum):
  """Supported watermark types."""

  TEXT = "text"
  IMAGE = "image"


class WatermarkPosition(Enum):
  """Watermark placement positioning options."""

  CENTER = "center"
  TOP_LEFT = "top_left"
  TOP_RIGHT = "top_right"
  BOTTOM_LEFT = "bottom_left"
  BOTTOM_RIGHT = "bottom_right"
  TILED = "tiled"
  CUSTOM = "custom"


@dataclass
class TextWatermarkConfig:
  """Configuration options for text watermarks."""

  text: str = "CONFIDENTIAL"
  font_family: str = "Sans"
  font_size: float = 48.0
  bold: bool = True
  italic: bool = False
  underline: bool = False
  color: tuple[float, float, float] = (0.8, 0.1, 0.1)  # RGB floats 0.0 - 1.0
  opacity: float = 0.4  # 0.0 to 1.0
  rotation: float = -45.0  # degrees
  position: WatermarkPosition = WatermarkPosition.CENTER
  margin_x: float = 20.0  # points
  margin_y: float = 20.0  # points
  custom_x: float = 50.0  # percentage (0 - 100%)
  custom_y: float = 50.0  # percentage (0 - 100%)
  align: str = "center"  # 'left', 'center', 'right'

  def to_dict(self) -> dict[str, Any]:
    """Serialize config to dictionary."""
    return {
      "text": self.text,
      "font_family": self.font_family,
      "font_size": self.font_size,
      "bold": self.bold,
      "italic": self.italic,
      "underline": self.underline,
      "color": list(self.color),
      "opacity": self.opacity,
      "rotation": self.rotation,
      "position": self.position.value,
      "margin_x": self.margin_x,
      "margin_y": self.margin_y,
      "custom_x": self.custom_x,
      "custom_y": self.custom_y,
      "align": self.align,
    }

  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> "TextWatermarkConfig":
    """Deserialize config from dictionary."""
    position = WatermarkPosition(data.get("position", WatermarkPosition.CENTER.value))
    color = tuple(data.get("color", [0.8, 0.1, 0.1]))
    if len(color) < 3:
      color = (0.8, 0.1, 0.1)
    return cls(
      text=data.get("text", "CONFIDENTIAL"),
      font_family=data.get("font_family", "Sans"),
      font_size=float(data.get("font_size", 48.0)),
      bold=bool(data.get("bold", True)),
      italic=bool(data.get("italic", False)),
      underline=bool(data.get("underline", False)),
      color=(float(color[0]), float(color[1]), float(color[2])),
      opacity=float(data.get("opacity", 0.4)),
      rotation=float(data.get("rotation", -45.0)),
      position=position,
      margin_x=float(data.get("margin_x", 20.0)),
      margin_y=float(data.get("margin_y", 20.0)),
      custom_x=float(data.get("custom_x", 50.0)),
      custom_y=float(data.get("custom_y", 50.0)),
      align=data.get("align", "center"),
    )


@dataclass
class ImageWatermarkConfig:
  """Configuration options for image watermarks."""

  image_path: str = ""
  scale: float = 1.0  # 0.1 to 5.0 (10% to 500%)
  opacity: float = 0.5  # 0.0 to 1.0
  rotation: float = 0.0  # degrees
  position: WatermarkPosition = WatermarkPosition.CENTER
  margin_x: float = 20.0
  margin_y: float = 20.0
  custom_x: float = 50.0  # percentage
  custom_y: float = 50.0  # percentage
  preserve_aspect: bool = True

  def to_dict(self) -> dict[str, Any]:
    """Serialize config to dictionary."""
    return {
      "image_path": self.image_path,
      "scale": self.scale,
      "opacity": self.opacity,
      "rotation": self.rotation,
      "position": self.position.value,
      "margin_x": self.margin_x,
      "margin_y": self.margin_y,
      "custom_x": self.custom_x,
      "custom_y": self.custom_y,
      "preserve_aspect": self.preserve_aspect,
    }

  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> "ImageWatermarkConfig":
    """Deserialize config from dictionary."""
    position = WatermarkPosition(data.get("position", WatermarkPosition.CENTER.value))
    return cls(
      image_path=data.get("image_path", ""),
      scale=float(data.get("scale", 1.0)),
      opacity=float(data.get("opacity", 0.5)),
      rotation=float(data.get("rotation", 0.0)),
      position=position,
      margin_x=float(data.get("margin_x", 20.0)),
      margin_y=float(data.get("margin_y", 20.0)),
      custom_x=float(data.get("custom_x", 50.0)),
      custom_y=float(data.get("custom_y", 50.0)),
      preserve_aspect=bool(data.get("preserve_aspect", True)),
    )


class ProtectionMode(Enum):
  """Document protection level against external editing."""

  RESTRICT_EDITING = "restrict_editing"
  FLATTEN_AND_RESTRICT = "flatten_and_restrict"
  DISABLED = "disabled"


@dataclass
class SecurityConfig:
  """Configuration options for document protection against editing."""

  enabled: bool = True
  mode: ProtectionMode = ProtectionMode.RESTRICT_EDITING
  allow_printing: bool = True
  allow_accessibility: bool = True
  owner_password: str = ""

  def to_dict(self) -> dict[str, Any]:
    """Serialize security config to dictionary."""
    return {
      "enabled": self.enabled,
      "mode": self.mode.value,
      "allow_printing": self.allow_printing,
      "allow_accessibility": self.allow_accessibility,
      "owner_password": self.owner_password,
    }

  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> "SecurityConfig":
    """Deserialize security config from dictionary."""
    mode_val = data.get("mode", ProtectionMode.RESTRICT_EDITING.value)
    try:
      mode = ProtectionMode(mode_val)
    except ValueError:
      mode = ProtectionMode.RESTRICT_EDITING

    return cls(
      enabled=bool(data.get("enabled", True)),
      mode=mode,
      allow_printing=bool(data.get("allow_printing", True)),
      allow_accessibility=bool(data.get("allow_accessibility", True)),
      owner_password=str(data.get("owner_password", "")),
    )


@dataclass
class WatermarkSettings:
  """Combined watermark settings container."""

  type: WatermarkType = WatermarkType.TEXT
  text_config: TextWatermarkConfig = field(default_factory=TextWatermarkConfig)
  image_config: ImageWatermarkConfig = field(default_factory=ImageWatermarkConfig)
  security_config: SecurityConfig = field(default_factory=SecurityConfig)

  def to_dict(self) -> dict[str, Any]:
    """Serialize settings to dictionary."""
    return {
      "type": self.type.value,
      "text_config": self.text_config.to_dict(),
      "image_config": self.image_config.to_dict(),
      "security_config": self.security_config.to_dict(),
    }

  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> "WatermarkSettings":
    """Deserialize settings from dictionary."""
    wm_type = WatermarkType(data.get("type", WatermarkType.TEXT.value))
    text_cfg = TextWatermarkConfig.from_dict(data.get("text_config", {}))
    img_cfg = ImageWatermarkConfig.from_dict(data.get("image_config", {}))
    sec_cfg = SecurityConfig.from_dict(data.get("security_config", {}))
    return cls(
      type=wm_type,
      text_config=text_cfg,
      image_config=img_cfg,
      security_config=sec_cfg,
    )
