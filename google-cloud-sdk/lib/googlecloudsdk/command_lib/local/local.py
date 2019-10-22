# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Library for manipulating serverless local development setup."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import base64
import os
import os.path
import re
from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.command_lib.local import yaml_helper
from googlecloudsdk.core import config
from googlecloudsdk.core import yaml
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import files
import six

IAM_MESSAGE_MODULE = apis.GetMessagesModule('iam', 'v1')
CRM_MESSAGE_MODULE = apis.GetMessagesModule('cloudresourcemanager', 'v1')

_POD_AND_SERVICES_TEMPLATE = """
apiVersion: v1
kind: Pod
metadata:
  name: {service}
  labels:
    service: {service}
spec:
  containers:
  - name: {service}-container
    image: {image}
    env:
    - name: PORT
      value: "8080"
    ports:
    - containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: {service}
spec:
  type: LoadBalancer
  selector:
    service: {service}
  ports:
  - protocol: TCP
    port: 8080
    targetPort: 8080
"""


def CreatePodAndService(service_name, image_name):
  """Create a pod and service specification for a service.

  Args:
    service_name: Name of the service.
    image_name: Image tag.

  Returns:
    List of dictionary objects representing the service and image yaml.
  """
  yaml_text = _POD_AND_SERVICES_TEMPLATE.format(
      service=service_name, image=image_name)
  return list(yaml.load_all(yaml_text))


# Regular expression for parsing a service account email address.
# Format is [id]@[project].iam.gserviceaccount.com
_SERVICE_ACCOUNT_RE = re.compile(
    r'(?P<id>[^@]+)@(?P<project>[^\.]+).iam.gserviceaccount.com')


def CreateDevelopmentServiceAccount(service_account_email):
  """Creates a service account for local development.

  Args:
    service_account_email: Email of the service account.

  Returns:
    The resource name of the service account.
  """
  matcher = _SERVICE_ACCOUNT_RE.match(service_account_email)
  if not matcher:
    raise ValueError(service_account_email +
                     ' is not a valid service account address')
  project_name = matcher.group('project')
  service_account_name = 'projects/{project}/serviceAccounts/{account}'.format(
      project=project_name, account=service_account_email)

  _CreateAccount('Serverless Local Development Service Account',
                 matcher.group('id'), project_name)

  # Make the service account an editor on the project
  _AddBinding(project_name, 'serviceAccount:' + service_account_email,
              'roles/editor')

  return service_account_name


def _CreateAccount(display_name, account_id, project):
  """Create an account if it does not already exist.

  Args:
    display_name: (str) Display name.
    account_id: (str) User account id.
    project: (str) Project name.
  """
  service = apis.GetClientInstance('iam', 'v1')
  try:
    service_account_msg = IAM_MESSAGE_MODULE.ServiceAccount(
        displayName=display_name)
    request = IAM_MESSAGE_MODULE.CreateServiceAccountRequest(
        accountId=account_id, serviceAccount=service_account_msg)
    service.projects_serviceAccounts.Create(
        IAM_MESSAGE_MODULE.IamProjectsServiceAccountsCreateRequest(
            name='projects/' + project, createServiceAccountRequest=request))
  except apitools_exceptions.HttpConflictError:
    # If account already exists, we can ignore the error
    pass


def _AddBinding(project, account, role):
  """Adds a binding.

  Args:
    project: (str) Project name.
    account: (str) User account.
    role: (str) Role.
  """
  crm_client = apis.GetClientInstance('cloudresourcemanager', 'v1')
  policy = crm_client.projects.GetIamPolicy(
      CRM_MESSAGE_MODULE.CloudresourcemanagerProjectsGetIamPolicyRequest(
          resource=project))

  if not iam_util.BindingInPolicy(policy, account, role):
    iam_util.AddBindingToIamPolicy(CRM_MESSAGE_MODULE.Binding, policy, account,
                                   role)
    req = CRM_MESSAGE_MODULE.CloudresourcemanagerProjectsSetIamPolicyRequest(
        resource=project,
        setIamPolicyRequest=CRM_MESSAGE_MODULE.SetIamPolicyRequest(
            policy=policy))
    crm_client.projects.SetIamPolicy(req)


_CREDENTIAL_SECRET_NAME = 'local-development-credential'


def AddServiceAccountSecret(configs):
  """Add a service account secret and mounts to kubernetes configs.

  Args:
    configs: List of kubernetes yaml configurations as dictionaries.
  """
  pods = (config for config in configs if config['kind'] == 'Pod')
  for pod in pods:
    volumes = yaml_helper.GetOrCreate(pod, ('spec', 'volumes'), list)
    _AddSecretVolume(volumes, _CREDENTIAL_SECRET_NAME)
    for container in yaml_helper.GetOrCreate(pod, ('spec', 'containers'), list):
      mounts = yaml_helper.GetOrCreate(container, ('volumeMounts',), list)
      _AddVolumeMount(mounts, _CREDENTIAL_SECRET_NAME)
      envs = yaml_helper.GetOrCreate(container, ('env',), list)
      _AddSecretEnvVar(envs, _CREDENTIAL_SECRET_NAME)


_SECRET_TEMPLATE = """
apiVersion: v1
kind: Secret
metadata:
  name: local-development-credential
type: Opaque
"""


