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
"""V2 Revision specific printer."""

from googlecloudsdk.command_lib.run.printers import k8s_object_printer_util as k8s_util
from googlecloudsdk.command_lib.run.printers.v2 import container_printer
from googlecloudsdk.command_lib.run.printers.v2 import printer_util
from googlecloudsdk.command_lib.run.printers.v2 import volume_printer
from googlecloudsdk.core.resource import custom_printer_base as cp
from googlecloudsdk.generated_clients.gapic_clients.run_v2.types import revision


REVISION_PRINTER_FORMAT = 'revision'


class RevisionPrinter(cp.CustomPrinterBase):
  """Prints the Run v2 Revision in a custom human-readable format.

  Format specific to Cloud Run revisions. Only available on Cloud Run
  commands that print worker revisions.
  """

  def Transform(self, record: revision.Revision):
    """Transform a revision into the output structure of marker classes."""
    fmt = cp.Lines([
        printer_util.BuildHeader(record, is_child_resource=True),
        k8s_util.GetLabels(record.labels),
        ' ',
        self.TransformSpec(record),
        printer_util.FormatReadyMessage(record),
    ])
    return fmt

  @staticmethod
  def TransformSpec(record: revision.Revision) -> cp.Lines:
    labels = [('Service account', record.service_account)]
    labels.extend([
        # TODO(b/366115709): add SQL connections printer.
        ('VPC access', printer_util.GetVpcNetwork(record.vpc_access)),
        ('CMEK', printer_util.GetCMEK(record.encryption_key)),
        ('Session Affinity', 'True' if record.session_affinity else ''),
        ('Volumes', volume_printer.GetVolumes(record.volumes)),
    ])
    return cp.Lines(
        [container_printer.GetContainers(record.containers), cp.Labeled(labels)]
    )
