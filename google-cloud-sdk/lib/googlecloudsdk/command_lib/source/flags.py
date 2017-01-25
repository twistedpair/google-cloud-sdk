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
"""Common arguments for `gcloud source repos` commands."""
from googlecloudsdk.calliope import arg_parsers


# regex copied from API docs
REPO_NAME_VALIDATOR = arg_parsers.RegexpValidator(
    r'[a-z][-a-z0-9]{1,61}[a-z0-9]',
    'may contain between 3 and 63 (inclusive) lowercase letters, digits, and '
    'hyphens, must start with a letter, and may not end with a hyphen.')
