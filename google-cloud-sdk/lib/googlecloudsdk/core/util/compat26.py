# Copyright 2014 Google Inc. All Rights Reserved.

"""Utilities for accessing python 2.7 functionality from 2.6."""

import subprocess as _subprocess

from googlecloudsdk.core.util import version


# Don't warn that subprocess doesn't start with a capital letter.  This
# allows compat26.subprocess.- to look like subprocess.-.
# pylint: disable=invalid-name
class subprocess(object):

  """subprocess.check_output simulates the python 2.7 library function.

  This implementation takes a subset of the flags allowed in
  python 2.7 library, but is otherwise intended to have the same
  behavior.
  """

  PIPE = _subprocess.PIPE
  STDOUT = _subprocess.STDOUT

  @staticmethod
  def check_output(cmd, stdin=None, stderr=None,
                   shell=False, universal_newlines=False, cwd=None):
    p = _subprocess.Popen(cmd, stdin=stdin, stderr=stderr,
                          stdout=subprocess.PIPE, shell=shell,
                          universal_newlines=universal_newlines, cwd=cwd)
    (stdout_data, _) = p.communicate()
    assert type(p.returncode) is int  # communicate() should ensure non-None
    if p.returncode == 0:
      return stdout_data
    else:
      raise subprocess.CalledProcessError(p.returncode, cmd, stdout_data)

  class CalledProcessError(_subprocess.CalledProcessError):

    """CalledProcessError in Python 2.6 doesn't accept the output parameter.
    """

    def __init__(self, returncode, cmd, output):
      if version.IS_ON_PYTHON26:
        super(subprocess.CalledProcessError, self).__init__(returncode, cmd)
        self.output = output
      else:
        super(subprocess.CalledProcessError, self).__init__(returncode, cmd,
                                                            output)

