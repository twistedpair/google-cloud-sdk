# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics datasets get-iam-policy.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.api_lib import genomics as lib
from googlecloudsdk.api_lib.genomics import genomics_util


class GetIamPolicy(base.Command):
  """Get IAM policy for a dataset.

  This command gets the IAM policy for a dataset, given a dataset ID.
  """

  @staticmethod
  def Args(parser):
    parser.add_argument('id', type=str,
                        help='The ID of the dataset.')

  @genomics_util.ReraiseHttpException
  def Run(self, args):
    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    messages = self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]
    resources = self.context[lib.GENOMICS_RESOURCES_KEY]

    dataset_resource = resources.Parse(args.id, collection='genomics.datasets')

    policy_request = messages.GenomicsDatasetsGetIamPolicyRequest(
        resource='datasets/{0}'.format(dataset_resource.Name()),
        getIamPolicyRequest=messages.GetIamPolicyRequest(),
    )
    return apitools_client.datasets.GetIamPolicy(policy_request)

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    # pylint:disable=not-callable, self.format is callable.
    self.format(result)
