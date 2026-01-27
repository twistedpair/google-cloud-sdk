# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Functions to add flags in rollout sequence commands."""

from __future__ import absolute_import
from __future__ import annotations
from __future__ import division
from __future__ import unicode_literals

import textwrap
from typing import List

from apitools.base.protorpclite import messages
from googlecloudsdk.api_lib.container.fleet import util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import parser_arguments
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.command_lib.container.fleet import resources as fleet_resources
from googlecloudsdk.core import yaml
from googlecloudsdk.generated_clients.apis.gkehub.v1alpha import gkehub_v1alpha_messages as fleet_messages_alpha
from googlecloudsdk.generated_clients.apis.gkehub.v1beta import gkehub_v1beta_messages as fleet_messages_beta


class RolloutSequenceFlags:
  """Add flags to the fleet rolloutsequence command surface."""

  def __init__(
      self,
      parser: parser_arguments.ArgumentInterceptor,
      release_track: base.ReleaseTrack = base.ReleaseTrack.BETA,
  ):
    self._parser = parser
    self._release_track = release_track

  @property
  def parser(self):
    return self._parser

  @property
  def release_track(self):
    return self._release_track

  def AddAsync(self):
    base.ASYNC_FLAG.AddToParser(self.parser)

  def AddDisplayName(self):
    self.parser.add_argument(
        '--display-name',
        type=str,
        help=textwrap.dedent("""\
            Display name of the rollout sequence to be created (optional).
        """),
    )

  def AddLabels(self):
    self.parser.add_argument(
        '--labels',
        help='Labels for the rollout sequence.',
        metavar='KEY=VALUE',
        type=arg_parsers.ArgDict(),
    )

  def AddStageConfig(self) -> None:
    self.parser.add_argument(
        '--stage-config',
        type=arg_parsers.FileContents(),
        required=True,
        help="""\
            Path to the YAML file containing the stage configurations. The YAML
            file should contain a list of stages. Fleet projects and soak_duration are required.
            If label_selector is not specified, there is no filtering.
            A fleet project is the project where the fleet is hosted.
            Example:

            ```yaml
            - stage:
              fleet-projects:
              # Expected format: projects/{project}
              - projects/my-dev-project
              soak-duration: 7d # Or 168h or 604800s
            - stage:
              fleet-projects:
              - projects/my-prod-project
              soak-duration: 3600s
              label-selector: resource.labels.canary=='true'
            - stage:
              fleet-projects:
              # Expected format: projects/{project}
              - projects/my-prod-project
              soak-duration: 30m
              ```
        """,
    )

  def AddRolloutSequenceResourceArg(self):
    fleet_resources.AddRolloutSequenceResourceArg(
        parser=self.parser,
        api_version=util.VERSION_MAP[self.release_track],
    )


class RolloutSequenceFlagParser:
  """Parse flags during fleet rolloutsequence command runtime."""

  def __init__(
      self, args: parser_extensions.Namespace, release_track: base.ReleaseTrack
  ):
    self.args = args
    self.release_track = release_track
    self.messages = util.GetMessagesModule(release_track)

  def IsEmpty(self, message: messages.Message) -> bool:
    """Determines if a message is empty.

    Args:
      message: A message to check the emptiness.

    Returns:
      A bool indictating if the message is equivalent to a newly initialized
      empty message instance.
    """
    return message == type(message)()

  def TrimEmpty(self, message: messages.Message):
    """Trim empty messages to avoid cluttered request."""
    if not self.IsEmpty(message):
      return message
    return None

  def RolloutSequence(
      self,
  ) -> (
      fleet_messages_alpha.RolloutSequence
      | fleet_messages_beta.RolloutSequence
  ):
    rollout_sequence = self.messages.RolloutSequence()
    rollout_sequence.name = util.RolloutSequenceName(self.args)
    rollout_sequence.displayName = self._DisplayName()
    rollout_sequence.labels = self._Labels()
    rollout_sequence.stages = self._Stages()
    return rollout_sequence

  def _DisplayName(self) -> str:
    return self.args.display_name

  def _Labels(self) -> (
      fleet_messages_alpha.RolloutSequence.LabelsValue
      | fleet_messages_beta.RolloutSequence.LabelsValue
  ):
    """Parses --labels."""
    if '--labels' not in self.args.GetSpecifiedArgs():
      return None

    labels = self.args.labels
    labels_value = self.messages.RolloutSequence.LabelsValue()
    for key, value in labels.items():
      labels_value.additionalProperties.append(
          self.messages.RolloutSequence.LabelsValue.AdditionalProperty(
              key=key, value=value
          )
      )
    return labels_value

  def _Stages(
      self,
  ) -> List[fleet_messages_alpha.Stage | fleet_messages_beta.Stage]:
    """Parses --stage-config."""
    if '--stage-config' not in self.args.GetSpecifiedArgs():
      return []

    try:
      stage_data_list = yaml.load(self.args.stage_config, location_value=True)
    except yaml.YAMLParseError as e:
      raise ValueError(f'Error parsing YAML file: {e}') from e
    except Exception as e:
      raise ValueError(f'Error reading config file: {e}') from e

    if not isinstance(stage_data_list, list):
      raise ValueError('The config file should contain a list of stages.')

    stages = []
    for stage_data in stage_data_list:
      # Initialize optional parameters to None
      cluster_selector = self.messages.ClusterSelector(
          labelSelector=stage_data.get('label-selector')
      )
      soak_duration = stage_data.get('soak-duration')
      if not soak_duration:
        raise ValueError('soak-duration is required in the yaml file')

      try:
        # Support duration units like 'm', 'h', 'd'.
        soak_duration = f'{arg_parsers.Duration()(soak_duration)}s'
      except (arg_parsers.ArgumentTypeError, TypeError):
        # Fallback to the raw value if it's already in the 'Ns' format
        # or if it's invalid (the backend will catch it).
        pass

      fleet_projects = stage_data.get('fleet-projects')
      if not fleet_projects:
        raise ValueError('fleet-projects is required in the yaml file')

      if not isinstance(fleet_projects, list):
        raise ValueError('fleet-projects should be a list in the yaml file')

      cluster_selector = self.TrimEmpty(cluster_selector)
      stage = self.messages.Stage(
          clusterSelector=cluster_selector,
          soakDuration=soak_duration,
          fleetProjects=fleet_projects,
      )
      stages.append(stage)

    return stages

  def Project(self) -> str:
    return self.args.project

  def Location(self) -> str:
    return self.args.location

  def Async(self) -> bool:
    """Parses --async flag.

    The internal representation of --async is set to args.async_, defined in
    calliope/base.py file.

    Returns:
      bool, True if specified, False if unspecified.
    """
    return self.args.async_
