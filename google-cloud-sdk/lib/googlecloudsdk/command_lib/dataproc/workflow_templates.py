# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Utilities for dataproc workflow template add-job CLI."""
from apitools.base.protorpclite import messages as apitools_messages
from apitools.base.py import encoding

from googlecloudsdk.api_lib.dataproc import util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions as gcloud_exceptions
from googlecloudsdk.command_lib.util import labels_util
from googlecloudsdk.core import exceptions as core_exceptions

import yaml


def AddConfigFileArgs(parser):
  """Flag that stores the location of YAML file to update workflow template."""
  # TODO(b/68668244): add link to YAML file syntax documentation.
  parser.add_argument(
      '--config-file',
      required=True,
      help='The config file that stores the cluster, jobs and labels details.')


def AddWorkflowTemplatesArgs(parser):
  """Register flags for this command."""
  labels_util.AddCreateLabelsFlags(parser)
  parser.add_argument(
      '--workflow-template', required=True,
      help='The dataproc workflow template ID.')

  parser.add_argument(
      '--step-id',
      required=True,
      type=str,
      help='The step ID of the job in the workflow template.')

  parser.add_argument(
      '--start-after',
      metavar='STEP_ID',
      type=arg_parsers.ArgList(element_type=str, min_length=1),
      help='(Optional) List of step IDs to start this job after.')


def CreateWorkflowTemplateOrderedJob(args, dataproc):
  """Create an ordered job for workflow template."""
  ordered_job = dataproc.messages.OrderedJob(stepId=args.step_id)
  if args.start_after:
    ordered_job.prerequisiteStepIds = args.start_after
  return ordered_job


def AddJobToWorkflowTemplate(args, dataproc, ordered_job):
  """Add an ordered job to the workflow template."""
  template = util.ParseWorkflowTemplates(args.workflow_template, dataproc)

  workflow_template = dataproc.GetRegionsWorkflowTemplate(
      template, args.version)

  jobs = workflow_template.jobs if workflow_template.jobs is not None else []
  jobs.append(ordered_job)

  workflow_template.jobs = jobs

  response = dataproc.client.projects_regions_workflowTemplates.Update(
      workflow_template)
  return response


def ConfigureOrderedJob(messages, job, args):
  """Add type-specific job configuration to job message."""
  # Parse labels (if present)
  labels = labels_util.UpdateLabels(
      None, messages.OrderedJob.LabelsValue,
      labels_util.GetUpdateLabelsDictFromArgs(args), None)
  job.labels = labels


def ParseYamlOrJsonToWorkflowTemplate(file_path, message_type):
  """Create a WorkflowTemplate protorpc.Message from a YAML or JSON file.

  Args:
    file_path: Path to the YAML or JSON file.
    message_type: Workflow template message type to convert YAML to.
  Returns:
    a protorpc.Message of type message_type filled in from the input
    YAML or JSON file.
  Raises:
    BadFileException if the YAML or JSON file is malformed.
  """
  try:
    with open(file_path) as config_file:
      template_to_parse = yaml.safe_load(config_file)
  except EnvironmentError:
    # EnvironmnetError is parent of IOError, OSError and WindowsError.
    # Raised when file does not exist or can't be opened/read.
    raise core_exceptions.Error('Unable to read file {0}'.format(file_path))
  except (yaml.scanner.ScannerError, yaml.parser.ParserError) as e:
    # Raised when the YAML file is not properly formatted.
    raise gcloud_exceptions.BadFileException(
        'File [{0}] is not a properly formatted YAML or JSON file. {1}'.format(
            file_path, str(e)))
  try:
    workflow_template = encoding.PyValueToMessage(message_type,
                                                  template_to_parse)
  except (AttributeError) as e:
    # Raised when the input file is not properly formatted YAML or JSON file.
    raise gcloud_exceptions.BadFileException(
        'File [{0}] is not a properly formatted YAML or JSON file. {1}'.format(
            file_path, str(e)))
  except (apitools_messages.DecodeError) as e:
    # DecodeError is raised when a field is badly formatted
    raise core_exceptions.Error('File [{0}] is not properly formatted. {1}'
                                .format(file_path, str(e)))
  return workflow_template
