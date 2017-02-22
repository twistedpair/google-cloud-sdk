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

"""Common helper methods for Service Management commands."""

import json
import re
import urllib2

from apitools.base.py import encoding
from apitools.base.py import exceptions as apitools_exceptions

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.resource import resource_printer
from googlecloudsdk.core.util import retry
from googlecloudsdk.core.util import times

import yaml


EMAIL_REGEX = re.compile(r'^.+@([^.@][^@]+)$')
FINGERPRINT_REGEX = re.compile(
    r'^([a-f0-9][a-f0-9]:){19}[a-f0-9][a-f0-9]$', re.IGNORECASE)
OP_BASE_CMD = 'gcloud service-management operations '
OP_DESCRIBE_CMD = OP_BASE_CMD + 'describe {0}'
OP_WAIT_CMD = OP_BASE_CMD + 'wait {0}'
SERVICES_COLLECTION = 'servicemanagement-v1.services'
CONFIG_COLLECTION = 'servicemanagement-v1.serviceConfigs'

ALL_IAM_PERMISSIONS = [
    'servicemanagement.services.get',
    'servicemanagement.services.getProjectSettings',
    'servicemanagement.services.delete',
    'servicemanagement.services.update',
    'servicemanagement.services.use',
    'servicemanagement.services.updateProjectSettings',
    'servicemanagement.services.check',
    'servicemanagement.services.report',
    'servicemanagement.services.setIamPolicy',
    'servicemanagement.services.getIamPolicy',
]


class OperationErrorException(core_exceptions.Error):

  def __init__(self, message):
    super(OperationErrorException, self).__init__(message)


def GetMessagesModule():
  return apis.GetMessagesModule('servicemanagement', 'v1')


def GetClientInstance():
  return apis.GetClientInstance('servicemanagement', 'v1')


def GetApiKeysMessagesModule():
  return apis.GetMessagesModule('apikeys', 'v1')


def GetApiKeysClientInstance():
  return apis.GetClientInstance('apikeys', 'v1')


def GetIamMessagesModule():
  return apis.GetMessagesModule('iam', 'v1')


def GetEndpointsServiceName():
  return 'endpoints.googleapis.com'


def GetServiceManagementServiceName():
  return 'servicemanagement.googleapis.com'


def GetValidatedProject(project_id):
  """Validate the project ID, if supplied, otherwise return the default project.

  Args:
    project_id: The ID of the project to validate. If None, gcloud's default
                project's ID will be returned.

  Returns:
    The validated project ID.
  """
  if project_id:
    properties.VALUES.core.project.Validate(project_id)
  else:
    project_id = properties.VALUES.core.project.Get(required=True)
  return project_id


def GetProjectSettings(service, consumer_project_id, view):
  """Returns the project settings for a given service, project, and view.

  Args:
    service: The service for which to return project settings.
    consumer_project_id: The consumer project id for which to return settings.
    view: The view (CONSUMER_VIEW or PRODUCER_VIEW).

  Returns:
    A ProjectSettings message with the settings populated.
  """
  # Shorten the request names for better readability
  get_request = (GetMessagesModule()
                 .ServicemanagementServicesProjectSettingsGetRequest)

  # Get the current list of quota settings to see if the quota override
  # exists in the first place.
  request = get_request(
      serviceName=service,
      consumerProjectId=consumer_project_id,
      view=view,
  )

  return GetClientInstance().services_projectSettings.Get(request)


def GetEnabledListRequest(project_id):
  return GetMessagesModule().ServicemanagementServicesListRequest(
      consumerId='project:' + project_id
  )


def GetAvailableListRequest():
  return GetMessagesModule().ServicemanagementServicesListRequest()


def GetProducedListRequest(project_id):
  return GetMessagesModule().ServicemanagementServicesListRequest(
      producerProjectId=project_id
  )


