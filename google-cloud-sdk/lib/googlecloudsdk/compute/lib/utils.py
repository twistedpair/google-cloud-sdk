# Copyright 2014 Google Inc. All Rights Reserved.
"""Utility functions that don't belong in the other utility modules."""

from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.third_party.apis.clouduseraccounts.alpha import clouduseraccounts_alpha_client
from googlecloudsdk.third_party.apis.clouduseraccounts.beta import clouduseraccounts_beta_client
from googlecloudsdk.third_party.apis.compute.alpha import compute_alpha_client
from googlecloudsdk.third_party.apis.compute.beta import compute_beta_client
from googlecloudsdk.third_party.apis.compute.v1 import compute_v1_client


def UpdateContextEndpointEntries(context, http, api_client_default='v1'):
  """Updates context to set API enpoints; requires context['http'] be set."""

  known_apis = {
      'alpha': compute_alpha_client.ComputeAlpha,
      'beta': compute_beta_client.ComputeBeta,
      'v1': compute_v1_client.ComputeV1,
  }

  known_clouduseraccounts_apis = {
      'alpha': clouduseraccounts_alpha_client.ClouduseraccountsAlpha,
      'beta': clouduseraccounts_beta_client.ClouduseraccountsBeta,
  }


  utils.UpdateContextEndpointEntries(context, http, api_client_default,
                                     known_apis, known_clouduseraccounts_apis)
