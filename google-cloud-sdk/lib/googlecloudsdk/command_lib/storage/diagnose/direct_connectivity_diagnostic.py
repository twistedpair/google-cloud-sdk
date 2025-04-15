# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Direct Connectivity Diagnostic."""

import io
import ipaddress
import json
import os
import re
import socket
import tempfile
import uuid

from googlecloudsdk.command_lib.storage import path_util
from googlecloudsdk.command_lib.storage.diagnose import diagnostic
from googlecloudsdk.command_lib.storage.resources import gcs_resource_reference
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core.credentials import gce_cache
from googlecloudsdk.core.util import files
import requests


_CORE_CHECK_NAME = 'Direct Connectivity Upload'
_SUCCESS = 'Success.'


def _get_ips(dns_path, service_name):
  """Returns IPv4 and IPv6 addresses associated with a regular web URL."""
  res = []
  for ip in socket.getaddrinfo(dns_path, port=443, proto=socket.IPPROTO_TCP):
    if ip[0] == socket.AddressFamily.AF_INET6:
      res.append((ipaddress.ip_address(ip[4][0]), service_name + ' IPv6'))
    elif ip[0] == socket.AddressFamily.AF_INET:
      res.append((ipaddress.ip_address(ip[4][0]), service_name + ' IPv4'))
  return res


def _get_region_string_or_not_found(s):
  return '"{}"'.format(s.lower()) if s else '[Not Found]'


def _check_zone_prefix(region, zone):
  """Returns true if the region is a prefix of the given zone."""
  return zone.lower().startswith(region.lower())


def _exec_and_return_stdout(command):
  """Returns standard output from executing gcloud command."""
  command = execution_utils.ArgsForGcloud() + command
  out = io.StringIO()
  execution_utils.Exec(
      command,
      no_exit=True,
      out_func=out.write,
  )
  return out.getvalue().strip()


def _log_running_check(check_name):
  log.info('Running Check: {}'.format(check_name))


