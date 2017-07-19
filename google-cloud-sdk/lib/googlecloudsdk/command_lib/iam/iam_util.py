# Copyright 2016 Google Inc. All Rights Reserved.
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
"""General IAM utilities used by the Cloud SDK."""
from apitools.base.protorpclite import messages as apitools_messages
from apitools.base.py import encoding

from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions as gcloud_exceptions
from googlecloudsdk.command_lib.iam import completers
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import files

import yaml

msgs = core_apis.GetMessagesModule('iam', 'v1')
MANAGED_BY = (msgs.IamProjectsServiceAccountsKeysListRequest
              .KeyTypesValueValuesEnum)
CREATE_KEY_TYPES = (msgs.CreateServiceAccountKeyRequest
                    .PrivateKeyTypeValueValuesEnum)
KEY_TYPES = (msgs.ServiceAccountKey.PrivateKeyTypeValueValuesEnum)
PUBLIC_KEY_TYPES = (
    msgs.IamProjectsServiceAccountsKeysGetRequest.PublicKeyTypeValueValuesEnum)

SERVICE_ACCOUNTS_COLLECTION = 'iam.projects.serviceAccounts'

SERVICE_ACCOUNT_FORMAT = 'table(displayName:label=NAME, email)'
SERVICE_ACCOUNT_KEY_FORMAT = """
    table(
        name.scope(keys):label=KEY_ID,
        validAfterTime:label=CREATED_AT,
        validBeforeTime:label=EXPIRES_AT
    )
"""


class IamEtagReadError(core_exceptions.Error):
  """IamEtagReadError is raised when etag is badly formatted."""


def AddArgsForAddIamPolicyBinding(parser, completer=None):
  """Adds the IAM policy binding arguments for role and members.

  Args:
    parser: An argparse.ArgumentParser-like object to which we add the argss.
    completer: A command_lib.iam.completers.IamRolesCompleter class to complete
      the --role flag value.

  Raises:
    ArgumentError if one of the arguments is already defined in the parser.
  """

  parser.add_argument(
      '--role', required=True, completer=completer,
      help='Define the role of the member.')
  parser.add_argument(
      '--member', required=True,
      help='The member to add to the binding. '
      'Should be of the form `user:user_email` '
      '(e.g. `user:test-user@gmail.com.`)')


def AddArgsForRemoveIamPolicyBinding(parser, completer=None):
  """Adds the IAM policy binding arguments for role and members.

  Args:
    parser: An argparse.ArgumentParser-like object to which we add the argss.
    completer: A command_lib.iam.completers.IamRolesCompleter class to complete
      the --role flag value.

  Raises:
    ArgumentError if one of the arguments is already defined in the parser.
  """

  parser.add_argument(
      '--role', required=True, completer=completer,
      help='The role to remove the member from.')
  parser.add_argument(
      '--member', required=True,
      help='The member to add to the binding. '
      'Should be of the form `user:user_email` '
      '(e.g. `user:test-user@gmail.com.`)')


def AddBindingToIamPolicy(binding_message_type, policy, member, role):
  """Given an IAM policy, add new bindings as specified by args.

  An IAM binding is a pair of role and member. Check if the arguments passed
  define both the role and member attribute, create a binding out of their
  values, and append it to the policy.

  Args:
    binding_message_type: The protorpc.Message of the Binding to create
    policy: IAM policy to which we want to add the bindings.
    member: The member to add to IAM policy.
    role: The role the member should have.
  """

  # First check all bindings to see if the member is already in a binding with
  # the same role.
  # A policy can have multiple bindings with the same role. This is why we need
  # to explicitly do this as a separate, first, step and check all bindings.
  for binding in policy.bindings:
    if binding.role == role:
      if member in binding.members:
        return  # Nothing to do. Member already has the role.

  # Second step: check to see if a binding already exists with the same role and
  # add the member to this binding. This is to not create new bindings with
  # the same role.
  for binding in policy.bindings:
    if binding.role == role:
      binding.members.append(member)
      return

  # Third step: no binding was found that has the same role. Create a new one.
  policy.bindings.append(binding_message_type(
      members=[member], role='{0}'.format(role)))


