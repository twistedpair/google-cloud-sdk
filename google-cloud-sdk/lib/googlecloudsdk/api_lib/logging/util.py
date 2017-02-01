# Copyright 2014 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A library that is used to support logging commands."""

from apitools.base.py import extra_types

from googlecloudsdk.api_lib.resource_manager import folders
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import apis as core_apis
from googlecloudsdk.core import log as sdk_log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


class TypedLogSink(object):
  """Class that encapsulates V1 and V2 LogSinks during the transition period.

  Attributes:
    name: present in both versions.
    destination: present in both versions.
    filter: present in both versions.
    format: format of exported entries, only present in V2 sinks.
    type: one-of log/service/project.
    writer_identity: identity that needs to be granted write access
        to the destination, only present in V2 sinks.
  """

  def __init__(self, sink, log_name=None, service_name=None):
    """Creates a TypedLogSink with type based on constructor values.

    Args:
      sink: instance of V1 or V2 LogSink
      log_name: name of log, if it's a log-sink.
      service_name: name of service, if it's a service-sink
    """
    self.name = sink.name
    self.destination = sink.destination
    self.filter = None
    # Get sink type.
    if log_name:
      self.type = 'LOG: %s' % log_name
    elif service_name:
      self.type = 'SERVICE: %s' % service_name
    else:
      self.type = 'PROJECT SINK'
      self.filter = sink.filter if sink.filter else '(empty filter)'
    # Get sink format.
    if hasattr(sink, 'outputVersionFormat'):
      self.format = sink.outputVersionFormat.name
    else:
      self.format = 'V1'
    # Get sink writer identity
    if hasattr(sink, 'writerIdentity'):
      self.writer_identity = sink.writerIdentity
    else:
      self.writer_identity = ''


def GetClient():
  """Returns the client for the logging API."""
  return core_apis.GetClientInstance('logging', 'v2')


def GetMessages():
  """Returns the messages for the logging API."""
  return core_apis.GetMessagesModule('logging', 'v2')


def GetClientV1():
  """Returns the client for the v1 logging API."""
  return core_apis.GetClientInstance('logging', 'v1beta3')


def GetMessagesV1():
  """Returns the messages for the v1 logging API."""
  return core_apis.GetMessagesModule('logging', 'v1beta3')


def GetCurrentProjectParent():
  """Returns the relative resource path to the current project."""
  project = properties.VALUES.core.project.Get(required=True)
  project_ref = resources.REGISTRY.Parse(
      project, collection='cloudresourcemanager.projects')
  return project_ref.RelativeName()


def WarnOnUsingLogOrServiceArguments(args):
  """Warns on using the --log or --service flag."""
  if args.log:
    sdk_log.warn('--log is deprecated and will soon be removed.')
  elif args.service:
    sdk_log.warn('--service is deprecated and will soon be removed.')


def CheckLegacySinksCommandArguments(args):
  """Validates that legacy sinks only use project arguments."""
  WarnOnUsingLogOrServiceArguments(args)
  is_legacy_sink = args.log or args.service

  if is_legacy_sink and args.organization:
    raise exceptions.InvalidArgumentException(
        '--organization', 'Legacy sinks do not support this feature')

  if is_legacy_sink and args.folder:
    raise exceptions.InvalidArgumentException(
        '--folder', 'Legacy sinks do not support this feature')

  if is_legacy_sink and args.billing_account:
    raise exceptions.InvalidArgumentException(
        '--billing-account', 'Legacy sinks do not support this feature')


def CheckSinksCommandArguments(args):
  """Validates arguments that are provided to 'sinks create/update' command.

  Args:
    args: arguments returned from argparser.

  Raises:
    InvalidArgumentException on error.
  """
  is_legacy_sink = args.log or args.service

  if is_legacy_sink and args.log_filter:
    raise exceptions.InvalidArgumentException(
        '--log-filter', 'Legacy sinks do not support filters')

  if is_legacy_sink and args.output_version_format == 'V2':
    raise exceptions.InvalidArgumentException(
        '--output-version-format', 'Legacy sinks do not support V2 format')

  CheckLegacySinksCommandArguments(args)


def FormatTimestamp(timestamp):
  """Returns a string representing timestamp in RFC3339 format.

  Args:
    timestamp: A datetime.datetime object.

  Returns:
    A timestamp string in format, which is accepted by Cloud Logging.
  """
  return timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def ConvertToJsonObject(json_string):
  """Tries to convert the JSON string into JsonObject."""
  try:
    return extra_types.JsonProtoDecoder(json_string)
  except Exception as e:
    raise exceptions.ToolException('Invalid JSON value: %s' % e.message)


