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
"""Utility wrappers around apitools generator."""

import logging
import os

from apitools.gen import gen_client


def GenerateApi(base_dir, root_dir, api_name, api_version, api_config):
  """Invokes apitools generator for given api."""
  discovery_doc = api_config['discovery_doc']

  args = [gen_client.__file__]

  unelidable_request_methods = api_config.get('unelidable_request_methods')
  if unelidable_request_methods:
    args.append('--unelidable_request_methods={0}'.format(
        ','.join(api_config['unelidable_request_methods'])))

  api_version_in_targets = api_config.get('version', api_version)
  args.extend([
      # TODO(b/25710611) enable empty init files.
      # '--init-file=empty',
      '--nogenerate_cli',
      '--infile={0}'.format(os.path.join(base_dir, root_dir, discovery_doc)),
      '--outdir={0}'.format(os.path.join(base_dir, root_dir, api_name,
                                         api_version_in_targets)),
      '--overwrite',
      '--apitools_version=CloudSDK',
      '--root_package',
      '{0}.{1}.{2}'.format(
          root_dir.replace('/', '.'), api_name, api_version_in_targets),
      'client',
  ])
  logging.debug('Apitools gen %s', args)
  gen_client.main(args)
