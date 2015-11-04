# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics datasets remove-iam-policy-binding
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.core.iam import iam_util
from googlecloudsdk.api_lib import genomics as lib
from googlecloudsdk.api_lib.genomics import genomics_util


class RemoveIamPolicyBinding(base.Command):
  """Remove IAM policy binding for a dataset.

  This command removes a policy binding to the IAM policy of a dataset,
  given a dataset ID and the binding.
  """

  detailed_help = iam_util.GetDetailedHelpForRemoveIamPolicyBinding(
      'dataset', '1000')

  @staticmethod
  def Args(parser):
    parser.add_argument('id', type=str,
                        help='The ID of the dataset.')
    iam_util.AddArgsForRemoveIamPolicyBinding(parser)

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
    policy = apitools_client.datasets.GetIamPolicy(policy_request)

    iam_util.RemoveBindingFromIamPolicy(policy, args)

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
