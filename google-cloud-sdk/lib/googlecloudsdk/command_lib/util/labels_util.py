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
"""Module for labels API support.

Typical usage (create command):

  # When defining arguments
  labels_util.AddCreateLabelsFlags(parser)
  # When running the command
  new_resource.labels = labels_util.Diff.FromCreateArgs(args).Apply(labels_cls)
  Create(..., new_resource)

Typical usage (update command):

  # When defining arguments
  labels_util.AddUpdateLabelsFlags(parser)
  # When running the command
  labels_diff = labels_util.Diff.FromUpdateArgs(args)
  if labels_diff.MayHaveUpdates():
    orig_resource = Get(...)  # to prevent unnecessary Get calls
    new_resource.labels = labels_diff.Apply(labels_cls, orig_resource.labels)
  Update(..., new_resource)
"""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as calliope_exceptions


def _IsLower(c):
  """Returns True if c is lower case or a caseless ideograph."""
  return c.isalpha() and (c.islower() or not c.isupper())


def _IsValueOrSubsequent(c):
  """Returns True if c is a valid value or subsequent (not first) character."""
  return c in ('_', '-') or c.isdigit() or _IsLower(c)


def IsValidLabelValue(value):
  r"""Implements the PCRE r'[\p{Ll}\p{Lo}\p{N}_-]{0,63}'.

  Only hyphens (-), underscores (_), lowercase characters, and numbers are
  allowed. International characters are allowed.

  Args:
    value: The label value, a string.

  Returns:
    True is the value is valid; False if not.
  """
  if value is None or len(value) > 63:
    return False
  return all(_IsValueOrSubsequent(c) for c in value)


def IsValidLabelKey(key):
  r"""Implements the PCRE r'[\p{Ll}\p{Lo}][\p{Ll}\p{Lo}\p{N}_-]{0,62}'.

  The key must start with a lowercase character and must be a valid label value.

  Args:
    key: The label key, a string.

  Returns:
    True if the key is valid; False if not.
  """
  if not key or not _IsLower(key[0]):
    return False
  return IsValidLabelValue(key)


KEY_FORMAT_ERROR = (
    'Only hyphens (-), underscores (_), lowercase characters, and numbers are '
    'allowed. Keys must start with a lowercase character. International '
    'characters are allowed.')

VALUE_FORMAT_ERROR = (
    'Only hyphens (-), underscores (_), lowercase characters, and numbers are '
    'allowed. International characters are allowed.')

KEY_FORMAT_VALIDATOR = arg_parsers.CustomFunctionValidator(
    IsValidLabelKey, KEY_FORMAT_ERROR)

VALUE_FORMAT_VALIDATOR = arg_parsers.CustomFunctionValidator(
    IsValidLabelValue, VALUE_FORMAT_ERROR)

CREATE_LABELS_FLAG = base.Argument(
    '--labels',
    metavar='KEY=VALUE',
    type=arg_parsers.ArgDict(
        key_type=KEY_FORMAT_VALIDATOR, value_type=VALUE_FORMAT_VALIDATOR),
    action=arg_parsers.UpdateAction,
    help='A list of label KEY=VALUE pairs to add.')


def _GetUpdateLabelsFlag(extra_message):
  return base.Argument(
      '--update-labels',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(
          key_type=KEY_FORMAT_VALIDATOR, value_type=VALUE_FORMAT_VALIDATOR),
      action=arg_parsers.UpdateAction,
      help="""\
      A list of label KEY=VALUE pairs to update. If a label exists its value
      is modified, otherwise a new label is created.""" + extra_message)


def _GetRemoveLabelsFlag(extra_message):
  return base.Argument(
      '--remove-labels',
      metavar='KEY',
      type=arg_parsers.ArgList(),
      action=arg_parsers.UpdateAction,
      help="""\
      A list of label keys to remove. If a label does not exist it is
      silently ignored.""" + extra_message)


def AddCreateLabelsFlags(parser):
  """Adds create command labels flags to an argparse parser.

  Args:
    parser: The argparse parser to add the flags to.
  """
  CREATE_LABELS_FLAG.AddToParser(parser)


def AddUpdateLabelsFlags(
    parser, extra_update_message='', extra_remove_message=''):
  """Adds update command labels flags to an argparse parser.

  Args:
    parser: The argparse parser to add the flags to.
    extra_update_message: str, extra message to append to help text for
                          --update-labels flag.
    extra_remove_message: str, extra message to append to help text for
                          --delete-labels flag.
  """
  _GetUpdateLabelsFlag(extra_update_message).AddToParser(parser)
  _GetRemoveLabelsFlag(extra_remove_message).AddToParser(parser)


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


def _PackageLabels(labels_cls, labels):
  # Sorted for test stability
  return labels_cls(additionalProperties=[
      labels_cls.AdditionalProperty(key=key, value=value)
      for key, value in sorted(labels.iteritems())])


class Diff(object):
  """A change to the labels on a resource."""

  def __init__(self, additions=None, subtractions=None):
    """Initialize a Diff.

    Args:
      additions: {str: str}, any label values to be updated
      subtractions: List[str], any labels to be removed

    Returns:
      Diff.
    """
    self.additions = additions
    self.subtractions = subtractions

  def Apply(self, labels_cls, labels=None):
    """Apply this Diff to the (possibly non-existing) labels.

    First, makes any additions. Then, removes any labels.

    Args:
      labels_cls: type, the LabelsValue class for the resource.
      labels: LabelsValue, the existing LabelsValue object for the original
        resource (or None, if the original resource is unknown)

    Returns:
      labels_cls, the instantiated LabelsValue message with the new set up
        labels, or None if there are no changes.
    """
    # Return None if there are no edits.
    if not self.MayHaveUpdates():
      return None

    new_labels = {}
    existing_labels = {}

    # Add pre-existing labels.
    if labels:
      for label in labels.additionalProperties:
        new_labels[label.key] = label.value
        existing_labels[label.key] = label.value

    # Add label updates and/or additions.
    if self.additions:
      new_labels.update(self.additions)

    # Remove labels if requested.
    if self.subtractions:
      for key in self.subtractions:
        new_labels.pop(key, None)

    # Return None if the edits are a no-op.
    if new_labels == existing_labels:
      return None

    return _PackageLabels(labels_cls, new_labels)

  def MayHaveUpdates(self):
    """Returns true if this Diff is non-empty (additions OR subtractions)."""
    return any([self.additions, self.subtractions])

  @classmethod
  def FromCreateArgs(cls, args):
    """Initializes a Diff based on the arguments in AddCreateLabelsFlags."""
    return cls(args.labels)

  @classmethod
  def FromUpdateArgs(cls, args):
    """Initializes a Diff based on the arguments in AddUpdateLabelsFlags."""
    return cls(args.update_labels, args.remove_labels)
