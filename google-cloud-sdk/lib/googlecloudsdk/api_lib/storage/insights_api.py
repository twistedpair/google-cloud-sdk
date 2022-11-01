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

from googlecloudsdk.api_lib.storage import errors
from googlecloudsdk.api_lib.storage import gcs_api
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.core import properties


# Backend has a limit of 500.
PAGE_SIZE = 500


def _get_unescaped_ascii(string):
  """Returns the ASCII string unescaping any escaped characters."""
  return string.encode('ascii').decode(
      'unicode-escape') if string is not None else None


def _get_parent_string(project, location):
  return 'projects/{}/locations/{}'.format(project, location.lower())


def _get_parent_string_from_bucket(bucket):
  gcs_client = gcs_api.GcsApi()
  bucket_resource = gcs_client.get_bucket(bucket)
  return _get_parent_string(bucket_resource.metadata.projectNumber,
                            bucket_resource.metadata.location.lower())


class InsightsApi:
  """Client for Storage Insights API."""

  def __init__(self):
    super(InsightsApi, self).__init__()
    self.client = core_apis.GetClientInstance('storageinsights', 'v1')
    self.messages = core_apis.GetMessagesModule('storageinsights', 'v1')

  def _get_csv_message(self, csv_separator, csv_delimiter, csv_header):
    unescaped_separator = _get_unescaped_ascii(csv_separator)
    return self.messages.CSVOptions(
        delimiter=csv_delimiter,
        headerRequired=csv_header,
        recordSeparator=unescaped_separator)

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
        csvOptions=self._get_csv_message(
            csv_separator, csv_delimiter, csv_header),
        displayName=display_name,
        frequencyOptions=frequency_options,
        objectMetadataReportOptions=object_metadata_report_options)
    create_request = self.messages.StorageinsightsProjectsLocationsReportConfigsCreateRequest(
        parent=_get_parent_string_from_bucket(source_bucket),
        reportConfig=report_config)
    return self.client.projects_locations_reportConfigs.Create(
        create_request)

  def _get_filters_for_list(self, source_bucket, destination):
    """Returns the filter string used for list API call."""
    filter_list = []
    if source_bucket is not None:
      filter_list.append(
          'objectMetadataReportOptions.storageFilters.bucket="{}"'.format(
              source_bucket.bucket_name))
    # TODO(b/255962994): Not used currently. Will be tested when we bring
    # back destination support.
    if destination is not None:
      filter_list.append(
          'objectMetadataReportOptions.storageDestinationOptions.'
          'bucket="{}"'.format(destination.bucket_name))
      if destination.object_name is not None:
        filter_list.append(
            'objectMetadataReportOptions.storageDestinationOptions.'
            'destinationPath="{}"'.format(destination.object_name))
    if filter_list:
      return ' AND '.join(filter_list)
    else:
      return None

  def list(self,
           source_bucket=None,
           destination=None,
           location=None,
           page_size=None):
    """Lists the report configs.

    Args:
      source_bucket (storage_url.CloudUrl): Source bucket for which reports will
        be generated.
      destination (storage_url.CloudUrl): The destination url where the
        generated reports will be stored.
      location (str): The location for which the report configs should be
        listed.
      page_size (int|None): Number of items per request to be returend.

    Returns:
      List of Report configs.
    """
    if location is not None:
      parent = _get_parent_string(properties.VALUES.core.project.Get(),
                                  location)
    else:
      parent = _get_parent_string_from_bucket(
          source_bucket.bucket_name
          if source_bucket is not None else destination.bucket_name)
    return list_pager.YieldFromList(
        self.client.projects_locations_reportConfigs,
        self.messages.StorageinsightsProjectsLocationsReportConfigsListRequest(
            parent=parent,
            filter=self._get_filters_for_list(source_bucket, destination)),
        batch_size=page_size if page_size is not None else PAGE_SIZE,
        batch_size_attribute='pageSize',
        field='reportConfigs')

  def get(self, report_config_name):
    """Gets the report config."""
    return self.client.projects_locations_reportConfigs.Get(
        self.messages.StorageinsightsProjectsLocationsReportConfigsGetRequest(
            name=report_config_name))

  def delete(self, report_config_name, force=False):
    """Deletes the report config."""
    request = (
        self.messages
        .StorageinsightsProjectsLocationsReportConfigsDeleteRequest(
            name=report_config_name, force=force))
    return self.client.projects_locations_reportConfigs.Delete(request)

  def _get_frequency_options_and_update_mask(self, start_date, end_date,
                                             frequency):
    """Returns a tuple of messages.FrequencyOptions and update_mask list."""
    update_mask = []
    if start_date is not None:
      start_date_message = self.messages.Date(
          year=start_date.year, month=start_date.month, day=start_date.day)
      update_mask.append('frequencyOptions.startDate')
    else:
      start_date_message = None
    if end_date is not None:
      end_date_message = self.messages.Date(
          year=end_date.year, month=end_date.month, day=end_date.day)
      update_mask.append('frequencyOptions.endDate')
    else:
      end_date_message = None
    if frequency is not None:
      frequency_message = getattr(
          self.messages.FrequencyOptions.FrequencyValueValuesEnum,
          frequency.upper())
      update_mask.append('frequencyOptions.frequency')
    else:
      frequency_message = None
    return (
        self.messages.FrequencyOptions(
            startDate=start_date_message,
            endDate=end_date_message,
            frequency=frequency_message),
        update_mask)

  def _get_metadata_options_and_update_mask(self, metadata_fields,
                                            destination_url):
    """Returns a tuple of messages.ObjectMetadataReportOptions and update_mask."""
    update_mask = []
    if metadata_fields:
      update_mask.append('objectMetadataReportOptions.metadataFields')
    if destination_url is not None:
      storage_destination_message = self.messages.CloudStorageDestinationOptions(
          bucket=destination_url.bucket_name,
          destinationPath=destination_url.object_name)
      update_mask.append(
          'objectMetadataReportOptions.storageDestinationOptions.bucket')
      update_mask.append(
          'objectMetadataReportOptions.storageDestinationOptions'
          '.destinationPath')
    else:
      storage_destination_message = None
    return (self.messages.ObjectMetadataReportOptions(
        metadataFields=metadata_fields,
        storageDestinationOptions=storage_destination_message), update_mask)

  def _get_csv_options_and_update_mask(self, csv_separator, csv_delimiter,
                                       csv_header):
    """Returns a tuple of messages.CSVOptions and update_mask list."""
    update_mask = []
    if csv_delimiter is not None:
      update_mask.append('csvOptions.delimiter')
    if csv_header is not None:
      update_mask.append('csvOptions.headerRequired')
    if csv_separator is not None:
      update_mask.append('csvOptions.recordSeparator')
    return (
        self._get_csv_message(csv_separator, csv_delimiter, csv_header),
        update_mask)

  def update(self,
             report_config_name,
             destination_url=None,
             metadata_fields=None,
             start_date=None,
             end_date=None,
             frequency=None,
             csv_separator=None,
             csv_delimiter=None,
             csv_header=None,
             display_name=None):
    """Updates a report config.

    Args:
      report_config_name (str): The name of the report config to be modified.
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
    frequency_options, frequency_update_mask = (
        self._get_frequency_options_and_update_mask(
            start_date, end_date, frequency))
    object_metadata_report_options, metadata_update_mask = (
        self._get_metadata_options_and_update_mask(
            metadata_fields, destination_url))
    csv_options, csv_update_mask = self._get_csv_options_and_update_mask(
        csv_separator, csv_delimiter, csv_header)

    # Only the fields present in the mask will be updated.
    update_mask = frequency_update_mask + metadata_update_mask + csv_update_mask

    if display_name is not None:
      update_mask.append('displayName')

    if not update_mask:
      raise errors.CloudApiError(
          'Nothing to update for report config: {}'.format(report_config_name))

    report_config = self.messages.ReportConfig(
        csvOptions=csv_options,
        displayName=display_name,
        frequencyOptions=frequency_options,
        objectMetadataReportOptions=object_metadata_report_options)
    request = self.messages.StorageinsightsProjectsLocationsReportConfigsPatchRequest(
        name=report_config_name,
        reportConfig=report_config,
        updateMask=','.join(update_mask))
    return self.client.projects_locations_reportConfigs.Patch(request)

  def list_report_details(self, report_config_name, page_size=None):
    """Lists the report details."""
    return list_pager.YieldFromList(
        self.client.projects_locations_reportConfigs_reportDetails,
        self.messages
        .StorageinsightsProjectsLocationsReportConfigsReportDetailsListRequest(
            parent=report_config_name),
        batch_size=page_size if page_size is not None else PAGE_SIZE,
        batch_size_attribute='pageSize',
        field='reportDetails')

  def get_report_details(self, report_config_name):
    return self.client.projects_locations_reportConfigs_reportDetails.Get(
        self.messages
        .StorageinsightsProjectsLocationsReportConfigsReportDetailsGetRequest(
            name=report_config_name))
