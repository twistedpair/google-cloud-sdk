# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Command helper libraries and utilities.

This package contains helper libraries and utilities to directly support
command implementations.  Things in this package should be restricted to things
that have an interface specific to argparse, calliope, or some aspect of the
human interface to gcloud.  Libraries should be organized in sub-packages by
command surface.

Libraries for calling APIs, dealing with data, or other interface agnostic
functionality should be put in api_lib.
"""
