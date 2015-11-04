# Copyright 2015 Google Inc. All Rights Reserved.

"""Command to remove IAM policy binding for a resource."""

from googlecloudsdk.api_lib.projects import util
from googlecloudsdk.calliope import base
from googlecloudsdk.core.iam import iam_util


@base.Hidden
@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class RemoveIamPolicyBinding(base.Command):
  """Remove IAM policy binding for a project.

  This command removes a policy binding to the IAM policy of a Project,
  given a Project ID and the binding.
  """

  detailed_help = {
      'brief': 'Remove IAM policy binding for a Project.',
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          The following command will remove a IAM policy binding for the role
          of 'editor' for the user 'test-user@gmail.com' on project
          'example-project-id-1'

            $ {command} example-project-id-1 --editor='user:test-user@gmail.com'
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument('id', help='Project ID')
    iam_util.AddArgsForRemoveIamPolicyBinding(parser)

  @util.HandleHttpError
  def Run(self, args):
    projects = self.context['projects_client']
    messages = self.context['projects_messages']
    resources = self.context['projects_resources']

    project_ref = resources.Parse(args.id,
                                  collection='cloudresourcemanager.projects')

    policy_request = messages.CloudresourcemanagerProjectsGetIamPolicyRequest(
        resource=project_ref.Name(),
        getIamPolicyRequest=messages.GetIamPolicyRequest())
    policy = projects.projects.GetIamPolicy(policy_request)

    iam_util.RemoveBindingFromIamPolicy(policy, args)

    policy_request = messages.CloudresourcemanagerProjectsSetIamPolicyRequest(
        resource=project_ref.Name(),
        setIamPolicyRequest=messages.SetIamPolicyRequest(policy=policy))
    return projects.projects.SetIamPolicy(policy_request)

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    # pylint:disable=not-callable, self.format is callable.
    self.format(result)
