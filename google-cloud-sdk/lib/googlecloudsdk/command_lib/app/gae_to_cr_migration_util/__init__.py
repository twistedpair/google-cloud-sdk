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

"""Utility functions for GAE to CR migration."""

import argparse
import collections
import enum
import json
import logging
import os
import os.path
import re
import subprocess

from googlecloudsdk.api_lib.app import appengine_api_client
from googlecloudsdk.api_lib.resource_manager import folders
from googlecloudsdk.api_lib.run import api_enabler
from googlecloudsdk.api_lib.run import k8s_object
from googlecloudsdk.api_lib.run import service as service_lib
from googlecloudsdk.api_lib.run import traffic
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as c_exceptions
from googlecloudsdk.command_lib.app.gae_to_cr_migration_util import list_incompatible_features
from googlecloudsdk.command_lib.app.gae_to_cr_migration_util import translate
from googlecloudsdk.command_lib.artifacts import docker_util
from googlecloudsdk.command_lib.run import artifact_registry
from googlecloudsdk.command_lib.run import build_util
from googlecloudsdk.command_lib.run import config_changes
from googlecloudsdk.command_lib.run import connection_context
from googlecloudsdk.command_lib.run import container_parser
from googlecloudsdk.command_lib.run import exceptions
from googlecloudsdk.command_lib.run import flags
from googlecloudsdk.command_lib.run import messages_util
from googlecloudsdk.command_lib.run import platforms
from googlecloudsdk.command_lib.run import pretty_print
from googlecloudsdk.command_lib.run import resource_args
from googlecloudsdk.command_lib.run import resource_change_validators
from googlecloudsdk.command_lib.run import serverless_operations
from googlecloudsdk.command_lib.run import stages
from googlecloudsdk.command_lib.util.args import map_util
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.console import progress_tracker


class GAEToCRMigrationUtil():
  """Utility class for GAE to CR migration."""

  DEFAULT_APPYAML = 'app.yaml'
  DEFAULT_SERVICE_NAME = 'default'
  SERVICE_FIELD = 'service'

  def __init__(self, api_client, args):
    """Initializes the GAEToCRMigration utility class.

    Args:
      api_client: The AppEngine API client.
      args: The argparse arguments.
    """
    print('\nDeploying to Cloud Run...\n')
    self.api_client = api_client
    self.input_dir = os.getcwd()

    # if app.yaml is not provided, use app.yaml in current directory
    if args.appyaml:
      self.appyaml_path = os.path.relpath(args.appyaml)
    elif args.service is None or args.version is None:
      print(
          'Using app.yaml in current directory.\n'
      )
      self.appyaml_path = os.path.join(self.input_dir, self.DEFAULT_APPYAML)
    self.project = properties.VALUES.core.project.Get()
