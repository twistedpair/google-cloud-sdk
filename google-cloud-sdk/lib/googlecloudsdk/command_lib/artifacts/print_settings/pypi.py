# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Utility for forming settings for pypi."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

SERVICE_ACCOUNT_SETTING_TEMPLATE = """\
# Insert the following snippet into your .pypirc

[distutils]
index-servers =
    {repo}

[{repo}]
repository: https://{location}-pypi.pkg.dev/{repo_path}/
username: _json_key_base64
password: {password}

# Insert the following snippet into your pip.conf

[global]
index-url = https://_json_key_base64:{password}@{location}-pypi.pkg.dev/{repo_path}/simple/
"""

NO_SERVICE_ACCOUNT_SETTING_TEMPLATE = """\
# Insert the following snippet into your .pypirc

[distutils]
index-servers =
    {repo}

[{repo}]
repository: https://{location}-pypi.pkg.dev/{repo_path}/

# Insert the following snippet into your pip.conf

[global]
index-url = https://{location}-pypi.pkg.dev/{repo_path}/simple/
"""
