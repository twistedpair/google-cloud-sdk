# Copyright 2015 Google Inc. All Rights Reserved.

"""Command to set IAM policy for a resource."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core.iam import iam_util
from googlecloudsdk.shared.projects import util


@base.Hidden
@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class SetIamPolicy(base.Command):
  """Set IAM policy for a Project.

  This command sets the IAM policy for a Project, given a Project ID and a
  file that contains the JSON encoded IAM policy.
  """

  detailed_help = {
      'brief': 'Set IAM policy for a Project.',
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          The following command will read an IAM policy defined in a JSON file
          'policy.json' and set it for a Project with identifier
          'example-project-id-1'

            $ {command} example-project-id-1 policy.json
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument('id', help='Project ID')
    parser.add_argument('policy_file', help='JSON file with the IAM policy')

  @util.HandleHttpError
  def Run(self, args):
    projects = self.context['projects_client']
    messages = self.context['projects_messages']
    resources = self.context['projects_resources']

    project_ref = resources.Parse(args.id,
                                  collection='cloudresourcemanager.projects')

    policy = iam_util.ParseJsonPolicyFile(args.policy_file, messages.Policy)

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
