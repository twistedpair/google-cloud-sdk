# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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

"""Revision-specific printer."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.api_lib.run import revision
from googlecloudsdk.command_lib.run.printers import container_and_volume_printer_util as container_util
from googlecloudsdk.command_lib.run.printers import k8s_object_printer_util as k8s_util
from googlecloudsdk.core.resource import custom_printer_base as cp
import six


REVISION_PRINTER_FORMAT = 'revision'
EXECUTION_ENV_VALS = {'gen1': 'First Generation', 'gen2': 'Second Generation'}


class RevisionPrinter(cp.CustomPrinterBase):
  """Prints the run Revision in a custom human-readable format.

  Format specific to Cloud Run revisions. Only available on Cloud Run commands
  that print revisions.
  """

  def Transform(self, record):
    """Transform a service into the output structure of marker classes."""
    fmt = cp.Lines([
        k8s_util.BuildHeader(record),
        k8s_util.GetLabels(record.labels),
        ' ',
        self.TransformSpec(record),
        k8s_util.FormatReadyMessage(record)])
    return fmt

  @staticmethod
  def GetTimeout(record):
    if record.timeout is not None:
      return '{}s'.format(record.timeout)
    return None

  @staticmethod
  def GetMinInstances(record):
    return record.annotations.get(revision.MIN_SCALE_ANNOTATION, '')

  @staticmethod
  def GetMaxInstances(record):
    return record.annotations.get(revision.MAX_SCALE_ANNOTATION, '')

  @staticmethod
  def GetExecutionEnv(record):
    execution_env_value = k8s_util.GetExecutionEnvironment(record)
    if execution_env_value in EXECUTION_ENV_VALS:
      return EXECUTION_ENV_VALS[execution_env_value]
    return execution_env_value

  @staticmethod
  def TransformSpec(record):
    limits = container_util.GetLimits(record)
    return cp.Labeled([
        ('Image', record.UserImage()),
        ('Command', ' '.join(record.container.command)),
        ('Args', ' '.join(record.container.args)),
        ('Port', ' '.join(
            six.text_type(p.containerPort) for p in record.container.ports)),
        ('Memory', limits['memory']),
        ('CPU', limits['cpu']),
        ('Service account', record.spec.serviceAccountName),
        ('Env vars', container_util.GetUserEnvironmentVariables(record)),
        ('Secrets', container_util.GetSecrets(record)),
        ('Config Maps', container_util.GetConfigMaps(record)),
        ('Concurrency', record.concurrency),
        ('Min Instances', RevisionPrinter.GetMinInstances(record)),
        ('Max Instances', RevisionPrinter.GetMaxInstances(record)),
        ('SQL connections', k8s_util.GetCloudSqlInstances(record)),
        ('Timeout', RevisionPrinter.GetTimeout(record)),
        ('VPC connector', k8s_util.GetVpcConnector(record)),
        ('Execution Environment', RevisionPrinter.GetExecutionEnv(record)),
    ])
