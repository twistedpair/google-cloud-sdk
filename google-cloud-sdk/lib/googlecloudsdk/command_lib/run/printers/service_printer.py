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
"""Service-specific printer."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json

from googlecloudsdk.api_lib.run import service
from googlecloudsdk.command_lib.run import threat_detection_util as crtd_util
from googlecloudsdk.command_lib.run.printers import k8s_object_printer_util as k8s_util
from googlecloudsdk.command_lib.run.printers import revision_printer
from googlecloudsdk.command_lib.run.printers import traffic_printer
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.resource import custom_printer_base as cp

SERVICE_PRINTER_FORMAT = 'service'
PRESET_ANNOTATION = 'run.googleapis.com/presets'


class ServicePrinter(cp.CustomPrinterBase):
  """Prints the run Service in a custom human-readable format.

  Format specific to Cloud Run services. Only available on Cloud Run commands
  that print services.
  """

  with_presets = False

  def _GetRevisionHeader(self, record):
    header = ''
    if record.status is None:
      header = 'Unknown revision'
    else:
      header = 'Revision {}'.format(record.status.latestCreatedRevisionName)
    return console_attr.GetConsoleAttr().Emphasize(header)

  def _RevisionPrinters(self, record):
    """Adds printers for the revision."""
    manual_scaling_enabled = False
    if (
        record.annotations.get(service.SERVICE_SCALING_MODE_ANNOTATION, '')
        == 'manual'
    ):
      manual_scaling_enabled = True
    return cp.Lines([
        self._GetPresetInfo(record) if self.with_presets else '',
        self._GetRevisionHeader(record),
        k8s_util.GetLabels(record.template.labels),
        revision_printer.RevisionPrinter.TransformSpec(
            record.template, manual_scaling_enabled
        ),
    ])

  def _GetServiceSettings(self, record):
    """Adds service-level values."""
    labels = [
        cp.Labeled([
            ('Binary Authorization', k8s_util.GetBinAuthzPolicy(record)),
        ])
    ]

    scaling_mode = self._GetScalingMode(record)
    if scaling_mode:
      scaling_mode_label = cp.Labeled([
          ('Scaling', scaling_mode),
      ])
      labels.append(scaling_mode_label)

    breakglass_value = k8s_util.GetBinAuthzBreakglass(record)
    if breakglass_value is not None:
      # Show breakglass even if empty, but only if set. There's no skip_none
      # option so this the workaround.
      breakglass_label = cp.Labeled([
          ('Breakglass Justification', breakglass_value),
      ])
      breakglass_label.skip_empty = False
      labels.append(breakglass_label)
    description = k8s_util.GetDescription(record)
    if description is not None:
      description_label = cp.Labeled([
          ('Description', description),
      ])
      labels.append(description_label)

    labels.append(
        cp.Labeled([
            (
                'Threat Detection',
                crtd_util.PrintThreatDetectionState(
                    record.threat_detection_state
                ),
            ),
        ])
    )
    return cp.Section(labels)

  def _GetPresetInfo(self, record):
    """Adds preset information if available."""
    preset_annotation = record.annotations.get(PRESET_ANNOTATION)
    if preset_annotation:
      try:
        presets_list = json.loads(preset_annotation)
        if isinstance(presets_list, list) and presets_list:
          preset_sections = []
          for p in presets_list:
            if isinstance(p, dict) and p.get('type'):
              preset_type = p.get('type')
              params = []
              for key, value in p.items():
                if key == 'config' and isinstance(value, dict):
                  for config_key, config_value in value.items():
                    params.append((config_key, config_value))
                elif key != 'type':
                  params.append((key, value))

              preset_sections.append((preset_type, cp.Labeled(params)))

          if preset_sections:
            return cp.Labeled([('Presets', cp.Table(preset_sections))])
      except (ValueError, TypeError):
        # Silently ignore if the annotation is not valid JSON.
        pass
    return ''

  def BuildHeader(self, record):
    return k8s_util.BuildHeader(record)

  def _GetScalingMode(self, record):
    """Returns the scaling mode of the service."""
    scaling_mode = record.annotations.get(
        service.SERVICE_SCALING_MODE_ANNOTATION, ''
    )

    if scaling_mode == 'manual':
      instance_count = record.annotations.get(
          service.MANUAL_INSTANCE_COUNT_ANNOTATION, ''
      )
      return 'Manual (Instances: %s)' % instance_count
    else:
      min_instance_count = record.annotations.get(
          service.SERVICE_MIN_SCALE_ANNOTATION, '0'
      )
      max_instance_count = record.annotations.get(
          service.SERVICE_MAX_SCALE_ANNOTATION, ''
      )
      if max_instance_count:
        return 'Auto (Min: %s, Max: %s)' % (
            min_instance_count,
            max_instance_count,
        )
      return 'Auto (Min: %s)' % min_instance_count

  def Transform(self, record):
    """Transform a service into the output structure of marker classes."""
    service_settings = self._GetServiceSettings(record)
    lines = [
        self.BuildHeader(record),
        k8s_util.GetLabels(record.labels),
    ]
    lines.extend([
        ' ',
        traffic_printer.TransformRouteFields(record),
        ' ',
        service_settings,
        (' ' if service_settings.WillPrintOutput() else ''),
        cp.Labeled([(
            k8s_util.LastUpdatedMessage(record),
            self._RevisionPrinters(record),
        )]),
        k8s_util.FormatReadyMessage(record),
    ])
    return cp.Lines(lines)


class ServicePrinterAlpha(ServicePrinter):
  """Prints the run Service in a custom human-readable format."""

  with_presets = True


class MultiRegionServicePrinter(ServicePrinter):
  """Prints the run MultiRegionService in a custom human-readable format."""

  def BuildHeader(self, record):
    return k8s_util.BuildHeader(record, is_multi_region=True)