def PrettyPrint(resource, print_format='json'):
  """Prints the given resource.

  Args:
    resource: The resource to print out.
    print_format: The print_format value to pass along to the resource_printer.
  """
  resource_printer.Print(
      resources=[resource],
      print_format=print_format,
      out=log.out)


def FilenameMatchesExtension(filename, extensions):
  """Checks to see if a file name matches one of the given extensions.

  Args:
    filename: The full path to the file to check
    extensions: A list of candidate extensions.

  Returns:
    True if the filename matches one of the extensions, otherwise False.
  """
  f = filename.lower()
  for ext in extensions:
    if f.endswith(ext.lower()):
      return True
  return False


def IsProtoDescriptor(filename):
  return FilenameMatchesExtension(filename, ['.pb', '.descriptor'])


def ReadServiceConfigFile(file_path):
  try:
    mode = 'rb' if IsProtoDescriptor(file_path) else 'r'
    with open(file_path, mode) as f:
      return f.read()
  except IOError as ex:
    raise exceptions.BadFileException(
        'Could not open service config file [{0}]: {1}'.format(file_path, ex))


def PushNormalizedGoogleServiceConfig(service_name, project, config_contents):
  """Pushes a given normalized Google service configuration.

  Args:
    service_name: name of the service
    project: the producer project Id
    config_contents: the contents of the Google Service Config file.

  Returns:
    Config Id assigned by the server which is the service configuration Id
  """
  messages = GetMessagesModule()
  client = GetClientInstance()

  service_config = encoding.JsonToMessage(messages.Service, config_contents)
  service_config.producerProjectId = project
  create_request = (
      messages.ServicemanagementServicesConfigsCreateRequest(
          serviceName=service_name,
          service=service_config,
      ))
  service_resource = client.services_configs.Create(create_request)
  return service_resource.id


def GetServiceConfigIdFromSubmitConfigSourceResponse(response):
  return response.get('serviceConfig', {}).get('id')


def PushMultipleServiceConfigFiles(service_name, config_files, async,
                                   validate_only=False):
  """Pushes a given set of service configuration files.

  Args:
    service_name: name of the service.
    config_files: a list of ConfigFile message objects.
    async: whether to wait for aync operations or not.
    validate_only: whether to perform a validate-only run of the operation
                     or not.

  Returns:
    Full response from the SubmitConfigSource request.
  """
  messages = GetMessagesModule()
  client = GetClientInstance()

  config_source = messages.ConfigSource()
  config_source.files.extend(config_files)

  config_source_request = messages.SubmitConfigSourceRequest(
      configSource=config_source,
      validateOnly=validate_only,
  )
  submit_request = (
      messages.ServicemanagementServicesConfigsSubmitRequest(
          serviceName=service_name,
          submitConfigSourceRequest=config_source_request,
      ))
  api_response = client.services_configs.Submit(submit_request)
  operation = ProcessOperationResult(api_response, async)

  response = operation.get('response', {})
  diagnostics = response.get('diagnostics', [])

  for diagnostic in diagnostics:
    kind = diagnostic.get('kind', '').upper()
    logger = log.error if kind == 'ERROR' else log.warning
    logger('{l}: {m}'.format(
        l=diagnostic.get('location'), m=diagnostic.get('message')))

  return response


def PushOpenApiServiceConfig(
    service_name, spec_file_contents, spec_file_path, async,
    validate_only=False):
  """Pushes a given Open API service configuration.

  Args:
    service_name: name of the service
    spec_file_contents: the contents of the Open API spec file.
    spec_file_path: the path of the Open API spec file.
    async: whether to wait for aync operations or not.
    validate_only: whether to perform a validate-only run of the operation
                   or not.

  Returns:
    Full response from the SubmitConfigSource request.
  """
  messages = GetMessagesModule()

  config_file = messages.ConfigFile(
      fileContents=spec_file_contents,
      filePath=spec_file_path,
      # Always use YAML because JSON is a subset of YAML.
      fileType=(messages.ConfigFile.
                FileTypeValueValuesEnum.OPEN_API_YAML),
  )
  return PushMultipleServiceConfigFiles(service_name, [config_file], async,
                                        validate_only=validate_only)


