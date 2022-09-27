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
"""Client for interacting with Storage Insights."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager

from googlecloudsdk.api_lib.storage import gcs_api
from googlecloudsdk.api_lib.util import apis as core_apis


class InsightsApi:
  """Client for Storage Insights API."""

  def __init__(self):
    super(InsightsApi, self).__init__()
    self.client = core_apis.GetClientInstance('storageinsights', 'v1alpha1')
    self.messages = core_apis.GetMessagesModule('storageinsights', 'v1alpha1')

  def _get_parent_string(self, bucket):
    gcs_client = gcs_api.GcsApi()
    bucket_resource = gcs_client.get_bucket(bucket)
    return 'projects/{}/locations/{}'.format(
        bucket_resource.metadata.projectNumber,
        bucket_resource.metadata.location.lower())

  def create(self,
             source_bucket,
             destination_url,
             metadata_fields=None,
             start_date=None,
             end_date=None,
             frequency=None,
             csv_separator=None,
             csv_delimiter=None,
             csv_header=None,
             display_name=None):
    """Creates a report config.

    Args:
      source_bucket (str): Source bucket name for which reports will be
        generated.
      destination_url (storage_url.CloudUrl): The destination url where the
        generated reports will be stored.
      metadata_fields (list[str]): Fields to be included in the report.
      start_date (datetime.datetime.date): The date to start generating reports.
      end_date (datetime.datetime.date): The date after which to stop generating
        reports.
      frequency (str): Can be either DAILY or WEEKLY.
      csv_separator (str): The character used to separate the records in the
        CSV file.
      csv_delimiter (str): The delimiter that separates the fields in the CSV
        file.
      csv_header (bool): If True, include the headers in the CSV file.
      display_name (str): Display name for the report config.

    Returns:
      The created ReportConfig object.
    """
    frequency_options = self.messages.FrequencyOptions(
        startDate=self.messages.Date(
            year=start_date.year, month=start_date.month, day=start_date.day),
        endDate=self.messages.Date(
            year=end_date.year, month=end_date.month, day=end_date.day),
        frequency=getattr(
            self.messages.FrequencyOptions.FrequencyValueValuesEnum,
            frequency.upper()))
    object_metadata_report_options = self.messages.ObjectMetadataReportOptions(
        metadataFields=metadata_fields,
        storageDestinationOptions=self.messages.CloudStorageDestinationOptions(
            bucket=destination_url.bucket_name,
            destinationPath=destination_url.object_name),
        storageFilters=self.messages.CloudStorageFilters(
            bucket=source_bucket))

    report_config = self.messages.ReportConfig(
        csvOptions=self.messages.CSVOptions(
            delimiter=csv_delimiter,
            headerRequired=csv_header,
            recordSeparator=csv_separator),
        displayName=display_name,
        frequencyOptions=frequency_options,
        objectMetadataReportOptions=object_metadata_report_options)
    create_request = self.messages.StorageinsightsProjectsLocationsReportConfigsCreateRequest(
        parent=self._get_parent_string(source_bucket),
        reportConfig=report_config)
    return self.client.projects_locations_reportConfigs.Create(
        create_request)

  def _get_filters_for_list(self, source_bucket, destination):
    """Returns the filter string used for list API call."""
    filter_list = []
    if source_bucket is not None:
      filter_list.append(
          'objectMetadataReportOptions.storageFilters.bucket:{}'.format(
              source_bucket.bucket_name))
    if destination is not None:
      filter_list.append(
          'objectMetadataReportOptions.storageDestinationOptions.'
          'bucket:{}'.format(destination.bucket_name))
      if destination.object_name is not None:
        filter_list.append(
            'objectMetadataReportOptions.storageDestinationOptions.'
            'destinationPath:{}'.format(destination.object_name))
    if filter_list:
      return ' AND '.join(filter_list)
    else:
      return None

  def list(self, source_bucket=None, destination=None):
    """Lists the report configs.

    Args:
      source_bucket (storage_url.CloudUrl): Source bucket for which reports will
        be generated.
      destination (storage_url.CloudUrl): The destination url where the
        generated reports will be stored.

    Returns:
      List of Report configs.
    """
    return list_pager.YieldFromList(
        self.client.projects_locations_reportConfigs,
        self.messages.StorageinsightsProjectsLocationsReportConfigsListRequest(
            parent=self._get_parent_string(
                source_bucket.bucket_name
                if source_bucket is not None else destination.bucket_name),
            filter=self._get_filters_for_list(source_bucket, destination)),
        field='reportConfigs',
        batch_size_attribute=None)

