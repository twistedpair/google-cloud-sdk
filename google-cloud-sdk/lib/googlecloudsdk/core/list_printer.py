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

"""List printer for Cloud Platform resources."""

from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import attrpath


def PrintResourceList(collection, items):
  """Print a list of cloud resources.

  Args:
    collection: str, The name of the collection to which the items belong.
    items: iterable, A list or otherwise iterable object that generates the
        rows of the list.
  """
  console_io.PrintExtendedList(items, COLLECTION_COLUMNS[collection])


def _Select(path, transform=None):
  """Get a column fetcher for the given attr path and transform.

  Args:
    path: str, The attr path that keys into the resource.
    transform: func(str)->str, A func that takes something found by the path
        and maps it to some other strip.

  Returns:
    func(obj)->str, A func that takes an object and returns the value
    for a particular column.
  """

  getter = attrpath.Selector(path)

  if transform is None:
    return getter

  def GetAndTransform(obj):
    return transform(getter(obj))
  return GetAndTransform


def _NameOnly(value):
  """Get only the last token from a longer path, usually the name.

  Intended to be a selector transform for URLs.

  Args:
    value: str, The value whose last token will be returned.

  Returns:
    str, The name from value.
  """
  if value:
    return value.split('/')[-1]
  return value


def _CommaList(default=None):
  def Transform(items):
    if not items:
      return default
    return ', '.join(items)
  return Transform


def _Boolean(value):
  """Returns a string indication whether a value is true ("truthy").

  Args:
    value: Any value.

  Returns:
    String indicating whether the value is true.
  """
  return '*' if value else '-'


def _DiskSize(value):
  """Returns a human readable string representation of the disk size.

  Args:
    value: str, Disk size represented as number of bytes.

  Returns:
    A human readable string representation of the disk size.
  """
  size = float(value)
  the_unit = 'TB'
  for unit in ['bytes', 'KB', 'MB', 'GB']:
    if size < 1024.0:
      the_unit = unit
      break
    size = float(size) / 1024.0
  if size == int(size):
    return '%d %s' % (size, the_unit)
  else:
    return '%3.1f %s' % (size, the_unit)


def _ScreenResolution(model):
  """Build a human readable string representation of a screen resolution.

  Args:
    model: a Test_v1.AndroidModel message (from ApiTools)

  Returns:
    Returns a human readable string representation of a screen resolution.
  """
  return '{y} x {x}'.format(y=model.screenY, x=model.screenX)


# Guidelines for choosing your resource columns:
# - Column headers are ANGRY_SNAKE_CASE, just like user input in usage. This
#   casing has a side effect in that column headers will never be confused for
#   fields in the API responses, which are camelCase.
# - Fields that are URL parameters (that is, they disambiguate your
#   resource) go first, starting at the end of the URL. So, often the first
#   column will be NAME. PROJECT is an exception: no PROJECT column unless the
#   resource being listed can be in a different project than the one found in
#   the project property.
# - If your resource has a STATUS column or something similar, put it last.
# - Aim for an 80-char-wide table, but if someone has a 70-char NAME it's not
#   your fault.


def _Default(default):
  def Transform(item):
    return default if item is None else item
  return Transform


def _SelectTime(path):
  return _Select(path, transform=lambda x: x and x.isoformat())


def _FormatOperationErrors(errs):
  if not errs:
    return None
  else:
    return '\n'.join(['[%s: %s]' % (e.code, e.message) for e in errs])


