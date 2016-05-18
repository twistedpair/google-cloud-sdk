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

"""Used to collect anonymous SDK metrics."""

import atexit
import os
import pickle
import platform
import socket
import sys
import tempfile
import time
import urllib
import uuid

from googlecloudsdk.core import config
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import platforms
from googlecloudsdk.third_party.py27 import py27_subprocess as subprocess


_GA_ENDPOINT = 'https://ssl.google-analytics.com/collect'
_GA_TID = 'UA-36037335-2'
_GA_TID_TESTING = 'UA-36037335-13'
_GA_INSTALLS_CATEGORY = 'Installs'
_GA_COMMANDS_CATEGORY = 'Commands'
_GA_HELP_CATEGORY = 'Help'
_GA_ERROR_CATEGORY = 'Error'
_GA_EXECUTIONS_CATEGORY = 'Executions'
_GA_TEST_EXECUTIONS_CATEGORY = 'TestExecutions'

_CSI_ENDPOINT = 'https://csi.gstatic.com/csi'
_CSI_ID = 'cloud_sdk'
_CSI_LOAD_EVENT = 'load'
_CSI_RUN_EVENT = 'run'
_CSI_TOTAL_EVENT = 'total'


class _GAEvent(object):

  def __init__(self, category, action, label, value, **kwargs):
    self.category = category
    self.action = action
    self.label = label
    self.value = value
    self.custom_dimensions = kwargs


def _GetTimeMillis(time_secs=None):
  return int(round((time_secs or time.time()) * 1000))


class _TimedEvent(object):

  def __init__(self, name):
    self.name = name
    self.time_millis = _GetTimeMillis()


class _CommandTimer(object):
  """A class for timing the execution of a command."""

  def __init__(self, start_time_ms):
    self.__start = start_time_ms
    self.__events = []
    self.__category = 'unknown'
    self.__action = 'unknown'
    self.__label = None
    self.__custom_dimensions = {}

  def SetContext(self, category, action, label, **kwargs):
    self.__category = category
    self.__action = action
    self.__label = label
    self.__custom_dimensions = kwargs

  def GetAction(self):
    return self.__action

  def Event(self, name):
    self.__events.append(_TimedEvent(name))

  def _GetCSIAction(self):
    csi_action = '{0},{1}'.format(self.__category, self.__action)
    if self.__label:
      csi_action = '{0},{1}'.format(csi_action, self.__label)
    csi_action = csi_action.replace('.', ',').replace('-', '_')
    return csi_action

  def GetCSIParams(self):
    """Gets the fields to send in the CSI beacon."""
    params = [('action', self._GetCSIAction())]
    params.extend([(k, v) for k, v in self.__custom_dimensions.iteritems()
                   if v is not None])

    response_times = [
        '{0}.{1}'.format(event.name, event.time_millis - self.__start)
        for event in self.__events]
    params.append(('rt', ','.join(response_times)))

    return params


