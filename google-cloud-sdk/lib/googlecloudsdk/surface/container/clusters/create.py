# Copyright 2014 Google Inc. All Rights Reserved.

"""Create cluster command."""
import argparse
import random
import string

from googlecloudsdk.api_lib.compute import constants
from googlecloudsdk.api_lib.container import api_adapter
from googlecloudsdk.api_lib.container import kubeconfig as kconfig
from googlecloudsdk.api_lib.container import util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.third_party.apitools.base.py import exceptions as apitools_exceptions


def _Args(parser):
  """Register flags for this command.

  Args:
    parser: An argparse.ArgumentParser-like object. It is mocked out in order
        to capture some information, but behaves like an ArgumentParser.
  """
  parser.add_argument('name', help='The name of this cluster.')
  # Timeout in seconds for operation
  parser.add_argument(
      '--timeout',
      type=int,
      default=1800,
      help=argparse.SUPPRESS)
  parser.add_argument(
      '--wait',
      action='store_true',
      default=True,
      help='Poll the operation for completion after issuing a create request.')
  parser.add_argument(
      '--num-nodes',
      type=int,
      help='The number of nodes in the cluster.',
      default=3)
  parser.add_argument(
      '--machine-type', '-m',
      help='The type of machine to use for workers. Defaults to '
      'server-specified')
  parser.add_argument(
      '--subnetwork',
      help='The name of the Google Compute Engine subnetwork'
      '(https://cloud.google.com/compute/docs/subnetworks) to which the '
      'cluster is connected. If specified, the cluster\'s network must be a '
      '"custom subnet" network. Specification of subnetworks is an '
      'alpha feature, and requires that the '
      'Google Compute Engine alpha API be enabled.')
  parser.add_argument(
      '--network',
      help='The Compute Engine Network that the cluster will connect to. '
      'Google Container Engine will use this network when creating routes '
      'and firewalls for the clusters. Defaults to the \'default\' network.')
  parser.add_argument(
      '--cluster-ipv4-cidr',
      help='The IP address range for the pods in this cluster in CIDR '
      'notation (e.g. 10.0.0.0/14). Defaults to server-specified')
  parser.add_argument(
      '--password',
      help='The password to use for cluster auth. Defaults to a '
      'randomly-generated string.')
  parser.add_argument(
      '--scopes',
      type=arg_parsers.ArgList(min_length=1),
      metavar='SCOPE',
      action=arg_parsers.FloatingListValuesCatcher(),
      help="""\
Specifies scopes for the node instances. The project's default
service account is used. Examples:

  $ {{command}} example-cluster --scopes https://www.googleapis.com/auth/devstorage.read_only

  $ {{command}} example-cluster --scopes bigquery,storage-rw,compute-ro

Multiple SCOPEs can specified, separated by commas. The scopes
necessary for the cluster to function properly (compute-rw, storage-ro),
are always added, even if not explicitly specified.

SCOPE can be either the full URI of the scope or an alias.
Available aliases are:

Alias,URI
{aliases}
""".format(
    aliases='\n        '.join(
        ','.join(value) for value in
        sorted(constants.SCOPES.iteritems()))))
  parser.add_argument(
      '--enable-cloud-logging',
      action='store_true',
      default=True,
      help='Automatically send logs from the cluster to the '
      'Google Cloud Logging API.')
  parser.set_defaults(enable_cloud_logging=True)
  parser.add_argument(
      '--enable-cloud-monitoring',
      action='store_true',
      default=True,
      help='Automatically send metrics from pods in the cluster to the '
      'Google Cloud Monitoring API. VM metrics will be collected by Google '
      'Compute Engine regardless of this setting.')
  parser.set_defaults(enable_cloud_monitoring=True)
  parser.add_argument(
      '--disk-size',
      type=int,
      help='Size in GB for node VM boot disks. Defaults to 100GB.')
  parser.add_argument(
      '--username', '-u',
      help='The user name to use for cluster auth.',
      default='admin')
  parser.add_argument(
      '--cluster-version',
      help=argparse.SUPPRESS)


NO_CERTS_ERROR_FMT = '''\
Failed to get certificate data for cluster; the kubernetes
api may not be accessible. You can retry later by running

{command}'''


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Create(base.Command):
  """Create a cluster for running containers."""

  @staticmethod
  def Args(parser):
    _Args(parser)

  def ParseCreateOptions(self, args):
    if not args.scopes:
      args.scopes = []
    cluster_ipv4_cidr = args.cluster_ipv4_cidr
    return api_adapter.CreateClusterOptions(
        node_machine_type=args.machine_type,
        scopes=args.scopes,
        num_nodes=args.num_nodes,
        user=args.username,
        password=args.password,
        cluster_version=args.cluster_version,
        network=args.network,
        subnetwork=args.subnetwork,
        cluster_ipv4_cidr=cluster_ipv4_cidr,
        node_disk_size_gb=args.disk_size,
        enable_cloud_logging=args.enable_cloud_logging,
        enable_cloud_monitoring=args.enable_cloud_monitoring)

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      Cluster message for the successfully created cluster.

    Raises:
      util.Error, if creation failed.
    """
    util.CheckKubectlInstalled()
    if not args.password:
      args.password = ''.join(random.SystemRandom().choice(
          string.ascii_letters + string.digits) for _ in range(16))

    adapter = self.context['api_adapter']

    if not args.scopes:
      args.scopes = []
    cluster_ref = adapter.ParseCluster(args.name)
    options = self.ParseCreateOptions(args)

    try:
      operation_ref = adapter.CreateCluster(cluster_ref, options)
      if not args.wait:
        return adapter.GetCluster(cluster_ref)

      adapter.WaitForOperation(
          operation_ref,
          'Creating cluster {0}'.format(cluster_ref.clusterId),
          timeout_s=args.timeout)
      cluster = adapter.GetCluster(cluster_ref)
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))

    log.CreatedResource(cluster_ref)
    # Persist cluster config
    current_context = kconfig.Kubeconfig.Default().current_context
    c_config = util.ClusterConfig.Persist(
        cluster, cluster_ref.projectId, self.cli)
    if not c_config.has_certs:
      # Purge config so we retry the cert fetch on next kubectl command
      util.ClusterConfig.Purge(
          cluster.name, cluster.zone, cluster_ref.projectId)
      # reset current context
      if current_context:
        kubeconfig = kconfig.Kubeconfig.Default()
        kubeconfig.SetCurrentContext(current_context)
        kubeconfig.SaveToFile()
      raise util.Error(NO_CERTS_ERROR_FMT.format(command=' '.join(
          args.command_path[:-1] + ['get-credentials', cluster.name])))
    return cluster

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    self.context['api_adapter'].PrintClusters([result])


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class CreateBeta(Create):
  """Create a cluster for running containers."""


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class CreateAlpha(Create):
  """Create a cluster for running containers."""
