# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Job-specific printer."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime

from googlecloudsdk.command_lib.run.printers import container_and_volume_printer_util as container_util
from googlecloudsdk.command_lib.run.printers import k8s_object_printer_util as k8s_util
from googlecloudsdk.command_lib.util import time_util
from googlecloudsdk.core.resource import custom_printer_base as cp

EXECUTION_PRINTER_FORMAT = 'execution'
JOB_PRINTER_FORMAT = 'job'
TASK_PRINTER_FORMAT = 'task'


def _PluralizedWord(word, count):
  return '{count} {word}{plural}'.format(
      count=count or 0, word=word, plural='' if count == 1 else 's'
  )


def FormatDurationShort(duration_seconds: int) -> str:
  """Format duration from seconds into shorthand string.

  Duration will be represented of the form `#d#h#m$s` for days, hours, minutes
  and seconds. Any field that's 0 will be excluded. So 3660 seconds (1 hour and
  1 minute) will be represented as "1h1m" with no days or seconds listed.

  Args:
    duration_seconds: the total time in seconds to format

  Returns:
    a string representing the duration in more human-friendly units.
  """
  if duration_seconds == 0:
    return '0s'

  duration = datetime.timedelta(seconds=duration_seconds)
  remaining = duration.seconds
  hours = remaining // 3600
  remaining = remaining % 3600
  minutes = remaining // 60
  seconds = remaining % 60
  res = ''
  if duration.days:
    res += '{}d'.format(duration.days)
  if hours:
    res += '{}h'.format(hours)
  if minutes:
    res += '{}m'.format(minutes)
  if seconds:
    res += '{}s'.format(seconds)
  return res


class JobPrinter(cp.CustomPrinterBase):
  """Prints the run Job in a custom human-readable format.

  Format specific to Cloud Run jobs. Only available on Cloud Run commands
  that print jobs.
  """

  @staticmethod
  def TransformSpec(record):
    return ExecutionPrinter.TransformSpec(record.execution_template, record)

  @staticmethod
  def TransformStatus(record):
    if record.status is None:
      return ''
    lines = [
        'Executed {}'.format(
            _PluralizedWord('time', record.status.executionCount)
        )
    ]
    if record.status.latestCreatedExecution is not None:
      lines.append(
          'Last executed {} with execution {}'.format(
              record.status.latestCreatedExecution.creationTimestamp,
              record.status.latestCreatedExecution.name,
          )
      )
    lines.append(k8s_util.LastUpdatedMessageForJob(record))
    return cp.Lines(lines)

  @staticmethod
  def _formatOutput(record):
    output = []
    header = k8s_util.BuildHeader(record)
    status = JobPrinter.TransformStatus(record)
    labels = k8s_util.GetLabels(record.labels)
    spec = JobPrinter.TransformSpec(record)
    ready_message = k8s_util.FormatReadyMessage(record)
    if header:
      output.append(header)
    if status:
      output.append(status)
    output.append(' ')
    if labels:
      output.append(labels)
      output.append(' ')
    if spec:
      output.append(spec)
    if ready_message:
      output.append(ready_message)

    return output

  def Transform(self, record):
    """Transform a job into the output structure of marker classes."""
    fmt = cp.Lines(JobPrinter._formatOutput(record))
    return fmt


class TaskPrinter(cp.CustomPrinterBase):
  """Prints the run execution Task in a custom human-readable format.

  Format specific to Cloud Run jobs. Only available on Cloud Run commands
  that print tasks.
  """

  @staticmethod
  def TransformSpec(record):
    labels = [
        (
            'Task Timeout',
            FormatDurationShort(record.spec.timeoutSeconds)
            if record.spec.timeoutSeconds
            else None,
        ),
        (
            'Max Retries',
            '{}'.format(record.spec.maxRetries)
            if record.spec.maxRetries is not None
            else None,
        ),
        ('Service account', record.service_account),
        ('VPC access', k8s_util.GetVpcNetwork(record.annotations)),
        ('SQL connections', k8s_util.GetCloudSqlInstances(record.annotations)),
        (
            'Volumes',
            container_util.GetVolumes(record),
        ),
    ]
    return cp.Lines([container_util.GetContainers(record), cp.Labeled(labels)])

  @staticmethod
  def TransformStatus(record):
    status = [
        ('Running state', record.running_state),
    ]
    if record.last_exit_code is not None:
      status.extend([
          (
              'Last Attempt Result',
              cp.Labeled([
                  ('Exit Code', record.last_exit_code),
                  ('Message', record.last_exit_message),
              ]),
          ),
      ])
    return cp.Labeled(status)

  def Transform(self, record):
    """Transform a job into the output structure of marker classes."""
    return cp.Lines([
        k8s_util.BuildHeader(record),
        self.TransformStatus(record),
        ' ',
        self.TransformSpec(record),
        k8s_util.FormatReadyMessage(record),
    ])