class _MetricsCollector(object):
  """A singleton class to handle metrics reporting."""

  _disabled_cache = None
  _instance = None
  test_group = None

  @staticmethod
  def GetCollectorIfExists():
    return _MetricsCollector._instance

  @staticmethod
  def GetCollector():
    """Returns the singleton _MetricsCollector instance or None if disabled."""
    if _MetricsCollector._IsDisabled():
      return None

    if not _MetricsCollector._instance:
      _MetricsCollector._instance = _MetricsCollector()
    return _MetricsCollector._instance

  @staticmethod
  def ResetCollectorInstance(disable_cache=None, ga_tid=_GA_TID):
    """Reset the singleton _MetricsCollector and reinitialize it.

    This should only be used for tests, where we want to collect some metrics
    but not others, and we have to reinitialize the collector with a different
    Google Analytics tracking id.

    Args:
      disable_cache: Metrics collector keeps an internal cache of the disabled
          state of metrics. This controls the value to reinitialize the cache.
          None means we will refresh the cache with the default values.
          True/False forces a specific value.
      ga_tid: The Google Analytics tracking ID to use for metrics collection.
          Defaults to _GA_TID.
    """
    _MetricsCollector._disabled_cache = disable_cache
    if _MetricsCollector._IsDisabled():
      _MetricsCollector._instance = None
    else:
      _MetricsCollector._instance = _MetricsCollector(ga_tid)

  @staticmethod
  def _IsDisabled():
    """Returns whether metrics collection should be disabled."""
    if _MetricsCollector._disabled_cache is None:
      # Don't collect metrics for completions.
      if '_ARGCOMPLETE' in os.environ:
        _MetricsCollector._disabled_cache = True
      else:
        # Don't collect metrics if the user has opted out.
        disabled = properties.VALUES.core.disable_usage_reporting.GetBool()
        if disabled is None:
          # There is no preference set, fall back to the installation default.
          disabled = config.INSTALLATION_CONFIG.disable_usage_reporting
        _MetricsCollector._disabled_cache = disabled
    return _MetricsCollector._disabled_cache

  def __init__(self, ga_tid=_GA_TID):
    """Initialize a new MetricsCollector.

    This should only be invoked through the static GetCollector() function or
    the static ResetCollectorInstance() function.

    Args:
      ga_tid: The Google Analytics tracking ID to use for metrics collection.
              Defaults to _GA_TID.
    """
    current_platform = platforms.Platform.Current()
    self._user_agent = 'CloudSDK/{version} {fragment}'.format(
        version=config.CLOUD_SDK_VERSION,
        fragment=current_platform.UserAgentFragment())
    self._async_popen_args = current_platform.AsyncPopenArgs()
    self._project_ids = {}

    hostname = socket.getfqdn()
    install_type = 'Google' if hostname.endswith('.google.com') else 'External'
    cid = _MetricsCollector._GetCID()

    # Table of common params to send to both GA and CSI.
    # First column is GA name, second column is CSI name, third is the value.
    common_params = [
        ('cd1', 'release_channel', config.INSTALLATION_CONFIG.release_channel),
        ('cd2', 'install_type', install_type),
        ('cd3', 'environment', properties.GetMetricsEnvironment()),
        ('cd4', 'interactive', console_io.IsInteractive(error=True,
                                                        heuristic=True)),
        ('cd5', 'python_version', platform.python_version()),
        ('cd7', 'environment_version',
         properties.VALUES.metrics.environment_version.Get())]

    self._ga_params = [
        ('v', '1'),
        ('tid', ga_tid),
        ('cid', cid),
        ('t', 'event')]
    self._ga_params.extend([(param[0], param[2]) for param in common_params])

    self._csi_params = [('s', _CSI_ID),
                        ('v', '2'),
                        ('rls', config.CLOUD_SDK_VERSION),
                        ('c', cid)]
    self._csi_params.extend([(param[1], param[2]) for param in common_params])

    self.StartTimer(_GetTimeMillis())
    self._metrics = []

    # Tracking the level so we can only report metrics for the top level action
    # (and not other actions executed within an action). Zero is the top level.
    self._action_level = 0

    log.debug('Metrics collector initialized...')

  @staticmethod
  def _GetCID():
    """Gets the client id from the config file, or generates a new one.

    Returns:
      str, The hex string of the client id.
    """
    uuid_path = config.Paths().analytics_cid_path
    cid = None
    if os.path.exists(uuid_path):
      with open(uuid_path) as f:
        cid = f.read()
      if cid:
        return cid

    files.MakeDir(os.path.dirname(uuid_path))
    with open(uuid_path, 'w') as f:
      cid = uuid.uuid4().hex
      f.write(cid)  # A random UUID

    return cid

  def IncrementActionLevel(self):
    self._action_level += 1

  def DecrementActionLevel(self):
    self._action_level -= 1

  def StartTimer(self, start_time_ms):
    self._timer = _CommandTimer(start_time_ms)

  def RecordTimedEvent(self, name, record_only_on_top_level=False):
    """Records the time when a particular event happened.

    Args:
      name: str, Name of the event.
      record_only_on_top_level: bool, Whether to record only on top level.
    """
    if self._action_level == 0 or not record_only_on_top_level:
      self._timer.Event(name)

  def SetTimerContext(self, category, action, label=None, **kwargs):
    """Sets the context for which the timer is collecting timed events.

    Args:
      category: str, Category of the action being timed.
      action: str, Name of the action being timed.
      label: str, Additional information about the action being timed.
      **kwargs: {str: str}, A dictionary of custom dimension names to values to
        include.
    """
    # We only want to time top level commands
    if category is _GA_COMMANDS_CATEGORY and self._action_level != 0:
      return

    # We want to report error times against the top level action
    if category is _GA_ERROR_CATEGORY and self._action_level != 0:
      action = self._timer.GetAction()

    self._timer.SetContext(category, action, label, **kwargs)

  def CollectCSIMetric(self):
    """Adds metric with latencies for the given command to the metrics queue."""
    params = self._timer.GetCSIParams()
    params.extend(self._csi_params)
    data = urllib.urlencode(params)

    self._metrics.append(
        ('{0}?{1}'.format(_CSI_ENDPOINT, data), 'GET', None, self._user_agent))

  def CollectGAMetric(self, event):
    """Adds the given GA event to the metrics queue.

    Args:
      event: _Event, The event to process.
    """
    params = [
        ('ec', event.category),
        ('ea', event.action),
        ('el', event.label),
        ('ev', event.value),
    ]
    params.extend([(k, v) for k, v in event.custom_dimensions.iteritems()
                   if v is not None])
    params.extend(self._ga_params)
    data = urllib.urlencode(params)

    self._metrics.append((_GA_ENDPOINT, 'POST', data, self._user_agent))

  def ReportMetrics(self, wait_for_report=False):
    """Reports the collected metrics using a separate async process."""
    if not self._metrics:
      return

    temp_metrics_file = tempfile.NamedTemporaryFile(delete=False)
    with temp_metrics_file:
      pickle.dump(self._metrics, temp_metrics_file)
      self._metrics = []

    # TODO(user): make this not depend on the file.
    reporting_script_path = os.path.realpath(
        os.path.join(os.path.dirname(__file__), 'metrics_reporter.py'))
    execution_args = execution_utils.ArgsForPythonTool(
        reporting_script_path, temp_metrics_file.name)

    exec_env = os.environ.copy()
    exec_env['PYTHONPATH'] = os.pathsep.join(sys.path)

    try:
      p = subprocess.Popen(execution_args, env=exec_env,
                           **self._async_popen_args)
      log.debug('Metrics reporting process started...')
    except OSError:
      # This can happen specifically if the Python executable moves between the
      # start of this process and now.
      log.debug('Metrics reporting process failed to start.')
    if wait_for_report:
      # NOTE: p.wait() can cause a deadlock. p.communicate() is recommended.
      # See python docs for more information.
      p.communicate()
      log.debug('Metrics reporting process finished.')