def AddNonProjectArgs(parser, help_string):
  """Adds optional arguments for non-project entities.

  Args:
    parser: parser to which arguments are added.
    help_string: text that is prepended to help for each argument.
  """
  entity_group = parser.add_mutually_exclusive_group()
  entity_group.add_argument(
      '--organization', required=False, metavar='ORGANIZATION_ID',
      completion_resource='cloudresourcemanager.organizations',
      help='{0} associated with this organization.'.format(help_string))

  entity_group.add_argument(
      '--folder', required=False, metavar='FOLDER_ID',
      help='{0} associated with this folder.'.format(help_string))

  entity_group.add_argument(
      '--billing-account', required=False, metavar='BILLING_ACCOUNT_ID',
      help='{0} associated with this billing account.'.format(help_string))


def GetParentFromArgs(args):
  """Returns the relative path to the parent from args.

  Args:
    args: command line args.

  Returns:
    The relative path. e.g. 'projects/foo', 'folders/1234'.
  """
  if args.organization:
    org_ref = resources.REGISTRY.Parse(
        args.organization,
        collection='cloudresourcemanager.organizations')
    return org_ref.RelativeName()
  elif args.folder:
    folder_ref = folders.FoldersRegistry().Parse(
        args.folder,
        collection='cloudresourcemanager.folders')
    return folder_ref.RelativeName()
  elif args.billing_account:
    billing_account_ref = resources.REGISTRY.Parse(
        args.billing_account,
        collection='cloudbilling.billingAccounts')
    return billing_account_ref.RelativeName()
  else:
    return GetCurrentProjectParent()


def CreateResourceName(parent, collection, resource_id):
  """Creates the full resource name.

  Args:
    parent: The project or organization id as a resource name, e.g.
      'projects/my-project' or 'organizations/123'.
    collection: The resource collection. e.g. 'logs'
    resource_id: The id within the collection , e.g. 'my-log'.

  Returns:
    resource, e.g. projects/my-project/logs/my-log.
  """
  # id needs to be escaped to create a valid resource name - i.e it is a
  # requirement of the Stackdriver Logging API that each component of a resource
  # name must have no slashes.
  return '{0}/{1}/{2}'.format(
      parent, collection, resource_id.replace('/', '%2F'))


def CreateLogResourceName(parent, log_id):
  """Creates the full log resource name.

  Args:
    parent: The project or organization id as a resource name, e.g.
      'projects/my-project' or 'organizations/123'.
    log_id: The log id, e.g. 'my-log'. This may already be a resource name, in
      which case parent is ignored and log_id is returned directly, e.g.
      CreateLogResourceName('projects/ignored', 'projects/bar/logs/my-log')
      returns 'projects/bar/logs/my-log'

  Returns:
    Log resource, e.g. projects/my-project/logs/my-log.
  """
  if '/logs/' in log_id:
    return log_id
  return CreateResourceName(parent, 'logs', log_id)


def ExtractLogId(log_resource):
  """Extracts only the log id and restore original slashes.

  Args:
    log_resource: The full log uri e.g projects/my-projects/logs/my-log.

  Returns:
    A log id that can be used in other commands.
  """
  log_id = log_resource.split('/logs/', 1)[1]
  return log_id.replace('%2F', '/')


def PrintPermissionInstructions(destination, writer_identity):
  """Prints a message to remind the user to set up permissions for a sink.

  Args:
    destination: the sink destination (either bigquery or cloud storage).
    writer_identity: identity to which to grant write access.
  """
  if writer_identity:
    grantee = '`{0}`'.format(writer_identity)
  else:
    grantee = 'the group `cloud-logs@google.com`'

  # TODO(b/31449674): if ladder needs test coverage
  if destination.startswith('bigquery'):
    sdk_log.status.Print('Please remember to grant {0} '
                         'the WRITER role on the dataset.'.format(grantee))
  elif destination.startswith('storage'):
    sdk_log.status.Print('Please remember to grant {0} '
                         'full-control access to the bucket.'.format(grantee))
  elif destination.startswith('pubsub'):
    sdk_log.status.Print('Please remember to grant {0} Pub/Sub '
                         'Publisher role to the topic.'.format(grantee))
  sdk_log.status.Print('More information about sinks can be found at https://'
                       'cloud.google.com/logging/docs/export/configure_export')
