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
import logging
import sys

LOGGER_NAME = "filigrane"


def setup_logging(level_name: str = "INFO") -> logging.Logger:
  """Configure structured logging for the application.

  Args:
      level_name: Desired logging verbosity level ('DEBUG', 'INFO', 'WARNING', 'ERROR').

  Returns:
      Configured Logger instance.
  """
  logger = logging.getLogger(LOGGER_NAME)

  numeric_level = getattr(logging, level_name.upper(), logging.INFO)
  logger.setLevel(numeric_level)

  if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s.%(module)s]: %(message)s", datefmt="%H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

  return logger


def get_logger() -> logging.Logger:
  """Get the application logger.

  Returns:
      Logger instance.
  """
  return logging.getLogger(LOGGER_NAME)
