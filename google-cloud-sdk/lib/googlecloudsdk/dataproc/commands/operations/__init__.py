# Copyright 2015 Google Inc. All Rights Reserved.

"""The command group for cloud dataproc operations."""

from googlecloudsdk.calliope import base


class Operations(base.Group):
  """View and manage Google Cloud Dataproc operations."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To cancel an active operation, run:

            $ {command} cancel operation_id

          To view the details of an operation, run:

            $ {command} describe operation_id

          To see the list of all operations, run:

            $ {command} list

          To delete the record of an inactive operation, run:

            $ {command} delete operation_id
          """,
  }
