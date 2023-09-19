# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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

"""Bigtable views API helper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import json
import textwrap

from apitools.base.py import encoding
from apitools.base.py import exceptions as api_exceptions
from googlecloudsdk.api_lib.bigtable import util
from googlecloudsdk.api_lib.util import exceptions
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import edit
import six

CREATE_HELP = textwrap.dedent("""\
    To create a view, specify a JSON or YAML formatted representation
    of a valid view protobuf. Lines beginning with "#" are ignored.

    Example:
    {
      "subsetView":
      {
        "rowPrefixes": ["cm93MQ=="],
        "familySubsets":
        {
          "column_family_name":
          {
            "qualifiers":["Y29sdW1uX2E="],
            "qualifierPrefixes":["Y29sdW1uX3ByZWZpeDE="]
          }
        }
      },
      "deletionProtection": true
    }
  """)

UPDATE_HELP = textwrap.dedent("""\
    Please pecify a JSON or YAML formatted representation of the new view.
    Lines beginning with "#" are ignored.

    Example:
    {
      "subsetView":
      {
        "rowPrefixes": ["cm93MQ=="],
        "familySubsets":
        {
          "column_family_name":
          {
            "qualifiers":["Y29sdW1uX2E="],
            "qualifierPrefixes":["Y29sdW1uX3ByZWZpeDE="]
          }
        }
      },
      "deletionProtection": true
    }

    Current view:
  """)


def ModifyCreateViewRequest(unused_ref, args, req):
  """Parse argument and construct create view request.

  Args:
    unused_ref: the gcloud resource (unused).
    args: input arguments.
    req: the real request to be sent to backend service.

  Returns:
    req: the real request to be sent to backend service.
  """
  # If args.definition_file is provided, the content in the file will be
  # automatically parsed as req.view.
  if not args.definition_file:
    # If no definition_file is provided, EDITOR will be executed with a
    # commented prompt for the user to fill out the view definition.
    req.view = PromptForViewDefinition(is_create=True)

  # The name field should be ignored and omitted from the request as it is
  # taken from the command line.
  req.view.name = None

  # By specifying the request_id_field for the view resource in the declarative
  # yaml file, the req.viewId and the req.parent will be automatically mapped.

  return req


def PromptForViewDefinition(is_create, current_view=None):
  """Prompt user to fill out a JSON/YAML format representation of a View.

  Returns the parsed View proto message from user's response.

  Args:
    is_create: True if the prompt is for creating a view. False if the prompt is
      for updating a view.
    current_view: The current view definition. Only used in the update case to
      be included as part of the initial commented prompt.

  Returns:
    a View proto message with fields filled accordingly.

  Raises:
    ChildProcessError if the user did not save the temporary file.
    ChildProcessError if there is a problem running the editor.
    ValueError if the user's response does not follow YAML or JSON format.
    ValueError if the YAML/JSON object cannot be parsed as a valid View.
  """
  view_message_type = util.GetAdminMessages().View
  if is_create:
    help_text = BuildCreateViewFileContents()
  else:
    help_text = BuildUpdateViewFileContents(current_view)
  try:
    content = edit.OnlineEdit(help_text)
  except edit.NoSaveException:
    raise ChildProcessError("Edit aborted by user.")
  except edit.EditorException as e:
    raise ChildProcessError(
        "There was a problem applying your changes. [{0}].".format(e)
    )
  try:
    view_to_parse = yaml.load(content)
    view = encoding.PyValueToMessage(view_message_type, view_to_parse)
  except yaml.YAMLParseError as e:
    raise ValueError(
        "Provided response is not a properly formatted YAML or JSON file."
        " [{0}].".format(e)
    )
  except AttributeError as e:
    raise ValueError(
        "Provided response cannot be parsed as a valid View. [{0}].".format(e)
    )
  return view


def BuildCreateViewFileContents():
  """Builds the help text for creating a View as the initial file content."""
  buf = io.StringIO()
  for line in CREATE_HELP.splitlines():
    buf.write("#")
    if line:
      buf.write(" ")
    buf.write(line)
    buf.write("\n")
  buf.write("\n")
  return buf.getvalue()


def ModifyUpdateViewRequest(original_ref, args, req):
  """Parse argument and construct update view request.

  Args:
    original_ref: the gcloud resource.
    args: input arguments.
    req: the real request to be sent to backend service.

  Returns:
    req: the real request to be sent to backend service.
  """

  # If args.definition_file is provided, the content in the file will be
  # automatically parsed as req.view.
  if not args.definition_file:
    # If no definition_file is provided, EDITOR will be executed with a
    # commented prompt for the user to fill out the view definition.
    current_view = GetCurrentView(original_ref.RelativeName())
    req.view = PromptForViewDefinition(
        is_create=False, current_view=current_view
    )

  if req.view.subsetView is not None:
    req = AddFieldToUpdateMask("subset_view", req)
  if req.view.deletionProtection is not None:
    req = AddFieldToUpdateMask("deletion_protection", req)

  # The name field should be ignored and omitted from the request as it is
  # taken from the command line.
  req.view.name = None

  return req


def GetCurrentView(view_name):
  """Get the current view resource object given the view name."""
  client = util.GetAdminClient()
  request = util.GetAdminMessages().BigtableadminProjectsInstancesTablesViewsGetRequest(
      name=view_name
  )
  try:
    return client.projects_instances_tables_views.Get(request)
  except api_exceptions.HttpError as error:
    raise exceptions.HttpException(error)


def SerializeToJsonOrYaml(view, serialized_format="json"):
  """Serializes a view protobuf to either JSON or YAML."""
  view_dict = encoding.MessageToDict(view)
  if serialized_format == "json":
    return six.text_type(json.dumps(view_dict, indent=2))
  if serialized_format == "yaml":
    return six.text_type(yaml.dump(view_dict))


def BuildUpdateViewFileContents(current_view):
  """Builds the help text for updating an existing View."""
  buf = io.StringIO()
  for line in UPDATE_HELP.splitlines():
    buf.write("#")
    if line:
      buf.write(" ")
    buf.write(line)
    buf.write("\n")

  serialized_original_view = SerializeToJsonOrYaml(current_view)
  for line in serialized_original_view.splitlines():
    buf.write("#")
    if line:
      buf.write(" ")
    buf.write(line)
    buf.write("\n")
  buf.write("\n")
  return buf.getvalue()


def AddFieldToUpdateMask(field, req):
  """Adding a new field to the update mask of the UpdateViewRequest.

  Args:
    field: the field to be updated.
    req: the original UpdateViewRequest.

  Returns:
    req: the UpdateViewRequest with update mask refreshed.
  """
  update_mask = req.updateMask
  if update_mask:
    if update_mask.count(field) == 0:
      req.updateMask = update_mask + "," + field
  else:
    req.updateMask = field
  return req
