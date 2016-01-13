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

"""Python 2.7 subprocess module compatibility for 2.6."""

import subprocess
from subprocess import *  # pylint: disable=wildcard-import


if not hasattr(subprocess, 'check_output'):

  # 2.6 CalledProcessError doesn't accept the output kwarg.
  class CalledProcessError(subprocess.CalledProcessError):

    def __init__(self, returncode, cmd, output=None):
      try:
        super(CalledProcessError, self).__init__(returncode, cmd, output)
      except TypeError:
        super(CalledProcessError, self).__init__(returncode, cmd)
        self.output = output

  def check_output(*popenargs, **kwargs):
    if 'stdout' in kwargs:
      raise ValueError('stdout argument not allowed.')
    p = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
    (stdout_data, _) = p.communicate()
    assert type(p.returncode) is int  # communicate() should ensure non-None
    if p.returncode:
      cmd = kwargs.get('args', popenargs[0])
      raise CalledProcessError(p.returncode, cmd, stdout_data)
    return stdout_data