def CreateServiceAccountKey(service_account_name):
  """Create a service account key.

  Args:
    service_account_name: Name of service acccount.

  Returns:
    The contents of the generated private key file as a string.
  """
  default_credential_path = os.path.join(
      config.Paths().global_config_dir,
      _Utf8ToBase64(service_account_name) + '.json')
  credential_file_path = os.environ.get('LOCAL_CREDENTIAL_PATH',
                                        default_credential_path)
  if os.path.exists(credential_file_path):
    return files.ReadFileContents(credential_file_path)

  warning_msg = ('Creating a user-managed service account key for '
                 '{service_account_name}. This service account key will be '
                 'the default credential pointed to by '
                 'GOOGLE_APPLICATION_CREDENTIALS in the local development '
                 'environment. The user is responsible for the storage,'
                 'rotation, and deletion of this key. A copy of this key will '
                 'be stored at {local_key_path}').format(
                     service_account_name=service_account_name,
                     local_key_path=credential_file_path)
  console_io.PromptContinue(
      message=warning_msg, prompt_string='Continue?', cancel_on_no=True)

  service = apis.GetClientInstance('iam', 'v1')
  message_module = service.MESSAGES_MODULE

  create_key_request = (
      message_module.IamProjectsServiceAccountsKeysCreateRequest(
          name=service_account_name,
          createServiceAccountKeyRequest=message_module
          .CreateServiceAccountKeyRequest(
              privateKeyType=message_module.CreateServiceAccountKeyRequest
              .PrivateKeyTypeValueValuesEnum.TYPE_GOOGLE_CREDENTIALS_FILE)))
  key = service.projects_serviceAccounts_keys.Create(create_key_request)

  files.WriteFileContents(credential_file_path, key.privateKeyData)

  return six.u(key.privateKeyData)


def LocalDevelopmentSecretSpec(key):
  """Create a kubernetes yaml spec for a secret.

  Args:
    key: (str) The private key as a JSON string.

  Returns:
    Dictionary representing yaml dictionary.
  """
  yaml_config = yaml.load(_SECRET_TEMPLATE)
  yaml_config['stringData'] = {'local_development_service_account.json': key}
  return yaml_config


_SECRET_VOLUME_TEMPLATE = """
name: {secret_name}
secret:
  secretName: {secret_name}
"""


def _AddSecretVolume(volumes, secret_name):
  """Add a secret volume to a list of volumes.

  Args:
    volumes: (list[dict]) List of volume specifications.
    secret_name: (str) Name of the secret.
  """
  if not _Contains(volumes, lambda volume: volume['name'] == secret_name):
    volumes.append(
        yaml.load(_SECRET_VOLUME_TEMPLATE.format(secret_name=secret_name)))


_SECRET_MOUNT_TEMPLATE = """
name: {secret_name}
mountPath: "/etc/{secret_path}"
readOnly: true
"""


def _AddVolumeMount(mounts, secret_name):
  """Add a secret volume mount.

  Args:
    mounts: (list[dict]) List of volume mount dictionaries.
    secret_name: (str) Name of the secret.
  """
  if not _Contains(mounts, lambda mount: mount['name'] == secret_name):
    yaml_text = _SECRET_MOUNT_TEMPLATE.format(
        secret_name=secret_name, secret_path=secret_name.replace('-', '_'))
    mounts.append(yaml.load(yaml_text))


def _IsApplicationCredentialVar(var):
  """Tests if the dictionary has name GOOGLE_APPLICATION_CREDENTIALS."""
  return var['name'] == 'GOOGLE_APPLICATION_CREDENTIALS'


def _AddSecretEnvVar(envs, secret_name):
  """Adds a environmental variable that points to the secret file.

  Add a environment varible where GOOGLE_APPLICATION_CREDENTIALS is the name
  and the path to the secret file is the value.

  Args:
    envs: (list[dict]) List of dictionaries with a name entry and value entry.
    secret_name: (str) Name of a secret.
  """
  if not _Contains(envs, _IsApplicationCredentialVar):
    envs.append({
        'name':
            'GOOGLE_APPLICATION_CREDENTIALS',
        'value':
            '/etc/' + secret_name.replace('-', '_') +
            '/local_development_service_account.json'
    })


def _FindByName(configs, name):
  """Finds a yaml config where the metadata name is the given name.

  Args:
    configs: (iterable[dict]) Iterable of yaml dictionaries.
    name: (str) Name for which to search.

  Returns:
    Dictionary where the name field of the metadata section is the given name.
    If no config matches that criteria, return None.
  """
  return _FindFirst(configs, lambda config: config['metadata']['name'] == name)


def _FindFirst(itr, matcher):
  """Finds a value in an iterable that matches the matcher.

  Args:
    itr: (iterable[object]) Iterable.
    matcher: Function accepting a single value and returning a boolean.

  Returns:
    The first value for which the matcher returns True. If no value matches,
    return None.
  """
  return next((x for x in itr if matcher(x)), None)


def _Contains(itr, matcher):
  """Returns True if the iterable contains a value specified by a matcher.

  Args:
    itr: (iterable[object]) Iterable.
    matcher: Function accepting a single value and returning a boolean.

  Returns:
    True if there is an object in the iterable for which the matcher True.
    False otherwise.
  """
  return not _IsEmpty(x for x in itr if matcher(x))


def _IsEmpty(itr):
  """Returns True if a given iterable returns no values."""
  return next(itr, None) is None


def _Utf8ToBase64(s):
  """Encode a utf-8 string as a base 64 string."""
  return base64.b64encode(s.encode('utf-8')).decode('utf-8')