def _CollectGAMetricAndSetTimerContext(category, action, label, value=0,
                                       flag_names=None):
  """Common code for processing a GA event."""
  collector = _MetricsCollector.GetCollector()
  if collector:
    # Override label for tests. This way we can filter by test group.
    if _MetricsCollector.test_group and category is not _GA_ERROR_CATEGORY:
      label = _MetricsCollector.test_group
    collector.CollectGAMetric(
        _GAEvent(category=category, action=action, label=label, value=value,
                 cd6=flag_names))

    # Dont include version. We already send it as the rls CSI parameter.
    if category in [_GA_COMMANDS_CATEGORY, _GA_EXECUTIONS_CATEGORY]:
      collector.SetTimerContext(category, action, flag_names=flag_names)
    elif category in [_GA_ERROR_CATEGORY, _GA_HELP_CATEGORY,
                      _GA_TEST_EXECUTIONS_CATEGORY]:
      collector.SetTimerContext(category, action, label, flag_names=flag_names)
    # Ignoring installs for now since there could be multiple per cmd execution.


def _GetFlagNameString(flag_names):
  if flag_names is None:
    # We have no information on the flags that were used.
    return ''
  if not flag_names:
    # We explicitly know that no flags were used.
    return '==NONE=='
  # One or more flags were used.
  return ','.join(sorted(flag_names))


def CaptureAndLogException(func):
  """Function decorator to capture and log any exceptions."""
  def Wrapper(*args, **kwds):
    try:
      return func(*args, **kwds)
    # pylint:disable=bare-except
    except:
      log.debug('Exception captured in %s', func.func_name, exc_info=True)
  return Wrapper


