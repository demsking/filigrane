"""Unit tests for PDFProcessor engine and watermark generation."""

import os

import pypdf
import pytest

from filigrane.core.pdf_processor import PDFProcessingError, PDFProcessor
from filigrane.core.watermark import (
  TextWatermarkConfig,
  WatermarkPosition,
  WatermarkSettings,
  WatermarkType,
)


@pytest.fixture
def sample_pdf_file(tmp_path):
  pdf_path = tmp_path / "sample.pdf"
  writer = pypdf.PdfWriter()
  writer.add_blank_page(width=612, height=792)
  with open(pdf_path, "wb") as f:
    writer.write(f)
  return str(pdf_path)


@pytest.fixture
def second_pdf_file(tmp_path):
  pdf_path = tmp_path / "second.pdf"
  writer = pypdf.PdfWriter()
  writer.add_blank_page(width=612, height=792)
  writer.add_blank_page(width=612, height=792)
  with open(pdf_path, "wb") as f:
    writer.write(f)
  return str(pdf_path)


def test_text_watermark_page_creation():
  config = TextWatermarkConfig(text="TEST WATERMARK", font_size=32.0)
  page = PDFProcessor.create_text_watermark_page(612.0, 792.0, config)
  assert page is not None
  assert page.mediabox.width == 612.0
  assert page.mediabox.height == 792.0


def test_tiled_whole_page_watermark_creation():
  config = TextWatermarkConfig(
    text="CONFIDENTIAL",
    position=WatermarkPosition.TILED,
    margin_x=30.0,
    margin_y=30.0,
  )
  page = PDFProcessor.create_text_watermark_page(612.0, 792.0, config)
  assert page is not None
  assert page.mediabox.width == 612.0
  assert page.mediabox.height == 792.0


def test_single_pdf_watermark_export(sample_pdf_file, tmp_path):
  output_path = str(tmp_path / "output.pdf")
  settings = WatermarkSettings(
    type=WatermarkType.TEXT,
    text_config=TextWatermarkConfig(text="TEST ONLY", position=WatermarkPosition.CENTER),
  )

  out = PDFProcessor.apply_watermark(
    input_path=sample_pdf_file,
    output_path=output_path,
    settings=settings,
  )

  assert os.path.exists(out)
  reader = pypdf.PdfReader(out)
  assert len(reader.pages) == 1


def test_single_pdf_in_place_watermark_export(sample_pdf_file):
  settings = WatermarkSettings(
    type=WatermarkType.TEXT,
    text_config=TextWatermarkConfig(text="OVERWRITE", position=WatermarkPosition.CENTER),
  )

  out = PDFProcessor.apply_watermark(
    input_path=sample_pdf_file,
    output_path=sample_pdf_file,
    settings=settings,
  )

  assert out == sample_pdf_file
  assert os.path.exists(out)
  reader = pypdf.PdfReader(out)
  assert len(reader.pages) == 1


def test_invalid_pdf_path_raises():
  settings = WatermarkSettings()
  with pytest.raises(PDFProcessingError):
    PDFProcessor.apply_watermark(
      input_path="/invalid/non_existent.pdf",
      output_path="/tmp/out.pdf",
      settings=settings,
    )


def test_image_watermark_export(sample_pdf_file, tmp_path):
  from PIL import Image

  img_path = str(tmp_path / "wm.png")
  img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
  img.save(img_path)

  output_path = str(tmp_path / "img_out.pdf")
  from filigrane.core.watermark import ImageWatermarkConfig

  settings = WatermarkSettings(
    type=WatermarkType.IMAGE,
    image_config=ImageWatermarkConfig(image_path=img_path, scale=0.5, opacity=0.8),
  )

  out = PDFProcessor.apply_watermark(
    input_path=sample_pdf_file,
    output_path=output_path,
    settings=settings,
  )

  assert os.path.exists(out)
  with pypdf.PdfReader(out) as reader:
    assert len(reader.pages) == 1


