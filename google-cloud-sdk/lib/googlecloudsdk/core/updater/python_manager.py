# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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

"""Python installers for gcloud."""

import os

from googlecloudsdk.core import config
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import platforms


MACOS_PYTHON_INSTALL_PATH = '/Library/Frameworks/Python.framework/Versions/3.12/'
MACOS_PYTHON = 'python-3.12.8-macos11.tar.gz'
MACOS_PYTHON_URL = (
    'https://dl.google.com/dl/cloudsdk/channels/rapid/' + MACOS_PYTHON
)
PYTHON_VERSION = '3.12'


def EnableVirtualEnv(python_to_use):
  """Enables virtual environment."""
  try:
    from googlecloudsdk import gcloud_main  # pylint: disable=g-import-not-at-top
    cli = gcloud_main.CreateCLI([])
    if os.path.isdir(config.Paths().virtualenv_dir):
      cli.Execute(['config', 'virtualenv', 'update'])
      cli.Execute(['config', 'virtualenv', 'enable'])
    else:
      cli.Execute(['config', 'virtualenv', 'create', '--python-to-use',
                   python_to_use])
      cli.Execute(['config', 'virtualenv', 'enable'])
  except ImportError:
    print('Failed to enable virtual environment')


def PromptAndInstallPythonOnMac():
  """Optionally install Python on Mac machines."""
  if platforms.OperatingSystem.Current() != platforms.OperatingSystem.MACOSX:
    return

  print('\nGoogle Cloud CLI works best with Python {} and certain modules.\n'
        .format(PYTHON_VERSION))

  already_have_python_version = os.path.isdir(MACOS_PYTHON_INSTALL_PATH)
  if already_have_python_version:
    prompt = ('Python {} installation detected, install recommended'
              ' modules?'.format(PYTHON_VERSION))
  else:
    prompt = 'Download and run Python {} installer?'.format(PYTHON_VERSION)
  setup_python = console_io.PromptContinue(prompt_string=prompt, default=True)

  if setup_python:
    install_errors = []
    if not already_have_python_version:
      print('Running Python {} installer, you may be prompted for sudo '
            'password...'.format(PYTHON_VERSION))

      # Xcode is required to install Python. Install it if it is not already
      # installed.
      PromptAndInstallXcode()

      with files.TemporaryDirectory() as tempdir:
        with files.ChDir(tempdir):
          curl_args = ['curl', '--silent', '-O', MACOS_PYTHON_URL]
          exit_code = execution_utils.Exec(curl_args, no_exit=True)
          if exit_code != 0:
            install_errors.append('Failed to download Python installer')
          else:
            exit_code = execution_utils.Exec(['tar', '-xf', MACOS_PYTHON],
                                             no_exit=True)
            if exit_code != 0:
              install_errors.append('Failed to extract Python installer')
            else:
              exit_code = execution_utils.Exec([
                  'sudo', 'installer', '-target', '/', '-pkg',
                  './python-3.12.8-macos11.pkg'
              ],
                                               no_exit=True)
              if exit_code != 0:
                install_errors.append('Installer failed.')

    if not install_errors:
      python_to_use = '{}/bin/python3'.format(MACOS_PYTHON_INSTALL_PATH)
      os.environ['CLOUDSDK_PYTHON'] = python_to_use
      print('Setting up virtual environment')
      EnableVirtualEnv(python_to_use)
    else:
      print('Failed to install Python. Errors \n\n{}'.format(
          '\n*'.join(install_errors)))


def CheckXcodeInstalled() -> bool:
  """Checks if Xcode is installed."""
  exit_code = execution_utils.Exec(['xcode-select', '-p'], no_exit=True)
  return exit_code == 0


def PromptAndInstallXcode():
  """Optionally install Xcode on Mac machines."""
  if platforms.OperatingSystem.Current() != platforms.OperatingSystem.MACOSX:
    return

  if CheckXcodeInstalled():
    print('Xcode is already installed.')
    return

  prompt = 'Xcode is required to install Python. Continue to install (Y/n)?'
  setup_xcode = console_io.PromptContinue(prompt_string=prompt, default=True)

  if setup_xcode:
    print('Installing Xcode...')
    xcode_command = ['xcode-select', '--install']
    exit_code = execution_utils.Exec(xcode_command, no_exit=True)
    if exit_code != 0:
      print('Failed to install Xcode. '
            'Please run `xcode-select --install` manually to install Xcode.')
    else:
      print('Xcode is installed.')
