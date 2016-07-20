# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Script to regenerate samples with latest client generator."""

import argparse
import logging
import os
import pprint
import sys

from googlecloudsdk.tools.regen_apis import regen
import yaml


def main(argv=None):
  if argv is None:
    argv = sys.argv

  parser = argparse.ArgumentParser(
      description='Regenerates apitools clients in given directory.')

  parser.add_argument('--config',
                      required=True,
                      help='Regeneration config filename.')

  parser.add_argument('--base-dir',
                      default=os.getcwd(),
                      help='Regeneration config filename.')

  parser.add_argument('--api',
                      help='api_name/api_version which to regenerate.'
                      'If ommited all will be regenerated.')

  parser.add_argument('-l',
                      '--log-level',
                      choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                      default='INFO',
                      help='Set the logging level')

  args = parser.parse_args(argv[1:])

  if args.log_level:
    logging.basicConfig(
        format='%(asctime)s %(filename)s:%(lineno)d %(message)s',
        level=getattr(logging, args.log_level))

  with open(args.config, 'r') as stream:
    config = yaml.load(stream)

  logging.debug('Config %s', pprint.pformat(config))

  root_dir = config['root_dir']
  logging.debug('Based dir %s', args.base_dir)
  if args.api is not None:
    api_name, api_version = args.api.split('/')
    api_config = config['apis'][api_name][api_version]
    regen.GenerateApi(args.base_dir, root_dir,
                      api_name, api_version, api_config)
  else:
    for api_name, api_version_config in config['apis'].iteritems():
      for api_version, api_config in api_version_config.iteritems():
        logging.info('Generating %s %s', api_name, api_version)
        regen.GenerateApi(args.base_dir, root_dir,
                          api_name, api_version, api_config)


if __name__ == '__main__':
  main()
