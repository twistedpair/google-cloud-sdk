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
"""Utilities for the container analysis data model."""

import abc
import collections

from googlecloudsdk.api_lib.util import apis

_INDENT = '  '
_NULL_SEVERITY = 'UNKNOWN'


class BaseCollection(collections.deque):
  """Base collection for different types of analysis results."""

  __metaclass__ = abc.ABCMeta

  def add(self, element):
    self.append(element)

  @abc.abstractmethod
  def __str__(self):
    pass


class PackageVulnerability(object):
  """Class defining vulnerability."""

  class Collection(BaseCollection):

    def __init__(self, *args, **kwargs):
      super(PackageVulnerability.Collection, self).__init__(*args, **kwargs)

    def __str__(self):
      if not self:
        return 'No known vulnerabilities at this time.'

      severities = collections.defaultdict(list)
      for x in list(self):
        sev = str(x.severity) if x.severity else _NULL_SEVERITY
        severities[sev].append(x)

      output = ['Vulnerabilities:']
      for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', _NULL_SEVERITY]:
        vulnz = severities[sev]
        if not vulnz:
          continue
        output.append('{0} ({1}):'.format(sev.capitalize(), len(vulnz)))
        for v in vulnz:
          output.append(str(v))
        # Line breaks between sections.
        output.append('')

      return ('\n' + _INDENT).join(output)

  class PackageVersion(object):
    """Helper class for Package name version."""

    def __init__(self, affected_location, fixed_location, not_fixed):
      self.affected_package = self._get_package_name(affected_location)
      if not_fixed:
        self.fixed_package = 'Not Fixed'
      else:
        self.fixed_package = self._get_package_name(fixed_location)

    def _get_package_name(self, package):
      if package.version.epoch:
        return '{name} ({epoch}:{version}-{rev})'.format(
            name=package.package,
            version=package.version.name,
            epoch=package.version.epoch,
            rev=package.version.revision)
      else:
        return '{name} ({version}-{rev})'.format(
            name=package.package,
            version=package.version.name,
            rev=package.version.revision)

  def __init__(self, occurrence):
    self.vulnerability = occurrence.noteName
    self.severity = occurrence.vulnerabilityDetails.severity
    self.pkg_vulnerabilities = []
    self.patch_not_available = False
    messages = apis.GetMessagesModule('containeranalysis', 'v1alpha1')
    for package_issue in occurrence.vulnerabilityDetails.packageIssue:
      current_issue_not_fixed = (package_issue.fixedLocation.version.kind ==
                                 messages.Version.KindValueValuesEnum.MAXIMUM)

      self.pkg_vulnerabilities.append(PackageVulnerability.PackageVersion(
          package_issue.affectedLocation, package_issue.fixedLocation,
          not_fixed=current_issue_not_fixed))
      self.patch_not_available = (current_issue_not_fixed or
                                  self.patch_not_available)

  def __str__(self):
    repr_str = ['', 'Vulnerability: {0}'.format(self.vulnerability)]
    for pkg_vuln in self.pkg_vulnerabilities:
      repr_str.append('Affected Package: {affected}'.format(
          affected=pkg_vuln.affected_package))
      repr_str.append('Fixed Package: {fixed}'.format(
          fixed=pkg_vuln.fixed_package))
    # TODO(b/36050346) Display related url after b/32774264 is fixed.
    return ('\n' + _INDENT + _INDENT).join(repr_str)


class BaseImage(object):
  """Class defining Base image Analysis Data."""

  class Collection(BaseCollection):

    def __str__(self):
      if not self:
        return 'No base image information is available for this image.'

      base_images = list(sorted(self, key=lambda x: x.distance, reverse=True))
      last_basis = base_images[-1]
      dockerfile = [
          'FROM {0}\t# +{1} layers'.format(x.base_image_url[8:], x.distance)
          for x in base_images
      ]
      for layer in reversed(last_basis.layer_info):
        if layer.directive and layer.arguments:
          dockerfile.append('{0} {1}'.format(layer.directive, layer.arguments))
        else:
          dockerfile.append('Could not recover information.')
      return ('\n' + _INDENT).join(['Image Basis:'] + dockerfile)

  def __init__(self, occurrence):
    self.base_image_url = occurrence.derivedImage.baseResourceUrl
    self.distance = occurrence.derivedImage.distance
    self.layer_info = occurrence.derivedImage.layerInfo


class BuildDetails(object):
  """Class Defining Build Details."""

  class Collection(BaseCollection):

    def __str__(self):
      if not self:
        return 'No build details are available for this image.'
      return '\n'.join(['Build Details:'] + map(str, self))

  def __init__(self, occurrence):
    self.create_time = occurrence.buildDetails.provenance.createTime
    provenance = occurrence.buildDetails.provenance
    self.creator = provenance.creator
    self.logs_bucket = provenance.logsBucket
    self.git_sha = None
    self.repo_name = None
    if (provenance.sourceProvenance and
        provenance.sourceProvenance.sourceContext):
      context = provenance.sourceProvenance.sourceContext.context
      self.git_sha = context.cloudRepo.revisionId
      self.repo_name = context.cloudRepo.repoId.projectRepoId.repoName

  def __str__(self):
    output = [
        'Create Time: {create_time}'.format(create_time=self.create_time),
        'Creator: {creator}'.format(creator=self.creator),
        'Logs Bucket: {bucket}'.format(bucket=self.logs_bucket),
    ]
    if self.git_sha and self.repo_name:
      output.append('Repository: {repo_name}@{git_sha}'.format(
          repo_name=self.repo_name, git_sha=self.git_sha))

    return ('\n' + _INDENT).join(output)


class ContainerAnalysisData(object):
  """Class defining all container analysis data."""

  def __init__(self, digest):
    self.digest = str(digest)
    self.vulz_analysis = PackageVulnerability.Collection()
    self.image_analysis = BaseImage.Collection()
    self.build_details = BuildDetails.Collection()
    # These should be a part of PackageVulnerability.Collection
    self.total_vulnerability_found = 0
    self.not_fixed_vulnerability_count = 0

  def add_record(self, occurrence):
    messages = apis.GetMessagesModule('containeranalysis', 'v1alpha1')
    if (occurrence.kind ==
        messages.Occurrence.KindValueValuesEnum.PACKAGE_VULNERABILITY):
      vulz = PackageVulnerability(occurrence)
      self.vulz_analysis.add(vulz)
      self.total_vulnerability_found += len(vulz.pkg_vulnerabilities)
      if vulz.patch_not_available:
        self.not_fixed_vulnerability_count += len(vulz.pkg_vulnerabilities)
    elif occurrence.kind == messages.Occurrence.KindValueValuesEnum.IMAGE_BASIS:
      self.image_analysis.add(BaseImage(occurrence))
    elif (occurrence.kind ==
          messages.Occurrence.KindValueValuesEnum.BUILD_DETAILS):
      self.build_details.add(BuildDetails(occurrence))

  def __str__(self):
    obj_str = [
        'Image: {0}'.format(self.digest),
        '',
        str(self.build_details),
        '',
        str(self.image_analysis),
        '',
        str(self.vulz_analysis),
        ''  # Trailing newline.
    ]
    return '\n'.join(obj_str)
