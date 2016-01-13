# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Default value constants exposed by core utilities."""

DEFAULT_REGISTRY = 'gcr.io'
REGIONAL_REGISTRIES = ['us.gcr.io', 'eu.gcr.io', 'asia.gcr.io']
BUCKET_REGISTRIES = ['b.gcr.io', 'bucket.gcr.io']
APPENGINE_REGISTRY = 'appengine.gcr.io'
SPECIALTY_REGISTRIES = BUCKET_REGISTRIES + [APPENGINE_REGISTRY]
ALL_SUPPORTED_REGISTRIES = ([DEFAULT_REGISTRY] + REGIONAL_REGISTRIES
                            + SPECIALTY_REGISTRIES)
DEFAULT_DEVSHELL_IMAGE = (DEFAULT_REGISTRY +
                          '/dev_con/cloud-dev-common:prod')
METADATA_IMAGE = DEFAULT_REGISTRY + '/google_appengine/faux-metadata:latest'
