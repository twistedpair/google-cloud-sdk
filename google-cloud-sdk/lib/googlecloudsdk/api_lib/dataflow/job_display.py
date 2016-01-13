# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Facility for displaying information about a Job message to a user.
"""

from googlecloudsdk.api_lib.dataflow import time_util


class DisplayInfo(object):
  """Information about a job displayed in command output.

  Fields:
    job_id: the job ID
    job_name: the job name
    job_type: one of 'batch', 'streaming'
    status: string representing the current job status
    creation_time: in the form yyyy-mm-dd hh:mm:ss
    status_time: in the form yyyy-mm-dd hh:mm:ss
  """

  def __init__(self, job, dataflow_messages):
    self.job_id = job.id
    self.job_name = job.name
    self.job_type = DisplayInfo._JobTypeForJob(job.type, dataflow_messages)
    self.status = DisplayInfo._StatusForJob(job.currentState, dataflow_messages)
    self.status_time = time_util.FormatTimestamp(job.currentStateTime)
    self.creation_time = time_util.FormatTimestamp(job.createTime)

  @staticmethod
  def _JobTypeForJob(job_type, dataflow_messages):
    """Return a string describing the job type.

    Args:
      job_type: The job type enum
      dataflow_messages: dataflow_messages package
    Returns:
      string describing the job type
    """
    type_value_enum = dataflow_messages.Job.TypeValueValuesEnum
    value_map = {
        type_value_enum.JOB_TYPE_BATCH: 'Batch',
        type_value_enum.JOB_TYPE_STREAMING: 'Streaming',
    }
    return value_map.get(job_type, 'Unknown')

  @staticmethod
  def _StatusForJob(job_state, dataflow_messages):
    """Return a string describing the job state.

    Args:
      job_state: The job state enum
      dataflow_messages: dataflow_messages package
    Returns:
      string describing the job state
    """
    state_value_enum = dataflow_messages.Job.CurrentStateValueValuesEnum
    value_map = {
        state_value_enum.JOB_STATE_CANCELLED: 'Cancelled',
        state_value_enum.JOB_STATE_DONE: 'Done',
        state_value_enum.JOB_STATE_FAILED: 'Failed',
        state_value_enum.JOB_STATE_RUNNING: 'Running',
        state_value_enum.JOB_STATE_STOPPED: 'Stopped',
        state_value_enum.JOB_STATE_UPDATED: 'Updated',
    }
    return value_map.get(job_state, 'Unknown')
