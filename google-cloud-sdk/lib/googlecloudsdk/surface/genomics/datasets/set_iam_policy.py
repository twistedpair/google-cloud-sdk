# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics datasets set-iam-policy.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.core.iam import iam_util
from googlecloudsdk.api_lib import genomics as lib
from googlecloudsdk.api_lib.genomics import genomics_util


class SetIamPolicy(base.Command):
  """Set IAM policy for a dataset.

  This command sets the IAM policy for a dataset, given a dataset ID and a
  file that contains the JSON encoded IAM policy.
  """

  detailed_help = iam_util.GetDetailedHelpForSetIamPolicy('dataset', '1000')

  @staticmethod
  def Args(parser):
    parser.add_argument('id', type=str,
                        help='The ID of the dataset.')
    parser.add_argument('policy_file', help='JSON file with the IAM policy')

  @genomics_util.ReraiseHttpException
  def Run(self, args):
    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    messages = self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]
    resources = self.context[lib.GENOMICS_RESOURCES_KEY]

    dataset_resource = resources.Parse(args.id, collection='genomics.datasets')

    policy = iam_util.ParseJsonPolicyFile(args.policy_file, messages.Policy)

    policy_request = messages.GenomicsDatasetsSetIamPolicyRequest(
        resource='datasets/{0}'.format(dataset_resource.Name()),
        setIamPolicyRequest=messages.SetIamPolicyRequest(policy=policy),
    )
    return apitools_client.datasets.SetIamPolicy(policy_request)

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    # pylint:disable=not-callable, self.format is callable.
    self.format(result)
