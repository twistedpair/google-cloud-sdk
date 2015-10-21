# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for creating SSL certificates."""

from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import file_utils


class Create(base_classes.BaseAsyncCreator):
  """Create a Google Compute Engine SSL certificate.

  *{command}* is used to create SSL certificates which can be used to
  configure a target HTTPS proxy. An SSL certificate consists of a
  certificate and private key. The private key is encrypted before it is
  stored.
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--description',
        help='An optional, textual description for the SSL certificate.')

    certificate = parser.add_argument(
        '--certificate',
        required=True,
        metavar='LOCAL_FILE_PATH',
        help='The path to a local certificate file.')
    certificate.detailed_help = """\
        The path to a local certificate file. The certificate must be in PEM
        format.  The certificate chain must be no greater than 5 certs long. The
        chain must include at least one intermediate cert.
        """

    private_key = parser.add_argument(
        '--private-key',
        required=True,
        metavar='LOCAL_FILE_PATH',
        help='The path to a local private key file.')
    private_key.detailed_help = """\
        The path to a local private key file. The private key must be in PEM
        format and must use RSA or ECDSA encryption.
        """

    parser.add_argument(
        'name',
        help='The name of the SSL certificate.')

  @property
  def service(self):
    return self.compute.sslCertificates

  @property
  def method(self):
    return 'Insert'

  @property
  def resource_type(self):
    return 'sslCertificates'

  def CreateRequests(self, args):
    """Returns the request necessary for adding the SSL certificate."""

    ssl_certificate_ref = self.CreateGlobalReference(
        args.name, resource_type='sslCertificates')
    certificate = file_utils.ReadFile(args.certificate, 'certificate')
    private_key = file_utils.ReadFile(args.private_key, 'private key')

    request = self.messages.ComputeSslCertificatesInsertRequest(
        sslCertificate=self.messages.SslCertificate(
            name=ssl_certificate_ref.Name(),
            certificate=certificate,
            privateKey=private_key,
            description=args.description),
        project=self.project)

    return [request]
