"""Unit tests for watermark data models and configurations."""

from filigrane.core.watermark import (
  ImageWatermarkConfig,
  TextWatermarkConfig,
  WatermarkPosition,
  WatermarkSettings,
  WatermarkType,
)


def test_text_watermark_defaults():
  cfg = TextWatermarkConfig()
  assert cfg.text == "CONFIDENTIAL"
  assert cfg.font_family == "Sans"
  assert cfg.font_size == 48.0
  assert cfg.bold is True
  assert cfg.opacity == 0.4
  assert cfg.rotation == -45.0
  assert cfg.position == WatermarkPosition.CENTER


def test_text_watermark_serialization():
  cfg = TextWatermarkConfig(
    text="DRAFT",
    font_size=36.0,
    position=WatermarkPosition.TOP_LEFT,
    color=(1.0, 0.0, 0.0),
  )
  d = cfg.to_dict()
  assert d["text"] == "DRAFT"
  assert d["position"] == "top_left"
  assert d["color"] == [1.0, 0.0, 0.0]

  deserialized = TextWatermarkConfig.from_dict(d)
  assert deserialized.text == "DRAFT"
  assert deserialized.position == WatermarkPosition.TOP_LEFT
  assert deserialized.color == (1.0, 0.0, 0.0)


def test_image_watermark_serialization():
  cfg = ImageWatermarkConfig(
    image_path="/tmp/logo.png",
    scale=2.0,
    opacity=0.8,
    position=WatermarkPosition.TILED,
  )
  d = cfg.to_dict()
  assert d["image_path"] == "/tmp/logo.png"
  assert d["scale"] == 2.0
  assert d["position"] == "tiled"

  deserialized = ImageWatermarkConfig.from_dict(d)
  assert deserialized.image_path == "/tmp/logo.png"
  assert deserialized.scale == 2.0
  assert deserialized.position == WatermarkPosition.TILED


def test_watermark_settings_toggle():
  settings = WatermarkSettings(type=WatermarkType.IMAGE)
  d = settings.to_dict()
  assert d["type"] == "image"

  loaded = WatermarkSettings.from_dict(d)
  assert loaded.type == WatermarkType.IMAGE


def test_security_config_serialization():
  from filigrane.core.watermark import ProtectionMode, SecurityConfig

  sec = SecurityConfig(
    enabled=True,
    mode=ProtectionMode.FLATTEN_AND_RESTRICT,
    allow_printing=False,
    owner_password="testpassword123",
  )
  d = sec.to_dict()
  assert d["enabled"] is True
  assert d["mode"] == "flatten_and_restrict"
  assert d["allow_printing"] is False
  assert d["owner_password"] == "testpassword123"

  loaded_sec = SecurityConfig.from_dict(d)
  assert loaded_sec.enabled is True
  assert loaded_sec.mode == ProtectionMode.FLATTEN_AND_RESTRICT
  assert loaded_sec.allow_printing is False
  assert loaded_sec.owner_password == "testpassword123"


def test_watermark_settings_with_security():
  from filigrane.core.watermark import ProtectionMode

  settings = WatermarkSettings()
  settings.security_config.mode = ProtectionMode.RESTRICT_EDITING

  d = settings.to_dict()
  assert "security_config" in d
  assert d["security_config"]["mode"] == "restrict_editing"

  restored = WatermarkSettings.from_dict(d)
  assert restored.security_config.mode == ProtectionMode.RESTRICT_EDITING
