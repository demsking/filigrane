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
import math
from typing import Any

import cairo
import gi
from PIL import Image
from PIL import ImageOps

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Poppler", "0.18")
gi.require_version("GLib", "2.0")
from gi.repository import Gdk, GLib, Poppler  # noqa: E402

from filigrane.core.watermark import (  # noqa: E402
  WatermarkPosition,
  WatermarkSettings,
  WatermarkType,
)
from filigrane.utils.logger import get_logger  # noqa: E402

logger = get_logger()


class PreviewRenderer:
  """Renders PDF pages with live watermarks into GTK Gdk.Texture instances."""

  def __init__(self) -> None:
    self._current_path: str | None = None
    self._poppler_doc: Poppler.Document | None = None
    self._total_pages: int = 0

  def set_document(self, file_path: str) -> bool:
    """Load a PDF document path for preview rendering.

    Args:
        file_path: Valid PDF file path.

    Returns:
        True if document loaded successfully, False otherwise.
    """
    self.close_document()
    if not file_path:
      return False

    try:
      uri = GLib.filename_to_uri(file_path)
      doc = Poppler.Document.new_from_file(uri, None)
      if doc:
        self._poppler_doc = doc
        self._current_path = file_path
        self._total_pages = doc.get_n_pages()
    except Exception as e:
      logger.error(f"Error loading document for preview {file_path}: {e}")
      self.close_document()

    return self._total_pages > 0

  def close_document(self) -> None:
    """Close and unload current PDF document."""
    self._poppler_doc = None
    self._current_path = None
    self._total_pages = 0

  @property
  def total_pages(self) -> int:
    """Total number of pages in the loaded document."""
    return self._total_pages

  def get_page_size(self, page_idx: int) -> tuple[float, float]:
    """Get original dimensions (width, height) of page in points."""
    if not self._poppler_doc or page_idx < 0 or page_idx >= self._total_pages:
      return 612.0, 792.0
    poppler_page = self._poppler_doc.get_page(page_idx)
    w, h = poppler_page.get_size()
    return w, h

  def render_page_texture(
    self,
    page_idx: int,
    settings: WatermarkSettings,
    scale_factor: float = 1.0,
  ) -> Gdk.Texture | None:
    """Render specified page with live watermark into a Gdk.Texture.

    Args:
        page_idx: 0-indexed page number.
        settings: Current watermark settings.
        scale_factor: Zoom scaling multiplier.

    Returns:
        Gdk.Texture containing rendered page image or None on error.
    """
    if not self._poppler_doc or page_idx < 0 or page_idx >= self._total_pages:
      return None

    poppler_page = self._poppler_doc.get_page(page_idx)
    orig_w, orig_h = poppler_page.get_size()

    # Render at 2x resolution for HiDPI crisp text and watermark quality
    dpi_multiplier = 2.0
    render_scale = scale_factor * dpi_multiplier

    pixel_w = max(1, int(orig_w * render_scale))
    pixel_h = max(1, int(orig_h * render_scale))

    # Create Cairo ARGB32 image surface
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, pixel_w, pixel_h)
    ctx = cairo.Context(surface)

    # Fill white background
    ctx.set_source_rgb(1.0, 1.0, 1.0)
    ctx.rectangle(0, 0, pixel_w, pixel_h)
    ctx.fill()

    # Scale context for Poppler rendering
    ctx.save()
    ctx.scale(render_scale, render_scale)
    poppler_page.render(ctx)
    ctx.restore()

    # Draw live watermark on top of PDF render
    ctx.save()
    ctx.scale(render_scale, render_scale)
    self._render_watermark_overlay(ctx, orig_w, orig_h, settings)
    ctx.restore()

    surface.flush()
    data = surface.get_data()
    gbytes = GLib.Bytes.new(data)

    try:
      texture = Gdk.MemoryTexture.new(
        pixel_w,
        pixel_h,
        Gdk.MemoryFormat.B8G8R8A8_PREMULTIPLIED,
        gbytes,
        surface.get_stride(),
      )
      return texture
    except Exception as e:
      logger.error(f"Error creating Gdk.MemoryTexture: {e}")
      return None

  def _render_watermark_overlay(
    self,
    ctx: Any,
    width: float,
    height: float,
    settings: WatermarkSettings,
  ) -> None:
    """Draw live vector watermark overlay on Cairo Context."""
    if settings.type == WatermarkType.TEXT:
      cfg = settings.text_config
      slant = cairo.FONT_SLANT_ITALIC if cfg.italic else cairo.FONT_SLANT_NORMAL
      weight = cairo.FONT_WEIGHT_BOLD if cfg.bold else cairo.FONT_WEIGHT_NORMAL

      ctx.select_font_face(cfg.font_family, slant, weight)
      ctx.set_font_size(cfg.font_size)
      ctx.set_source_rgba(cfg.color[0], cfg.color[1], cfg.color[2], cfg.opacity)

      extents = ctx.text_extents(cfg.text)
      text_w = extents.width
      text_h = extents.height
      x_bearing = extents.x_bearing
      y_bearing = extents.y_bearing

      rad = math.radians(cfg.rotation)
      cos_a = abs(math.cos(rad))
      sin_a = abs(math.sin(rad))
      rot_w = text_w * cos_a + text_h * sin_a
      rot_h = text_w * sin_a + text_h * cos_a

      def draw_text_at(x: float, y: float) -> None:
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(rad)

        off_x = -text_w / 2.0 - x_bearing
        off_y = -text_h / 2.0 - y_bearing

        ctx.move_to(off_x, off_y)
        ctx.show_text(cfg.text)

        if cfg.underline:
          line_y = off_y + y_bearing + text_h + 3.0
          ctx.set_line_width(max(1.0, cfg.font_size / 16.0))
          ctx.move_to(off_x + x_bearing, line_y)
          ctx.line_to(off_x + x_bearing + text_w, line_y)
          ctx.stroke()

        ctx.restore()

      if cfg.position == WatermarkPosition.TILED:
        spacing_x = max(30.0, rot_w + cfg.margin_x)
        spacing_y = max(30.0, rot_h + cfg.margin_y)
        y = rot_h / 2.0
        while y < height + spacing_y:
          x = rot_w / 2.0
          while x < width + spacing_x:
            draw_text_at(x, y)
            x += spacing_x
          y += spacing_y
      else:
        pos_x, pos_y = self._calc_pos(
          width,
          height,
          text_w,
          text_h,
          cfg.position,
          cfg.margin_x,
          cfg.margin_y,
          cfg.custom_x,
          cfg.custom_y,
          cfg.rotation,
        )
        draw_text_at(pos_x, pos_y)

    elif settings.type == WatermarkType.IMAGE and settings.image_config.image_path:
      icfg = settings.image_config
      try:
        with Image.open(icfg.image_path) as raw_img:
          pil_img = ImageOps.exif_transpose(raw_img).convert("RGBA")
        orig_w, orig_h = pil_img.size
        img_w = float(orig_w) * icfg.scale
        img_h = float(orig_h) * icfg.scale

        img_bytes = pil_img.tobytes("raw", "BGRA")
        img_surface = cairo.ImageSurface.create_for_data(bytearray(img_bytes), cairo.FORMAT_ARGB32, orig_w, orig_h, orig_w * 4)

        rad = math.radians(icfg.rotation)
        cos_a = abs(math.cos(rad))
        sin_a = abs(math.sin(rad))
        rot_w = img_w * cos_a + img_h * sin_a
        rot_h = img_w * sin_a + img_h * cos_a

        def draw_img_at(x: float, y: float) -> None:
          ctx.save()
          ctx.translate(x, y)
          ctx.rotate(rad)
          ctx.scale(icfg.scale, icfg.scale)
          ctx.set_source_surface(img_surface, -orig_w / 2.0, -orig_h / 2.0)
          ctx.paint_with_alpha(icfg.opacity)
          ctx.restore()

        if icfg.position == WatermarkPosition.TILED:
          spacing_x = max(30.0, rot_w + icfg.margin_x)
          spacing_y = max(30.0, rot_h + icfg.margin_y)
          y = rot_h / 2.0
          while y < height + spacing_y:
            x = rot_w / 2.0
            while x < width + spacing_x:
              draw_img_at(x, y)
              x += spacing_x
            y += spacing_y
        else:
          pos_x, pos_y = self._calc_pos(
            width,
            height,
            img_w,
            img_h,
            icfg.position,
            icfg.margin_x,
            icfg.margin_y,
            icfg.custom_x,
            icfg.custom_y,
            icfg.rotation,
          )
          draw_img_at(pos_x, pos_y)
      except Exception as e:
        logger.warning(f"Failed to render image watermark preview: {e}")

  def _calc_pos(
    self,
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
    """Calculate placement coordinates on Cairo canvas."""
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
