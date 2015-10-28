# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for modifying backend services."""


from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import resources


class InvalidResourceError(exceptions.ToolException):
  # Normally we'd want to subclass core.exceptions.Error, but base_classes.Edit
  # abuses ToolException to classify errors when displaying messages to users,
  # and we should continue to fit in that framework for now.
  pass


class Edit(base_classes.BaseEdit):
  """Modify backend services."""

  @staticmethod
  def Args(parser):
    base_classes.BaseEdit.Args(parser)
    parser.add_argument(
        'name',
        help='The name of the backend service to modify.')

  @property
  def service(self):
    return self.compute.backendServices

  @property
  def resource_type(self):
    return 'backendServices'

  @property
  def example_resource(self):
    uri_prefix = ('https://www.googleapis.com/compute/v1/projects/'
                  'my-project/')
    resource_views_uri_prefix = (
        'https://www.googleapis.com/resourceviews/v1beta1/projects/'
        'my-project/zones/')

    return self.messages.BackendService(
        backends=[
            self.messages.Backend(
                balancingMode=(
                    self.messages.Backend.BalancingModeValueValuesEnum.RATE),
                group=(
                    resource_views_uri_prefix +
                    'us-central1-a/resourceViews/group-1'),
                maxRate=100),
            self.messages.Backend(
                balancingMode=(
                    self.messages.Backend.BalancingModeValueValuesEnum.RATE),
                group=(
                    resource_views_uri_prefix +
                    'europe-west1-a/resourceViews/group-2'),
                maxRate=150),
        ],
        description='My backend service',
        healthChecks=[
            uri_prefix + 'global/httpHealthChecks/my-health-check-1',
            uri_prefix + 'global/httpHealthChecks/my-health-check-2'
        ],
        name='backend-service',
        port=80,
        portName='http',
        protocol=self.messages.BackendService.ProtocolValueValuesEnum.HTTP,
        selfLink=uri_prefix + 'global/backendServices/backend-service',
        timeoutSec=30,
    )

  def CreateReference(self, args):
    return self.CreateGlobalReference(args.name)

  @property
  def reference_normalizers(self):

    def MakeReferenceNormalizer(field_name, allowed_collections):
      """Returns a function to normalize resource references."""
      def NormalizeReference(reference):
        """Returns normalized URI for field_name."""
        try:
          value_ref = self.resources.Parse(reference)
        except resources.UnknownCollectionException:
          raise InvalidResourceError(
              '[{field_name}] must be referenced using URIs.'.format(
                  field_name=field_name))

        if value_ref.Collection() not in allowed_collections:
          raise InvalidResourceError(
              'Invalid [{field_name}] reference: [{value}].'. format(
                  field_name=field_name, value=reference))
        return value_ref.SelfLink()
      return NormalizeReference

    # Ensure group is a uri or full collection path representing a resource
    # view or an instance group.  Full uris/paths are required because if the
    # user gives us less, we don't want to be in the business of guessing
    # resource view or instance group.  The same applies, mutatis mutandis,
    # to health checks.
    return [
        ('healthChecks[]',
         MakeReferenceNormalizer(
             'healthChecks',
             ('compute.httpHealthChecks', 'compute.httpsHealthChecks'))),

        ('backends[].group',
         MakeReferenceNormalizer(
             'group',
             ('resourceviews.zoneViews', 'compute.instanceGroups')))]

  def GetGetRequest(self, args):
    return (
        self.service,
        'Get',
        self.messages.ComputeBackendServicesGetRequest(
            project=self.project,
            backendService=self.ref.Name()))

  def GetSetRequest(self, args, replacement, _):
    return (
        self.service,
        'Update',
        self.messages.ComputeBackendServicesUpdateRequest(
            project=self.project,
            backendService=self.ref.Name(),
            backendServiceResource=replacement))


Edit.detailed_help = {
    'brief': 'Modify backend services',
    'DESCRIPTION': """\
        *{command}* can be used to modify a backend service. The backend
        service resource is fetched from the server and presented in a text
        editor. After the file is saved and closed, this command will
        update the resource. Only fields that can be modified are
        displayed in the editor.

        Backends are named by their associated instances groups, and one
        of the ``--group'' or ``--instance-group'' flags is required to
        identify the backend that you are modifying.  You cannot "change"
        the instance group associated with a backend, but you can accomplish
        something similar with ``backend-services remove-backend'' and
        ``backend-services add-backend''.

        The editor used to modify the resource is chosen by inspecting
        the ``EDITOR'' environment variable.
        """,
}
