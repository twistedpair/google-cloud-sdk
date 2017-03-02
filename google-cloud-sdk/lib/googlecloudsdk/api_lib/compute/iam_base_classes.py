# Copyright 2014 Google Inc. All Rights Reserved.
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
"""Internal base classes for abstracting away common logic."""
import abc
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.command_lib.compute import flags
from googlecloudsdk.command_lib.iam import iam_util


# TODO(user): Investigate sharing more code with BaseDescriber command.
class BaseGetIamPolicy(base_classes.BaseCommand):
  """Base class for getting the Iam Policy for a resource."""

  __metaclass__ = abc.ABCMeta

  @staticmethod
  def Args(parser, resource=None, list_command_path=None):
    BaseGetIamPolicy.AddArgs(parser, resource, list_command_path)

  @staticmethod
  def AddArgs(parser, resource=None, list_command_path=None):
    """Add required flags for set Iam policy."""
    parser.add_argument(
        'name',
        metavar='NAME',
        completion_resource=resource,
        list_command_path=list_command_path,
        help='The resources whose IAM policy to fetch.')

  @property
  def method(self):
    return 'GetIamPolicy'

  def ScopeRequest(self, ref, request):
    """Adds a zone or region to the request object if necessary."""

  def SetResourceName(self, ref, request):
    """Adds a the name of the resource to the request object."""
    resource_name = self.service.GetMethodConfig(self.method).ordered_params[-1]
    setattr(request, resource_name, ref.Name())

  @abc.abstractmethod
  def CreateReference(self, args):
    pass

  def Run(self, args):

    ref = self.CreateReference(args)
    request_class = self.service.GetRequestType(self.method)
    request = request_class(project=self.project)
    self.ScopeRequest(ref, request)
    self.SetResourceName(ref, request)

    get_policy_request = (self.service, self.method, request)
    errors = []
    objects = request_helper.MakeRequests(
        requests=[get_policy_request],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors)

    # Converting the objects genrator to a list triggers the
    # logic that actually populates the errors list.
    resources = list(objects)
    if errors:
      utils.RaiseToolException(
          errors,
          error_message='Could not fetch resource:')

    # TODO(user): determine how this output should look when empty.

    # GetIamPolicy always returns either an error or a valid policy.
    # If no policy has been set it returns a valid empty policy (just an etag.)
    # It is not possible to have multiple policies for one resource.
    return resources[0]


def GetIamPolicyHelp(resource_name):
  return {
      'brief': 'Get the IAM Policy for a Google Compute Engine {0}.'.format(
          resource_name),
      'DESCRIPTION': """\
          *{{command}}* displays the Iam Policy associated with a Google Compute
          Engine {0} in a project.
          """.format(resource_name)}


class ZonalGetIamPolicy(BaseGetIamPolicy):
  """Base class for zonal iam_get_policy commands."""

  @staticmethod
  def Args(parser, resource=None, command=None):
    BaseGetIamPolicy.AddArgs(parser, resource, command)
    flags.AddZoneFlag(
        parser,
        resource_type='resource',
        operation_type='fetch')

  def CreateReference(self, args):
    return self.CreateZonalReference(args.name, args.zone)

  def ScopeRequest(self, ref, request):
    request.zone = ref.zone


class RegionalGetIamPolicy(BaseGetIamPolicy):
  """Base class for regional iam_get_policy commands."""

  @staticmethod
  def Args(parser, resource=None, command=None):
    BaseGetIamPolicy.AddArgs(parser, resource, command)
    flags.AddRegionFlag(
        parser,
        resource_type='resource',
        operation_type='fetch')

  def CreateReference(self, args):
    return self.CreateRegionalReference(args.name, args.region)

  def ScopeRequest(self, ref, request):
    request.region = ref.region


class GlobalGetIamPolicy(BaseGetIamPolicy):
  """Base class for global iam_get_policy commands."""

  def CreateReference(self, args):
    return self.CreateGlobalReference(args.name)


