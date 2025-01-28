# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Appliance offline import feature printer."""

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core.resource import custom_printer_base
from googlecloudsdk.core.resource import flattened_printer
from googlecloudsdk.core.resource import resource_transform


OFFLINE_IMPORT_PRINTER_FORMAT = "offlineImportFeature"


class OfflineImportPrinter(custom_printer_base.CustomPrinterBase):
  """Prints Offline Import feature fields in customized format."""

  MESSAGES = apis.GetMessagesModule("transferappliance", "v1alpha1")

  def Transform(self, resp):
    """Transforms Offline Import feature data into a customized format.

    Args:
      resp: Response object containing data for the offline import feature,
            including its status, bytes transferred, objects transferred,
            destination, end time, and any missing files.

    Example output:
      Status              : Completed with errors
      Bytes transferred   : 1.8 MiB of 2.5 MiB
      Objects transferred : 8 objects of 10 objects
      Destination         : example-bucket
      Start time          : June 10, 2024, 06:47 PM UTC
      End time            : March 12, 2024, 04:30 PM UTC
      Found Files         : gs://example-bucket/logs/found_files.log
      Missing Files       : gs://example-bucket/logs/failed_transfers.log
    """
    printer = flattened_printer.FlattenedPrinter()

    status = self._get_status_message(resp.offlineImportFeature)
    bytes_transferred = self._get_bytes_transferred(resp.offlineImportFeature)
    bytes_prepared = self._get_bytes_prepared(resp.offlineImportFeature)
    objects_transferred = self._get_objects_transferred(
        resp.offlineImportFeature
    )
    destination = self._get_destination(resp.offlineImportFeature)
    start_time = self._get_start_time(resp.offlineImportFeature)
    end_time = self._get_end_time(resp.offlineImportFeature)
    found_files = self._get_found_files(resp.offlineImportFeature)
    missing_files = self._get_missing_files(resp.offlineImportFeature)

    records = [
        {"Status              ": status},
        {"Bytes prepared      ": bytes_prepared},
        {"Bytes transferred   ": bytes_transferred},
        {"Objects transferred ": objects_transferred},
        {"Destination         ": destination},
        {"Start time          ": start_time},
        {"End time            ": end_time},
        {"Found Files         ": found_files},
        {"Missing Files       ": missing_files}
    ]

    for record in records:
      printer.AddRecord(record, delimit=False)

  def _get_status_message(self, offline_import_feature):
    state = self._get_value(
        offline_import_feature, "state"
    )
    if state is None:
      return "-"

    state_enum = self.MESSAGES.OfflineImportFeature.StateValueValuesEnum
    status_messages = {
        state_enum.STATE_UNSPECIFIED: "State unspecified",
        state_enum.DRAFT: "Draft",
        state_enum.ACTIVE: "Not Yet Started",
        state_enum.PREPARING: "Preparing data for transfer",
        state_enum.TRANSFERRING: "Transferring data to customer bucket",
        state_enum.VERIFYING: "Verifying Transferred data",
        state_enum.COMPLETED: "Successfully Completed",
        state_enum.CANCELLED: "Cancelled",
    }

    # Handle completion status
    if (
        state
        == self.MESSAGES.OfflineImportFeature.StateValueValuesEnum.COMPLETED
    ):
      return self._check_completion_status(offline_import_feature)

    return status_messages.get(state, "-")

  def _check_completion_status(self, offline_import_feature):
    objects_found = self._get_value(
        offline_import_feature, "transferResults.objectsFoundCount"
    )
    objects_copied = self._get_value(
        offline_import_feature, "transferResults.objectsCopiedCount"
    )

    if objects_found is None or objects_copied is None:
      return "-"

    return (
        "Completed with errors"
        if objects_found > objects_copied
        else "Successfully Completed"
    )

  def _get_bytes_prepared(self, offline_import_feature):
    bytes_prepared = self._get_value(
        offline_import_feature, "preparedBytesCount"
    )
    bytes_allocated = self._get_value(
        offline_import_feature, "allocatedBytesCount"
    )

    if bytes_prepared is None or bytes_allocated is None:
      return "-"

    return (
        f"{resource_transform.TransformSize(bytes_prepared)}"
        f" of {resource_transform.TransformSize(bytes_allocated)}"
    )

  def _get_bytes_transferred(self, offline_import_feature):
    bytes_copied = self._get_value(
        offline_import_feature, "transferResults.bytesCopiedCount"
    )
    bytes_found = self._get_value(
        offline_import_feature, "transferResults.bytesFoundCount"
    )

    if bytes_copied is None or bytes_found is None:
      return "-"

    return (
        f"{resource_transform.TransformSize(offline_import_feature.transferResults.bytesCopiedCount)}"
        f" of {resource_transform.TransformSize(offline_import_feature.transferResults.bytesFoundCount)}"
    )

  def _get_objects_transferred(self, offline_import_feature):
    objects_copied = self._get_value(
        offline_import_feature, "transferResults.objectsCopiedCount"
    )
    objects_found = self._get_value(
        offline_import_feature, "transferResults.objectsFoundCount"
    )

    if objects_copied is None or objects_found is None:
      return "-"

    return (
        f"{offline_import_feature.transferResults.objectsCopiedCount} of "
        f"{offline_import_feature.transferResults.objectsFoundCount} objects"
    )

  def _get_destination(self, offline_import_feature):
    destination = self._get_value(
        offline_import_feature, "destination.outputBucket"
    )
    return destination if destination else "-"

  def _get_start_time(self, offline_import_feature):
    start_time = self._get_value(
        offline_import_feature, "transferResults.startTime"
    )
    if start_time:
      return resource_transform.TransformDate(
          start_time, format="%B %d, %Y, %I:%M %p %Z"
      )
    return "-"

  def _get_end_time(self, offline_import_feature):
    end_time = self._get_value(
        offline_import_feature, "transferResults.endTime"
    )
    if end_time:
      return resource_transform.TransformDate(
          end_time, format="%B %d, %Y, %I:%M %p %Z"
      )
    return "-"

  def _get_found_files(self, offline_import_feature):
    found_files = self._get_value(
        offline_import_feature, "transferResults.applianceFilesInfoUri"
    )
    return found_files if found_files else "-"

  def _get_missing_files(self, offline_import_feature):
    missing_files = self._get_value(
        offline_import_feature, "transferResults.errorLog"
    )
    return missing_files if missing_files else "-"

  def _get_value(self, obj, attribute):
    """Responsible for returning an attribute (might be nested) from an object."""
    attributes = attribute.split(".")
    for attribute in attributes:
      obj = getattr(obj, attribute, None)
      if obj is None:
        return None
    return obj
