# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for creating target HTTPS proxies."""

from googlecloudsdk.shared.compute import base_classes


class Create(base_classes.BaseAsyncCreator):
  """Create a target HTTPS proxy."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--description',
        help='An optional, textual description for the target HTTPS proxy.')

    ssl_certificate = parser.add_argument(
        '--ssl-certificate',
        required=True,
        help=('A reference to an SSL certificate resource that is used for '
              'server-side authentication.'))
    ssl_certificate.detailed_help = """\
        A reference to an SSL certificate resource that is used for
        server-side authentication. The SSL certificate must exist and cannot
        be deleted while referenced by a target HTTPS proxy.
        """

    url_map = parser.add_argument(
        '--url-map',
        required=True,
        help=('A reference to a URL map resource that defines the mapping of '
              'URLs to backend services.'))
    url_map.detailed_help = """\
        A reference to a URL map resource that defines the mapping of
        URLs to backend services. The URL map must exist and cannot be
        deleted while referenced by a target HTTPS proxy.
        """

    parser.add_argument(
        'name',
        help='The name of the target HTTPS proxy.')

  @property
  def service(self):
    return self.compute.targetHttpsProxies

  @property
  def method(self):
    return 'Insert'

  @property
  def resource_type(self):
    return 'targetHttpsProxies'

  def CreateRequests(self, args):
    ssl_certificate_ref = self.CreateGlobalReference(
        args.ssl_certificate, resource_type='sslCertificates')

    url_map_ref = self.CreateGlobalReference(
        args.url_map, resource_type='urlMaps')

    target_https_proxy_ref = self.CreateGlobalReference(
        args.name, resource_type='targetHttpsProxies')

    request = self.messages.ComputeTargetHttpsProxiesInsertRequest(
        project=self.project,
        targetHttpsProxy=self.messages.TargetHttpsProxy(
            description=args.description,
            name=target_https_proxy_ref.Name(),
            urlMap=url_map_ref.SelfLink(),
            sslCertificates=[ssl_certificate_ref.SelfLink()]))
    return [request]


Create.detailed_help = {
    'brief': 'Create a target HTTPS proxy',
    'DESCRIPTION': """
        *{command}* is used to create target HTTPS proxies. A target
        HTTPS proxy is referenced by one or more forwarding rules which
        define which packets the proxy is responsible for routing. The
        target HTTPS proxy points to a URL map that defines the rules
        for routing the requests. The URL map's job is to map URLs to
        backend services which handle the actual requests. The target
        HTTPS proxy also points to an SSL certificate used for
        server-side authentication.
        """,
}
