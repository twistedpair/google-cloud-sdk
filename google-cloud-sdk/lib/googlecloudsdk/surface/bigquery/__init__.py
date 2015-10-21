# Copyright 2014 Google Inc. All Rights Reserved.

"""The main command group for gcloud bigquery.
"""

import urlparse

from googlecloudsdk.calliope import base
from googlecloudsdk.core import cli
from googlecloudsdk.core import properties
from googlecloudsdk.core import resolvers
from googlecloudsdk.core import resources
from googlecloudsdk.core.credentials import store as c_store
from googlecloudsdk.shared.bigquery import bigquery
from googlecloudsdk.third_party.apis.bigquery.v2 import bigquery_v2_client
from googlecloudsdk.third_party.apis.bigquery.v2 import bigquery_v2_messages

SERVICE_NAME = 'bigquery'

BIGQUERY_API_MODULE_KEY = 'bigquery-api-module'
BIGQUERY_MESSAGES_MODULE_KEY = 'bigquery-messages-module'
APITOOLS_CLIENT_KEY = 'bigquery-apitools-client'
BIGQUERY_REGISTRY_KEY = 'bigquery-registry'


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Bigquery(base.Group):
  """A group of commands for using BigQuery.
  """

  def Filter(self, context, args):
    """Initialize context for bigquery commands.

    Args:
      context: The current context.
      args: The argparse namespace that was specified on the CLI or API.

    Returns:
      The updated context.
    """
    resources.SetParamDefault(
        api='bigquery', collection=None, param='projectId',
        resolver=resolvers.FromProperty(properties.VALUES.core.project))

    # TODO(cherba): remove command dependence on these.
    context[BIGQUERY_API_MODULE_KEY] = bigquery_v2_client
    context[BIGQUERY_MESSAGES_MODULE_KEY] = bigquery_v2_messages

    context[APITOOLS_CLIENT_KEY] = bigquery_v2_client.BigqueryV2(
        url=properties.VALUES.api_endpoint_overrides.bigquery.Get(),
        get_credentials=False,
        http=self.Http())
    context[BIGQUERY_REGISTRY_KEY] = resources.REGISTRY

    # Inject bigquery backend params.
    bigquery.Bigquery.SetResourceParser(resources.REGISTRY)
    bigquery.Bigquery.SetApiEndpoint(
        self.Http(), properties.VALUES.api_endpoint_overrides.bigquery.Get())

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--fingerprint-job-id',
        action='store_true',
        help='Whether to use a job id that is derived from a fingerprint of '
        'the job configuration.')
