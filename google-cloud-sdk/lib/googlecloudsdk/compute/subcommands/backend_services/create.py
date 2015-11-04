# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for creating backend services.

   There are separate alpha, beta, and GA command classes in this file.  The
   key differences are that each track passes different message modules for
   inferring options to --balancing-mode.
"""


from googlecloudsdk.api_lib.compute import backend_services_utils
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.third_party.apis.compute.alpha import compute_alpha_messages
from googlecloudsdk.third_party.apis.compute.beta import compute_beta_messages
from googlecloudsdk.third_party.apis.compute.v1 import compute_v1_messages


def _Args(parser, messages):
  """Common arguments to create commands for each release track."""
  backend_services_utils.AddUpdatableArgs(parser, messages)

  parser.add_argument(
      'name',
      help='The name of the backend service.')


@base.ReleaseTracks(base.ReleaseTrack.GA)
class CreateGA(base_classes.BaseAsyncCreator):
  """Create a backend service."""

  @staticmethod
  def Args(parser):
    _Args(parser, compute_v1_messages)

  @property
  def service(self):
    return self.compute.backendServices

  @property
  def method(self):
    return 'Insert'

  @property
  def resource_type(self):
    return 'backendServices'

  def _CommonBackendServiceKwargs(self, args):
    """Prepare BackendService kwargs for fields common to all release tracks.

    Args:
      args: CLI args to translate to BackendService proto kwargs.

    Returns:
      A dictionary of keyword arguments to be passed to the BackendService proto
      constructor.
    """
    backend_services_ref = self.CreateGlobalReference(args.name)

    if args.port:
      port = args.port
    else:
      port = 80
      if args.protocol == 'HTTPS':
        port = 443

    if args.port_name:
      port_name = args.port_name
    else:
      port_name = 'http'
      if args.protocol == 'HTTPS':
        port_name = 'https'

    protocol = self.messages.BackendService.ProtocolValueValuesEnum(
        args.protocol)

    health_checks = backend_services_utils.GetHealthChecks(args, self)
    if not health_checks:
      raise exceptions.ToolException('At least one health check required.')

    return dict(
        description=args.description,
        healthChecks=health_checks,
        name=backend_services_ref.Name(),
        port=port,
        portName=port_name,
        protocol=protocol,
        timeoutSec=args.timeout)

  def CreateRequests(self, args):
    request = self.messages.ComputeBackendServicesInsertRequest(
        backendService=self.messages.BackendService(
            **self._CommonBackendServiceKwargs(args)),
        project=self.project)

    return [request]


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class CreateAlpha(CreateGA):
  """Create a backend service."""

  @staticmethod
  def Args(parser):
    _Args(parser, compute_alpha_messages)

    enable_cdn = parser.add_argument(
        '--enable-cdn',
        action='store_true',
        default=None,  # Tri-valued, None => don't change the setting.
        help='Enable cloud CDN.')
    enable_cdn.detailed_help = """\
        Enable Cloud CDN for the backend service. Cloud CDN can cache HTTP
        responses from a backend service at the edge of the network, close to
        users.
        """

  def CreateRequests(self, args):
    kwargs = self._CommonBackendServiceKwargs(args)
    if args.enable_cdn is not None:
      kwargs['enableCDN'] = args.enable_cdn

    request = self.messages.ComputeBackendServicesInsertRequest(
        backendService=self.messages.BackendService(**kwargs),
        project=self.project)

    return [request]


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class CreateBeta(CreateGA):
  """Create a backend service."""

  @staticmethod
  def Args(parser):
    _Args(parser, compute_beta_messages)


CreateGA.detailed_help = {
    'DESCRIPTION': """
        *{command}* is used to create backend services. Backend
        services define groups of backends that can receive
        traffic. Each backend group has parameters that define the
        group's capacity (e.g., max CPU utilization, max queries per
        second, ...). URL maps define which requests are sent to which
        backend services.

        Backend services created through this command will start out
        without any backend groups. To add backend groups, use 'gcloud
        compute backend-services add-backend' or 'gcloud compute
        backend-services edit'.
        """,
}
CreateAlpha.detailed_help = CreateGA.detailed_help
CreateBeta.detailed_help = CreateGA.detailed_help
