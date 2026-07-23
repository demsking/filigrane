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
import gettext
import os
from pathlib import Path

DOMAIN = "filigrane"
LOCALE_DIR = os.environ.get("FILIGRANE_LOCALE_DIR")

if not LOCALE_DIR:
  dev_locale = Path(__file__).resolve().parent.parent.parent / "po"
  system_locale = Path("/usr/share/locale")
  LOCALE_DIR = str(dev_locale) if dev_locale.exists() else str(system_locale)

try:
  gettext.bindtextdomain(DOMAIN, LOCALE_DIR)
  gettext.textdomain(DOMAIN)
  _t = gettext.translation(DOMAIN, LOCALE_DIR, fallback=True)
  _ = _t.gettext
except Exception:

  def _(message: str) -> str:
    return message
