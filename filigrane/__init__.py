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
import tomllib
from pathlib import Path


_pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"

if not _pyproject_path.exists():
  _pyproject_path = Path(__file__).resolve().parent / "pyproject.toml"

with _pyproject_path.open("rb") as file:
  _package = tomllib.load(file)["project"]

  __version__ = _package["version"]
  __author_name__ = _package["authors"][0]["name"]
  __author_email__ = _package["authors"][0]["email"]
  __project_repository_url__ = _package["urls"]["Repository"]
  __project_website_url__ = _package["urls"]["Website"]
  __project_service_desk_url__ = _package["urls"]["Service Desk"]
  __project_issues_url__ = _package["urls"]["Issues"]
  __app_id__ = "io.gitlab.demsking.filigrane"

  del _package
  del tomllib
