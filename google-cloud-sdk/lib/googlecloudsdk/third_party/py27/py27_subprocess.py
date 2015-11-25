# Copyright 2015 Google Inc. All Rights Reserved.

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
