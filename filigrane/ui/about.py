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
import gi

from filigrane import __app_id__
from filigrane import __author_email__
from filigrane import __author_name__
from filigrane import __project_issues_url__
from filigrane import __project_service_desk_url__
from filigrane import __project_website_url__

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from filigrane import __version__  # noqa: E402
from filigrane.utils.i18n import _  # noqa: E402


def show_about_dialog(parent_window: Gtk.Window) -> None:
  """Display modern Libadwaita About dialog.

  Args:
      parent_window: Parent window for modal presentation.
  """
  about = Adw.AboutDialog.new()
  about.set_application_name(_("Filigrane"))
  about.set_developer_name(__author_name__)
  about.set_version(__version__)
  about.set_comments(
    _(
      "Filigrane is a modern GNOME application designed to apply elegant vector text or high-resolution image watermarks to PDF documents quickly and securely."
    )
  )
  about.set_website(__project_website_url__)
  about.set_issue_url(__project_issues_url__)
  about.set_support_url(__project_service_desk_url__)
  about.set_license_type(Gtk.License.GPL_3_0)
  about.set_copyright(f"© 2026 {__author_name__}")
  about.set_application_icon(__app_id__)
  about.set_developers([f"{__author_name__} <{__author_email__}>"])
  about.set_translator_credits(_(f"{__author_name__} <{__author_email__}>"))

  about.present(parent_window)