def StartTestMetrics(test_group_id, test_method):
  _MetricsCollector.ResetCollectorInstance(False, _GA_TID_TESTING)
  _MetricsCollector.test_group = test_group_id
  _CollectGAMetricAndSetTimerContext(
      _GA_TEST_EXECUTIONS_CATEGORY,
      test_method,
      test_group_id,
      value=0)


def StopTestMetrics():
  collector = _MetricsCollector.GetCollectorIfExists()
  if collector:
    collector.ReportMetrics(wait_for_report=True)
  _MetricsCollector.test_group = None
  _MetricsCollector.ResetCollectorInstance(True)


@CaptureAndLogException
@atexit.register
def Shutdown():
  """Reports the metrics that were collected."""
  collector = _MetricsCollector.GetCollectorIfExists()
  if collector:
    collector.RecordTimedEvent(_CSI_TOTAL_EVENT)
    collector.CollectCSIMetric()
    collector.ReportMetrics()


@CaptureAndLogException
def Installs(component_id, version_string):
  """Logs that an SDK component was installed.

  Args:
    component_id: str, The component id that was installed.
    version_string: str, The version of the component.
  """
  _CollectGAMetricAndSetTimerContext(
      _GA_INSTALLS_CATEGORY, component_id, version_string)


@CaptureAndLogException
def Commands(command_path, version_string, flag_names):
  """Logs that a gcloud command was run.

  Args:
    command_path: str, The '.' separated name of the calliope command.
    version_string: str, The version of the command.
    flag_names: [str], The names of the flags that were used during this
      execution.
  """
  if not version_string:
    version_string = 'unknown'
  _CollectGAMetricAndSetTimerContext(
      _GA_COMMANDS_CATEGORY, command_path, version_string,
      flag_names=_GetFlagNameString(flag_names))


@CaptureAndLogException
def Help(command_path, mode):
  """Logs that help for a gcloud command was run.

  Args:
    command_path: str, The '.' separated name of the calliope command.
    mode: str, The way help was invoked (-h, --help, help).
  """
  _CollectGAMetricAndSetTimerContext(_GA_HELP_CATEGORY, command_path, mode)


@CaptureAndLogException
def Error(command_path, exc, flag_names):
  """Logs that a top level Exception was caught for a gcloud command.

  Args:
    command_path: str, The '.' separated name of the calliope command.
    exc: Exception, The exception that was caught.
    flag_names: [str], The names of the flags that were used during this
      execution.
  """
  try:
    cls = exc.__class__
    name = '{0}.{1}'.format(cls.__module__, cls.__name__)
  # pylint:disable=bare-except, Never want to fail on metrics reporting.
  except:
    name = 'unknown'
  _CollectGAMetricAndSetTimerContext(
      _GA_ERROR_CATEGORY, command_path, name,
      flag_names=_GetFlagNameString(flag_names))


@CaptureAndLogException
def Executions(command_name, version_string):
  """Logs that a top level SDK script was run.

  Args:
    command_name: str, The script name.
    version_string: str, The version of the command.
  """
  if not version_string:
    version_string = 'unknown'
  _CollectGAMetricAndSetTimerContext(
      _GA_EXECUTIONS_CATEGORY, command_name, version_string)


@CaptureAndLogException
def Started(start_time):
  """Record the time when the command was started."""
  collector = _MetricsCollector.GetCollector()
  if collector:
    collector.StartTimer(_GetTimeMillis(start_time))


@CaptureAndLogException
def Loaded():
  """Record the time when command loading was completed."""
  collector = _MetricsCollector.GetCollector()
  if collector:
    collector.RecordTimedEvent(name=_CSI_LOAD_EVENT,
                               record_only_on_top_level=True)
    collector.IncrementActionLevel()


@CaptureAndLogException
def Ran():
  """Record the time when command running was completed."""
  collector = _MetricsCollector.GetCollector()
  if collector:
    collector.DecrementActionLevel()
    collector.RecordTimedEvent(name=_CSI_RUN_EVENT,
                               record_only_on_top_level=True)


@CaptureAndLogException
def CustomTimedEvent(event_name):
  """Record the time when a custom event was completed.

  Args:
    event_name: The name of the event. This must match the pattern
      "[a-zA-Z0-9_]+".
  """
  collector = _MetricsCollector.GetCollector()
  if collector:
    collector.RecordTimedEvent(event_name)
