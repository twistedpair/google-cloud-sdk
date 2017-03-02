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
import imp
import json
import os
import sys


def eprint(*args, **kwargs):
  """Print to stderr."""
  print(*args, file=sys.stderr, **kwargs)


VERIFY_TENSORFLOW_VERSION = ('Please verify the installed tensorflow version '
                             'with: "python -c \'import tensorflow; '
                             'print tensorflow.__version__\'".')

VERIFY_CLOUDML_VERSION = ('Please verify the installed cloudml sdk version with'
                          ': "python -c \'import google.cloud.ml as cloudml; '
                          'print cloudml.__version__\'".')


def _verify_tensorflow():
  """Check whether TensorFlow is installed at an appropriate version."""
  packages_ok = True

  # Check tensorflow with a recent version is installed.
  try:
    # pylint: disable=g-import-not-at-top
    import tensorflow as tf
    # pylint: enable=g-import-not-at-top
  except ImportError:
    eprint('Cannot import Tensorflow. Please verify '
           '"python -c \'import tensorflow\'" works.')
    packages_ok = False
  try:
    if tf.__version__ < '0.10.0':
      eprint('Tensorflow version must be at least 0.10.0. ',
             VERIFY_TENSORFLOW_VERSION)
      packages_ok = False
  except (NameError, AttributeError) as e:
    eprint('Error while getting the installed TensorFlow version: ', e,
           '\n', VERIFY_TENSORFLOW_VERSION)
    packages_ok = False

  return packages_ok


def _import_prediction_lib():
  """Import a prediction library.

  In preference order:
  - an importable Cloud ML SDK with a valid version
  - the bundled prediction library.

  Returns:
    a Python module with the Cloud ML predictions library.
  """
  # TODO(user): Don't try to import the Cloud ML SDK at all.
  # pylint: disable=g-import-not-at-top
  try:
    import google.cloud.ml as cloudml
  except ImportError:
    failure_msg = ('Cannot import google.cloud.ml. Please verify '
                   '"python -c \'import google.cloud.ml\'" works.')
  else:
    try:
      cloud_ml_version = cloudml.__version__
    except (NameError, AttributeError) as e:
      failure_msg = '\n'.join((
          'Error while getting the installed Cloud ML SDK version:\n', e, '\n'))
    else:
      if cloud_ml_version >= '0.1.7':
        from google.cloud.ml import prediction
        return prediction
      failure_msg = ('Cloudml SDK version must be at least 0.1.7 '
                     'to run local prediction.')

  try:
    # This horrible hack is necessary because we're executing outside of the
    # context of the Cloud SDK. There's no guarantee about what is/is not on the
    # PYTHONPATH.
    return imp.load_source(
        'predict_lib_beta',
        os.path.join(os.path.dirname(__file__), 'prediction_lib_beta.py'))
  except ImportError:
    # This shouldn't happen; we should always have predict_lib.py available.
    # But if it does happen, an installed Cloud ML SDK will always work.
    eprint(failure_msg, VERIFY_CLOUDML_VERSION)
    sys.exit(-1)
  # pylint: enable=g-import-not-at-top


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--model-dir', required=True, help='Path of the model.')
  args, _ = parser.parse_known_args()
  if not _verify_tensorflow():
    sys.exit(-1)

  instances = []
  for line in sys.stdin:
    instance = json.loads(line.rstrip('\n'))
    instances.append(instance)

  prediction = _import_prediction_lib()
  predictions = prediction.local_predict(model_dir=args.model_dir,
                                         instances=instances)
  print(json.dumps(predictions))


if __name__ == '__main__':
  main()