def RemoveBindingFromIamPolicy(policy, member, role):
  """Given an IAM policy, add remove bindings as specified by the args.

  An IAM binding is a pair of role and member. Check if the arguments passed
  define both the role and member attribute, search the policy for a binding
  that contains this role and member, and remove it from the policy.

  Args:
    policy: IAM policy from which we want to remove bindings.
    member: The member to remove from the IAM policy.
    role: The role the member should be removed from.
  """

  # First, remove the member from any binding that has the given role.
  # A server policy can have duplicates.
  for binding in policy.bindings:
    if binding.role == role and member in binding.members:
      binding.members.remove(member)

  # Second, remove any empty bindings.
  policy.bindings[:] = [b for b in policy.bindings if b.members]


def ConstructUpdateMaskFromPolicy(policy_file_path):
  """Construct a FieldMask based on input policy.

  Args:
    policy_file_path: Path to the JSON or YAML IAM policy file.
  Returns:
    a FieldMask containing policy fields to be modified, based on which fields
    are present in the input file.
  """
  policy_file = files.GetFileContents(policy_file_path)
  try:
    # Since json is a subset of yaml, parse file as yaml.
    policy = yaml.load(policy_file)
  except yaml.YAMLError as e:
    raise gcloud_exceptions.BadFileException(
        'Policy file {0} is not a properly formatted JSON or YAML policy file'
        '. {1}'.format(policy_file_path, str(e)))

  # The IAM update mask should only contain top level fields. Sort the fields
  # for testing purposes.
  return ','.join(sorted(policy.keys()))


def ParsePolicyFile(policy_file_path, policy_message_type):
  """Construct an IAM Policy protorpc.Message from a JSON or YAML formated file.

  Args:
    policy_file_path: Path to the JSON or YAML IAM policy file.
    policy_message_type: Policy message type to convert JSON or YAML to.
  Returns:
    a protorpc.Message of type policy_message_type filled in from the JSON or
    YAML policy file.
  Raises:
    BadFileException if the JSON or YAML file is malformed.
  """
  try:
    policy = ParseJsonPolicyFile(policy_file_path, policy_message_type)
  except gcloud_exceptions.BadFileException:
    try:
      policy = ParseYamlPolicyFile(policy_file_path, policy_message_type)
    except gcloud_exceptions.BadFileException:
      raise gcloud_exceptions.BadFileException(
          'Policy file {0} is not a properly formatted JSON or YAML policy file'
          '.'.format(policy_file_path))

  if not policy.etag:
    msg = ('The specified policy does not contain an "etag" field '
           'identifying a specific version to replace. Changing a '
           'policy without an "etag" can overwrite concurrent policy '
           'changes.')
    console_io.PromptContinue(
        message=msg, prompt_string='Replace existing policy', cancel_on_no=True)
  return policy


def ParseJsonPolicyFile(policy_file_path, policy_message_type):
  """Construct an IAM Policy protorpc.Message from a JSON formated file.

  Args:
    policy_file_path: Path to the JSON IAM policy file.
    policy_message_type: Policy message type to convert JSON to.
  Returns:
    a protorpc.Message of type policy_message_type filled in from the JSON
    policy file.
  Raises:
    BadFileException if the JSON file is malformed.
    IamEtagReadError if the etag is badly formatted.
  """
  try:
    with open(policy_file_path) as policy_file:
      policy_json = policy_file.read()
  except EnvironmentError:
    # EnvironmnetError is parent of IOError, OSError and WindowsError.
    # Raised when file does not exist or can't be opened/read.
    raise core_exceptions.Error(
        'Unable to read policy file {0}'.format(policy_file_path))

  try:
    policy = encoding.JsonToMessage(policy_message_type, policy_json)
  except (ValueError) as e:
    # ValueError is raised when JSON is badly formatted
    raise gcloud_exceptions.BadFileException(
        'Policy file {0} is not a properly formatted JSON policy file. {1}'
        .format(policy_file_path, str(e)))
  except (apitools_messages.DecodeError) as e:
    # DecodeError is raised when etag is badly formatted (not proper Base64)
    raise IamEtagReadError(
        'The etag of policy file {0} is not properly formatted. {1}'
        .format(policy_file_path, str(e)))
  return policy


