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
import io
import math
import os
import secrets
import threading
from collections.abc import Callable
from pathlib import Path

import cairo
import pypdf
from PIL import Image
from PIL import ImageOps
from pypdf.constants import UserAccessPermissions

from filigrane.core.watermark import ImageWatermarkConfig
from filigrane.core.watermark import ProtectionMode
from filigrane.core.watermark import TextWatermarkConfig
from filigrane.core.watermark import WatermarkPosition
from filigrane.core.watermark import WatermarkSettings
from filigrane.core.watermark import WatermarkType
from filigrane.utils.file_utils import is_valid_pdf_file
from filigrane.utils.logger import get_logger

logger = get_logger()

# Type callback for progress updates: (fraction: float, status_message: str)
ProgressCallback = Callable[[float, str], None]


class PDFProcessingError(Exception):
  """Exception raised when PDF processing or watermarking fails."""

  pass


class PDFProcessor:
  """Core engine for merging PDFs and applying text or image watermarks."""

  @staticmethod
  def create_text_watermark_page(width: float, height: float, config: TextWatermarkConfig) -> pypdf.PageObject:
    """Create a transparent PDF page containing a rendered vector text watermark.

    Args:
        width: Target page width in points.
        height: Target page height in points.
        config: Text watermark settings.

    Returns:
        pypdf.PageObject containing the watermark.
    """
    buf = io.BytesIO()
    surface = cairo.PDFSurface(buf, width, height)
    ctx = cairo.Context(surface)

    slant = cairo.FONT_SLANT_ITALIC if config.italic else cairo.FONT_SLANT_NORMAL
    weight = cairo.FONT_WEIGHT_BOLD if config.bold else cairo.FONT_WEIGHT_NORMAL

    ctx.select_font_face(config.font_family, slant, weight)
    ctx.set_font_size(config.font_size)
    ctx.set_source_rgba(config.color[0], config.color[1], config.color[2], config.opacity)

    extents = ctx.text_extents(config.text)
    text_w = extents.width
    text_h = extents.height
    x_bearing = extents.x_bearing
    y_bearing = extents.y_bearing

    rad = math.radians(config.rotation)
    cos_a = abs(math.cos(rad))
    sin_a = abs(math.sin(rad))
    rot_w = text_w * cos_a + text_h * sin_a
    rot_h = text_w * sin_a + text_h * cos_a

    def draw_single_text(x: float, y: float) -> None:
      ctx.save()
      ctx.translate(x, y)
      ctx.rotate(rad)

      offset_x = -text_w / 2.0 - x_bearing
      offset_y = -text_h / 2.0 - y_bearing

      ctx.move_to(offset_x, offset_y)
      ctx.show_text(config.text)

      if config.underline:
        line_y = offset_y + y_bearing + text_h + 3.0
        ctx.set_line_width(max(1.0, config.font_size / 16.0))
        ctx.move_to(offset_x + x_bearing, line_y)
        ctx.line_to(offset_x + x_bearing + text_w, line_y)
        ctx.stroke()

      ctx.restore()

    if config.position == WatermarkPosition.TILED:
      # Draw grid of watermarks repeated across the entire page starting at left=0 and top=0
      spacing_x = max(30.0, rot_w + config.margin_x)
      spacing_y = max(30.0, rot_h + config.margin_y)
      y = rot_h / 2.0
      while y < height + spacing_y:
        x = rot_w / 2.0
        while x < width + spacing_x:
          draw_single_text(x, y)
          x += spacing_x
        y += spacing_y
    else:
      pos_x, pos_y = PDFProcessor._calculate_position(
        width,
        height,
        text_w,
        text_h,
        config.position,
        config.margin_x,
        config.margin_y,
        config.custom_x,
        config.custom_y,
        config.rotation,
      )
      draw_single_text(pos_x, pos_y)

    surface.finish()
    buf.seek(0)

    with pypdf.PdfReader(buf) as reader:
      return reader.pages[0]

  @staticmethod
  def create_image_watermark_page(width: float, height: float, config: ImageWatermarkConfig) -> pypdf.PageObject:
    """Create a transparent PDF page containing a rendered image watermark.

    Args:
        width: Target page width in points.
        height: Target page height in points.
        config: Image watermark settings.

    Returns:
        pypdf.PageObject containing the watermark.
    """
    if not config.image_path or not os.path.exists(config.image_path):
      raise PDFProcessingError(f"Image path does not exist: {config.image_path}")

    try:
      with Image.open(config.image_path) as raw_img:
        pil_img = ImageOps.exif_transpose(raw_img).convert("RGBA")
    except Exception as e:
      raise PDFProcessingError(f"Failed to load image file {config.image_path}: {e}") from e

    orig_w, orig_h = pil_img.size
    img_w = float(orig_w) * config.scale
    img_h = float(orig_h) * config.scale

    # Convert PIL Image to Cairo ImageSurface
    img_bytes = pil_img.tobytes("raw", "BGRA")
    img_surface = cairo.ImageSurface.create_for_data(bytearray(img_bytes), cairo.FORMAT_ARGB32, orig_w, orig_h, orig_w * 4)

    buf = io.BytesIO()
    surface = cairo.PDFSurface(buf, width, height)
    ctx = cairo.Context(surface)

    rad = math.radians(config.rotation)
    cos_a = abs(math.cos(rad))
    sin_a = abs(math.sin(rad))
    rot_w = img_w * cos_a + img_h * sin_a
    rot_h = img_w * sin_a + img_h * cos_a

    def draw_single_image(x: float, y: float) -> None:
      ctx.save()
      ctx.translate(x, y)
      ctx.rotate(rad)
      ctx.scale(config.scale, config.scale)
      ctx.set_source_surface(img_surface, -orig_w / 2.0, -orig_h / 2.0)
      ctx.paint_with_alpha(config.opacity)
      ctx.restore()

    if config.position == WatermarkPosition.TILED:
      # Draw grid of image watermarks repeated across the entire page starting at left=0 and top=0
      spacing_x = max(30.0, rot_w + config.margin_x)
      spacing_y = max(30.0, rot_h + config.margin_y)
      y = rot_h / 2.0
      while y < height + spacing_y:
        x = rot_w / 2.0
        while x < width + spacing_x:
          draw_single_image(x, y)
          x += spacing_x
        y += spacing_y
    else:
      pos_x, pos_y = PDFProcessor._calculate_position(
        width,
        height,
        img_w,
        img_h,
        config.position,
        config.margin_x,
        config.margin_y,
        config.custom_x,
        config.custom_y,
        config.rotation,
      )
      draw_single_image(pos_x, pos_y)

    surface.finish()
    buf.seek(0)

    with pypdf.PdfReader(buf) as reader:
      return reader.pages[0]

  @staticmethod
  def _calculate_position(
    page_w: float,
    page_h: float,
    elem_w: float,
    elem_h: float,
    position: WatermarkPosition,
    margin_x: float,
    margin_y: float,
    custom_x: float,
    custom_y: float,
    rotation: float = 0.0,
  ) -> tuple[float, float]:
    """Calculate center (X, Y) coordinates for watermark placement."""
    rad = math.radians(rotation)
    cos_a = abs(math.cos(rad))
    sin_a = abs(math.sin(rad))
    rot_w = elem_w * cos_a + elem_h * sin_a
    rot_h = elem_w * sin_a + elem_h * cos_a

    if position == WatermarkPosition.CENTER:
      return page_w / 2.0, page_h / 2.0
    elif position == WatermarkPosition.TOP_LEFT:
      return margin_x + rot_w / 2.0, margin_y + rot_h / 2.0
    elif position == WatermarkPosition.TOP_RIGHT:
      return page_w - (margin_x + rot_w / 2.0), margin_y + rot_h / 2.0
    elif position == WatermarkPosition.BOTTOM_LEFT:
      return margin_x + rot_w / 2.0, page_h - (margin_y + rot_h / 2.0)
    elif position == WatermarkPosition.BOTTOM_RIGHT:
      return page_w - (margin_x + rot_w / 2.0), page_h - (margin_y + rot_h / 2.0)
    elif position == WatermarkPosition.CUSTOM:
      return (page_w * custom_x / 100.0), (page_h * custom_y / 100.0)
    else:
      return page_w / 2.0, page_h / 2.0

  @classmethod
  def apply_watermark(
    cls,
    input_path: str,
    output_path: str,
    settings: WatermarkSettings,
    progress_callback: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
  ) -> str:
    """Apply specified watermark to all pages of a single input PDF document.

    Args:
        input_path: File path to the input PDF document.
        output_path: Target path for the generated watermarked PDF.
        settings: Watermark configuration settings.
        progress_callback: Optional progress reporter callback.
        cancel_event: Threading event to signal cancellation.

    Returns:
        Path of generated output file.
    """
    if not input_path or not is_valid_pdf_file(input_path):
      raise PDFProcessingError(f"Invalid or unreadable PDF file: {input_path}")

    if progress_callback:
      progress_callback(0.05, "Reading input PDF file...")

    try:
      reader = pypdf.PdfReader(input_path)
    except Exception as e:
      raise PDFProcessingError(f"Failed reading PDF {input_path}: {e}") from e

    total_pages = len(reader.pages)
    if total_pages == 0:
      raise PDFProcessingError("Input document contains no pages")

    logger.info(f"Applying watermark to {total_pages} pages of {input_path}...")

    abs_input = os.path.abspath(input_path)
    abs_output = os.path.abspath(output_path)
    is_same_file = abs_input == abs_output

    out_dir = Path(output_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    target_write_path = f"{output_path}.tmp" if is_same_file else output_path

    try:
      with pypdf.PdfWriter() as writer:
        watermark_cache: dict[tuple[float, float], pypdf.PageObject] = {}

        poppler_doc = None
        if settings.security_config.enabled and settings.security_config.mode == ProtectionMode.FLATTEN_AND_RESTRICT:
          try:
            import gi

            gi.require_version("Poppler", "0.18")
            from gi.repository import GLib, Poppler

            poppler_doc = Poppler.Document.new_from_file(GLib.filename_to_uri(abs_input), None)
          except Exception as pe:
            logger.warning(f"Poppler loading failed for flattening mode: {pe}")
            poppler_doc = None

        for page_idx, page in enumerate(reader.pages):
          if cancel_event and cancel_event.is_set():
            raise PDFProcessingError("Operation cancelled by user")

          bbox = page.mediabox
          w = float(bbox.width)
          h = float(bbox.height)

          key = (round(w, 2), round(h, 2))
          if key not in watermark_cache:
            if settings.type == WatermarkType.TEXT:
              wm_page = cls.create_text_watermark_page(w, h, settings.text_config)
            else:
              wm_page = cls.create_image_watermark_page(w, h, settings.image_config)
            watermark_cache[key] = wm_page
          else:
            wm_page = watermark_cache[key]

          if poppler_doc and page_idx < poppler_doc.get_n_pages():
            try:
              p_page = poppler_doc.get_page(page_idx)
              scale = 2.0
              img_w, img_h = int(w * scale), int(h * scale)
              img_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, img_w, img_h)
              ctx = cairo.Context(img_surf)
              ctx.scale(scale, scale)
              p_page.render(ctx)

              buf = io.BytesIO()
              pdf_surf = cairo.PDFSurface(buf, w, h)
              pdf_ctx = cairo.Context(pdf_surf)
              pdf_ctx.scale(1.0 / scale, 1.0 / scale)
              pdf_ctx.set_source_surface(img_surf, 0, 0)
              pdf_ctx.paint()
              pdf_surf.finish()
              buf.seek(0)

              with pypdf.PdfReader(buf) as buf_reader:
                flat_page = buf_reader.pages[0]
                flat_page.merge_page(wm_page)
                writer.add_page(flat_page)
            except Exception as fe:
              logger.warning(f"Page flattening error for page {page_idx}: {fe}")
              page.merge_page(wm_page)
              writer.add_page(page)
          else:
            page.merge_page(wm_page)
            writer.add_page(page)

          if progress_callback:
            frac = 0.10 + 0.80 * ((page_idx + 1) / total_pages)
            progress_callback(frac, f"Watermarking page {page_idx + 1} of {total_pages}...")

        if cancel_event and cancel_event.is_set():
          raise PDFProcessingError("Operation cancelled by user")

        writer.compress_identical_objects()

        sec = settings.security_config
        if sec.enabled and sec.mode != ProtectionMode.DISABLED:
          flags = 0
          if sec.allow_printing:
            flags |= UserAccessPermissions.PRINT | UserAccessPermissions.PRINT_TO_REPRESENTATION
          if sec.allow_accessibility:
            flags |= UserAccessPermissions.EXTRACT_TEXT_AND_GRAPHICS

          owner_pwd = sec.owner_password if sec.owner_password else secrets.token_urlsafe(32)
          try:
            writer.encrypt(
              user_password="",  # nosec B106
              owner_password=owner_pwd,
              permissions_flag=UserAccessPermissions(flags),
              algorithm="AES-256",
            )
          except Exception as enc_err:
            logger.warning(f"AES-256 encryption fallback due to: {enc_err}")
            writer.encrypt(
              user_password="",  # nosec B106
              owner_password=owner_pwd,
              permissions_flag=UserAccessPermissions(flags),
              use_128bit=True,
            )

        if progress_callback:
          progress_callback(0.95, "Saving output file...")

        writer.write(target_write_path)

      if is_same_file:
        os.replace(target_write_path, output_path)

    except Exception as e:
      if is_same_file and os.path.exists(target_write_path):
        try:
          os.remove(target_write_path)
        except OSError:
          pass
      if isinstance(e, PDFProcessingError):
        raise
      raise PDFProcessingError(f"Failed to write output PDF file {output_path}: {e}") from e

    if progress_callback:
      progress_callback(1.0, "Export completed successfully")

    logger.info(f"Successfully created watermarked PDF at: {output_path}")
    return output_path
