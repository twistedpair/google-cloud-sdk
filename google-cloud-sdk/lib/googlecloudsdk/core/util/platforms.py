# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Utilities for determining the current platform and architecture."""

import os
import platform
import sys


class Error(Exception):
  """Base class for exceptions in the platforms moudle."""
  pass


class InvalidEnumValue(Error):
  """Exception for when a string could not be parsed to a valid enum value."""

  def __init__(self, given, enum_type, options):
    """Constructs a new exception.

    Args:
      given: str, The given string that could not be parsed.
      enum_type: str, The human readable name of the enum you were trying to
        parse.
      options: list(str), The valid values for this enum.
    """
    super(InvalidEnumValue, self).__init__(
        'Could not parse [{0}] into a valid {1}.  Valid values are [{2}]'
        .format(given, enum_type, ', '.join(options)))


def GetHomePath():
  return ExpandHomePath('~')


def ExpandHomePath(path):
  return os.path.expanduser(path)


class OperatingSystem(object):
  """An enum representing the operating system you are running on."""

  class _OS(object):

    # pylint: disable=redefined-builtin
    def __init__(self, id, name, file_name):
      self.id = id
      self.name = name
      self.file_name = file_name

  WINDOWS = _OS('WINDOWS', 'Windows', 'windows')
  MACOSX = _OS('MACOSX', 'Mac OS X', 'darwin')
  LINUX = _OS('LINUX', 'Linux', 'linux')
  CYGWIN = _OS('CYGWIN', 'Cygwin', 'cygwin')
  MSYS = _OS('MSYS', 'Msys', 'msys')
  _ALL = [WINDOWS, MACOSX, LINUX, CYGWIN, MSYS]

  @staticmethod
  def AllValues():
    """Gets all possible enum values.

    Returns:
      list, All the enum values.
    """
    return list(OperatingSystem._ALL)

  @staticmethod
  def FromId(os_id, error_on_unknown=True):
    """Gets the enum corresponding to the given operating system id.

    Args:
      os_id: str, The operating system id to parse
      error_on_unknown: bool, True to raise an exception if the id is unknown,
        False to just return None.

    Raises:
      InvalidEnumValue: If the given value cannot be parsed.

    Returns:
      OperatingSystemTuple, One of the OperatingSystem constants or None if the
      input is None.
    """
    if not os_id:
      return None
    for operating_system in OperatingSystem._ALL:
      if operating_system.id == os_id:
        return operating_system
    if error_on_unknown:
      raise InvalidEnumValue(os_id, 'Operating System',
                             [value.id for value in OperatingSystem._ALL])
    return None

  @staticmethod
  def Current():
    """Determines the current operating system.

    Returns:
      OperatingSystemTuple, One of the OperatingSystem constants or None if it
      cannot be determined.
    """
    if os.name == 'nt':
      return OperatingSystem.WINDOWS
    elif 'linux' in sys.platform:
      return OperatingSystem.LINUX
    elif 'darwin' in sys.platform:
      return OperatingSystem.MACOSX
    elif 'cygwin' in sys.platform:
      return OperatingSystem.CYGWIN
    # TODO(user): More reliable handling of OS types
    # TODO(user): What happens when we use jython, does it actually use the
    # 'java' os name?
    return None


class Architecture(object):
  """An enum representing the system architecture you are running on."""

  class _ARCH(object):

    # pylint: disable=redefined-builtin
    def __init__(self, id, name, file_name):
      self.id = id
      self.name = name
      self.file_name = file_name

  x86 = _ARCH('x86', 'x86', 'x86')
  x86_64 = _ARCH('x86_64', 'x86_64', 'x86_64')
  ppc = _ARCH('PPC', 'PPC', 'ppc')
  _ALL = [x86, x86_64, ppc]
  _MACHINE_TO_ARCHITECTURE = {'AMD64': x86_64, 'x86_64': x86_64,
                              'i386': x86, 'i686': x86, 'x86': x86,
                              'Power Macintosh': ppc}

  @staticmethod
  def AllValues():
    """Gets all possible enum values.

    Returns:
      list, All the enum values.
    """
    return list(Architecture._ALL)

  @staticmethod
  def FromId(architecture_id, error_on_unknown=True):
    """Gets the enum corresponding to the given architecture id.

    Args:
      architecture_id: str, The architecture id to parse
      error_on_unknown: bool, True to raise an exception if the id is unknown,
        False to just return None.

    Raises:
      InvalidEnumValue: If the given value cannot be parsed.

    Returns:
      ArchitectureTuple, One of the Architecture constants or None if the input
      is None.
    """
    if not architecture_id:
      return None
    for arch in Architecture._ALL:
      if arch.id == architecture_id:
        return arch
    if error_on_unknown:
      raise InvalidEnumValue(architecture_id, 'Architecture',
                             [value.id for value in Architecture._ALL])
    return None

  @staticmethod
  def Current():
    """Determines the current system architecture.

    Returns:
      ArchitectureTuple, One of the Architecture constants or None if it cannot
      be determined.
    """
    return Architecture._MACHINE_TO_ARCHITECTURE.get(platform.machine())


