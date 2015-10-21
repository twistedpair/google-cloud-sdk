# Copyright 2015 Google Inc. All Rights Reserved.

"""To determine the version of Python used."""

import sys

IS_ON_PYTHON26 = False

if sys.version_info[:2] < (2, 7):
  IS_ON_PYTHON26 = True


