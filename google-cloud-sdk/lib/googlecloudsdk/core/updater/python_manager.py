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


PYTHON_VERSION = '3.12'
PYTHON_VERSION_INFO = (3, 12)
MACOS_PYTHON = 'python-3.12.8-macos11.tar.gz'

HOMEBREW_BIN = '/opt/homebrew/bin'
MACOS_PYTHON_INSTALL_PATH = (
    f'/Library/Frameworks/Python.framework/Versions/{PYTHON_VERSION}/')
MACOS_PYTHON_URL = (
    'https://dl.google.com/dl/cloudsdk/channels/rapid/' + MACOS_PYTHON
)


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


def _IsHomebrewInstalled():
  return os.path.isdir(HOMEBREW_BIN) and 'homebrew' in config.GcloudPath()


def _PromptPythonUpdate(python_install_path):
  return (
      f'Python {PYTHON_VERSION} installation detected in '
      f'{python_install_path}, install recommended modules?')


def _PromptPythonInstall():
  if _IsHomebrewInstalled():
    return f'Homebrew install Python {PYTHON_VERSION}?'
  else:
    return f'Download and run Python {PYTHON_VERSION} installer?'


def _BrewInstallPython():
  """Make sure python version is correct for user using gcloud with homebrew."""
  brew_install = f'{HOMEBREW_BIN}/brew install python@{PYTHON_VERSION}'
  print(f'Running "{brew_install}".')

  exit_code = execution_utils.Exec(brew_install.split(' '), no_exit=True)
  if exit_code != 0:
    return (
        f'"{brew_install}" failed. Please brew install '
        f'python@{PYTHON_VERSION} manually.')
  return None


def _MacInstallPython():
  """Optionally install Python on Mac machines."""

  print(f'Running Python {PYTHON_VERSION} installer, you may be prompted for '
        'sudo password...')

  # Xcode Command Line Tools is required to install Python.
  PromptAndInstallXcodeCommandLineTools()

  with files.TemporaryDirectory() as tempdir:
    with files.ChDir(tempdir):
      curl_args = ['curl', '--silent', '-O', MACOS_PYTHON_URL]
      exit_code = execution_utils.Exec(curl_args, no_exit=True)
      if exit_code != 0:
        return 'Failed to download Python installer'

      exit_code = execution_utils.Exec(
          ['tar', '-xf', MACOS_PYTHON], no_exit=True)
      if exit_code != 0:
        return 'Failed to extract Python installer'

      exit_code = execution_utils.Exec([
          'sudo', 'installer', '-target', '/', '-pkg',
          './python-3.12.8-macos11.pkg'
      ], no_exit=True)
      if exit_code != 0:
        return 'Installer failed.'

  return None


def PromptAndInstallPythonOnMac():
  """Optionally install Python on Mac machines."""
  if platforms.OperatingSystem.Current() != platforms.OperatingSystem.MACOSX:
    return

  print(
      f'\nGoogle Cloud CLI works best with Python {PYTHON_VERSION} '
      'and certain modules.\n')

  # Determine python install path
  homebrew_installed = _IsHomebrewInstalled()

  if homebrew_installed:
    python_to_use = f'{HOMEBREW_BIN}/python{PYTHON_VERSION}'
  else:
    python_to_use = f'{MACOS_PYTHON_INSTALL_PATH}bin/python3'
  already_installed = os.path.isfile(python_to_use)

  # Prompt for user permission
  if already_installed:
    prompt = _PromptPythonUpdate(python_to_use)
  else:
    prompt = _PromptPythonInstall()
  if not console_io.PromptContinue(prompt_string=prompt, default=True):
    return

  # Install python if needed
  if not already_installed:
    install_errors = (_BrewInstallPython()
                      if homebrew_installed else _MacInstallPython())
  else:
    install_errors = None

  # Update python dependencies
  if not install_errors:
    os.environ['CLOUDSDK_PYTHON'] = python_to_use
    print('Setting up virtual environment')
    EnableVirtualEnv(python_to_use)
  else:
    print(f'Failed to install Python. Error: {install_errors}')


def CheckXcodeCommandLineToolsInstalled() -> bool:
  """Checks if Xcode Command Line Tools is installed."""
  exit_code = execution_utils.Exec(['xcode-select', '-p'], no_exit=True)
  return exit_code == 0


def PromptAndInstallXcodeCommandLineTools():
  """Optionally install Xcode Command Line Tools on Mac machines."""
  if platforms.OperatingSystem.Current() != platforms.OperatingSystem.MACOSX:
    return

  if CheckXcodeCommandLineToolsInstalled():
    print('Xcode Command Line Tools is already installed.')
    return

  prompt = (
      'Xcode Command Line Tools is required to install Python. Continue to'
      ' install (Y/n)?'
  )
  setup_xcode = console_io.PromptContinue(prompt_string=prompt, default=True)

  if setup_xcode:
    print('Installing Xcode Command Line Tools...')
    xcode_command = ['xcode-select', '--install']
    exit_code = execution_utils.Exec(xcode_command, no_exit=True)
    if exit_code != 0:
      print('Failed to install Xcode Command Line Tools. '
            'Please run `xcode-select --install` manually to install '
            'Xcode Command Line Tools.')
    else:
      print('Xcode Command Line Tools is installed.')