class Platform(object):
  """Holds an operating system and architecture."""

  def __init__(self, operating_system, architecture):
    """Constructs a new platform.

    Args:
      operating_system: OperatingSystem, The OS
      architecture: Architecture, The machine architecture.
    """
    self.operating_system = operating_system
    self.architecture = architecture

  @staticmethod
  def Current(os_override=None, arch_override=None):
    """Determines the current platform you are running on.

    Args:
      os_override: OperatingSystem, A value to use instead of the current.
      arch_override: Architecture, A value to use instead of the current.

    Returns:
      Platform, The platform tuple of operating system and architecture.  Either
      can be None if it could not be determined.
    """
    return Platform(
        os_override if os_override else OperatingSystem.Current(),
        arch_override if arch_override else Architecture.Current())

  def UserAgentFragment(self):
    """Generates the fragment of the User-Agent that represents the OS.

    Examples:
      (Linux 3.2.5-gg1236)
      (Windows NT 6.1.7601)
      (Macintosh; PPC Mac OS X 12.4.0)
      (Macintosh; Intel Mac OS X 12.4.0)

    Returns:
      str, The fragment of the User-Agent string.
    """
    # Below, there are examples of the value of platform.uname() per platform.
    # platform.release() is uname[2], platform.version() is uname[3].
    if self.operating_system == OperatingSystem.LINUX:
      # ('Linux', '<hostname goes here>', '3.2.5-gg1236',
      # '#1 SMP Tue May 21 02:35:06 PDT 2013', 'x86_64', 'x86_64')
      return '({name} {version})'.format(
          name=self.operating_system.name, version=platform.release())
    elif self.operating_system == OperatingSystem.WINDOWS:
      # ('Windows', '<hostname goes here>', '7', '6.1.7601', 'AMD64',
      # 'Intel64 Family 6 Model 45 Stepping 7, GenuineIntel')
      return '({name} NT {version})'.format(
          name=self.operating_system.name, version=platform.version())
    elif self.operating_system == OperatingSystem.MACOSX:
      # ('Darwin', '<hostname goes here>', '12.4.0',
      # 'Darwin Kernel Version 12.4.0: Wed May  1 17:57:12 PDT 2013;
      # root:xnu-2050.24.15~1/RELEASE_X86_64', 'x86_64', 'i386')
      format_string = '(Macintosh; {name} Mac OS X {version})'
      arch_string = (self.architecture.name
                     if self.architecture == Architecture.ppc else 'Intel')
      return format_string.format(
          name=arch_string, version=platform.release())
    else:
      return '()'

  def AsyncPopenArgs(self):
    """Returns the args for spawning an async process using Popen on this OS.

    Returns:
      {str:}, The args for spawning an async process using Popen on this OS.
    """
    args = {}
    if self.operating_system == OperatingSystem.WINDOWS:
      args['close_fds'] = True
      detached_process = 0x00000008
      args['creationflags'] = detached_process
    return args

  def SyncPopenArgs(self):
    """Returns args for spawning a synchronous process using Popen on this OS.

    Returns:
      {str:}, The args for spawning a syncronous process using Popen on this OS.
    """
    args = {}
    if self.operating_system == OperatingSystem.WINDOWS:
      args['close_fds'] = True
    return args


class PythonVersion(object):
  """Class to validate the Python version we are using.

  The Cloud SDK officially supports Python 2.7.

  However, many commands do work with Python 2.6, so we don't error out when
  users are using this (we consider it "compatible" but not "supported").
  """

  # See class docstring for descriptions of what these mean
  MIN_REQUIRED_VERSION = (2, 6)
  MIN_SUPPORTED_VERSION = (2, 7)

  def __init__(self, version=None):
    if version:
      self.version = version
    elif hasattr(sys, 'version_info'):
      self.version = sys.version_info[:2]
    else:
      self.version = None

  def MinSupportedVersionString(self):
    return '{0}.{1}.x'.format(PythonVersion.MIN_SUPPORTED_VERSION[0],
                              PythonVersion.MIN_SUPPORTED_VERSION[1])

  def __PrintEnvVarMessage(self):
    """Prints how to set CLOUDSDK_PYTHON."""
    sys.stderr.write('\nIf you have a compatible Python interpreter installed, '
                     'you can use it by setting the CLOUDSDK_PYTHON '
                     'environment variable to point to it.\n')

  def IsCompatible(self, print_errors=True):
    """Ensure that the Python version we are using is compatible.

    This will print an error message if not compatible.

    Compatible versions are 2.6 and 2.7.

    Args:
      print_errors: bool, if False disable the error messages about not being
          compatible..

    Returns:
      bool, True if the version is valid, False otherwise.
    """
    error = None
    if not self.version:
      error = ('ERROR: Your current version of Python is not compatible with '
               'the Google Cloud SDK. Please upgrade to Python {0}\n'
               .format(self.MinSupportedVersionString()))
    elif self.version[0] >= 3:
      error = ('ERROR: Python 3 and later is not compatible with by the Google '
               'Cloud SDK. Please use a Python {0} version.\n'
               .format(self.MinSupportedVersionString()))
    elif self.version < PythonVersion.MIN_REQUIRED_VERSION:
      error = ('ERROR: Python {0}.{1} is not compatible with the Google Cloud '
               'SDK. Please upgrade to Python {2}\n'
               .format(self.version[0], self.version[1],
                       self.MinSupportedVersionString()))

    if error:
      if print_errors:
        sys.stderr.write(error)
        self.__PrintEnvVarMessage()
      return False
    return True

  def IsSupported(self):
    """Return whether this Python version is recommended.

    Only version 2.7 is supported.

    Returns:
      bool, True if the Python version is recommended
    """
    return (self.IsCompatible(print_errors=False) and
            self.version >= self.MIN_SUPPORTED_VERSION)

  def IsPython26(self):
    """Check specifically if we are running on Python 2.6 so we can warn.

    Returns:
      True, if running on Python 2.6, False otherwise.
    """
    return self.version == (2, 6)