class ExecutionPrinter(cp.CustomPrinterBase):
  """Prints the run Execution in a custom human-readable format.

  Format specific to Cloud Run jobs. Only available on Cloud Run commands
  that print executions.
  """

  @staticmethod
  def TransformSpec(record, record_for_annotations):
    """Transforms the execution spec into a custom human-readable format.

    Args:
      record: The execution or execution template to transform.
      record_for_annotations: The resource whose annotations should be used to
        extract Cloud Run feature settings. It should be an execution or a job.

    Returns:
      A custom printer Marker class for a list of lines.
    """
    breakglass_value = k8s_util.GetBinAuthzBreakglass(record_for_annotations)
    return cp.Lines([
        cp.Labeled([
            ('Tasks', record.spec.taskCount),
            (
                'Parallelism',
                record.parallelism if record.parallelism else 'No limit',
            ),
        ]),
        TaskPrinter.TransformSpec(record.template),
        cp.Labeled([
            (
                'Binary Authorization',
                k8s_util.GetBinAuthzPolicy(record_for_annotations),
            ),
            # pylint: disable=g-explicit-bool-comparison
            # Empty breakglass string is valid, space is used to force it
            # showing
            (
                'Breakglass Justification',
                ' ' if breakglass_value == '' else breakglass_value,
            ),
            (
                'Threat Detection',
                k8s_util.GetThreatDetectionEnabled(record_for_annotations),
            ),
        ]),
    ])

  @staticmethod
  def TransformStatus(record):
    if record.status is None:
      return ''
    lines = []
    if record.ready_condition['status'] is None:
      lines.append(
          '{} currently running'.format(
              _PluralizedWord('task', record.status.runningCount)
          )
      )
    lines.append(
        '{} completed successfully'.format(
            _PluralizedWord('task', record.status.succeededCount)
        )
    )
    if record.status.failedCount is not None and record.status.failedCount > 0:
      lines.append(
          '{} failed to complete'.format(
              _PluralizedWord('task', record.status.failedCount)
          )
      )
    if (
        record.status.cancelledCount is not None
        and record.status.cancelledCount > 0
    ):
      lines.append(
          '{} cancelled'.format(
              _PluralizedWord('task', record.status.cancelledCount)
          )
      )
    if (
        record.status.completionTime is not None
        and record.creation_timestamp is not None
    ):
      lines.append(
          'Elapsed time: '
          + ExecutionPrinter._elapsedTime(
              record.creation_timestamp, record.status.completionTime
          )
      )
    if record.status.logUri is not None:
      # adding a blank line before Log URI
      lines.append(' ')
      lines.append('Log URI: {}'.format(record.status.logUri))
    return cp.Lines(lines)

  @staticmethod
  def _elapsedTime(start, end):
    duration = datetime.timedelta(
        seconds=time_util.Strptime(end) - time_util.Strptime(start)
    ).seconds
    hours = duration // 3600
    duration = duration % 3600
    minutes = duration // 60
    seconds = duration % 60
    if hours > 0:
      # Only hours and minutes for short message
      return '{} and {}'.format(
          _PluralizedWord('hour', hours), _PluralizedWord('minute', minutes)
      )
    if minutes > 0:
      return '{} and {}'.format(
          _PluralizedWord('minute', minutes), _PluralizedWord('second', seconds)
      )
    return _PluralizedWord('second', seconds)

  @staticmethod
  def _formatOutput(record):
    output = []
    header = k8s_util.BuildHeader(record)
    status = ExecutionPrinter.TransformStatus(record)
    labels = k8s_util.GetLabels(record.labels)
    spec = ExecutionPrinter.TransformSpec(record, record)
    ready_message = k8s_util.FormatReadyMessage(record)
    if header:
      output.append(header)
    if status:
      output.append(status)
    output.append(' ')
    if labels:
      output.append(labels)
      output.append(' ')
    if spec:
      output.append(spec)
    if ready_message:
      output.append(ready_message)

    return output

  def Transform(self, record):
    """Transform a job into the output structure of marker classes."""
    fmt = cp.Lines(ExecutionPrinter._formatOutput(record))
    return fmt
