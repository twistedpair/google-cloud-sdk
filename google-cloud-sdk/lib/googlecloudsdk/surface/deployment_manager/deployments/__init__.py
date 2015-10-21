# Copyright 2014 Google Inc. All Rights Reserved.

"""Deployment Manager deployments sub-group."""

from googlecloudsdk.calliope import base


class Deployments(base.Group):
  """Commands for Deployment Manager deployments.

  Commands to create, update, delete, and examine deployments of resources.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To create a deployment, run:

            $ {command} create my-deployment --config config.yaml

          To update a deployment, run:

            $ {command} update my-deployment --config new_config.yaml

          To stop a deployment create or update in progress, run:

            $ {command} stop my-deployment

          To cancel a previewed create or update, run:

            $ {command} cancel-preview my-deployment

          To delete a deployment, run:

            $ {command} delete my-deployment

          To view the details of a deployment, run:

            $ {command} describe my-deployment

          To see the list of all deployments, run:

            $ {command} list
          """,
  }
