# Copyright 2014 Google Inc. All Rights Reserved.

"""Deployment Manager operations sub-group."""

from googlecloudsdk.calliope import base


class Operations(base.Group):
  """Commands for Deployment Manager operations.

  Commands to list, examine, and wait for long-running operations.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To view the details of an operation, run:

            $ {command} describe operation-name

          To see the list of all operations, run:

            $ {command} list

          To wait for an operation to complete, run:

            $ {command} wait operation-name
          """,
  }