COLLECTION_COLUMNS = {
    # APPENGINE
    'app.module_versions': (
        ('MODULE', _Select('module')),
        ('VERSION', _Select('version')),
        ('TRAFFIC_SPLIT', _Select('traffic_split')),
    ),

    'app.versions': (
        ('SERVICE', _Select('service')),
        ('VERSION', _Select('id')),
        ('TRAFFIC_SPLIT', _Select('traffic_split',
                                  transform='{0:.2f}'.format)),
        ('LAST_DEPLOYED', _Select(
            'last_deployed_time',
            transform=lambda x: x and x.isoformat())),
        ('SERVING_STATUS', _Select('version.servingStatus'))
    ),

    # AUTOSCALER
    'autoscaler.instances': (
        ('NAME', _Select('name')),
        ('DESCRIPTION', _Select('description')),
        ('STATE', _Select('state')),
        ('STATE_DETAILS', _Select('state_details')),
    ),

    # BIGQUERY
    'bigquery.datasets': (
        ('DATASET_ID', _Select('datasetReference.datasetId')),
    ),
    'bigquery.jobs.describe': (
        ('JOB_TYPE', _Select('job_type')),
        ('STATE', _Select('state')),
        ('START_TIME', _Select('start_time')),
        ('DURATION', _Select('duration')),
        ('BYTES_PROCESSED', _Select('bytes_processed')),
    ),
    'bigquery.jobs.list': (
        ('JOB_ID', _Select('job_id')),
        ('JOB_TYPE', _Select('job_type')),
        ('STATE', _Select('state')),
        ('START_TIME', _Select('start_time')),
        ('DURATION', _Select('duration')),
    ),
    'bigquery.jobs.wait': (
        ('JOB_TYPE', _Select('job_type')),
        ('STATE', _Select('state')),
        ('START_TIME', _Select('start_time')),
        ('DURATION', _Select('duration')),
        ('BYTES_PROCESSED', _Select('bytes_processed')),
    ),
    'bigquery.projects': (
        ('PROJECT_ID', _Select('projectReference.projectId')),
        ('FRIENDLY_NAME', _Select('friendlyName')),
    ),
    'bigquery.tables.list': (
        ('ID', _Select('id')),
        ('TABLE_OR_VIEW', _Select('type')),
    ),

    # CLOUD BILLING
    'cloudbilling.billingAccount': (
        ('ID', _Select('name', transform=lambda x: x[16:])),
        ('NAME', _Select('displayName')),
        ('OPEN', _Select('open')),
    ),

    'cloudbilling.projectBillingInfo': (
        ('PROJECT_ID', _Select('projectId')),
        ('BILLING_ACCOUNT_ID', _Select('billingAccountName',
                                       # Strip "billingAccounts/"
                                       transform=lambda x: x[16:])),
        ('BILLING_ENABLED', _Select('billingEnabled')),
    ),

    # COMPUTE
    'compute.instances': (
        ('NAME', _Select('name')),
        ('ZONE', _Select('zone', _NameOnly)),
        ('MACHINE_TYPE', _Select('machineType', _NameOnly)),
        ('INTERNAL_IP', _Select('networkInterfaces[0].networkIP')),
        ('EXTERNAL_IP', _Select('networkInterfaces[0].accessConfigs[0].natIP')),
        ('STATUS', _Select('status')),
    ),

    # CONTAINER
    'container.projects.zones.clusters': (
        ('NAME', _Select('name')),
        ('ZONE', _Select('zone')),
        ('MASTER_VERSION', _Select('currentMasterVersion')),
        ('MASTER_IP', _Select('endpoint')),
        ('MACHINE_TYPE', _Select('nodePools[0].config',
                                 transform=lambda x: (
                                     '%s' % (x.machineType)) if x else None)),
        ('NODE_VERSION', _Select('currentNodeVersion')),
        ('NUM_NODES', _Select('currentNodeCount')),
        ('STATUS', _Select('status')),
    ),

    'container.projects.zones.clusters.nodePools': (
        ('NAME', _Select('name')),
        ('MACHINE_TYPE', _Select(
            'config', transform=lambda x: x.machineType)),
        ('DISK_SIZE_GB', _Select(
            'config', transform=lambda x: x.diskSizeGb)),
        ('NODE_VERSION', _Select('version')),
    ),

    'container.projects.zones.operations': (
        ('NAME', _Select('name')),
        ('TYPE', _Select('operationType')),
        ('ZONE', _Select('zone')),
        ('TARGET', _Select('targetLink', _NameOnly)),
        ('STATUS_MESSAGE', _Select('statusMessage')),
        ('STATUS', _Select('status')),
    ),

    # DATAFLOW
    'dataflow.jobs': (
        ('ID', _Select('job_id')),
        ('NAME', _Select('job_name')),
        ('TYPE', _Select('job_type')),
        ('CREATION_TIME', _Select('creation_time')),
        ('STATUS', _Select('status')),
    ),

    # DATAPROC
    'dataproc.clusters': (
        ('NAME', _Select('clusterName')),
        ('WORKER_COUNT', _Select(
            'config.workerConfig.numInstances')),
        ('ZONE', _Select(
            'config.gceClusterConfig.zoneUri', _NameOnly)),
        ('STATUS', _Select('status.state')),
    ),
    'dataproc.jobs': (
        ('ID', _Select('reference.jobId')),
        ('TYPE', _Select('type')),
        ('STATUS', _Select('status.state')),
    ),
    'dataproc.operations': (
        ('NAME', _Select('name')),
        ('DONE', _Select('done', _Boolean)),
    ),

    # DNS
    'dns.changes': (
        ('ID', _Select('id')),
        ('START_TIME', _Select('startTime')),
        ('STATUS', _Select('status')),
    ),
    'dns.managedZones': (
        ('NAME', _Select('name')),
        ('DNS_NAME', _Select('dnsName')),
        ('DESCRIPTION', _Select('description')),
    ),
    'dns.resourceRecordSets': (
        ('NAME', _Select('name')),
        ('TYPE', _Select('type')),
        ('TTL', _Select('ttl')),
        ('DATA', _Select('rrdatas', _CommaList(''))),
    ),

    # DEPLOYMENTMANAGER V2
    'deploymentmanagerv2.deployments': (
        ('NAME', _Select('name')),
        ('LAST_OPERATION_TYPE', _Select('operation.operationType')),
        ('STATUS', _Select('operation.status')),
        ('DESCRIPTION', _Select('description')),
        ('MANIFEST', _Select('manifest', transform=
                             lambda x: x.split('/')[-1] if x else None)),
        ('ERRORS', _Select('operation.error.errors',
                           transform=_FormatOperationErrors)),
    ),
    'deploymentmanagerv2.operations': (
        ('NAME', _Select('name')),
        ('TYPE', _Select('operationType')),
        ('STATUS', _Select('status')),
        ('TARGET', _Select('targetLink', transform=
                           lambda x: x.split('/')[-1] if x else None)),
        ('ERRORS', _Select('error.errors', transform=_FormatOperationErrors)),
    ),
    'deploymentmanagerv2.resources': (
        ('NAME', _Select('name')),
        ('TYPE', _Select('type')),
        ('STATE', _Select('update.state',
                          transform=lambda x: 'COMPLETED' if x is None else x)),
        ('ERRORS', _Select('update.error.errors',
                           transform=_FormatOperationErrors)),
    ),

    # FUNCTIONS
    'functions.projects.regions.functions': (
        ('NAME', _Select('name', transform=
                         lambda x: x.split('/')[-1] if x else None)),
        ('STATUS', _Select('status')),
        ('TRIGGERS_NUMBER', _Select('triggers',
                                    transform=lambda x: len(x) if x else 0)),
    ),

    # GENOMICS
    'genomics.datasets': (
        ('ID', _Select('id')),
        ('NAME', _Select('name')),
    ),

    'genomics.callSets': (
        ('ID', _Select('id')),
        ('NAME', _Select('name')),
        ('VARIANT_SET_IDS', _Select('variantSetIds')),
    ),

    'genomics.readGroupSets': (
        ('ID', _Select('id')),
        ('NAME', _Select('name')),
        ('REFERENCE_SET_ID', _Select('referenceSetId')),
    ),

    'genomics.referenceSets': (
        ('ID', _Select('id')),
        ('ASSEMBLY_ID', _Select('assemblyId')),
        ('SOURCE_ACCESSIONS', _Select('sourceAccessions')),
    ),

    'genomics.references': (
        ('ID', _Select('id')),
        ('NAME', _Select('name')),
        ('LENGTH', _Select('length')),
        ('SOURCE_URI', _Select('sourceUri')),
        ('ACCESSIONS', _Select('sourceAccessions')),
    ),

    'genomics.variants': (
        ('VARIANT_SET_ID', _Select('variantSetId')),
        ('REFERENCE_NAME', _Select('referenceName')),
        ('START', _Select('start')),
        ('END', _Select('end')),
        ('REFERENCE_BASES', _Select('referenceBases')),
        ('ALTERNATE_BASES', _Select('alternateBases')),
    ),

    'genomics.variantsets': (
        ('ID', _Select('id')),
        ('NAME', _Select('name')),
        ('DESCRIPTION', _Select('description')),
    ),

    # SQL
    'sql.backupRuns': (
        ('DUE_TIME', _SelectTime('dueTime')),
        ('ERROR', _Select('error.code')),
        ('STATUS', _Select('status')),
    ),
    'sql.backupRuns.v1beta4': (
        ('ID', _Select('id')),
        ('WINDOW_START_TIME', _SelectTime('windowStartTime')),
        ('ERROR', _Select('error.code')),
        ('STATUS', _Select('status')),
    ),
    'sql.flags': (
        ('NAME', _Select('name')),
        ('TYPE', _Select('type')),
        ('ALLOWED_VALUES', _Select('allowedStringValues', _CommaList(''))),
    ),
    'sql.instances': (
        ('NAME', _Select('instance')),
        ('REGION', _Select('region')),
        ('TIER', _Select('settings.tier')),
        ('ADDRESS', _Select('ipAddresses[0].ipAddress')),
        ('STATUS', _Select('state')),
    ),
    'sql.instances.v1beta4': (
        ('NAME', _Select('name')),
        ('REGION', _Select('region')),
        ('TIER', _Select('settings.tier')),
        ('ADDRESS', _Select('ipAddresses[0].ipAddress')),
        ('STATUS', _Select('state')),
    ),
    'sql.operations': (
        ('OPERATION', _Select('operation')),
        ('TYPE', _Select('operationType')),
        ('START', _SelectTime('startTime')),
        ('END', _SelectTime('endTime')),
        ('ERROR', _Select('error[0].code')),
        ('STATUS', _Select('state')),
    ),
    'sql.operations.v1beta4': (
        ('NAME', _Select('name')),
        ('TYPE', _Select('operationType')),
        ('START', _SelectTime('startTime')),
        ('END', _SelectTime('endTime')),
        ('ERROR', _Select('error[0].code')),
        ('STATUS', _Select('status')),
    ),
    'sql.sslCerts': (
        ('NAME', _Select('commonName')),
        ('SHA1_FINGERPRINT', _Select('sha1Fingerprint')),
        ('EXPIRATION', _Select('expirationTime')),
    ),
    'sql.tiers': (
        ('TIER', _Select('tier')),
        ('AVAILABLE_REGIONS', _Select('region', _CommaList(''))),
        ('RAM', _Select('RAM', _DiskSize)),
        ('DISK', _Select('DiskQuota', _DiskSize)),
    ),

    # projects
    'cloudresourcemanager.projects': (
        ('PROJECT_ID', _Select('projectId')),
        ('NAME', _Select('name')),
        ('PROJECT_NUMBER', _Select('projectNumber')),
    ),

    # source
    'source.jobs.list': (
        ('REPO_NAME', _Select('name', _Default('default'))),
        ('PROJECT_ID ', _Select('projectId')),
        ('VCS', _Select('vcs')),
        ('STATE', _Select('state')),
        ('CREATE_TIME', _Select('createTime')),
    ),
    'source.captures.list': (
        ('PROJECT_ID ', _Select('project_id')),
        ('CAPTURE_ID', _Select('id')),
    ),

    # TEST
    'test.web.browsers': (
        ('BROWSER_ID', _Select('id')),
        ('NAME', _Select('name')),
        ('RELEASE', _Select('release')),
        ('VERSION', _Select('versionString')),
        ('ANDROID_CATALOG', _Select('androidCatalog', _Boolean)),
        ('LINUX_CATALOG', _Select('linuxCatalog', _Boolean)),
        ('WINDOWS_CATALOG', _Select('windowsCatalog', _Boolean)),
    ),

    # Cloud Logging
    'logging.logs': (
        ('NAME', _Select('name')),
    ),
    'logging.typedSinks': (
        ('NAME', _Select('name')),
        ('DESTINATION', _Select('destination')),
        ('TYPE', _Select('type')),
        ('FORMAT', _Select('format')),
        ('FILTER', _Select('filter'))
    ),
    'logging.metrics': (
        ('NAME', _Select('name')),
        ('DESCRIPTION', _Select('description')),
        ('FILTER', _Select('filter')),
    ),
    'logging.resourceDescriptors': (
        ('TYPE', _Select('type')),
        ('DESCRIPTION', _Select('description')),
        ('LABELS', _Select('labels',
                           # Print a comma separated list of label 'keys'.
                           lambda x: ', '.join([ele.key for ele in x]))),
    ),

    # Service Management (Inception)
    'servicemanagement-v1.services': (
        ('NAME', _Select('serviceName')),
        ('TITLE', _Select('serviceConfig.title')),
    ),
}
