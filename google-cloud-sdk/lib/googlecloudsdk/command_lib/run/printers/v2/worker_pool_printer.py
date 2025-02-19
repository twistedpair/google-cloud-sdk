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
"""V2 WorkerPool specific printer."""


from googlecloudsdk.command_lib.run import resource_name_conversion
from googlecloudsdk.command_lib.run.printers import k8s_object_printer_util as k8s_util
from googlecloudsdk.command_lib.run.printers.v2 import container_printer
from googlecloudsdk.command_lib.run.printers.v2 import instance_split_printer
from googlecloudsdk.command_lib.run.printers.v2 import printer_util
from googlecloudsdk.command_lib.run.printers.v2 import volume_printer
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.resource import custom_printer_base as cp
from googlecloudsdk.generated_clients.gapic_clients.run_v2.types import vendor_settings
from googlecloudsdk.generated_clients.gapic_clients.run_v2.types import worker_pool as worker_pool_objects
from googlecloudsdk.generated_clients.gapic_clients.run_v2.types import worker_pool_revision_template as revision_template_objects

WORKER_POOL_PRINTER_FORMAT = 'workerpool'


class WorkerPoolPrinter(cp.CustomPrinterBase):
  """Prints the Run v2 WorkerPool in a custom human-readable format.

  Format specific to Cloud Run worker pools. Only available on Cloud Run
  commands that print worker pools.
  """

  def _GetRevisionHeader(self, record: worker_pool_objects.WorkerPool):
    header = 'Unknown revision'
    if record.latest_created_revision:
      header = 'Revision {}'.format(
          resource_name_conversion.GetNameFromFullChildName(
              record.latest_created_revision
          )
      )
    return console_attr.GetConsoleAttr().Emphasize(header)

  def _TransformTemplate(
      self, record: revision_template_objects.WorkerPoolRevisionTemplate
  ):
    labels = [('Service account', record.service_account)]
    labels.extend([
        # TODO(b/366115709): add SQL connections printer.
        ('VPC access', printer_util.GetVpcNetwork(record.vpc_access)),
        ('CMEK', printer_util.GetCMEK(record.encryption_key)),
        ('Session Affinity', 'True' if record.session_affinity else ''),
        ('Volumes', volume_printer.GetVolumes(record.volumes)),
    ])
    return cp.Lines([
        container_printer.GetContainers(record.containers),
        cp.Labeled(labels),
    ])

  def _RevisionPrinters(self, record: worker_pool_objects.WorkerPool):
    """Adds printers for the revision."""
    return cp.Lines([
        self._GetRevisionHeader(record),
        k8s_util.GetLabels(record.template.labels),
        self._TransformTemplate(record.template),
    ])

  def _GetBinaryAuthorization(self, record: worker_pool_objects.WorkerPool):
    """Adds worker pool level values."""
    if record.binary_authorization is None:
      return None
    if record.binary_authorization.use_default:
      return 'Default'
    return record.binary_authorization.policy

  def _GetWorkerPoolSettings(self, record: worker_pool_objects.WorkerPool):
    """Adds worker pool level values."""
    labels = [
        cp.Labeled([
            ('Binary Authorization', self._GetBinaryAuthorization(record)),
        ])
    ]

    breakglass_value = record.binary_authorization.breakglass_justification
    if breakglass_value:
      # Show breakglass even if empty, but only if set. There's no skip_none
      # option so this the workaround.
      breakglass_label = cp.Labeled([
          ('Breakglass Justification', breakglass_value),
      ])
      breakglass_label.skip_empty = False
      labels.append(breakglass_label)
    description = record.description
    if description:
      description_label = cp.Labeled([
          ('Description', description),
      ])
      labels.append(description_label)
    scaling_mode = self._GetScalingMode(record)
    if scaling_mode:
      scaling_mode_label = cp.Labeled([
          ('Scaling', scaling_mode),
      ])
      labels.append(scaling_mode_label)
    return cp.Section(labels)

  def _GetScalingMode(self, record: worker_pool_objects.WorkerPool):
    """Returns the scaling mode of the worker pool."""
    scaling_mode = record.scaling.scaling_mode

    if scaling_mode == vendor_settings.WorkerPoolScaling.ScalingMode.MANUAL:
      instance_count = record.scaling.manual_instance_count
      return 'Manual (Instances: %s)' % instance_count
    else:
      instance_count = record.scaling.min_instance_count
      if record.scaling.max_instance_count:
        return 'Auto (Min: %s, Max: %s)' % (
            instance_count,
            record.scaling.max_instance_count,
        )
      return 'Auto (Min: %s)' % instance_count

  def Transform(self, record: worker_pool_objects.WorkerPool):
    """Transform a worker pool into the output structure of marker classes."""
    worker_pool_settings = self._GetWorkerPoolSettings(record)
    fmt = cp.Lines([
        printer_util.BuildHeader(record),
        k8s_util.GetLabels(record.labels),
        ' ',
        instance_split_printer.TransformWorkerPoolInstanceSplit(record),
        ' ',
        worker_pool_settings,
        (' ' if worker_pool_settings.WillPrintOutput() else ''),
        cp.Labeled([(
            printer_util.LastUpdatedMessage(record),
            self._RevisionPrinters(record),
        )]),
        printer_util.FormatReadyMessage(record),
    ])
    return fmt
