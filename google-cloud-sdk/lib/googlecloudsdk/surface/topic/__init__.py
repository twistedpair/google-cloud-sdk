# Copyright 2014 Google Inc. All Rights Reserved.

"""gcloud supplementary help topic command group."""

from googlecloudsdk.calliope import base


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Topic(base.Group):
  """gcloud supplementary help.

  This command provides supplementary help for topics not directly associated
  with individual commands. Run $ gcloud topic TOPIC to list help for TOPIC.
  """
