# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Utility for interacting with containeranalysis API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.containeranalysis import requests as ca_requests
import six


class ContainerAnalysisMetadata:
  """ContainerAnalysisMetadata defines metadata retrieved from containeranalysis API."""

  def __init__(self):
    self.vulnerability = PackageVulnerabilitySummary()
    self.image = ImageBasisSummary()
    self.discovery = DiscoverySummary()
    self.deployment = DeploymentSummary()
    self.build = BuildSummary()

  def AddOccurrence(self, occ):
    """Adds occurrences retrieved from containeranalysis API."""
    messages = ca_requests.GetMessages()
    if occ.kind == messages.Occurrence.KindValueValuesEnum.VULNERABILITY:
      self.vulnerability.AddOccurrence(occ)
    elif occ.kind == messages.Occurrence.KindValueValuesEnum.IMAGE:
      self.image.AddOccurrence(occ)
    elif occ.kind == messages.Occurrence.KindValueValuesEnum.BUILD:
      self.build.AddOccurrence(occ)
    elif occ.kind == messages.Occurrence.KindValueValuesEnum.DEPLOYMENT:
      self.deployment.AddOccurrence(occ)
    elif occ.kind == messages.Occurrence.KindValueValuesEnum.DISCOVERY:
      self.discovery.AddOccurrence(occ)

  def ImagesDescribeView(self):
    """Returns a dictionary representing the metadata.

    The returned dictionary is used by artifacts docker images describe command.
    """
    view = {}
    if self.image.base_images:
      view['image_basis_summary'] = self.image
    if self.deployment.deployments:
      view['deployment_summary'] = self.deployment
    if self.discovery.discovery:
      view['discovery_summary'] = self.discovery
    if self.build.build_details:
      view['build_details_summary'] = self.build
    vuln = self.vulnerability.ImagesDescribeView()
    if vuln:
      view['package_vulnerability_summary'] = vuln
    return view


class PackageVulnerabilitySummary:
  """PackageVulnerabilitySummary holds package vulnerability information."""

  def __init__(self):
    self.vulnerabilities = {}
    self.counts = []

  def AddOccurrence(self, occ):
    sev = six.text_type(occ.vulnerability.severity)
    self.vulnerabilities.setdefault(sev, []).append(occ)

  def AddSummary(self, summary):
    self.counts += summary.counts

  def AddCount(self, count):
    self.counts.append(count)

  def ImagesDescribeView(self):
    """Returns a dictionary representing the metadata.

    The returned dictionary is used by artifacts docker images describe command.
    """
    messages = ca_requests.GetMessages()
    view = {}
    if self.vulnerabilities:
      view['vulnerabilities'] = self.vulnerabilities
    for count in self.counts:
      # SEVERITY_UNSPECIFIED represents total counts across all serverities
      if (count.severity ==
          messages.FixableTotalByDigest
          .SeverityValueValuesEnum.SEVERITY_UNSPECIFIED):
        view['not_fixed_vulnerability_count'] = (
            count.totalCount - count.fixableCount)
        view['total_vulnerability_count'] = count.totalCount
        break
    return view


class ImageBasisSummary:
  """ImageBasisSummary holds image basis information."""

  def __init__(self):
    self.base_images = []

  def AddOccurrence(self, occ):
    self.base_images.append(occ)


class BuildSummary:
  """BuildSummary holds image build information."""

  def __init__(self):
    self.build_details = []

  def AddOccurrence(self, occ):
    self.build_details.append(occ)


class DeploymentSummary:
  """DeploymentSummary holds image deployment information."""

  def __init__(self):
    self.deployments = []

  def AddOccurrence(self, occ):
    self.deployments.append(occ)


class DiscoverySummary:
  """DiscoverySummary holds image vulnerability discovery information."""

  def __init__(self):
    self.discovery = []

  def AddOccurrence(self, occ):
    self.discovery.append(occ)


def GetContainerAnalysisMetadata(docker_version, args):
  """Retrieves metadata for a docker image."""
  metadata = ContainerAnalysisMetadata()
  occ_filter = _CreateFilterFromArgs(args)
  if occ_filter is None:
    return metadata

  occurrences = ca_requests.ListOccurrences(
      docker_version.project,
      _HasField('resource_uri', docker_version.GetDockerString()), occ_filter)
  for occ in occurrences:
    metadata.AddOccurrence(occ)

  if metadata.vulnerability.vulnerabilities:
    vuln_summary = ca_requests.GetVulnerabilitySummary(
        docker_version.project,
        _HasField('resource_uri', docker_version.GetDockerString()))
    metadata.vulnerability.AddSummary(vuln_summary)

  return metadata


def _CreateFilterFromArgs(args):
  r"""Parses user-provided arguments into a filter to send to containeranalysis API.

  The returned filter will combine the user-provided filter specified by
  the --metadata-filter flag and occurrence kind filters specified by flags
  such as --show-package-vulnerability.

  Returns None if there is no information to fetch from containeranalysis API.

  Args:
    args: user provided command line arguments.

  Returns:
    A filter string to send to the containeranalysis API.

  For example, given a user input:
  gcloud docker images describe MY_IMAGE --show-package-vulnerability \
    --show-image-basis \
    --metadata-filter='createTime>"2019-04-10T"'

  this method will create a filter:

  '((kind="VULNERABILITY") OR (kind="IMAGE")) AND (createTime>"2019-04-10T")'
  """
  filter_kinds = []

  # We don't need to filter on kinds when showing all metadata
  if not args.show_all_metadata:
    if args.show_build_details:
      filter_kinds.append(_HasField('kind', 'BUILD'))
    if args.show_package_vulnerability:
      filter_kinds.append(_HasField('kind', 'VULNERABILITY'))
      filter_kinds.append(_HasField('kind', 'DISCOVERY'))
    if args.show_image_basis:
      filter_kinds.append(_HasField('kind', 'IMAGE'))
    if args.show_deployment:
      filter_kinds.append(_HasField('kind', 'DEPLOYMENT'))

    # args include none of the occurrence types, there's no need to call the
    # containeranalysis API.
    if not filter_kinds:
      return None

  occ_filter = _OrJoinFilters(*filter_kinds)
  occ_filter = _AndJoinFilters(occ_filter, args.metadata_filter)
  return occ_filter


def _AndJoinFilters(*filters):
  return ' AND '.join(['({})'.format(f) for f in filters if f])


def _OrJoinFilters(*filters):
  return ' OR '.join(['({})'.format(f) for f in filters if f])


def _HasField(field, value):
  return '{} = "{}"'.format(field, value)
