# Copyright 2015 Google Inc. All Rights Reserved.

"""The command group for cloud dataproc clusters."""

from googlecloudsdk.calliope import base


class Clusters(base.Group):
  """Create and manage Google Cloud Dataproc clusters."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To create a cluster, run:

            $ {command} create my_cluster

          To resize a cluster, run:

            $ {command} update my_cluster --num_workers 5

          To delete a cluster, run:

            $ {command} delete my_cluster

          To view the details of a cluster, run:

            $ {command} describe my_cluster

          To see the list of all clusters, run:

            $ {command} list
          """,
  }