def test_position_calculations():
  page_w, page_h = 600.0, 800.0
  elem_w, elem_h = 100.0, 50.0

  # Zero margin: top left should start at left=0 (center x = elem_w/2 = 50) and top=0 (center y = elem_h/2 = 25)
  pos_x, pos_y = PDFProcessor._calculate_position(
    page_w, page_h, elem_w, elem_h, WatermarkPosition.TOP_LEFT, 0.0, 0.0, 50.0, 50.0, rotation=0.0
  )
  assert pos_x == 50.0
  assert pos_y == 25.0
  assert pos_x - elem_w / 2.0 == 0.0  # left edge = 0

  # Zero margin: bottom left should start at left=0 (center x = 50) and bottom=800 (center y = 775)
  pos_x, pos_y = PDFProcessor._calculate_position(
    page_w, page_h, elem_w, elem_h, WatermarkPosition.BOTTOM_LEFT, 0.0, 0.0, 50.0, 50.0, rotation=0.0
  )
  assert pos_x == 50.0
  assert pos_y == 775.0
  assert pos_x - elem_w / 2.0 == 0.0  # left edge = 0

  # Zero margin: top right should end at right=600 (center x = 550)
  pos_x, pos_y = PDFProcessor._calculate_position(
    page_w, page_h, elem_w, elem_h, WatermarkPosition.TOP_RIGHT, 0.0, 0.0, 50.0, 50.0, rotation=0.0
  )
  assert pos_x == 550.0
  assert pos_y == 25.0
  assert pos_x + elem_w / 2.0 == 600.0  # right edge = page_w

  # Zero margin: bottom right should end at right=600 (center x = 550)
  pos_x, pos_y = PDFProcessor._calculate_position(
    page_w, page_h, elem_w, elem_h, WatermarkPosition.BOTTOM_RIGHT, 0.0, 0.0, 50.0, 50.0, rotation=0.0
  )
  assert pos_x == 550.0
  assert pos_y == 775.0
  assert pos_x + elem_w / 2.0 == 600.0  # right edge = page_w


def test_pdf_encryption_and_protection(sample_pdf_file, tmp_path):
  from filigrane.core.watermark import ProtectionMode, SecurityConfig

  output_path = str(tmp_path / "protected.pdf")
  settings = WatermarkSettings(
    type=WatermarkType.TEXT,
    text_config=TextWatermarkConfig(text="PROTECTED DOCUMENT"),
    security_config=SecurityConfig(
      enabled=True,
      mode=ProtectionMode.RESTRICT_EDITING,
      allow_printing=True,
      allow_accessibility=True,
      owner_password="test_owner_key_98765",
    ),
  )

  out = PDFProcessor.apply_watermark(
    input_path=sample_pdf_file,
    output_path=output_path,
    settings=settings,
  )

  assert os.path.exists(out)
  reader = pypdf.PdfReader(out)
  assert reader.is_encrypted is True

  # Verify opening document with empty user password works seamlessly
  assert reader.decrypt("") in (pypdf.PasswordType.USER_PASSWORD, pypdf.PasswordType.OWNER_PASSWORD, 1, 2)
  assert len(reader.pages) == 1


def test_pdf_flatten_and_restrict_mode(sample_pdf_file, tmp_path):
  from filigrane.core.watermark import ProtectionMode, SecurityConfig

  output_path = str(tmp_path / "flattened.pdf")
  settings = WatermarkSettings(
    type=WatermarkType.TEXT,
    text_config=TextWatermarkConfig(text="FLATTENED SECURE"),
    security_config=SecurityConfig(
      enabled=True,
      mode=ProtectionMode.FLATTEN_AND_RESTRICT,
      allow_printing=True,
    ),
  )

  out = PDFProcessor.apply_watermark(
    input_path=sample_pdf_file,
    output_path=output_path,
    settings=settings,
  )

  assert os.path.exists(out)
  reader = pypdf.PdfReader(out)
  assert reader.is_encrypted is True
  assert len(reader.pages) == 1