class BaseSetIamPolicy(base_classes.BaseCommand):
  """Base class for setting the Iam Policy for a resource."""

  __metaclass__ = abc.ABCMeta

  @staticmethod
  def Args(parser, resource=None, list_command_path=None):
    BaseSetIamPolicy.AddArgs(parser, resource, list_command_path)

  @staticmethod
  def AddArgs(parser, resource=None, list_command_path=None):
    """Add required flags for set Iam policy."""
    parser.add_argument(
        'name',
        metavar='NAME',
        completion_resource=resource,
        list_command_path=list_command_path,
        help='The resources whose IAM policy to set.')

    parser.add_argument(
        'policy_file',
        metavar='POLICY_FILE',
        help="""\
        Path to a local JSON or YAML formatted file containing a valid policy.
        """)
    # TODO(user): fill in detailed help.

  @property
  def method(self):
    return 'SetIamPolicy'

  def ScopeRequest(self, ref, request):
    """Adds a zone or region to the request object if necessary."""

  def SetResourceName(self, ref, request):
    """Adds a the name of the resource to the request object."""
    resource_name = self.service.GetMethodConfig(self.method).ordered_params[-1]
    setattr(request, resource_name, ref.Name())

  @abc.abstractmethod
  def CreateReference(self, args):
    pass

  def Run(self, args):
    policy = iam_util.ParsePolicyFile(args.policy_file, self.messages.Policy)

    ref = self.CreateReference(args)
    request_class = self.service.GetRequestType(self.method)
    request = request_class(project=self.project)
    self.ScopeRequest(ref, request)
    self.SetResourceName(ref, request)
    request.policy = policy

    set_policy_request = (self.service, self.method, request)
    errors = []
    objects = request_helper.MakeRequests(
        requests=[set_policy_request],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors)

    # Converting the objects genrator to a list triggers the
    # logic that actually populates the errors list.
    resources = list(objects)
    if errors:
      utils.RaiseToolException(
          errors,
          error_message='Could not fetch resource:')

    # TODO(user): determine how this output should look when empty.

    # SetIamPolicy always returns either an error or the newly set policy.
    # If the policy was just set to the empty policy it returns a valid empty
    # policy (just an etag.)
    # It is not possible to have multiple policies for one resource.
    return resources[0]


def SetIamPolicyHelp(resource_name):
  return {
      'brief': 'Set the IAM Policy for a Google Compute Engine {0}.'.format(
          resource_name),
      'DESCRIPTION': """\
        *{{command}}* sets the Iam Policy associated with a Google Compute
        Engine {0} in a project.
        """.format(resource_name)}


class ZonalSetIamPolicy(BaseSetIamPolicy):
  """Base class for zonal iam_get_policy commands."""

  @staticmethod
  def Args(parser, resource=None, command=None):
    BaseSetIamPolicy.AddArgs(parser, resource, command)
    flags.AddZoneFlag(
        parser,
        resource_type='resource',
        operation_type='fetch')

  def CreateReference(self, args):
    return self.CreateZonalReference(args.name, args.zone)

  def ScopeRequest(self, ref, request):
    request.zone = ref.zone


class RegionalSetIamPolicy(BaseSetIamPolicy):
  """Base class for regional iam_get_policy commands."""

  @staticmethod
  def Args(parser, resource=None, command=None):
    BaseSetIamPolicy.AddArgs(parser, resource, command)
    flags.AddRegionFlag(
        parser,
        resource_type='resource',
        operation_type='fetch')

  def CreateReference(self, args):
    return self.CreateRegionalReference(args.name, args.region)

  def ScopeRequest(self, ref, request):
    request.region = ref.region


class GlobalSetIamPolicy(BaseSetIamPolicy):
  """Base class for global iam_get_policy commands."""

  def CreateReference(self, args):
    return self.CreateGlobalReference(args.name)
