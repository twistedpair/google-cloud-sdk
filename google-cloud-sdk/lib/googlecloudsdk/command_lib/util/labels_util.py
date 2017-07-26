# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Module for labels API support."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as calliope_exceptions


CREATE_LABELS_FLAG = base.Argument(
    '--labels',
    metavar='KEY=VALUE',
    type=arg_parsers.ArgDict(),
    action=arg_parsers.UpdateAction,
    help='A list of label KEY=VALUE pairs to add.')

UPDATE_LABELS_FLAG = base.Argument(
    '--update-labels',
    metavar='KEY=VALUE',
    type=arg_parsers.ArgDict(),
    action=arg_parsers.UpdateAction,
    help="""\
    A list of label KEY=VALUE pairs to update. If a label exists its value
    is modified, otherwise a new label is created.""")

REMOVE_LABELS_FLAG = base.Argument(
    '--remove-labels',
    metavar='KEY',
    type=arg_parsers.ArgList(),
    action=arg_parsers.UpdateAction,
    help="""\
    A list of label keys to remove. If a label does not exist it is
    silently ignored.""")


def AddCreateLabelsFlags(parser):
  """Adds create command labels flags to an argparse parser.

  Args:
    parser: The argparse parser to add the flags to.
  """
  CREATE_LABELS_FLAG.AddToParser(parser)


def AddUpdateLabelsFlags(parser):
  """Adds update command labels flags to an argparse parser.

  Args:
    parser: The argparse parser to add the flags to.
  """
  UPDATE_LABELS_FLAG.AddToParser(parser)
  REMOVE_LABELS_FLAG.AddToParser(parser)


def GetUpdateLabelsDictFromArgs(args):
  """Returns the update labels dict from the parsed args.

  Args:
    args: The parsed args.

  Returns:
    The update labels dict from the parsed args.
  """
  return args.labels if hasattr(args, 'labels') else args.update_labels


def GetRemoveLabelsListFromArgs(args):
  """Returns the remove labels list from the parsed args.

  Args:
    args: The parsed args.

  Returns:
    The remove labels list from the parsed args.
  """
  return args.remove_labels


def UpdateLabels(labels, labels_value, update_labels=None, remove_labels=None):
  """Returns a labels update proto based on the current state plus edits.

  Args:
    labels: The current label values proto.
    labels_value: The LabelsValue proto message class.
    update_labels: A dict of label key=value edits.
    remove_labels: A list of labels keys to remove.

  Returns:
    A new labels request proto representing the update and remove edits, None
    if there are no changes.
  """
  # Return None if there are no edits.
  if not update_labels and not remove_labels:
    return None

  new_labels = {}
  existing_labels = {}

  # Add pre-existing labels.
  if labels:
    for label in labels.additionalProperties:
      new_labels[label.key] = label.value
      existing_labels[label.key] = label.value

  # Add label updates and/or addtions.
  if update_labels:
    new_labels.update(update_labels)

  # Remove labels if requested.
  if remove_labels:
    for key in remove_labels:
      new_labels.pop(key, None)

  # Return None if the edits are a no-op.
  if new_labels == existing_labels:
    return None

  # Return the labels proto with all edits applied, sorted for reproducability.
  return labels_value(additionalProperties=[
      labels_value.AdditionalProperty(key=key, value=value)
      for key, value in sorted(new_labels.iteritems())])


def GetAndValidateOpsFromArgs(parsed_args):
  """Validates and returns labels specific args.

  At least one of --update-labels, --labels or --remove-labels must be present.

  Args:
    parsed_args: The parsed args.
  Returns:
    (update_labels, remove_labels)
    update_labels contains values from --labels and --update-labels flags
    respectively.
    remove_labels contains values from --remove-labels flag
  Raise:
    RequiredArgumentException if all labels arguments are absent.
  """
  update_labels = GetUpdateLabelsDictFromArgs(parsed_args)
  remove_labels = GetRemoveLabelsListFromArgs(parsed_args)
  if update_labels is None and remove_labels is None:
    raise calliope_exceptions.RequiredArgumentException(
        'LABELS',
        'At least one of --update-labels or --remove-labels must be specified.')

  return update_labels, remove_labels
