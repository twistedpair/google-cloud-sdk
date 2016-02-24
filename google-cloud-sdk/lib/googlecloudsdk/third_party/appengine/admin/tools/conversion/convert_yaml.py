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
"""A script for converting between legacy YAML and public JSON representation.

Example invocation:
  convert_yaml.py app.yaml > app.json
"""

import json
import os
import sys

import yaml

from googlecloudsdk.third_party.appengine.admin.tools.conversion import yaml_schema


def main():
  if len(sys.argv) != 2:
    sys.stderr.write(
        'Usage: {0} <input_file.yaml>\n'.format(os.path.basename(sys.argv[0])))
    sys.exit(1)

  with open(sys.argv[1]) as input_file:
    input_yaml = yaml.safe_load(input_file)

  converted_yaml = yaml_schema.SCHEMA.ConvertValue(input_yaml)
  json.dump(converted_yaml, sys.stdout, indent=2, sort_keys=True)


if __name__ == '__main__':
  main()