class DirectConnectivityDiagnostic(diagnostic.Diagnostic):
  """Direct Connectivity Diagnostic."""

  def __init__(
      self,
      bucket_resource: gcs_resource_reference.GcsBucketResource,
      logs_path=None,
  ):
    """Initializes the Direct Connectivity Diagnostic."""
    self._bucket_resource = bucket_resource
    self._cleaned_up = False
    self._object_path = 'direct_connectivity_diagnostics_' + str(uuid.uuid4())
    self._process_count = 1
    self._results = []
    self._retain_logs = bool(logs_path)
    self._thread_count = 1
    self._vm_zone = None

    if logs_path is None:
      self._logs_path = os.path.join(
          tempfile.gettempdir(),
          'direct_connectivity_log_'
          + path_util.generate_random_int_for_path()
          + '.txt',
      )
    else:
      self._logs_path = files.ExpandHomeDir(logs_path)

  @property
  def name(self) -> str:
    return 'Direct Connectivity Diagnostic'

  def _clean_up(self):
    """Restores environment variables and cleans up temporary cloud object."""
    if not self._cleaned_up:
      super(DirectConnectivityDiagnostic, self)._post_process()
      self._clean_up_objects(
          self._bucket_resource.storage_url.url_string, self._object_path
      )
      self._cleaned_up = True

  def _generic_check_for_string_in_logs(
      self,
      target_string,
  ):
    """Checks if target is substring of a line in the logs."""
    with files.FileReader(self._logs_path) as file_reader:
      for line in file_reader:
        if target_string in line:
          return True
    return False

  def _check_core_upload(self):
    """Returns true if can upload object over Direct Connectivity infra."""
    self._set_parallelism_env_vars()
    self._set_env_variable('ATTEMPT_DIRECT_PATH', 1)
    self._set_env_variable(
        'CLOUDSDK_STORAGE_PREFERRED_API', 'grpc_with_json_fallback'
    )
    self._set_env_variable('GRPC_TRACE', 'http')
    self._set_env_variable('GRPC_VERBOSITY', 'debug')

    with files.FileWriter(self._logs_path) as file_writer:
      command = execution_utils.ArgsForGcloud() + [
          '--verbosity=debug',
          'storage',
          'cp',
          '-',
          self._bucket_resource.storage_url.join(self._object_path).url_string,
      ]

      return_code = execution_utils.Exec(
          command,
          err_func=file_writer.write,
          in_str=self._generate_random_string(length=1),
          no_exit=True,
      )

    if return_code == 0:
      with files.FileReader(self._logs_path) as file_reader:
        for line in file_reader:
          if re.search(
              r'(?:\[ipv6:(?:%5B)?2001:4860:80[4-7].+\])?(?:\[ipv4:(?:%5B)?34\.126.+\])?',
              line,
          ):
            return _SUCCESS
    return 'Failed. See log at ' + self._logs_path

  def _check_private_service_connect(self):
    """Checks if connecting to PSC endpoint."""
    if self._generic_check_for_string_in_logs(
        # gcloud-disable-gdu-domain
        target_string='.p.googleapis.com'
    ):
      return (
          'Found PSC endpoint. For context, search for ".p.googleapis.com" in'
          ' logs at '
          + self._logs_path
      )
    return _SUCCESS

  def _check_inside_vm(self):
    """Checks if user is inside a GCE VM."""
    if gce_cache.GetOnGCE():
      return _SUCCESS
    return 'Detected this command is not being run from within a VM.'

  def _check_traffic_director_access(self):
    """Checks if user can access Traffic Director service."""
    try:
      # gcloud-disable-gdu-domain
      requests.get('https://directpath-pa.googleapis.com:443')
      return _SUCCESS
    except requests.exceptions.RequestException:
      return 'Unable to connect to Traffic Director.'

  def _check_firewalls(self):
    """Checks if user can access Traffic Director service."""
    desired_ip_networks = [
        (ipaddress.ip_network('34.126.0.0/18'), 'Direct Connectivity IPv4'),
        (
            ipaddress.ip_network('2001:4860:8040::/42'),
            'Direct Connectivity IPv6',
        ),
    ]
    desired_ip_addresses = _get_ips(
        # gcloud-disable-gdu-domain
        'storage.googleapis.com',
        'storage.googleapis.com',
        # gcloud-disable-gdu-domain
    ) + _get_ips('directpath-pa.googleapis.com', 'Traffic Director')
    firewall_response = json.loads(
        _exec_and_return_stdout(
            ['compute', 'firewall-rules', 'list', '--format=json']
        )
    )
    found_any_problem = False
    for firewall in firewall_response:
      if firewall['direction'] != 'EGRESS' or firewall['disabled']:
        continue

      found_firewall_problem = False
      for firewall_ip_string in firewall['sourceRanges']:
        blocked_service = None
        firewall_network = ipaddress.ip_network(firewall_ip_string)
        for desired_ip_network, service_name in desired_ip_networks:
          try:
            if firewall_network.subnet_of(desired_ip_network):
              blocked_service = service_name
          except TypeError:  # Triggered by comparing IPv4 to IPv6.
            pass

        firewall_ip = ipaddress.ip_address(firewall_ip_string)
        for desired_ip_address, service_name in desired_ip_addresses:
          if desired_ip_address == firewall_ip:
            blocked_service = service_name

        if blocked_service is not None:
          log.error(
              'Found firewall blocking {}: "{}"'.format(
                  blocked_service, firewall_ip_string
              )
          )
          found_firewall_problem = True

      if found_firewall_problem:
        log.error(
            'To disable run "gcloud compute firewall-rules update --disabled'
            ' {}"'.format(firewall['name'])
        )
        found_any_problem = True

    if found_any_problem:
      return 'Found conflicting firewalls. See STDERR messages.'
    return _SUCCESS

  def _check_bucket_region(self):
    """Checks if bucket has problematic region."""

    bucket_location = self._bucket_resource.location.lower()

    # Dual-region buckets may have replicas in the same region as the VM. For
    # custom dual-regions, the VM must be in one of the regions covered by the
    # dual-region. For predefined dual-regions, the customer can check manually.
    if self._bucket_resource.location_type == 'dual-region':
      if self._bucket_resource.data_locations:
        regions = self._bucket_resource.data_locations
        for region in regions:
          if _check_zone_prefix(region, self._vm_zone):
            return _SUCCESS
        return (
            f'Bucket "{self._bucket_resource}" locations'
            f' {_get_region_string_or_not_found(regions[0])} and'
            f' {_get_region_string_or_not_found(regions[1])} do not include VM'
            f' "{socket.gethostname()}" zone'
            f' {_get_region_string_or_not_found(self._vm_zone)}'
        )
      return (
          f'Found bucket "{self._bucket_resource}" is in a dual-region. Ensure '
          f'VM "{socket.gethostname()}" is in one of the regions covered by '
          f'the dual-region by looking up the dual-region '
          f'{_get_region_string_or_not_found(self._bucket_resource.location)} '
          f'in the following table: '
          f'https://cloud.google.com/storage/docs/locations#predefined '
          f'VM zone {_get_region_string_or_not_found(self._vm_zone)} should '
          f'start with one of the regions covered by the dual-region '
          f'{_get_region_string_or_not_found(self._bucket_resource.location)}.'
      )
    # For other region types, the substring check is sufficient.
    if self._vm_zone and _check_zone_prefix(bucket_location, self._vm_zone):
      return _SUCCESS
    return 'Bucket "{}" location {} does not match VM "{}" zone {}'.format(
        self._bucket_resource,
        _get_region_string_or_not_found(bucket_location),
        socket.gethostname(),
        _get_region_string_or_not_found(self._vm_zone),
    )

  def _check_vm_has_service_account(self):
    """Checks if VM has a service account."""
    if not self._vm_zone:
      return 'Found no VM zone and, therefore, could not check service account.'
    service_accounts = _exec_and_return_stdout([
        'compute',
        'instances',
        'describe',
        socket.gethostname(),
        '--zone={}'.format(self._vm_zone),
        '--format=table[csv,no-heading](serviceAccounts)',
    ])
    if service_accounts and service_accounts.startswith('[{'):
      # VM with SA will respond with a string like: "[{'email': ..."
      return _SUCCESS
    return (
        'Compute VM missing service account. See: '
        'https://cloud.google.com/compute/docs/instances/change-service-account'
    )

  def _run(self):
    """Runs the diagnostic test."""
    log.warning(
        'This diagnostic is experimental. The output may change,'
        ' and checks may be added or removed at any time. Please do not rely on'
        ' the diagnostic being present.'
    )

    _log_running_check(_CORE_CHECK_NAME)
    res = self._check_core_upload()
    self._results.append(
        diagnostic.DiagnosticOperationResult(
            name=_CORE_CHECK_NAME,
            result=res,
            payload_description=(
                'Able to upload object to bucket using Direct'
                ' Connectivity network path.'
            ),
        )
    )
    if res == _SUCCESS:
      if not self._retain_logs and os.path.exists(self._logs_path):
        os.remove(self._logs_path)
      self._clean_up()
      return

    self._vm_zone = _exec_and_return_stdout([
        'compute',
        'instances',
        'list',
        '--filter=name:{}'.format(socket.gethostname()),
        '--format=table[csv,no-heading](zone)',
    ])

    for check, name, description in [
        (
            self._check_private_service_connect,
            'Private Service Connect',
            (
                'Checks for string in logs containing incompatible PSC endpoint'
                # gcloud-disable-gdu-domain
                ' of format "*.p.googleapis.com".'
            ),
        ),
        (
            self._check_inside_vm,
            'Compute Engine VM',
            (
                'Direct Connectivity is only accessible from within Compute'
                ' Engine virtual machines.'
            ),
        ),
        (
            self._check_traffic_director_access,
            'Traffic Director',
            (
                'Direct Connectivity requires access to the Traffic Director'
                ' service.'
            ),
        ),
        (
            self._check_firewalls,
            'Firewalls',
            (
                'Direct Connectivity requires access to various IP addresses'
                ' that may be blocked by firewalls.'
            ),
        ),
        (
            self._check_bucket_region,
            'Bucket Region',
            (
                'Direct Connectivity supports all bucket region types, but only'
                ' data with replicas in the same region as the VM will be'
                ' accessible. Consider co-locating the bucket and VM in the'
                ' same region.'
            ),
        ),
        (
            self._check_vm_has_service_account,
            'VM has Service Account',
            'Direct Connectivity requires the VM have a service account.',
        ),
    ]:
      try:
        _log_running_check(name)
        res = check()
      # pylint: disable=broad-except
      except Exception as e:
        # pylint: enable=broad-except
        res = e
      self._results.append(
          diagnostic.DiagnosticOperationResult(
              name=name,
              result=res,
              payload_description=description,
          )
      )

  def _post_process(self):
    """See _clean_up.

    Using redundant calls because we can clean up earlier during _run, and
    keeping _post_process ensures clean up if _run fails.
    """
    self._clean_up()

  @property
  def result(self) -> diagnostic.DiagnosticResult:
    """Returns the summarized result of the diagnostic execution."""
    return diagnostic.DiagnosticResult(
        name=self.name,
        operation_results=self._results,
    )
