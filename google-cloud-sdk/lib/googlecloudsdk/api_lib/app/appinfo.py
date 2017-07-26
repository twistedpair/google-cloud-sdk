# Copyright 2017 Google Inc. All Rights Reserved.
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

"""A module to modify appinfo during import."""

from googlecloudsdk.third_party.appengine.api import appinfo
from googlecloudsdk.third_party.appengine.api import validation

# TODO(b/37542869): Get rid of this hack once the server can correct accept
# runtime names that start with gs://. Until then, override the regex for
# validation in gcloud.
_RUNTIME_RE_STRING_OVERRIDE = (
    r'((gs://[a-z0-9\-\._/]+)|({orig}))'.format(
        orig=appinfo.RUNTIME_RE_STRING))
appinfo.AppInfoExternal.ATTRIBUTES[appinfo.RUNTIME] = (
    validation.Optional(_RUNTIME_RE_STRING_OVERRIDE))
