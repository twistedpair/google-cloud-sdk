# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Checks to run before running `gcloud app` commands."""
import sys

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import platforms


# TODO(b/24169312): remove
CHANGE_WARNING = """\
The `gcloud preview app` surface is rapidly improving. Look out for
changing flags and new commands before the transition out of the `preview`
component. These changes will be documented in the Cloud SDK release notes
<https://goo.gl/X8apDJ> and via deprecation notices for changing commands.

If you would like to avoid changing behavior, please pin to a fixed version of
the Google Cloud SDK as described under the "Alternative Methods" section of the
Cloud SDK web site: <https://cloud.google.com/sdk/#alternative>.
"""


class UnsupportedPythonVersionError(exceptions.Error):
  pass


def WarnAboutChangingBehavior():
  # TODO(b/24169312): remove
  if not properties.VALUES.app.suppress_change_warning.GetBool():
    log.warn(CHANGE_WARNING)
    properties.PersistProperty(properties.VALUES.app.suppress_change_warning,
                               'true')


def RaiseIfNotPython27():
  if not platforms.PythonVersion().IsSupported():
    raise UnsupportedPythonVersionError(
        ('Python 2.7 or greater is required for App Engine commands in gcloud.'
         '\n\n'
         'Your Python location: [{0}]\n\n'
         'Please set the CLOUDSDK_PYTHON environment variable to point to a '
         'supported version in order to use this command.'
        ).format(sys.executable))
