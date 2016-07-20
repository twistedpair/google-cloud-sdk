# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Base template using which the apis_map.py is generated."""


class APIDef(object):
  """Struct for info required to instantiate clients/messages for API versions.

  Attributes:
    client_classpath: str, Path to the client class for an API version.
    messages_modulepath: str, Path to the messages module for an API version.
    default_version: bool, Whether this API version is the default version for
    the API.
  """

  def __init__(self,
               client_classpath,
               messages_modulepath,
               default_version=False):
    self.client_classpath = client_classpath
    self.messages_modulepath = messages_modulepath
    self.default_version = default_version

  def __eq__(self, other):
    return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)

  def __ne__(self, other):
    return not self.__eq__(other)

  def get_init_source(self):
    src_fmt = 'APIDef("{0}", "{1}", {2})'
    return src_fmt.format(self.client_classpath, self.messages_modulepath,
                          self.default_version)

  def __repr__(self):
    return self.get_init_source()


MAP = {
    'apikeys': {
        'v1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.apikeys.v1.apikeys_v1_client.ApikeysV1',
            messages_modulepath='googlecloudsdk.third_party.apis.apikeys.v1.apikeys_v1_messages',
            default_version=True
        ),
    },
    'appengine': {
        'v1beta5': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.appengine.v1beta5.appengine_v1beta5_client.AppengineV1beta5',
            messages_modulepath='googlecloudsdk.third_party.apis.appengine.v1beta5.appengine_v1beta5_messages',
            default_version=True
        ),
    },
    'bigquery': {
        'v2': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.bigquery.v2.bigquery_v2_client.BigqueryV2',
            messages_modulepath='googlecloudsdk.third_party.apis.bigquery.v2.bigquery_v2_messages',
            default_version=True
        ),
    },
    'bigtableadmin': {
        'v2': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.bigtableadmin.v2.bigtableadmin_v2_client.BigtableadminV2',
            messages_modulepath='googlecloudsdk.third_party.apis.bigtableadmin.v2.bigtableadmin_v2_messages',
            default_version=True
        ),
    },
    'bigtableclusteradmin': {
        'v1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.bigtableclusteradmin.v1.bigtableclusteradmin_v1_client.BigtableclusteradminV1',
            messages_modulepath='googlecloudsdk.third_party.apis.bigtableclusteradmin.v1.bigtableclusteradmin_v1_messages',
            default_version=True
        ),
    },
    'cloudbilling': {
        'v1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.cloudbilling.v1.cloudbilling_v1_client.CloudbillingV1',
            messages_modulepath='googlecloudsdk.third_party.apis.cloudbilling.v1.cloudbilling_v1_messages',
            default_version=True
        ),
    },
    'cloudbuild': {
        'v1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.cloudbuild.v1.cloudbuild_v1_client.CloudbuildV1',
            messages_modulepath='googlecloudsdk.third_party.apis.cloudbuild.v1.cloudbuild_v1_messages',
            default_version=True
        ),
    },
    'clouddebugger': {
        'v2': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.clouddebugger.v2.clouddebugger_v2_client.ClouddebuggerV2',
            messages_modulepath='googlecloudsdk.third_party.apis.clouddebugger.v2.clouddebugger_v2_messages',
            default_version=True
        ),
    },
    'clouderrorreporting': {
        'v1beta1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.clouderrorreporting.v1beta1.clouderrorreporting_v1beta1_client.ClouderrorreportingV1beta1',
            messages_modulepath='googlecloudsdk.third_party.apis.clouderrorreporting.v1beta1.clouderrorreporting_v1beta1_messages',
            default_version=True
        ),
    },
    'cloudfunctions': {
        'v1beta1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.cloudfunctions.v1beta1.cloudfunctions_v1beta1_client.CloudfunctionsV1beta1',
            messages_modulepath='googlecloudsdk.third_party.apis.cloudfunctions.v1beta1.cloudfunctions_v1beta1_messages',
            default_version=True
        ),
    },
    'cloudresourcemanager': {
        'v1beta1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.cloudresourcemanager.v1beta1.cloudresourcemanager_v1beta1_client.CloudresourcemanagerV1beta1',
            messages_modulepath='googlecloudsdk.third_party.apis.cloudresourcemanager.v1beta1.cloudresourcemanager_v1beta1_messages',
            default_version=True
        ),
    },
    'clouduseraccounts': {
        'alpha': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.clouduseraccounts.alpha.clouduseraccounts_alpha_client.ClouduseraccountsAlpha',
            messages_modulepath='googlecloudsdk.third_party.apis.clouduseraccounts.alpha.clouduseraccounts_alpha_messages',
            default_version=False
        ),
        'beta': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.clouduseraccounts.beta.clouduseraccounts_beta_client.ClouduseraccountsBeta',
            messages_modulepath='googlecloudsdk.third_party.apis.clouduseraccounts.beta.clouduseraccounts_beta_messages',
            default_version=True
        ),
    },
    'compute': {
        'alpha': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.compute.alpha.compute_alpha_client.ComputeAlpha',
            messages_modulepath='googlecloudsdk.third_party.apis.compute.alpha.compute_alpha_messages',
            default_version=False
        ),
        'beta': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.compute.beta.compute_beta_client.ComputeBeta',
            messages_modulepath='googlecloudsdk.third_party.apis.compute.beta.compute_beta_messages',
            default_version=False
        ),
        'v1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.compute.v1.compute_v1_client.ComputeV1',
            messages_modulepath='googlecloudsdk.third_party.apis.compute.v1.compute_v1_messages',
            default_version=True
        ),
    },
    'container': {
        'v1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.container.v1.container_v1_client.ContainerV1',
            messages_modulepath='googlecloudsdk.third_party.apis.container.v1.container_v1_messages',
            default_version=True
        ),
    },
    'dataflow': {
        'v1b3': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.dataflow.v1b3.dataflow_v1b3_client.DataflowV1b3',
            messages_modulepath='googlecloudsdk.third_party.apis.dataflow.v1b3.dataflow_v1b3_messages',
            default_version=True
        ),
    },
    'dataproc': {
        'v1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.dataproc.v1.dataproc_v1_client.DataprocV1',
            messages_modulepath='googlecloudsdk.third_party.apis.dataproc.v1.dataproc_v1_messages',
            default_version=True
        ),
    },
    'deploymentmanager': {
        'alpha': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.deploymentmanager.alpha.deploymentmanager_alpha_client.DeploymentmanagerAlpha',
            messages_modulepath='googlecloudsdk.third_party.apis.deploymentmanager.alpha.deploymentmanager_alpha_messages',
            default_version=False
        ),
        'v2': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.deploymentmanager.v2.deploymentmanager_v2_client.DeploymentmanagerV2',
            messages_modulepath='googlecloudsdk.third_party.apis.deploymentmanager.v2.deploymentmanager_v2_messages',
            default_version=True
        ),
        'v2beta': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.deploymentmanager.v2beta.deploymentmanager_v2beta_client.DeploymentmanagerV2beta',
            messages_modulepath='googlecloudsdk.third_party.apis.deploymentmanager.v2beta.deploymentmanager_v2beta_messages',
            default_version=False
        ),
    },
    'dns': {
        'v1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.dns.v1.dns_v1_client.DnsV1',
            messages_modulepath='googlecloudsdk.third_party.apis.dns.v1.dns_v1_messages',
            default_version=True
        ),
        'v1beta1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.dns.v1beta1.dns_v1beta1_client.DnsV1beta1',
            messages_modulepath='googlecloudsdk.third_party.apis.dns.v1beta1.dns_v1beta1_messages',
            default_version=False
        ),
    },
    'genomics': {
        'v1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.genomics.v1.genomics_v1_client.GenomicsV1',
            messages_modulepath='googlecloudsdk.third_party.apis.genomics.v1.genomics_v1_messages',
            default_version=True
        ),
        'v1alpha2': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.genomics.v1alpha2.genomics_v1alpha2_client.GenomicsV1alpha2',
            messages_modulepath='googlecloudsdk.third_party.apis.genomics.v1alpha2.genomics_v1alpha2_messages',
            default_version=False
        ),
    },
    'iam': {
        'v1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.iam.v1.iam_v1_client.IamV1',
            messages_modulepath='googlecloudsdk.third_party.apis.iam.v1.iam_v1_messages',
            default_version=True
        ),
    },
    'logging': {
        'v1beta3': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.logging.v1beta3.logging_v1beta3_client.LoggingV1beta3',
            messages_modulepath='googlecloudsdk.third_party.apis.logging.v1beta3.logging_v1beta3_messages',
            default_version=True
        ),
        'v2beta1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.logging.v2beta1.logging_v2beta1_client.LoggingV2beta1',
            messages_modulepath='googlecloudsdk.third_party.apis.logging.v2beta1.logging_v2beta1_messages',
            default_version=False
        ),
    },
    'manager': {
        'v1beta2': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.manager.v1beta2.manager_v1beta2_client.ManagerV1beta2',
            messages_modulepath='googlecloudsdk.third_party.apis.manager.v1beta2.manager_v1beta2_messages',
            default_version=True
        ),
    },
    'pubsub': {
        'v1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.pubsub.v1.pubsub_v1_client.PubsubV1',
            messages_modulepath='googlecloudsdk.third_party.apis.pubsub.v1.pubsub_v1_messages',
            default_version=True
        ),
    },
    'replicapoolupdater': {
        'v1beta1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.replicapoolupdater.v1beta1.replicapoolupdater_v1beta1_client.ReplicapoolupdaterV1beta1',
            messages_modulepath='googlecloudsdk.third_party.apis.replicapoolupdater.v1beta1.replicapoolupdater_v1beta1_messages',
            default_version=True
        ),
    },
    'runtimeconfig': {
        'v1beta1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.runtimeconfig.v1beta1.runtimeconfig_v1beta1_client.RuntimeconfigV1beta1',
            messages_modulepath='googlecloudsdk.third_party.apis.runtimeconfig.v1beta1.runtimeconfig_v1beta1_messages',
            default_version=True
        ),
    },
    'servicemanagement': {
        'v1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.servicemanagement.v1.servicemanagement_v1_client.ServicemanagementV1',
            messages_modulepath='googlecloudsdk.third_party.apis.servicemanagement.v1.servicemanagement_v1_messages',
            default_version=True
        ),
    },
    'serviceregistry': {
        'v1alpha': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.serviceregistry.v1alpha.serviceregistry_v1alpha_client.ServiceregistryV1alpha',
            messages_modulepath='googlecloudsdk.third_party.apis.serviceregistry.v1alpha.serviceregistry_v1alpha_messages',
            default_version=True
        ),
    },
    'source': {
        'v1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.source.v1.source_v1_client.SourceV1',
            messages_modulepath='googlecloudsdk.third_party.apis.source.v1.source_v1_messages',
            default_version=True
        ),
    },
    'sqladmin': {
        'v1beta3': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.sqladmin.v1beta3.sqladmin_v1beta3_client.SqladminV1beta3',
            messages_modulepath='googlecloudsdk.third_party.apis.sqladmin.v1beta3.sqladmin_v1beta3_messages',
            default_version=True
        ),
        'v1beta4': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.sqladmin.v1beta4.sqladmin_v1beta4_client.SqladminV1beta4',
            messages_modulepath='googlecloudsdk.third_party.apis.sqladmin.v1beta4.sqladmin_v1beta4_messages',
            default_version=False
        ),
    },
    'storage': {
        'v1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.storage.v1.storage_v1_client.StorageV1',
            messages_modulepath='googlecloudsdk.third_party.apis.storage.v1.storage_v1_messages',
            default_version=True
        ),
    },
    'testing': {
        'v1': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.testing.v1.testing_v1_client.TestingV1',
            messages_modulepath='googlecloudsdk.third_party.apis.testing.v1.testing_v1_messages',
            default_version=True
        ),
    },
    'toolresults': {
        'v1beta3': APIDef(
            client_classpath='googlecloudsdk.third_party.apis.toolresults.v1beta3.toolresults_v1beta3_client.ToolresultsV1beta3',
            messages_modulepath='googlecloudsdk.third_party.apis.toolresults.v1beta3.toolresults_v1beta3_messages',
            default_version=True
        ),
    },
}
