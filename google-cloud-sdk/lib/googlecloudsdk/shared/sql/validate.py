# Copyright 2015 Google Inc. All Rights Reserved.

"""Common sql utility functions for validating."""

from googlecloudsdk.calliope import exceptions


def ValidateInstanceName(instance_name):
  if ':' in instance_name:
    possible_project = instance_name[:instance_name.rindex(':')]
    possible_instance = instance_name[instance_name.rindex(':')+1:]
    raise exceptions.ToolException("""\
Instance names cannot contain the ':' character. If you meant to indicate the
project for [{instance}], use only '{instance}' for the argument, and either add
'--project {project}' to the command line or first run
  $ gcloud config set project {project}
""".format(project=possible_project, instance=possible_instance))
