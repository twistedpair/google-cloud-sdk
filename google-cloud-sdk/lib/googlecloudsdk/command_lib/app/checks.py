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
from googlecloudsdk.core.util import platforms


class UnsupportedPythonVersionError(exceptions.Error):
  pass


def RaiseIfNotPython27():
  if not platforms.PythonVersion().IsSupported():
    raise UnsupportedPythonVersionError(
        ('Python 2.7 or greater is required for App Engine commands in gcloud.'
         '\n\n'
         'Your Python location: [{0}]\n\n'
         'Please set the CLOUDSDK_PYTHON environment variable to point to a '
         'supported version in order to use this command.'
        ).format(sys.executable))
