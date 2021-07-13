# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Troubleshoot Network and firewall for ssh connection."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import random
import socket
import string

import time

from dns import resolver

from googlecloudsdk.api_lib.services import enable_api
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.compute import ssh_troubleshooter
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.console.console_io import OperationCancelledError

import six

_NUM_RANDOM_CHARACTERS = 5

_API_NETWORKMANAGEMENT_CLIENT_NAME = 'networkmanagement'
_API_COMPUTE_CLIENT_NAME = 'compute'
_API_CLIENT_VERSION_V1 = 'v1'

networkmanagement_permissions = [
    'networkmanagement.connectivitytests.get',
    'networkmanagement.connectivitytests.delete'
]


def _GetRandomSuffix():
  random_characters = [
      random.choice(string.ascii_lowercase + string.digits)
      for _ in range(_NUM_RANDOM_CHARACTERS)
  ]
  return ''.join(random_characters)


class NetworkTroubleshooter(ssh_troubleshooter.SshTroubleshooter):
  """Check network and firewall setting by running network connectivity test."""

  def __init__(self, project, zone, instance):
    self.project = project
    self.zone = zone
    self.instance = instance
    self.nm_client = apis.GetClientInstance(_API_NETWORKMANAGEMENT_CLIENT_NAME,
                                            _API_CLIENT_VERSION_V1)
    self.nm_message = apis.GetMessagesModule(_API_NETWORKMANAGEMENT_CLIENT_NAME,
                                             _API_CLIENT_VERSION_V1)
    self.compute_client = apis.GetClientInstance(_API_COMPUTE_CLIENT_NAME,
                                                 _API_CLIENT_VERSION_V1)
    self.compute_message = apis.GetMessagesModule(_API_COMPUTE_CLIENT_NAME,
                                                  _API_CLIENT_VERSION_V1)
    self.skip_troubleshoot = False
    self.test_id = 'ssh-troubleshoot-' + _GetRandomSuffix()

  def check_prerequisite(self):
    log.status.Print('---- Checking network connectivity ----')
    msg = ("The troubleshooting tool needs permission to check the VM's "
           'network connectivity.')
    prompt = 'Is it OK to run this test?'
    cancel = ('Test skipped.\n'
              'To manually test network connectivity, try reaching another '
              'device on the same network.')
    try:
      prompt_continue = console_io.PromptContinue(
          message=msg,
          prompt_string=prompt,
          cancel_on_no=True,
          cancel_string=cancel)
      self.skip_troubleshoot = not prompt_continue
    except OperationCancelledError:
      self.skip_troubleshoot = True

    if self.skip_troubleshoot:
      return

    # Enable API
    enable_api.EnableService(self.project.name,
                             'networkmanagement.googleapis.com')
    # Test IAM Permission
    missing_permissions = self._CheckNetworkManagementPermissions()

    if missing_permissions:
      log.status.Print(
          'Missing the IAM permissions {0} necessary to perform the network '
          'connectivity test. To manually test network connectivity, try '
          'reaching another device on the same network.'.format(
              ' '.join(missing_permissions)))
      self.skip_troubleshoot = True
      return

  def cleanup_resources(self):
    if not self.skip_troubleshoot:
      self._DeleteNetworkConnectivityTest()
    return

  def troubleshoot(self):
    if self.skip_troubleshoot:
      return

    self.ip_address = self._GetSourceIPAddress()
    log.status.Print('Your source IP address is {0}'.format(self.ip_address))
    if not self.ip_address:
      log.status.Print('Could not resolve source external IP address, can\'t '
                       'run network connectivity test')
      self.skip_troubleshoot = True
      return

    # Running network connectivity test if source IP available.
    operation_name = self._RunConnectivityTest()
    while not self._IsConnectivityTestFinish(operation_name):
      time.sleep(1)

    test_result = self._GetConnectivityTestResult()
    self._PrintConciseConnectivityTestResult(test_result)
    return

  def _RunConnectivityTest(self):
    connectivity_test = self._CreateConnectivityTest()
    # pylint: disable=line-too-long
    connectivity_test_create_req = self.nm_message.NetworkmanagementProjectsLocationsGlobalConnectivityTestsCreateRequest(
        parent='projects/{project_id}/locations/global'.format(
            project_id=self.project.name),
        testId=self.test_id,
        connectivityTest=connectivity_test)
    return self.nm_client.projects_locations_global_connectivityTests.Create(
        connectivity_test_create_req).name

  def _GetConnectivityTestResult(self):
    name = ('projects/{project_id}/locations/global/connectivityTests/'
            '{test_id}'.format(project_id=self.project.name,
                               test_id=self.test_id))
    connectivity_test_get_req = self.nm_message.NetworkmanagementProjectsLocationsGlobalConnectivityTestsGetRequest(
        name=name)
    return self.nm_client.projects_locations_global_connectivityTests.Get(
        connectivity_test_get_req)

  def _IsConnectivityTestFinish(self, name):
    # pylint: disable=line-too-long
    operation_get_req = self.nm_message.NetworkmanagementProjectsLocationsGlobalOperationsGetRequest(
        name=name)
    return self.nm_client.projects_locations_global_operations.Get(
        operation_get_req).done

  def _CreateConnectivityTest(self):
    return self.nm_message.ConnectivityTest(
        name='projects/{name}/locations/global/connectivityTests/{testId}'
        .format(name=self.project.name, testId=self.test_id),
        description='This connectivity test is created by '
        "'gcloud compute ssh --troubleshoot'",
        source=self.nm_message.Endpoint(
            ipAddress=self.ip_address, projectId=self.project.name),
        destination=self.nm_message.Endpoint(
            port=22,
            instance='projects/{project}/zones/{zone}/instances/{instance}'
            .format(
                project=self.project.name,
                zone=self.zone,
                instance=self.instance.name)),
        protocol='TCP')

  def _CheckNetworkManagementPermissions(self):
    resource_url = ('projects/{project_id}/locations/global/'
                    'connectivityTests/*'.format(project_id=self.project.name))
    test_permission_req = self.nm_message.TestIamPermissionsRequest(
        permissions=networkmanagement_permissions)
    # pylint: disable=line-too-long
    nm_testiampermission_req = self.nm_message.NetworkmanagementProjectsLocationsGlobalConnectivityTestsTestIamPermissionsRequest(
        resource=resource_url, testIamPermissionsRequest=test_permission_req)
    response = self.nm_client.projects_locations_global_connectivityTests.TestIamPermissions(nm_testiampermission_req)
    return set(networkmanagement_permissions) - set(response.permissions)

  def _DeleteNetworkConnectivityTest(self):
    # pylint: disable=line-too-long
    delete_req = self.nm_message.NetworkmanagementProjectsLocationsGlobalConnectivityTestsDeleteRequest(
        name='projects/{project_id}/locations/global/connectivityTests/{test_id}'
        .format(project_id=self.project.name, test_id=self.test_id))
    self.nm_client.projects_locations_global_connectivityTests.Delete(
        delete_req)

  def _GetSourceIPAddress(self):
    """Get current external IP from Google DNS server.

    Returns:
      str, an ipv4 address represented by string
    """
    re = resolver.Resolver()
    # pylint: disable=g-socket-gethostbyname
    re.nameservers = [socket.gethostbyname('ns1.google.com')]
    for rdata in re.query(qname='o-o.myaddr.l.google.com', rdtype='TXT'):
      return six.text_type(rdata).strip('"')
    return ''

  def _PrintConciseConnectivityTestResult(self, response):
    """Print concise network connectivity test result from response.

    Args:
      response: A response from projects_locations_global_connectivityTests Get

    Returns:

    """
    details = response.reachabilityDetails
    if details:
      log.status.Print('Network Connectivity Test Result: {0}'.format(
          details.result))
    traces = details.traces
    for trace in traces:
      log.status.Print('EndpointInfo {0}'.format(trace.endpointInfo))
      for step in trace.steps:
        log.status.Print('{0}'.format(step.description))
        log.status.Print('{0}'.format(step.state))