def ParseYamlPolicyFile(policy_file_path, policy_message_type):
  """Construct an IAM Policy protorpc.Message from a YAML formatted file.

  Args:
    policy_file_path: Path to the YAML IAM policy file.
    policy_message_type: Policy message type to convert YAML to.
  Returns:
    a protorpc.Message of type policy_message_type filled in from the YAML
    policy file.
  Raises:
    BadFileException if the YAML file is malformed.
    IamEtagReadError if the etag is badly formatted.
  """
  try:
    with open(policy_file_path) as policy_file:
      policy_to_parse = yaml.safe_load(policy_file)
  except EnvironmentError:
    # EnvironmnetError is parent of IOError, OSError and WindowsError.
    # Raised when file does not exist or can't be opened/read.
    raise core_exceptions.Error('Unable to read policy file {0}'.format(
        policy_file_path))
  except (yaml.scanner.ScannerError, yaml.parser.ParserError) as e:
    # Raised when the YAML file is not properly formatted.
    raise gcloud_exceptions.BadFileException(
        'Policy file {0} is not a properly formatted YAML policy file. {1}'
        .format(policy_file_path, str(e)))
  try:
    policy = encoding.PyValueToMessage(policy_message_type, policy_to_parse)
  except (AttributeError) as e:
    # Raised when the YAML file is not properly formatted YAML policy file.
    raise gcloud_exceptions.BadFileException(
        'Policy file {0} is not a properly formatted YAML policy file. {1}'
        .format(policy_file_path, str(e)))
  except (apitools_messages.DecodeError) as e:
    # DecodeError is raised when etag is badly formatted (not proper Base64)
    raise IamEtagReadError(
        'The etag of policy file {0} is not properly formatted. {1}'
        .format(policy_file_path, str(e)))
  return policy


def GetDetailedHelpForSetIamPolicy(collection, example_id, example_see_more='',
                                   additional_flags=''):
  """Returns a detailed_help for a set-iam-policy command.

  Args:
    collection: Name of the command collection (ex: "project", "dataset")
    example_id: Collection identifier to display in a sample command
        (ex: "my-project", '1234')
    example_see_more: Optional "See ... for details" message. If not specified,
        includes a default reference to IAM managing-policies documentation
    additional_flags: str, additional flags to include in the example command
        (after the command name and before the ID of the resource).
  Returns:
    a dict with boilerplate help text for the set-iam-policy command
  """
  if not example_see_more:
    example_see_more = """
          See https://cloud.google.com/iam/docs/managing-policies for details
          of the policy file format and contents."""

  additional_flags = additional_flags + ' ' if additional_flags else ''
  return {
      'brief': 'Set IAM policy for a {0}.'.format(collection),
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          The following command will read an IAM policy defined in a JSON file
          'policy.json' and set it for a {collection} with identifier '{id}'

            $ {{command}} {flags}{id} policy.json

          {see_more}""".format(collection=collection, id=example_id,
                               see_more=example_see_more,
                               flags=additional_flags)
  }


def GetDetailedHelpForAddIamPolicyBinding(collection, example_id,
                                          role='roles/editor'):
  """Returns a detailed_help for an add-iam-policy-binding command.

  Args:
    collection: Name of the command collection (ex: "project", "dataset")
    example_id: Collection identifier to display in a sample command
        (ex: "my-project", '1234')
    role: The sample role to use in the documentation. The default of
        'roles/editor' is usually sufficient, but if your command group's
        users would more likely use a different role, you can override it here.
  Returns:
    a dict with boilerplate help text for the add-iam-policy-binding command
  """
  return {
      'brief': 'Add IAM policy binding for a {0}.'.format(collection),
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          The following command will add an IAM policy binding for the role
          of '{role}' for the user 'test-user@gmail.com' on a {collection} with
          identifier '{example_id}'

            $ {{command}} {example_id} --member='user:test-user@gmail.com' --role='{role}'

          See https://cloud.google.com/iam/docs/managing-policies for details
          of policy role and member types.
          """.format(collection=collection, example_id=example_id, role=role)
  }