def CreateServiceIfNew(service_name, project):
  """Creates a Service resource if it does not already exist.

  Args:
    service_name: name of the service to be returned or created.
    project: the project Id
  """
  messages = GetMessagesModule()
  client = GetClientInstance()
  get_request = messages.ServicemanagementServicesGetRequest(
      serviceName=service_name,
  )
  try:
    client.services.Get(get_request)
  except apitools_exceptions.HttpError as error:
    if error.status_code == 404:
      # create service
      create_request = messages.ManagedService(
          serviceName=service_name,
          producerProjectId=project,
      )
      client.services.Create(create_request)
    else:
      raise error


def ConvertUTCDateTimeStringToLocalTimeString(utc_string):
  """Returns a string representation of the given UTC string in local time.

  Args:
    utc_string: The string representation of the UTC datetime.

  Returns:
    A string representing the input time in local time. The format will follow
    '%Y-%m-%d %H:%M:%S %Z'.
  """
  try:
    utc_dt = times.ParseDateTime(utc_string)
  except ValueError:
    log.warn('Failed to parse UTC string %s', utc_string)
    return utc_string
  except OverflowError:
    log.warn('Parsed UTC date exceeds largest valid C integer on this system')
    return utc_string
  return times.FormatDateTime(
      utc_dt, '%Y-%m-%d %H:%M:%S %Z', tzinfo=times.LOCAL)


def GetByteStringFromFingerprint(fingerprint):
  """Helper function to create a byte string from a SHA fingerprint.

  Args:
    fingerprint: The fingerprint to transform in the form of
                 "12:34:56:78:90:...:EF".

  Returns:
    The fingerprint converted to a byte string (excluding the colons).
  """
  if not ValidateFingerprint(fingerprint):
    raise exceptions.ToolException('Invalid fingerprint')
  byte_tokens = fingerprint.split(':')
  return str(bytearray([int(b, 16) for b in byte_tokens]))


def ValidateFingerprint(fingerprint):
  return re.match(FINGERPRINT_REGEX, fingerprint) is not None


def ValidateEmailString(email):
  """Returns true if the input is a valid email string.

  This method uses a somewhat rudimentary regular expression to determine
  input validity, but it should suffice for basic sanity checking.

  It also verifies that the email string is no longer than 254 characters,
  since that is the specified maximum length.

  Args:
    email: The email string to validate

  Returns:
    A bool -- True if the input is valid, False otherwise
  """
  return EMAIL_REGEX.match(email or '') is not None and len(email) <= 254


def ProcessOperationResult(result, async=False):
  """Validate and process Operation outcome for user display.

  Args:
    result: The message to process (expected to be of type Operation)'
    async: If False, the method will block until the operation completes.

  Returns:
    The processed Operation message in Python dict form
  """
  op = GetProcessedOperationResult(result, async)
  if async:
    cmd = OP_WAIT_CMD.format(op.get('name'))
    log.status.Print('Asynchronous operation is in progress... '
                     'Use the following command to wait for its '
                     'completion:\n {0}'.format(cmd))
  else:
    cmd = OP_DESCRIBE_CMD.format(op.get('name'))
    log.status.Print('Operation finished successfully. '
                     'The following command can describe '
                     'the Operation details:\n {0}'.format(cmd))

  return op


