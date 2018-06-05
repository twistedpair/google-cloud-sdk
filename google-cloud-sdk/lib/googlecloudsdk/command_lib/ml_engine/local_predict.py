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
"""Utilities for running predictions locally.

This module will always be run within a subprocess, and therefore normal
conventions of Cloud SDK do not apply here.
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import json
import sys


def eprint(*args, **kwargs):
  """Print to stderr."""
  # Print is being over core.log because this is a special case as
  # this is a script called by gcloud.
  print(*args, file=sys.stderr, **kwargs)


VERIFY_TENSORFLOW_VERSION = ('Please verify the installed tensorflow version '
                             'with: "python -c \'import tensorflow; '
                             'print tensorflow.__version__\'".')


def _verify_tensorflow(version):
  """Check whether TensorFlow is installed at an appropriate version."""
  # Check tensorflow with a recent version is installed.
  try:
    # pylint: disable=g-import-not-at-top
    import tensorflow as tf  # pytype: disable=import-error
    # pylint: enable=g-import-not-at-top
  except ImportError:
    eprint('Cannot import Tensorflow. Please verify '
           '"python -c \'import tensorflow\'" works.')
    return False
  try:
    if tf.__version__ < version:
      eprint('Tensorflow version must be at least {} .'.format(version),
             VERIFY_TENSORFLOW_VERSION)
      return False
  except (NameError, AttributeError) as e:
    eprint('Error while getting the installed TensorFlow version: ', e,
           '\n', VERIFY_TENSORFLOW_VERSION)
    return False

  return True


def main():
  if not _verify_tensorflow('1.0.0'):
    sys.exit(-1)
  # We want to do this *after* we verify tensorflow so the user gets a nicer
  # error message.
  # pylint: disable=g-import-not-at-top
  from cloud.ml.prediction import prediction_lib
  # pylint: enable=g-import-not-at-top
  parser = argparse.ArgumentParser()
  parser.add_argument('--model-dir', required=True, help='Path of the model.')
  parser.add_argument('--framework', required=False, default='tensorflow',
                      help=('The ML framework used to train this version of '
                            'the model. If not specified, defaults to '
                            '`tensorflow`'))
  args, _ = parser.parse_known_args()

  instances = []
  for line in sys.stdin:
    instance = json.loads(line.rstrip('\n'))
    instances.append(instance)

  predictions = prediction_lib.local_predict(model_dir=args.model_dir,
                                             instances=instances,
                                             framework=args.framework)
  print(json.dumps(predictions))


if __name__ == '__main__':
  main()