def GetDetailedHelpForRemoveIamPolicyBinding(collection, example_id,
                                             role='roles/editor'):
  """Returns a detailed_help for a remove-iam-policy-binding command.

  Args:
    collection: Name of the command collection (ex: "project", "dataset")
    example_id: Collection identifier to display in a sample command
        (ex: "my-project", '1234')
    role: The sample role to use in the documentation. The default of
        'roles/editor' is usually sufficient, but if your command group's
        users would more likely use a different role, you can override it here.
  Returns:
    a dict with boilerplate help text for the remove-iam-policy-binding command
  """
  return {
      'brief': 'Remove IAM policy binding for a {0}.'.format(collection),
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          The following command will remove a IAM policy binding for the role
          of '{role}' for the user 'test-user@gmail.com' on {collection} with
          identifier '{example_id}'

            $ {{command}} {example_id} --member='user:test-user@gmail.com' --role='{role}'

          See https://cloud.google.com/iam/docs/managing-policies for details
          of policy role and member types.
          """.format(collection=collection, example_id=example_id, role=role)
  }


def ManagedByFromString(managed_by):
  """Parses a string into a MANAGED_BY enum.

  MANAGED_BY is an enum of who manages a service account key resource. IAM
  will rotate any SYSTEM_MANAGED keys by default.

  Args:
    managed_by: A string representation of a MANAGED_BY. Can be one of *user*,
    *system* or *any*.

  Returns:
    A KeyTypeValueValuesEnum (MANAGED_BY) value.
  """
  if managed_by == 'user':
    return [MANAGED_BY.USER_MANAGED]
  elif managed_by == 'system':
    return [MANAGED_BY.SYSTEM_MANAGED]
  elif managed_by == 'any':
    return []
  else:
    return [MANAGED_BY.KEY_TYPE_UNSPECIFIED]


def KeyTypeFromString(key_str):
  """Parses a string into a KeyType enum.

  Args:
    key_str: A string representation of a KeyType. Can be either *p12* or
    *json*.

  Returns:
    A PrivateKeyTypeValueValuesEnum value.
  """
  if key_str == 'p12':
    return KEY_TYPES.TYPE_PKCS12_FILE
  elif key_str == 'json':
    return KEY_TYPES.TYPE_GOOGLE_CREDENTIALS_FILE
  else:
    return KEY_TYPES.TYPE_UNSPECIFIED


def KeyTypeToString(key_type):
  """Get a string version of a KeyType enum.

  Args:
    key_type: An enum of either KEY_TYPES or CREATE_KEY_TYPES.

  Returns:
    The string representation of the key_type, such that
    parseKeyType(keyTypeToString(x)) is a no-op.
  """
  if (key_type == KEY_TYPES.TYPE_PKCS12_FILE or
      key_type == CREATE_KEY_TYPES.TYPE_PKCS12_FILE):
    return 'p12'
  elif (key_type == KEY_TYPES.TYPE_GOOGLE_CREDENTIALS_FILE or
        key_type == CREATE_KEY_TYPES.TYPE_GOOGLE_CREDENTIALS_FILE):
    return 'json'
  else:
    return 'unspecified'


def KeyTypeToCreateKeyType(key_type):
  """Transforms between instances of KeyType enums.

  Transforms KeyTypes into CreateKeyTypes.

  Args:
    key_type: A ServiceAccountKey.PrivateKeyTypeValueValuesEnum value.

  Returns:
    A IamProjectsServiceAccountKeysCreateRequest.PrivateKeyTypeValueValuesEnum
    value.
  """
  # For some stupid reason, HTTP requests generates different enum types for
  # each instance of an enum in the proto buffer. What's worse is that they're
  # not equal to one another.
  if key_type == KEY_TYPES.TYPE_PKCS12_FILE:
    return CREATE_KEY_TYPES.TYPE_PKCS12_FILE
  elif key_type == KEY_TYPES.TYPE_GOOGLE_CREDENTIALS_FILE:
    return CREATE_KEY_TYPES.TYPE_GOOGLE_CREDENTIALS_FILE
  else:
    return CREATE_KEY_TYPES.TYPE_UNSPECIFIED


def KeyTypeFromCreateKeyType(key_type):
  """The inverse of *toCreateKeyType*."""
  if key_type == CREATE_KEY_TYPES.TYPE_PKCS12_FILE:
    return KEY_TYPES.TYPE_PKCS12_FILE
  elif key_type == CREATE_KEY_TYPES.TYPE_GOOGLE_CREDENTIALS_FILE:
    return KEY_TYPES.TYPE_GOOGLE_CREDENTIALS_FILE
  else:
    return KEY_TYPES.TYPE_UNSPECIFIED


def AccountNameValidator():
  # https://cloud.google.com/iam/reference/rest/v1/projects.serviceAccounts/create
  return arg_parsers.RegexpValidator(
      r'[a-z][a-z0-9\-]{4,28}[a-z0-9]',
      'Service account name must be between 6 and 30 characters (inclusive), '
      'must begin with a lowercase letter, and consist of alphanumeric '
      'characters that can be separated by hyphens.')


def ProjectToProjectResourceName(project):
  """Turns a project id into a project resource name."""
  return 'projects/{0}'.format(project)


def EmailToAccountResourceName(email):
  """Turns an email into a service account resource name."""
  return 'projects/-/serviceAccounts/{0}'.format(email)


def EmailAndKeyToResourceName(email, key):
  """Turns an email and key id into a key resource name."""
  return 'projects/-/serviceAccounts/{0}/keys/{1}'.format(email, key)


def GetKeyIdFromResourceName(name):
  """Gets the key id from a resource name. No validation is done."""
  return name.split('/')[5]


def PublicKeyTypeFromString(key_str):
  """Parses a string into a PublicKeyType enum.

  Args:
    key_str: A string representation of a PublicKeyType. Can be either *pem* or
    *raw*.

  Returns:
    A PublicKeyTypeValueValuesEnum value.
  """
  if key_str == 'pem':
    return PUBLIC_KEY_TYPES.TYPE_X509_PEM_FILE
  return PUBLIC_KEY_TYPES.TYPE_RAW_PUBLIC_KEY


def ServiceAccountsUriFunc(resource):
  """Transforms a service account resource into a URL string.

  Args:
    resource: The ServiceAccount object

  Returns:
    URL to the service account
  """

  ref = resources.REGISTRY.Parse(resource.uniqueId,
                                 {'projectsId': resource.projectId},
                                 collection=SERVICE_ACCOUNTS_COLLECTION)
  return ref.SelfLink()


def AddServiceAccountNameArg(parser, action='to act on'):
  """Adds the IAM service account name argument that supports tab completion.

  Args:
    parser: An argparse.ArgumentParser-like object to which we add the args.
    action: Action to display in the help message. Should be something like
      'to act on' or a relative phrase like 'whose policy to get'.

  Raises:
    ArgumentError if one of the arguments is already defined in the parser.
  """

  parser.add_argument('service_account',
                      metavar='SERVICE_ACCOUNT',
                      type=GetIamAccountFormatValidator(),
                      completer=completers.IamServiceAccountCompleter,
                      help=('The service account {}. The account should be '
                            'formatted as an email, like this: '
                            'my-iam-account@somedomain.com.'.format(action)))


def LogSetIamPolicy(name, kind):
  log.status.Print('Updated IAM policy for {} [{}].'.format(kind, name))


def GetIamAccountFormatValidator():
  """Checks that provided iam account identifier is a valid email address."""
  return arg_parsers.RegexpValidator(
      r'^.+@.+\..+$',  # Overly broad on purpose but catches most common issues.
      'Not a valid email address. It should be of the form: '
      'my-iam-account@somedomain.com or '
      'my-iam-account@PROJECT_ID.iam.gserviceaccount.com')