def GetProcessedOperationResult(result, async=False):
  """Validate and process Operation result message for user display.

  This method checks to make sure the result is of type Operation and
  converts the StartTime field from a UTC timestamp to a local datetime
  string.

  Args:
    result: The message to process (expected to be of type Operation)'
    async: If False, the method will block until the operation completes.

  Returns:
    The processed message in Python dict form
  """
  if not result:
    return

  messages = GetMessagesModule()

  RaiseIfResultNotTypeOf(result, messages.Operation)

  result_dict = encoding.MessageToDict(result)

  if not async:
    op_name = result_dict['name']
    op_ref = resources.REGISTRY.Parse(
        op_name,
        collection='servicemanagement.operations')
    log.status.Print(
        'Waiting for async operation {0} to complete...'.format(op_name))
    result_dict = encoding.MessageToDict(WaitForOperation(
        op_ref, apis.GetClientInstance('servicemanagement', 'v1')))

  # Convert metadata startTime to local time
  if 'metadata' in result_dict and 'startTime' in result_dict['metadata']:
    result_dict['metadata']['startTime'] = (
        ConvertUTCDateTimeStringToLocalTimeString(
            result_dict['metadata']['startTime']))

  return result_dict


def RaiseIfResultNotTypeOf(test_object, expected_type, nonetype_ok=False):
  if nonetype_ok and test_object is None:
    return
  if not isinstance(test_object, expected_type):
    raise TypeError('result must be of type %s' % expected_type)


def GetCallerViews():
  messages = GetMessagesModule()
  get_request = messages.ServicemanagementServicesProjectSettingsGetRequest
  return {
      'CONSUMER': get_request.ViewValueValuesEnum.CONSUMER_VIEW,
      'PRODUCER': get_request.ViewValueValuesEnum.PRODUCER_VIEW,
      'ALL': get_request.ViewValueValuesEnum.ALL,
  }


def WaitForOperation(operation_ref, client):
  """Waits for an operation to complete.

  Args:
    operation_ref: A reference to the operation on which to wait.
    client: The client object that contains the GetOperation request object.

  Raises:
    ToolException: if the operation does not complete in time.
    OperationErrorException: if the operation fails.

  Returns:
    The Operation object, if successful. Raises an exception on failure.
  """
  WaitForOperation.operation_response = None
  messages = GetMessagesModule()
  operation_id = operation_ref.operationsId

  def _CheckOperation(operation_id):  # pylint: disable=missing-docstring
    request = messages.ServicemanagementOperationsGetRequest(
        operationsId=operation_id,
    )

    result = client.operations.Get(request)

    if result.done:
      WaitForOperation.operation_response = result
      return True
    else:
      return False

  # Wait for no more than 30 minutes while retrying the Operation retrieval
  try:
    retry.Retryer(exponential_sleep_multiplier=1.1, wait_ceiling_ms=10000,
                  max_wait_ms=30*60*1000).RetryOnResult(
                      _CheckOperation, [operation_id], should_retry_if=False,
                      sleep_ms=1500)
  except retry.MaxRetrialsException:
    raise exceptions.ToolException('Timed out while waiting for '
                                   'operation {0}. Note that the operation '
                                   'is still pending.'.format(operation_id))

  # Check to see if the operation resulted in an error
  if WaitForOperation.operation_response.error is not None:
    raise OperationErrorException(
        'The operation with ID {0} resulted in a failure.'.format(operation_id))

  # If we've gotten this far, the operation completed successfully,
  # so return the Operation object
  return WaitForOperation.operation_response


def LoadJsonOrYaml(input_string):
  """Tries to load input string as JSON first, then YAML if that fails.

  Args:
    input_string: The string to convert to a dictionary

  Returns:
    A dictionary of the resulting decoding, or None if neither format could be
    detected.
  """
  def TryJson():
    try:
      return json.loads(input_string)
    except ValueError:
      log.info('No JSON detected in service config. Trying YAML...')

  def TryYaml():
    try:
      return yaml.load(input_string)
    except yaml.YAMLError as e:
      if hasattr(e, 'problem_mark'):
        mark = e.problem_mark
        log.error('Service config YAML had an error at position (%s:%s)'
                  % (mark.line+1, mark.column+1))

  # First, try to decode JSON. If that fails, try to decode YAML.
  return TryJson() or TryYaml()


def GenerateManagementUrl(service, project):
  return ('https://console.cloud.google.com/endpoints/api/'
          '{service}/overview?project={project}'.format(
              service=urllib2.quote(service),
              project=urllib2.quote(project)))
