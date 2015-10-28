# Copyright 2015 Google Inc. All Rights Reserved.

"""Command to get IAM policy for a resource."""

from googlecloudsdk.api_lib.projects import util
from googlecloudsdk.calliope import base


@base.Hidden
@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class GetIamPolicy(base.Command):
  """Get IAM policy for a Project.

  This command gets the IAM policy for a Project, given a Project ID.
  """

  detailed_help = {
      'brief': 'Get IAM policy for a Project.',
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          The following command will print IAM policy for a Project with
          identifier 'example-project-id-1'

            $ {command} example-project-id-1
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument('id', help='Project ID')

  @util.HandleHttpError
  def Run(self, args):
    projects = self.context['projects_client']
    messages = self.context['projects_messages']
    resources = self.context['projects_resources']

    project_ref = resources.Parse(args.id,
                                  collection='cloudresourcemanager.projects')
    policy_request = messages.CloudresourcemanagerProjectsGetIamPolicyRequest(
        resource=project_ref.Name(),
        getIamPolicyRequest=messages.GetIamPolicyRequest(),
    )
    return projects.projects.GetIamPolicy(policy_request)

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    # pylint:disable=not-callable, self.format is callable.
    self.format(result)
