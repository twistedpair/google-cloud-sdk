# Copyright 2013 Google Inc. All Rights Reserved.

"""gcloud command line tool."""

import time
START_TIME = time.time()

# pylint:disable=g-bad-import-order
# pylint:disable=g-import-not-at-top, We want to get the start time first.
import os
import signal
import sys

from googlecloudsdk.calliope import backend
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import cli
from googlecloudsdk.core import config
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core import properties
from googlecloudsdk.core.updater import local_state
from googlecloudsdk.core.updater import update_manager
from googlecloudsdk.core.util import platforms
import googlecloudsdk.surface


# Disable stack traces when people kill a command.
def CTRLCHandler(unused_signal, unused_frame):
  """Custom SIGNINT handler.

  Signal handler that doesn't print the stack trace when a command is
  killed by keyboard interupt.
  """
  try:
    log.err.Print('\n\nCommand killed by keyboard interrupt\n')
  except NameError:
    sys.stderr.write('\n\nCommand killed by keyboard interrupt\n')
  # Kill ourselves with SIGINT so our parent can detect that we exited because
  # of a signal. SIG_DFL disables further KeyboardInterrupt exceptions.
  signal.signal(signal.SIGINT, signal.SIG_DFL)
  os.kill(os.getpid(), signal.SIGINT)
  # Just in case the kill failed ...
  sys.exit(1)
signal.signal(signal.SIGINT, CTRLCHandler)


# Enable normal UNIX handling of SIGPIPE to play nice with grep -q, head, etc.
# See https://mail.python.org/pipermail/python-list/2004-June/273297.html and
# http://utcc.utoronto.ca/~cks/space/blog/python/SignalExceptionSurprise
# for more details.
if hasattr(signal, 'SIGPIPE'):
  signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def _DoStartupChecks():
  if not platforms.PythonVersion().IsCompatible():
    sys.exit(1)
  if not platforms.Platform.Current().IsSupported():
    sys.exit(1)

_DoStartupChecks()

if not config.Paths().sdk_root:
  # Don't do update checks if there is no install root.
  properties.VALUES.component_manager.disable_update_check.Set(True)


def UpdateCheck(command_path, **unused_kwargs):
  try:
    update_manager.UpdateManager.PerformUpdateCheck(command_path=command_path)
  # pylint:disable=broad-except, We never want this to escape, ever. Only
  # messages printed should reach the user.
  except Exception:
    log.debug('Failed to perform update check.', exc_info=True)


def CreateCLI(surfaces):
  """Generates the gcloud CLI from 'surface' folder with extra surfaces.

  Args:
    surfaces: list(tuple(dot_path, dir_path)), extra commands or subsurfaces
              to add, where dot_path is calliope command path and dir_path
              path to command group or command.
  Returns:
    calliope cli object.
  """
  def VersionFunc():
    generated_cli.Execute(['version'])

  pkg_root = os.path.dirname(os.path.dirname(googlecloudsdk.surface.__file__))
  loader = cli.CLILoader(
      name='gcloud',
      command_root_directory=os.path.join(pkg_root, 'surface'),
      allow_non_existing_modules=True,
      version_func=VersionFunc)
  loader.AddReleaseTrack(base.ReleaseTrack.ALPHA,
                         os.path.join(pkg_root, 'surface', 'alpha'),
                         component='alpha')
  loader.AddReleaseTrack(base.ReleaseTrack.BETA,
                         os.path.join(pkg_root, 'surface', 'beta'),
                         component='beta')

  for dot_path, dir_path in surfaces:
    loader.AddModule(dot_path, dir_path, component=None)

  # Check for updates on shutdown but not for any of the updater commands.
  loader.RegisterPostRunHook(UpdateCheck,
                             exclude_commands=r'gcloud\.components\..*')
  generated_cli = loader.Generate()
  return generated_cli


def _PrintSuggestedAction(err, err_string):
  """Print the best action for the user to take, given the error."""
  if (isinstance(err, backend.CommandLoadFailure) and
      type(err.root_exception) is ImportError):
    # This usually indicates installation corruption.
    # We do want to suggest `gcloud components reinstall` here, because
    # there's a good chance it'll work (rather than a manual reinstall).
    # Don't suggest `gcloud feedback`, because this is probably an
    # installation problem.
    log.error(
        ('gcloud failed to load ({0}): {1}\n\n'
         'This usually indicates corruption in your gcloud installation. '
         'Please run the following command to reinstall:\n'
         '    $ gcloud components reinstall\n\n'
         'If that command fails, please reinstall the Cloud SDK using the '
         'instructions here:\n'
         '    https://cloud.google.com/sdk/'
        ).format(err.command, err_string))
  else:
    log.error('gcloud crashed ({0}): {1}'.format(
        getattr(err, 'error_name', type(err).__name__),
        err_string))
    log.err.Print('\nIf you would like to report this issue, please run the '
                  'following command:')
    log.err.Print('  gcloud feedback')


def main(gcloud_cli=None):
  metrics.Started(START_TIME)
  # TODO(markpell): Put a real version number here
  metrics.Executions(
      'gcloud',
      local_state.InstallationState.VersionForInstalledComponent('core'))
  if gcloud_cli is None:
    gcloud_cli = CreateCLI([])
  try:
    gcloud_cli.Execute()
  except Exception as err:  # pylint:disable=broad-except
    _PrintSuggestedAction(err, gcloud_cli.SafeExceptionToString(err))

    if properties.VALUES.core.print_unhandled_tracebacks.GetBool():
      # We want to see the traceback as normally handled by Python
      raise
    else:
      # This is the case for most non-Cloud SDK developers. They shouldn't see
      # the full stack trace, but just the nice "gcloud crashed" message.
      sys.exit(1)


if __name__ == '__main__':
  try:
    main()
  except KeyboardInterrupt:
    CTRLCHandler(None, None)
