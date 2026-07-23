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
import os
from pathlib import Path

from filigrane.utils.logger import get_logger

logger = get_logger()

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg"}
SUPPORTED_PDF_EXTENSIONS = {".pdf"}


def is_valid_pdf_file(file_path: str | Path) -> bool:
  """Validate whether a path points to a readable non-empty PDF file.

  Args:
      file_path: Path to the file.

  Returns:
      True if file exists, is non-empty, and has .pdf extension or header.
  """
  path = Path(file_path)
  if not path.is_file() or path.stat().st_size == 0:
    return False
  if path.suffix.lower() not in SUPPORTED_PDF_EXTENSIONS:
    return False

  try:
    with open(path, "rb") as f:
      header = f.read(5)
      return header.startswith(b"%PDF-")
  except Exception as e:
    logger.warning(f"Error checking PDF header for {file_path}: {e}")
    return False


def is_valid_image_file(file_path: str | Path) -> bool:
  """Validate whether a path points to a readable image file (PNG, SVG, JPEG).

  Args:
      file_path: Path to image file.

  Returns:
      True if valid supported image file.
  """
  path = Path(file_path)
  if not path.is_file() or path.stat().st_size == 0:
    return False
  return path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS


def format_file_size(size_bytes: int) -> str:
  """Format file size into human-readable string (e.g. 1.5 MB).

  Args:
      size_bytes: File size in bytes.

  Returns:
      Formatted size string.
  """
  if size_bytes < 1024:
    return f"{size_bytes} B"
  elif size_bytes < 1024 * 1024:
    return f"{size_bytes / 1024:.1f} KB"
  elif size_bytes < 1024 * 1024 * 1024:
    return f"{size_bytes / (1024 * 1024):.1f} MB"
  else:
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def get_default_output_filename(input_path: str | Path | None) -> str:
  """Generate a reasonable default output filename for watermarked export.

  Args:
      input_path: Path to the input PDF file.

  Returns:
      Default output file name (e.g. 'doc_watermarked.pdf').
  """
  if not input_path:
    return "output_watermarked.pdf"

  stem = Path(input_path).stem
  return f"{stem}_watermarked.pdf"


def resolve_file_path(uri_or_path: str) -> str | None:
  """Convert file URI or raw path to absolute file system path.

  Args:
      uri_or_path: File path or file:// URI string.

  Returns:
      Clean absolute path string or None if invalid.
  """
  if not uri_or_path:
    return None

  if uri_or_path.startswith("file://"):
    from urllib.parse import unquote, urlparse

    parsed = urlparse(uri_or_path)
    path = unquote(parsed.path)
  else:
    path = uri_or_path

  abs_path = os.path.abspath(path)
  if os.path.exists(abs_path):
    return abs_path
  return None
