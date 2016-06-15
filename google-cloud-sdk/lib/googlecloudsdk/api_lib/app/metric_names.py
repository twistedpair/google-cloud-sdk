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

"""Appengine CSI metric names."""
# Metric names for CSI

# Reserved CSI metric prefix for appengine
_APPENGINE_PREFIX = 'app_deploy_'

# Time to upload project source tarball to GCS
CLOUDBUILD_UPLOAD = _APPENGINE_PREFIX + 'cloudbuild_upload'

# Time to execute Argo Cloud Build request
CLOUDBUILD_EXECUTE = _APPENGINE_PREFIX + 'cloudbuild_execute'

# Time to copy application files to the application code bucket
COPY_APP_FILES = _APPENGINE_PREFIX + 'copy_app_files'

# Time to copy application files to the application code bucket without gsutil.
COPY_APP_FILES_NO_GSUTIL = _APPENGINE_PREFIX + 'copy_app_files_no_gsutil'

# Time for a deploy using appengine API
DEPLOY_API = _APPENGINE_PREFIX + 'deploy_api'

# Time for API request to get the application code bucket.
GET_CODE_BUCKET = _APPENGINE_PREFIX + 'get_code_bucket'

# Time for setting deployed version to default using appengine API
SET_DEFAULT_VERSION_API = (
    _APPENGINE_PREFIX + 'set_default_version_api')
