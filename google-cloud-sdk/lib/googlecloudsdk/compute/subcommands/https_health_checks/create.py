# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for creating HTTPS health checks."""
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.shared.compute import base_classes


class CreateHttpsHealthCheck(base_classes.BaseAsyncCreator):
  """Create an HTTPS health check to monitor load balanced instances."""

  @staticmethod
  def Args(parser):
    host = parser.add_argument(
        '--host',
        help='The value of the host header used by the HTTPS health check.')
    host.detailed_help = """\
        The value of the host header used in this HTTPS health check request.
        By default, this is empty and Google Compute Engine automatically sets
        the host header in health requests to the same external IP address as
        the forwarding rule associated with the target pool.
        """

    port = parser.add_argument(
        '--port',
        help='The TCP port number for the health request. Default is 443.',
        type=int,
        default=443)
    port.detailed_help = """\
        The TCP port number that this health check monitors. The default value
        is 443.
        """

    request_path = parser.add_argument(
        '--request-path',
        help="The request path for the health check. Default is ``/''.",
        default='/')
    request_path.detailed_help = """\
        The request path that this health check monitors. For example,
        ``/healthcheck''. The default value is ``/''.
        """

    check_interval_sec = parser.add_argument(
        '--check-interval',
        help='How often to run the check. Default is 5s.',
        type=arg_parsers.Duration(),
        default='5s')
    check_interval_sec.detailed_help = """\
        How often to perform a health check for an instance. For example,
        specifying ``10s'' will run the check every 10 seconds. Valid units
        for this flag are ``s'' for seconds and ``m'' for minutes.
        The default value is ``5s''.
        """

    timeout_sec = parser.add_argument(
        '--timeout',
        help='How long to wait until check is a failure. Default is 5s.',
        type=arg_parsers.Duration(),
        default='5s')
    timeout_sec.detailed_help = """\
        If Google Compute Engine doesn't receive an HTTPS 200 response from the
        instance by the time specified by the value of this flag, the health
        check request is considered a failure. For example, specifying ``10s''
        will cause the check to wait for 10 seconds before considering the
        request a failure.  Valid units for this flag are ``s'' for seconds and
        ``m'' for minutes.  The default value is ``5s''.
        """

    unhealthy_threshold = parser.add_argument(
        '--unhealthy-threshold',
        help='Consecutive failures to mark instance unhealthy. Default is 2.',
        type=int,
        default=2)
    unhealthy_threshold.detailed_help = """\
        The number of consecutive health check failures before a healthy
        instance is marked as unhealthy. The default is 2.
        """

    healthy_threshold = parser.add_argument(
        '--healthy-threshold',
        help='Consecutive successes to mark instance healthy. Default is 2.',
        type=int,
        default=2)
    healthy_threshold.detailed_help = """\
        The number of consecutive successful health checks before an
        unhealthy instance is marked as healthy. The default is 2.
        """

    parser.add_argument(
        '--description',
        help='An optional, textual description for the HTTPS health check.')

    parser.add_argument(
        'name',
        help='The name of the HTTPS health check.')

  @property
  def service(self):
    return self.compute.httpsHealthChecks

  @property
  def method(self):
    return 'Insert'

  @property
  def resource_type(self):
    return 'httpsHealthChecks'

  def CreateRequests(self, args):
    """Returnst the request necessary for adding the health check."""

    health_check_ref = self.CreateGlobalReference(
        args.name, resource_type='httpsHealthChecks')

    request = self.messages.ComputeHttpsHealthChecksInsertRequest(
        httpsHealthCheck=self.messages.HttpsHealthCheck(
            name=health_check_ref.Name(),
            host=args.host,
            port=args.port,
            description=args.description,
            requestPath=args.request_path,
            checkIntervalSec=args.check_interval,
            timeoutSec=args.timeout,
            healthyThreshold=args.healthy_threshold,
            unhealthyThreshold=args.unhealthy_threshold,
        ),
        project=self.project)

    return [request]


CreateHttpsHealthCheck.detailed_help = {
    'brief': ('Create an HTTPS health check to monitor load balanced '
              'instances'),
    'DESCRIPTION': """\
        *{command}* is used to create an HTTPS health check. HTTPS health checks
        monitor instances in a load balancer controlled by a target pool. All
        arguments to the command are optional except for the name of the health
        check. For more information on load balancing, see
        link:https://cloud.google.com/compute/docs/load-balancing-and-autoscaling/[].
        """,
}
