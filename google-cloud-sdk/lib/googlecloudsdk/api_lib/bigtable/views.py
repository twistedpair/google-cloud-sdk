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
import textwrap

from apitools.base.py import encoding
from googlecloudsdk.api_lib.bigtable import util
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import edit

HELP = textwrap.dedent("""\
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
    req.view = PromptForViewDefinition()

  # The name field should be ignored and omitted from the request as it is
  # taken from the command line.
  req.view.name = None

  # By specifying the request_id_field for the view resource in the declarative
  # yaml file, the req.viewId and the req.parent will be automatically mapped.

  return req


def PromptForViewDefinition():
  """Prompt user to fill out a JSON/YAML format representation of a View.

  Returns the parsed View proto message from user's response.

  Returns:
    a View proto message with fields filled accordingly.

  Raises:
    ChildProcessError if the user did not save the temporary file.
    ChildProcessError if there is a problem running the editor.
    ValueError if the user's response does not follow YAML or JSON format.
    ValueError if the YAML/JSON object cannot be parsed as a valid View.
  """
  view_message_type = util.GetAdminMessages().View
  try:
    content = edit.OnlineEdit(BuildCreateViewFileContents())
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
  for line in HELP.splitlines():
    buf.write("#")
    if line:
      buf.write(" ")
    buf.write(line)
    buf.write("\n")
  buf.write("\n")
  return buf.getvalue()
