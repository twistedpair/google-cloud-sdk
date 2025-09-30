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

import collections
from typing import Sequence, Optional

from apitools.base.py import list_pager

from googlecloudsdk.api_lib.storage import errors
from googlecloudsdk.api_lib.storage.gcs_json import client as gcs_json_client
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.core import properties


# Backend has a limit of 500.
PAGE_SIZE = 500
_CSV_PARQUET_ERROR_MESSGE = 'CSV options cannot be set with parquet.'


def _get_unescaped_ascii(string):
  """Returns the ASCII string unescaping any escaped characters."""
  return string.encode('ascii').decode(
      'unicode-escape') if string is not None else None


def _get_parent_string(
    project,
    location,
):
  return 'projects/{}/locations/{}'.format(project, location.lower())


def _get_parent_string_from_bucket(bucket):
  gcs_client = gcs_json_client.JsonClient()
  bucket_resource = gcs_client.get_bucket(bucket)
  return _get_parent_string(
      bucket_resource.metadata.projectNumber,
      bucket_resource.metadata.location.lower(),
  )


# Tuple to hold the CsvOptions or ParquetOptions. Only one of the fields should
# be set.
ReportFormatOptions = collections.namedtuple(
    'ReportFormatOptions', ('csv', 'parquet')
)


class InsightsApi:
  """Client for Storage Insights API."""

  def __init__(self):
    super(InsightsApi, self).__init__()
    self.client = core_apis.GetClientInstance('storageinsights', 'v1')
    self.messages = core_apis.GetMessagesModule('storageinsights', 'v1')

  def create_dataset_config(
      self,
      dataset_config_name: str,
      location: str,
      destination_project: str,
      organization_number: int,
      retention_period: int,
      activity_data_retention_period: Optional[int] = None,
      organization_scope: bool = False,
      source_projects_list: Optional[Sequence[int]] = None,
      source_folders_list: Optional[Sequence[int]] = None,
      include_buckets_prefix_regex_list: Optional[Sequence[str]] = None,
      exclude_buckets_prefix_regex_list: Optional[Sequence[str]] = None,
      include_buckets_name_list: Optional[Sequence[str]] = None,
      exclude_buckets_name_list: Optional[Sequence[str]] = None,
      include_source_locations: Optional[Sequence[str]] = None,
      exclude_source_locations: Optional[Sequence[str]] = None,
      auto_add_new_buckets: bool = False,
      identity_type: str = None,
      description: str = None,
  ):
    """Creates a dataset config.

    Args:
      dataset_config_name: Name for the dataset config being created.
      location: The location where insights data will be stored in a GCS
        managed BigQuery instance.
      destination_project: The project in which the dataset config is
        being created and by extension the insights data will be stored.
      organization_number: Organization number of the organization to
        which all source projects / folders must belong.
      retention_period: No of days for which insights data is to be
        retained in BigQuery instance.
      activity_data_retention_period: No of days for which activity data is to
        be retained in BigQuery instance. If not set, retention period will be
        used by the API.
      organization_scope: If True, Insights data will be collected for
        all resources in the given organization.
      source_projects_list: List of source project numbers. Insights
        data is to be collected for buckets that belong to these projects.
      source_folders_list: List of source folder numbers. Insights
        data is to be collected for buckets that belong to these folders.
      include_buckets_prefix_regex_list: List of bucket prefix regex
        patterns which are to be included for insights processing from the
        source projects. We can either use included or excluded bucket
        parameters.
      exclude_buckets_prefix_regex_list: List of bucket prefix regex
        patterns which are to be excluded from insights processing from the
        source projects. We can either use included or excluded bucket
        parameters.
      include_buckets_name_list: List of bucket names which are to
        be included for insights processing from the source projects. We can
        either use included or excluded bucket parameters.
      exclude_buckets_name_list: List of bucket names which are to
        be excluded from insights processing from the source projects. We can
        either use included or excluded bucket parameters.
      include_source_locations: List of bucket locations which are
        to be included for insights processing from the source projects. We can
        either use included or excluded location parameters.
      exclude_source_locations: List of bucket locations which are
        to be excluded from insights processing from the source projects. We can
        either use included or excluded location parameters.
      auto_add_new_buckets: If True, auto includes any new buckets added
        to source projects that satisfy the include/exclude criterias.
      identity_type: Option for how permissions need to be setup for a
        given dataset config. Default option is IDENTITY_TYPE_PER_CONFIG.
      description: Human readable description text for the given dataset
        config.

    Returns:
      An instance of Operation message
    """
    if identity_type is not None:
      identity_type_enum = self.messages.Identity.TypeValueValuesEnum(
          identity_type.upper()
      )
      identity_type = self.messages.Identity(type=identity_type_enum)
    else:
      identity_type = self.messages.Identity(
          type=self.messages.Identity.TypeValueValuesEnum.IDENTITY_TYPE_PER_CONFIG
      )

    source_projects = self.messages.SourceProjects(
        projectNumbers=source_projects_list
    ) if source_projects_list else None

    source_folders = self.messages.SourceFolders(
        folderNumbers=source_folders_list
    ) if source_folders_list else None

    dataset_config = self.messages.DatasetConfig(
        description=description,
        identity=identity_type,
        includeNewlyCreatedBuckets=auto_add_new_buckets,
        name=dataset_config_name,
        organizationNumber=organization_number,
        retentionPeriodDays=retention_period,
        sourceProjects=source_projects,
        sourceFolders=source_folders,
        organizationScope=organization_scope if organization_scope else None,
    )

    if activity_data_retention_period is not None:
      dataset_config.activityDataRetentionPeriodDays = (
          activity_data_retention_period
      )

    # Exclude and Include options are marked as mutex flags,
    # hence we can make the below assumption about only being available
    if exclude_buckets_name_list or exclude_buckets_prefix_regex_list:
      excluded_storage_buckets = [
          self.messages.CloudStorageBucket(bucketName=excluded_name)
          for excluded_name in exclude_buckets_name_list or []
      ]
      excluded_storage_buckets += [
          self.messages.CloudStorageBucket(bucketPrefixRegex=excluded_regex)
          for excluded_regex in exclude_buckets_prefix_regex_list or []
      ]
      dataset_config.excludeCloudStorageBuckets = (
          self.messages.CloudStorageBuckets(
              cloudStorageBuckets=excluded_storage_buckets
          )
      )

    if include_buckets_name_list or include_buckets_prefix_regex_list:
      included_storage_buckets = [
          self.messages.CloudStorageBucket(bucketName=included_name)
          for included_name in include_buckets_name_list or []
      ]
      included_storage_buckets += [
          self.messages.CloudStorageBucket(bucketPrefixRegex=included_regex)
          for included_regex in include_buckets_prefix_regex_list or []
      ]
      dataset_config.includeCloudStorageBuckets = (
          self.messages.CloudStorageBuckets(
              cloudStorageBuckets=included_storage_buckets
          )
      )

    if exclude_source_locations:
      dataset_config.excludeCloudStorageLocations = (
          self.messages.CloudStorageLocations(
              locations=exclude_source_locations
          )
      )

    if include_source_locations:
      dataset_config.includeCloudStorageLocations = (
          self.messages.CloudStorageLocations(
              locations=include_source_locations
          )
      )

    create_request = self.messages.StorageinsightsProjectsLocationsDatasetConfigsCreateRequest(
        datasetConfig=dataset_config,
        datasetConfigId=dataset_config_name,
        parent=_get_parent_string(destination_project, location),
    )
    return self.client.projects_locations_datasetConfigs.Create(create_request)

  def create_dataset_config_link(self, dataset_config_relative_name):
    """Creates the dataset config link."""
    request = self.messages.StorageinsightsProjectsLocationsDatasetConfigsLinkDatasetRequest(
        name=dataset_config_relative_name
    )
    return self.client.projects_locations_datasetConfigs.LinkDataset(request)

  def delete_dataset_config(self, dataset_config_relative_name):
    """Deletes the dataset config."""
    request = self.messages.StorageinsightsProjectsLocationsDatasetConfigsDeleteRequest(
        name=dataset_config_relative_name
    )
    return self.client.projects_locations_datasetConfigs.Delete(request)

  def delete_dataset_config_link(self, dataset_config_relative_name):
    """Deletes the dataset config link."""
    request = self.messages.StorageinsightsProjectsLocationsDatasetConfigsUnlinkDatasetRequest(
        name=dataset_config_relative_name
    )
    return self.client.projects_locations_datasetConfigs.UnlinkDataset(request)

  def get_dataset_config(self, dataset_config_relative_name):
    """Gets the dataset config."""
    return self.client.projects_locations_datasetConfigs.Get(
        self.messages.StorageinsightsProjectsLocationsDatasetConfigsGetRequest(
            name=dataset_config_relative_name
        )
    )

  def list_dataset_config(self, location=None, page_size=None):
    """Lists the dataset configs.

    Args:
      location (str): The location where insights data will be stored in a GCS
        managed BigQuery instance.
      page_size (int|None): Number of items per request to be returned.

    Returns:
      List of dataset configs.
    """
    if location is not None:
      parent = _get_parent_string(
          properties.VALUES.core.project.Get(), location
      )
    else:
      parent = _get_parent_string(properties.VALUES.core.project.Get(), '-')

    return list_pager.YieldFromList(
        self.client.projects_locations_datasetConfigs,
        self.messages.StorageinsightsProjectsLocationsDatasetConfigsListRequest(
            parent=parent
        ),
        batch_size=page_size if page_size is not None else PAGE_SIZE,
        batch_size_attribute='pageSize',
        field='datasetConfigs',
    )

  def _get_dataset_config_update_mask(
      self,
      organization_scope: bool = None,
      source_projects: Optional[Sequence[int]] = None,
      source_folders: Optional[Sequence[int]] = None,
      include_buckets_name_list: Optional[Sequence[str]] = None,
      include_buckets_prefix_regex_list: Optional[Sequence[str]] = None,
      exclude_buckets_name_list: Optional[Sequence[str]] = None,
      exclude_buckets_prefix_regex_list: Optional[Sequence[str]] = None,
      include_source_locations: Optional[Sequence[str]] = None,
      exclude_source_locations: Optional[Sequence[str]] = None,
      auto_add_new_buckets: bool = None,
      retention_period: int = None,
      activity_data_retention_period: Optional[int] = None,
      description: str = None,
  ):
    """Returns the update_mask list."""
    update_mask = []

    mask_conditions = [
        ('organizationScope', organization_scope),
        ('sourceProjects', source_projects is not None),
        ('sourceFolders', source_folders is not None),
        (
            'includeCloudStorageBuckets',
            include_buckets_name_list is not None
            or include_buckets_prefix_regex_list is not None,
        ),
        (
            'excludeCloudStorageBuckets',
            exclude_buckets_name_list is not None
            or exclude_buckets_prefix_regex_list is not None,
        ),
        ('includeCloudStorageLocations', include_source_locations is not None),
        ('excludeCloudStorageLocations', exclude_source_locations is not None),
        ('includeNewlyCreatedBuckets', auto_add_new_buckets is not None),
        ('retentionPeriodDays', retention_period is not None),
        (
            'activityDataRetentionPeriodDays',
            activity_data_retention_period is not None,
        ),
        ('description', description is not None),
    ]

    for mask, condition in mask_conditions:
      if condition:
        update_mask.append(mask)

    return update_mask

  def update_dataset_config(
      self,
      dataset_config_relative_name,
      organization_scope: bool = None,
      source_projects_list: Optional[Sequence[int]] = None,
      source_folders_list: Optional[Sequence[int]] = None,
      include_buckets_name_list: Optional[Sequence[str]] = None,
      include_buckets_prefix_regex_list: Optional[Sequence[str]] = None,
      exclude_buckets_name_list: Optional[Sequence[str]] = None,
      exclude_buckets_prefix_regex_list: Optional[Sequence[str]] = None,
      include_source_locations: Optional[Sequence[str]] = None,
      exclude_source_locations: Optional[Sequence[str]] = None,
      auto_add_new_buckets: bool = None,
      retention_period: int = None,
      activity_data_retention_period: Optional[int] = None,
      description: str = None,
  ):
    """Updates the dataset config.

    Args:
      dataset_config_relative_name: The relative name of the dataset
        config to be modified.
      organization_scope: If True, Insights data will be collected for
        all resources in the given organization. If this field is Empty/None,
        Either the sourceProjects or the sourceFolders must be set to update
        the scope.
      source_projects_list: List of source project numbers. Insights
        data is to be collected for buckets that belong to these projects. If
        this field is Empty/None, Either the organizationScope will be True or
        the sourceFolders must be set to update the scope.
      source_folders_list: List of source folder IDs. Insights
        data is to be collected for buckets that belong to these organisational
        folders. If this field is Empty/None, Either the organizationScope will
        be True or the sourceProjects must be set to update the scope.
      include_buckets_name_list: Optional list of bucket names which
        are to be included for insights processing from the source projects. Can
        either use included or excluded bucket parameters.
      include_buckets_prefix_regex_list: Optional list of bucket
        prefix regex patterns which are to be included for insights processing
        from the source projects. Can either use included or excluded bucket
        parameters.
      exclude_buckets_name_list: Optional list of bucket names which
        are to be excluded from insights processing from the source projects.
        Can either use included or excluded bucket parameters.
      exclude_buckets_prefix_regex_list: Optional list of bucket
        prefix regex patterns which are to be excluded from insights processing
        from the source projects. Can either use included or excluded bucket
        parameters.
      include_source_locations: Optional list of bucket locations
        which are to be included for insights processing from the source
        projects. Can either use included or excluded location parameters.
      exclude_source_locations: Optional list of bucket locations
        which are to be excluded from insights processing from the source
        projects. Can either use included or excluded location parameters.
      auto_add_new_buckets: If True, auto includes any new buckets added
        to source projects that satisfy the include/exclude criterias.
      retention_period: No of days for which insights data is to be
        retained in BigQuery instance.
      activity_data_retention_period: No of days for which activity data is to
        be retained in BigQuery instance.
      description: Human readable description text for the given dataset
        config.

    Returns:
      An instance of Operation message.
    """

    # Only the fields present in the mask will be updated.
    update_mask = self._get_dataset_config_update_mask(
        organization_scope=organization_scope,
        source_projects=source_projects_list,
        source_folders=source_folders_list,
        include_buckets_name_list=include_buckets_name_list,
        include_buckets_prefix_regex_list=include_buckets_prefix_regex_list,
        exclude_buckets_name_list=exclude_buckets_name_list,
        exclude_buckets_prefix_regex_list=exclude_buckets_prefix_regex_list,
        include_source_locations=include_source_locations,
        exclude_source_locations=exclude_source_locations,
        auto_add_new_buckets=auto_add_new_buckets,
        retention_period=retention_period,
        activity_data_retention_period=activity_data_retention_period,
        description=description,
    )

    if not update_mask:
      raise errors.InsightApiError(
          'Nothing to update for dataset config: {}'.format(
              dataset_config_relative_name
          )
      )

    source_projects = self.messages.SourceProjects(
        projectNumbers=source_projects_list
    ) if source_projects_list is not None else None

    source_folders = self.messages.SourceFolders(
        folderNumbers=source_folders_list
    ) if source_folders_list is not None else None

    dataset_config = self.messages.DatasetConfig(
        retentionPeriodDays=retention_period,
        description=description,
        sourceProjects=source_projects,
        sourceFolders=source_folders,
        includeNewlyCreatedBuckets=auto_add_new_buckets,
    )

    if organization_scope:
      dataset_config.organizationScope = True

    if activity_data_retention_period is not None:
      dataset_config.activityDataRetentionPeriodDays = (
          activity_data_retention_period
      )

    # Exclude and Include options are marked as mutex flags,
    # hence can make the below assumption about only one of the options being
    # available.
    if exclude_buckets_name_list or exclude_buckets_prefix_regex_list:
      excluded_storage_buckets = [
          self.messages.CloudStorageBucket(bucketName=excluded_name)
          for excluded_name in exclude_buckets_name_list or []
      ]
      excluded_storage_buckets += [
          self.messages.CloudStorageBucket(bucketPrefixRegex=excluded_regex)
          for excluded_regex in exclude_buckets_prefix_regex_list or []
      ]
      dataset_config.excludeCloudStorageBuckets = (
          self.messages.CloudStorageBuckets(
              cloudStorageBuckets=excluded_storage_buckets
          )
      )
    elif include_buckets_name_list or include_buckets_prefix_regex_list:
      included_storage_buckets = [
          self.messages.CloudStorageBucket(bucketName=included_name)
          for included_name in include_buckets_name_list or []
      ]
      included_storage_buckets += [
          self.messages.CloudStorageBucket(bucketPrefixRegex=included_regex)
          for included_regex in include_buckets_prefix_regex_list or []
      ]
      dataset_config.includeCloudStorageBuckets = (
          self.messages.CloudStorageBuckets(
              cloudStorageBuckets=included_storage_buckets
          )
      )

    if exclude_source_locations:
      dataset_config.excludeCloudStorageLocations = (
          self.messages.CloudStorageLocations(
              locations=exclude_source_locations
          )
      )

    if include_source_locations:
      dataset_config.includeCloudStorageLocations = (
          self.messages.CloudStorageLocations(
              locations=include_source_locations
          )
      )

    request = self.messages.StorageinsightsProjectsLocationsDatasetConfigsPatchRequest(
        name=dataset_config_relative_name,
        datasetConfig=dataset_config,
        updateMask=','.join(update_mask),
    )
    return self.client.projects_locations_datasetConfigs.Patch(request)

  def _get_report_format_options(
      self, csv_separator, csv_delimiter, csv_header, parquet
  ):
    """Returns ReportFormatOptions instance."""
    if parquet:
      parquet_options = self.messages.ParquetOptions()
      if csv_header or csv_delimiter or csv_separator:
        raise errors.GcsApiError('CSV options cannot be set with parquet.')
      csv_options = None
    else:
      parquet_options = None
      unescaped_separator = _get_unescaped_ascii(csv_separator)
      csv_options = self.messages.CSVOptions(
          delimiter=csv_delimiter,
          headerRequired=csv_header,
          recordSeparator=unescaped_separator,
      )
    return ReportFormatOptions(
        csv=csv_options,
        parquet=parquet_options,
    )

  def create_inventory_report(
      self,
      source_bucket,
      destination_url,
      metadata_fields=None,
      start_date=None,
      end_date=None,
      frequency=None,
      csv_separator=None,
      csv_delimiter=None,
      csv_header=None,
      parquet=None,
      display_name=None,
  ):
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
      parquet (bool): If True, set the parquet options.
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
            destinationPath=destination_url.resource_name),
        storageFilters=self.messages.CloudStorageFilters(
            bucket=source_bucket))

    report_format_options = self._get_report_format_options(
        csv_separator, csv_delimiter, csv_header, parquet)

    report_config = self.messages.ReportConfig(
        csvOptions=report_format_options.csv,
        parquetOptions=report_format_options.parquet,
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
      if destination.resource_name is not None:
        filter_list.append(
            'objectMetadataReportOptions.storageDestinationOptions.'
            'destinationPath="{}"'.format(destination.resource_name))
    if filter_list:
      return ' AND '.join(filter_list)
    else:
      return None

  def list_inventory_reports(
      self, source_bucket=None, destination=None, location=None, page_size=None
  ):
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

  def get_inventory_report(self, report_config_name):
    """Gets the report config."""
    return self.client.projects_locations_reportConfigs.Get(
        self.messages.StorageinsightsProjectsLocationsReportConfigsGetRequest(
            name=report_config_name))

  def delete_inventory_report(self, report_config_name, force=False):
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
      storage_destination_message = (
          self.messages.CloudStorageDestinationOptions(
              bucket=destination_url.bucket_name,
              destinationPath=destination_url.resource_name,
          )
      )
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

  def _get_report_format_options_and_update_mask(
      self, csv_separator, csv_delimiter, csv_header, parquet):
    """Returns a tuple of ReportFormatOptions and update_mask list."""
    report_format_options = self._get_report_format_options(
        csv_separator, csv_delimiter, csv_header, parquet)
    update_mask = []
    if report_format_options.parquet is not None:
      update_mask.append('parquetOptions')
    else:
      if csv_delimiter is not None:
        update_mask.append('csvOptions.delimiter')
      if csv_header is not None:
        update_mask.append('csvOptions.headerRequired')
      if csv_separator is not None:
        update_mask.append('csvOptions.recordSeparator')
    return (report_format_options, update_mask)

  def update_inventory_report(
      self,
      report_config_name,
      destination_url=None,
      metadata_fields=None,
      start_date=None,
      end_date=None,
      frequency=None,
      csv_separator=None,
      csv_delimiter=None,
      csv_header=None,
      parquet=None,
      display_name=None,
  ):
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
      parquet (bool): If True, set the parquet options.
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

    report_format_options, report_format_mask = (
        self._get_report_format_options_and_update_mask(
            csv_separator, csv_delimiter, csv_header, parquet))

    # Only the fields present in the mask will be updated.
    update_mask = (
        frequency_update_mask + metadata_update_mask + report_format_mask)

    if display_name is not None:
      update_mask.append('displayName')

    if not update_mask:
      raise errors.CloudApiError(
          'Nothing to update for report config: {}'.format(report_config_name))

    report_config = self.messages.ReportConfig(
        csvOptions=report_format_options.csv,
        parquetOptions=report_format_options.parquet,
        displayName=display_name,
        frequencyOptions=frequency_options,
        objectMetadataReportOptions=object_metadata_report_options)
    request = (
        self.messages.StorageinsightsProjectsLocationsReportConfigsPatchRequest(
            name=report_config_name,
            reportConfig=report_config,
            updateMask=','.join(update_mask),
        )
    )
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

  def cancel_operation(self, operation_name):
    self.client.projects_locations_operations.Cancel(
        self.messages.StorageinsightsProjectsLocationsOperationsCancelRequest(
            name=operation_name
        )
    )

  def get_operation(self, operation_name):
    return self.client.projects_locations_operations.Get(
        self.messages.StorageinsightsProjectsLocationsOperationsGetRequest(
            name=operation_name
        )
    )

  def list_operations(self, parent_resource_name):
    request = (
        self.messages.StorageinsightsProjectsLocationsOperationsListRequest(
            name=parent_resource_name,
        )
    )
    return list_pager.YieldFromList(
        self.client.projects_locations_operations,
        request,
        batch_size_attribute='pageSize',
        field='operations',
    )
