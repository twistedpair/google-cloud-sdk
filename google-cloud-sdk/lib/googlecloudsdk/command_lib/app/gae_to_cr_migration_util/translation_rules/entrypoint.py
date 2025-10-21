# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Translation rule for entrypoint."""

import logging
from typing import Sequence


_DEFAULT_PYTHON_ENTRYPOINT = 'gunicorn -b :$PORT main:app'
# Cloud Run service must listen on 0.0.0.0 host,
# ref https://cloud.google.com/run/docs/container-contract#port
_DEFAULT_RUBY_ENTRYPOINT = 'bundle exec ruby app.rb -o 0.0.0.0'
_DEFAULT_ENTRYPOINT_INFO_FORMAT = (
    '[Info] Default entrypoint for %s is : "%s", retry'
    ' `gcloud app migrate appengine-to-cloudrun` with the'
    ' --entrypoint="%s" flag.\n'
)


def translate_entrypoint_features(
    command: str,
) -> Sequence[str]:
  """Tranlsate entrypoint from App Engine app to entrypoint for equivalent Cloud Run app."""
  if command is None:
    warning_text = (
        'Warning: entrypoint for the app is not detected/provided, if an'
        ' entrypoint is needed to start the app, please use the `--entrypoint`'
        ' flag to specify the entrypoint for the App.\n'
    )
    logging.info(warning_text)
  return []
