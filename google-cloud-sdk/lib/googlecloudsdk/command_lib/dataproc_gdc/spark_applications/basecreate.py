# -*- coding: utf-8 -*- #
# Copyright 2024 Google Inc. All Rights Reserved.
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
"""`gcloud dataproc-gdc instances create` command."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import uuid

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.apis import yaml_data
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs
from googlecloudsdk.core import log
from googlecloudsdk.core import resources


DATAPROCGDC_API_NAME = 'dataprocgdc'
DATAPROCGDC_API_VERSION = 'v1alpha1'


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
@base.DefaultUniverseOnly
class BaseGDCSparkApplicationCommand(base.CreateCommand):
  """Create a Dataproc GDC spark application.

  A Saprk application that run locally on the Dataproc
  GDC cluster.
  """

  @staticmethod
  def Args(parser):
    concept_parsers.ConceptParser(
        [
            GetSparkApplicationResourcePresentationSpec(),
            GetApplicationEnvironmentResourcePresentationSpec(),
            GetInstanceResourcePresentationSpec(),
        ],
        command_level_fallthroughs={
            # Set the Application Environment to the same instance and location
            # as the Spark Application.
            '--application-environment.instance': ['--instance.instance'],
            '--application-environment.location': ['--instance.location'],
            '--application.instance': ['--instance.instance'],
            '--application.location': ['--instance.location'],
        },
    ).AddToParser(parser)
    parser.add_argument(
        '--request-id',
        help="""An optional request ID to identify requests. If the service receives two identical
        instance create requests with the same request_id, the second request is
        ignored and the operation that corresponds to the first request is returned for both.

        The request ID must be a valid UUID with the exception that zero UUID is
        not supported (00000000-0000-0000-0000-000000000000).""",
    )
    parser.add_argument(
        '--display-name',
        help=(
            'Human-readable name for this service instance to be used in user'
            ' interfaces.'
        ),
    )
    parser.add_argument(
        '--namespace',
        help='namespace to run the application in',
    )
    parser.add_argument(
        '--version',
        help='version of the application',
    )
    parser.add_argument(
        '--properties',
        type=arg_parsers.ArgDict(),
        metavar='PROPERTY=VALUE',
        help=(
            'List of key value pairs to configure Spark. For a list of '
            'available properties, see: '
            'https://spark.apache.org/docs/latest/'
            'configuration.html#available-properties.'
        ),
    )
    parser.add_argument(
        '--annotations',
        metavar='KEY=VALUE',
        type=arg_parsers.ArgDict(),
        action=arg_parsers.UpdateAction,
        help=(
            'List of annotation KEY=VALUE pairs to add to the service instance.'
        ),
    )
    labels_util.AddCreateLabelsFlags(parser)
    base.ASYNC_FLAG.AddToParser(parser)

  def Submit(self, args, application_ref, create_req):
    request_id = args.request_id or uuid.uuid4().hex
    # If the application id was not set, generate a random id.
    application_id = (
        application_ref.Name()
        if application_ref is not None
        else uuid.uuid4().hex
    )

    create_req.requestId = request_id
    create_req.sparkApplicationId = application_id

    dataprocgdc_client = apis.GetClientInstance(
        DATAPROCGDC_API_NAME, DATAPROCGDC_API_VERSION
    )

    create_op = dataprocgdc_client.projects_locations_serviceInstances_sparkApplications.Create(
        create_req
    )

    if not args.async_:
      # Poll for operation
      operation_ref = resources.REGISTRY.Parse(
          create_op.name, collection='dataprocgdc.projects.locations.operations'
      )
      poller = waiter.CloudOperationPoller(
          dataprocgdc_client.projects_locations_serviceInstances_sparkApplications,
          dataprocgdc_client.projects_locations_operations,
      )
      waiter.WaitFor(
          poller,
          operation_ref,
          'Waiting for spark application create operation [{0}]'.format(
              operation_ref.RelativeName()
          ),
      )
      log.CreatedResource(
          application_ref.Name(),
          details=(
              '- spark application in service instance [{0}]'.format(
                  application_ref.Parent().RelativeName()
              )
          ),
      )
      return

    log.status.Print(
        'Create request issued for: [{0}]\nCheck operation [{1}] for status.'
        .format(application_id, create_op.name)
    )


def GetSparkApplicationResourcePresentationSpec():
  application_data = yaml_data.ResourceYAMLData.FromPath(
      'dataproc_gdc.spark_application'
  )
  # dataprocgdc.projects.locations.serviceInstances.sparkApplications
  resource_spec = concepts.ResourceSpec.FromYaml(application_data.GetData())
  return presentation_specs.ResourcePresentationSpec(
      name='--application',
      concept_spec=resource_spec,
      group_help='Spark application to create.',
      required=False,
      prefixes=False,
      flag_name_overrides={'instance': '', 'location': ''},
  )


def GetApplicationEnvironmentResourcePresentationSpec():
  instance_data = yaml_data.ResourceYAMLData.FromPath(
      'dataproc_gdc.application_environment'
  )
  resource_spec = concepts.ResourceSpec.FromYaml(instance_data.GetData())
  return presentation_specs.ResourcePresentationSpec(
      name='--application-environment',
      concept_spec=resource_spec,
      group_help=(
          'Name of the application environment to reference for this Spark '
          'Application.'
      ),
      required=False,
      prefixes=True,
      flag_name_overrides={'instance': '', 'location': ''},
  )


def GetInstanceResourcePresentationSpec():
  instance_data = yaml_data.ResourceYAMLData.FromPath(
      'dataproc_gdc.service_instance'
  )
  resource_spec = concepts.ResourceSpec.FromYaml(instance_data.GetData())
  return presentation_specs.ResourcePresentationSpec(
      name='--instance',
      concept_spec=resource_spec,
      group_help=(
          'Name of the service instance on which this Spark Application will '
          'run.'
      ),
      required=True,
      prefixes=False,
  )
