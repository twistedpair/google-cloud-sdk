# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud bigquery datasets describe.
"""

from googlecloudsdk.api_lib.bigquery import bigquery_client_helper
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.surface import bigquery as commands


class DatasetsDescribe(base.Command):
  """Shows the last-modified date and access-control lists of a dataset.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('dataset_name', help='The name of the dataset.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Returns:
      a Dataset message
    """

    apitools_client = self.context[commands.APITOOLS_CLIENT_KEY]
    bigquery_messages = self.context[commands.BIGQUERY_MESSAGES_MODULE_KEY]
    resource_parser = self.context[commands.BIGQUERY_REGISTRY_KEY]
    resource = resource_parser.Parse(
        args.dataset_name, collection='bigquery.datasets')
    request = bigquery_messages.BigqueryDatasetsGetRequest(
        projectId=resource.projectId, datasetId=resource.datasetId)
    return apitools_client.datasets.Get(request)

  def Display(self, args, dataset):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      dataset: The Dataset message returned from the Run() method.
    """
    if dataset.friendlyName:
      log.out.Print('{0} (dataset {1})'.format(
          dataset.friendlyName, dataset.id))
    else:
      log.out.Print('Dataset {0}'.format(dataset.id))
    if dataset.description:
      log.out.Print(dataset.description)
    log.out.Print()
    log.out.Print(
        'Created: {0}'.format(
            bigquery_client_helper.FormatTime(dataset.creationTime)))
    log.out.Print(
        'Last modified: {0}'.format(
            bigquery_client_helper.FormatTime(dataset.lastModifiedTime)))
    log.out.Print('ACLs:')
    log.out.Print(_FormatAcl(dataset.access))


def _FormatAcl(acl):
  """Format a server-returned ACL for printing.

  Args:
    acl: the ACL

  Returns:
    the ACL as a string formatted for output
  """

  acl_entries = {
      'OWNER': [],
      'WRITER': [],
      'READER': [],
  }
  for entry in acl:
    role = entry.role
    # TODO(nhcohen): Replace the following if statement with a reflective loop.
    # How does one enumerate the attributes of an AccessValueListEntry?
    if entry.specialGroup:
      acl_entries[role].append(entry.specialGroup)
    elif entry.domain:
      acl_entries[role].append(entry.domain)
    elif entry.groupByEmail:
      acl_entries[role].append(entry.groupByEmail)
    elif entry.userByEmail:
      acl_entries[role].append(entry.userByEmail)
    elif entry.view:
      acl_entries[role].append(entry.view)
  result_lines = []
  if acl_entries['OWNER']:
    result_lines.extend(
        ['\tOwners:'
         + ',\n'.join(' {0}'.format(p) for p in acl_entries['OWNER'])])
  if acl_entries['WRITER']:
    result_lines.extend(
        ['\tWriters:'
         + ',\n'.join(' {0}'.format(p) for p in acl_entries['WRITER'])])
  if acl_entries['READER']:
    result_lines.extend(
        ['\tReaders:'
         + ',\n'.join(' {0}'.format(p) for p in acl_entries['READER'])])
  return '\n'.join(result_lines)
