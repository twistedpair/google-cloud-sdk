# -*- coding: utf-8 -*- #
# Copyright 2024 Google Inc. All Rights Reserved.
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
"""util functions for dataprocgdc."""

import time

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.console import progress_tracker
import six


DATAPROCGDC_API_NAME = 'dataprocgdc'
VERSION_MAP = {
    base.ReleaseTrack.ALPHA: 'v1alpha1',
    base.ReleaseTrack.GA: 'v1',
}


def WaitForSparkAppTermination(
    self,
    dataprocgdc_client,
    application_path,
    application_id,
    goal_state,
    spark_app,
    dataproc_poll_period_s=10,
):
  """Poll dataproc GDC spark application until terminal state is reached.

  Args:
    self: The self object.
    dataprocgdc_client: wrapper for dataproc gdc resources.
    application_path: the path for spark application.
    application_id: The id of spark application.
    goal_state: The desired state of the spark application.
    spark_app: The spark application which is being polled.
    dataproc_poll_period_s: delay in seconds between the polling API calls.

  Returns:
    sparkApp: The final value of spark application.

  Raises:
    Error: if the spark application finishes with an error.
  """
  api_version = VERSION_MAP.get(self.ReleaseTrack())
  messages = apis.GetMessagesModule(DATAPROCGDC_API_NAME, api_version)
  get_req = messages.DataprocgdcProjectsLocationsServiceInstancesSparkApplicationsGetRequest(
      name=application_path
  )
  last_spark_app_poll_time = 0
  now = time.time()
  wait_display = progress_tracker.ProgressTracker(
      'Waiting for Spark app completion', autotick=True
  )
  with wait_display:
    while True:
      regular_spark_app_poll = (
          now >= last_spark_app_poll_time + dataproc_poll_period_s
      )

      if regular_spark_app_poll:
        last_spark_app_poll_time = now
        try:
          spark_app = dataprocgdc_client.projects_locations_serviceInstances_sparkApplications.Get(
              get_req
          )
        except apitools_exceptions.HttpError as error:
          log.warning(
              'Get Spark Application failed:\n{}'.format(six.text_type(error))
          )
          if IsClientHttpException(error):
            raise
      if spark_app.state in [
          messages.SparkApplication.StateValueValuesEnum.CANCELLED,
          messages.SparkApplication.StateValueValuesEnum.SUCCEEDED,
          messages.SparkApplication.StateValueValuesEnum.FAILED,
      ]:
        break
      now = time.time()

  state = spark_app.state
  if state is goal_state:
    return spark_app
  if state is messages.SparkApplication.StateValueValuesEnum.FAILED:
    raise exceptions.Error(
        'Spark Application [{0}] failed.'.format(application_id)
    )
  if state is messages.SparkApplication.StateValueValuesEnum.CANCELLED:
    raise exceptions.Error(
        'Spark Application [{0}] was cancelled.'.format(application_id)
    )


def IsClientHttpException(http_exception):
  """Returns true if the http exception given is an HTTP 4xx error."""
  return http_exception.status_code >= 400 and http_exception.status_code < 500
