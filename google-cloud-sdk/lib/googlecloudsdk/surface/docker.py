# Copyright 2014 Google Inc. All Rights Reserved.

"""Provides the docker CLI access to the Google Container Registry.

Sets docker up to authenticate with the Google Container Registry,
and passes all flags after -- to the docker CLI.
"""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.docker import constants
from googlecloudsdk.core.docker import docker


# By default, we'll set up authentication for these registries.
# If the user changes the --server argument to something not in this list,
# we'll just give them a warning that they're using an unexpected server.
_DEFAULT_REGISTRIES = constants.ALL_SUPPORTED_REGISTRIES


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Docker(base.Command):
  """Provides the docker CLI access to the Google Container Registry."""

  detailed_help = {
      'DESCRIPTION': """\
          The docker sub-command of gcloud wraps docker commands, so that
          gcloud can inject the appropriate fresh authentication token into
          requests that interact with the docker registry.  As commands are
          simply passed through to docker, see
          http://docs.docker.com/reference/commandline/cli/[] for a full
          reference of command-line options that can be supplied after the --.

          For more information please visit https://gcr.io/[].
      """,
      'EXAMPLES': """\
          Pull the image '{registry}/google-containers/pause:1.0' from the
          docker registry:

            $ {{command}} -- pull {registry}/google-containers/pause:1.0

          Push the image '{registry}/example-org/example-image:latest' to our
          private docker registry.

            $ {{command}} -- push {registry}/example-org/example-image:latest

          Configure authentication, then simply use docker:

            $ {{command}} --authorize-only

            $ docker push {registry}/example-org/example-image:latest

      """.format(registry=constants.DEFAULT_REGISTRY),
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--server', '-s',
        type=arg_parsers.ArgList(min_length=1),
        metavar='SERVER',
        action=arg_parsers.FloatingListValuesCatcher(),
        help='The address of the Google Cloud Registry.',
        required=False,
        default=_DEFAULT_REGISTRIES)
    # TODO(mattmoor): This should evolve into something that launches an
    # auth daemon process, or utilizes a more permanent credential.
    parser.add_argument(
        '--authorize-only', '-a',
        help='Configure docker authorization only, do not launch the '
        'docker command-line.',
        action='store_true')

    parser.add_argument(
        '--docker-host',
        help='The URL to connect to Docker Daemon. Format: tcp://host:port or '
        'unix:///path/to/socket.')

    parser.add_argument(
        'extra_args', nargs='*', default=[],
        help='Arguments to pass to docker.')

  def Run(self, args):
    """Executes the given docker command, after refreshing our credentials.

    Args:
      args: An argparse.Namespace that contains the values for
         the arguments specified in the .Args() method.

    Raises:
      exceptions.ExitCodeNoError: The docker command execution failed.
    """
    for server in args.server:
      if server not in _DEFAULT_REGISTRIES:
        log.warn('Authenticating to a non-default server: {server}.'.format(
            server=server))
      docker.UpdateDockerCredentials(server)

    if args.authorize_only:
      # NOTE: We don't know at this point how long the access token we have
      # placed in the docker configuration will last.  More information needs
      # to be exposed from all credential kinds in order for us to have an
      # accurate awareness of lifetime here.
      log.err.Print('Short-lived access for {server} configured.'.format(
          server=args.server))
      return

    # TODO(mattmoor): reconcile with the 'gcloud app' docker stuff,
    # which should be using a gcloud config property.
    extra_args = (args.extra_args if not args.docker_host else
                  ['-H', args.docker_host] + args.extra_args)

    result = docker.Execute(extra_args)
    # Explicitly avoid displaying an error message that might
    # distract from the docker error message already displayed.
    if result:
      raise exceptions.ExitCodeNoError(exit_code=result)
    return
