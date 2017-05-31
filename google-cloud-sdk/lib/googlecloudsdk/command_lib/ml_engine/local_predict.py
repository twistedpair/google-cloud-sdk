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

from __future__ import print_function

import argparse
import json
import os
import sys


def eprint(*args, **kwargs):
  """Print to stderr."""
  print(*args, file=sys.stderr, **kwargs)


VERIFY_TENSORFLOW_VERSION = ('Please verify the installed tensorflow version '
                             'with: "python -c \'import tensorflow; '
                             'print tensorflow.__version__\'".')


def _verify_tensorflow(version):
  """Check whether TensorFlow is installed at an appropriate version."""
  # Check tensorflow with a recent version is installed.
  try:
    # pylint: disable=g-import-not-at-top
    import tensorflow as tf
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


def import_prediction_lib():
  try:
    if not _verify_tensorflow('1.0.0'):
      sys.exit(-1)

    sdk_root_dir = os.environ['CLOUDSDK_ROOT']
    # pylint: disable=g-import-not-at-top
    try:
      # This horrible hack is necessary because we can't import the Cloud ML SDK
      # like normal; we're probably missing dependencies. We just want to import
      # prediction.prediction_lib.
      sys.path.insert(0, os.path.join(sdk_root_dir, 'lib', 'third_party',
                                      'cloud_ml_engine_sdk', 'prediction'))
      import prediction_lib
      return prediction_lib
    finally:
      sys.path.pop(0)
    # pylint: enable=g-import-not-at-top
  except ImportError as err:
    if 'prediction_lib' in err:
      # This shouldn't happen; we should always have predict_lib.py available.
      # If anyone gets here, we want to know about it.
      eprint('Error importing prediction library:\n\n',
             str(err), '\n\nPlease contact support.')
      sys.exit(-1)
    else:
      # We shouldn't ever get here after _verify_tensorflow succeeds
      eprint('Missing dependency for local prediction:', err)
      eprint('Please make sure this module is available to `python`.')
    sys.exit(1)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--model-dir', required=True, help='Path of the model.')
  args, _ = parser.parse_known_args()

  instances = []
  for line in sys.stdin:
    instance = json.loads(line.rstrip('\n'))
    instances.append(instance)

  prediction_lib = import_prediction_lib()
  predictions = prediction_lib.local_predict(model_dir=args.model_dir,
                                             instances=instances)
  print(json.dumps(predictions))


if __name__ == '__main__':
  main()
