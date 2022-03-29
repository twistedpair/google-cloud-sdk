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

from googlecloudsdk.command_lib.run.printers import container_and_volume_printer_util as container_util
from googlecloudsdk.command_lib.run.printers import k8s_object_printer_util as k8s_util
from googlecloudsdk.core.resource import custom_printer_base as cp

EXECUTION_PRINTER_FORMAT = 'execution'
JOB_PRINTER_FORMAT = 'job'
TASK_PRINTER_FORMAT = 'task'


def _PluralizedWord(word, count):
  return '{count} {word}{plural}'.format(
      count=count or 0, word=word, plural='' if count == 1 else 's')


class JobPrinter(cp.CustomPrinterBase):
  """Prints the run Job in a custom human-readable format.

  Format specific to Cloud Run jobs. Only available on Cloud Run commands
  that print jobs.
  """

  @staticmethod
  def TransformSpec(record):
    limits = container_util.GetLimits(record.template)
    breakglass_value = k8s_util.GetBinAuthzBreakglass(record)
    return cp.Labeled([
        ('Image', record.template.UserImage()),
        ('Tasks', record.task_count),
        ('Command', ' '.join(record.template.container.command)),
        ('Args', ' '.join(record.template.container.args)),
        ('Binary Authorization', k8s_util.GetBinAuthzPolicy(record)),
        # pylint: disable=g-explicit-bool-comparison
        # Empty breakglass string is valid, space is used to force it showing
        ('Breakglass Justification',
         ' ' if breakglass_value == '' else breakglass_value),
        ('Memory', limits['memory']),
        ('CPU', limits['cpu']),
        ('Task Timeout', '{}s'.format(record.template.spec.timeoutSeconds)
         if record.template.spec.timeoutSeconds else None),
        ('Max Retries', record.max_retries),
        ('Parallelism',
         record.parallelism if record.parallelism else 'No limit'),
        ('Service account', record.template.service_account),
        ('Env vars',
         container_util.GetUserEnvironmentVariables(record.template)),
        ('Secrets', container_util.GetSecrets(record.template)),
        ('VPC connector', k8s_util.GetVpcConnector(record)),
        ('SQL connections', k8s_util.GetCloudSqlInstances(record)),
    ])

  @staticmethod
  def TransformStatus(record):
    if record.status is None:
      return ''
    lines = [
        'Executed {}'.format(
            _PluralizedWord('time', record.status.executionCount))
    ]
    if record.status.latestCreatedExecution is not None:
      lines.append('Last executed {} with execution {}'.format(
          record.status.latestCreatedExecution.creationTimestamp,
          record.status.latestCreatedExecution.name))
    return cp.Lines(lines)

  def Transform(self, record):
    """Transform a job into the output structure of marker classes."""
    fmt = cp.Lines([
        k8s_util.BuildHeader(record),
        self.TransformStatus(record), ' ',
        k8s_util.GetLabels(record.labels), ' ',
        self.TransformSpec(record),
        k8s_util.FormatReadyMessage(record)
    ])
    return fmt


class TaskPrinter(cp.CustomPrinterBase):
  """Prints the run execution Task in a custom human-readable format.

  Format specific to Cloud Run jobs. Only available on Cloud Run commands
  that print tasks.
  """

  @staticmethod
  def TransformSpec(record):
    limits = container_util.GetLimits(record)
    return cp.Labeled([
        ('Image', record.image),
        ('Command', ' '.join(record.container.command)),
        ('Args', ' '.join(record.container.args)),
        ('Memory', limits['memory']),
        ('CPU', limits['cpu']),
        ('Timeout', '{}s'.format(record.spec.timeoutSeconds)
         if record.spec.timeoutSeconds else None),
        ('Max Retries', record.spec.maxRetries),
        ('Service account', record.service_account),
        ('Env vars', container_util.GetUserEnvironmentVariables(record)),
        ('Secrets', container_util.GetSecrets(record)),
        ('VPC connector', k8s_util.GetVpcConnector(record)),
        ('SQL connections', k8s_util.GetCloudSqlInstances(record)),
    ])

  @staticmethod
  def TransformStatus(record):
    return cp.Lines(['Running state: {}'.format(record.running_state)])

  def Transform(self, record):
    """Transform a job into the output structure of marker classes."""
    return cp.Lines([
        k8s_util.BuildHeader(record),
        self.TransformStatus(record), ' ',
        self.TransformSpec(record),
        k8s_util.FormatReadyMessage(record)
    ])


class ExecutionPrinter(cp.CustomPrinterBase):
  """Prints the run Execution in a custom human-readable format.

  Format specific to Cloud Run jobs. Only available on Cloud Run commands
  that print executions.
  """

  @staticmethod
  def TransformSpec(record):
    limits = container_util.GetLimits(record.template)
    breakglass_value = k8s_util.GetBinAuthzBreakglass(record)
    return cp.Labeled([
        ('Image', record.template.UserImage()),
        ('Tasks', record.spec.taskCount),
        ('Command', ' '.join(record.template.container.command)),
        ('Args', ' '.join(record.template.container.args)),
        ('Binary Authorization', k8s_util.GetBinAuthzPolicy(record)),
        # pylint: disable=g-explicit-bool-comparison
        # Empty breakglass string is valid, space is used to force it showing
        ('Breakglass Justification',
         ' ' if breakglass_value == '' else breakglass_value),
        ('Memory', limits['memory']),
        ('CPU', limits['cpu']),
        ('Task Timeout', '{}s'.format(record.template.spec.timeoutSeconds)
         if record.template.spec.timeoutSeconds else None),
        ('Max Retries', record.template.spec.maxRetries),
        ('Parallelism', record.parallelism),
        ('Service account', record.template.service_account),
        ('Env vars',
         container_util.GetUserEnvironmentVariables(record.template)),
        ('Secrets', container_util.GetSecrets(record.template)),
        ('VPC connector', k8s_util.GetVpcConnector(record)),
        ('SQL connections', k8s_util.GetCloudSqlInstances(record)),
    ])

  @staticmethod
  def TransformStatus(record):
    if record.status is None:
      return ''
    lines = []
    if record.ready_condition['status'] is None:
      lines.append('{} currently running'.format(
          _PluralizedWord('task', record.status.runningCount)))
    lines.append('{} completed successfully'.format(
        _PluralizedWord('task', record.status.succeededCount)))
    if record.status.failedCount is not None and record.status.failedCount > 0:
      lines.append('{} failed to complete'.format(
          _PluralizedWord('task', record.status.failedCount)))
    return cp.Lines(lines)

  def Transform(self, record):
    """Transform a job into the output structure of marker classes."""
    fmt = cp.Lines([
        k8s_util.BuildHeader(record),
        self.TransformStatus(record), ' ',
        k8s_util.GetLabels(record.labels), ' ',
        self.TransformSpec(record),
        k8s_util.FormatReadyMessage(record)
    ])
    return fmt
