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

import collections

from googlecloudsdk.core import apis


class VulzAnalysis(object):
  """Class defining vulnerability."""

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

    def __str__(self):
      return ('Affected Package: {affected}'
              '\nFixed Package: {fixed}').format(affected=self.affected_package,
                                                 fixed=self.fixed_package)

  def __init__(self, note, vul_details):
    self.vulnerability = note
    self.severity = vul_details.severity
    self.pkg_vulnerabilities = []
    self.patch_not_available = False
    messages = apis.GetMessagesModule('containeranalysis', 'v1alpha1')
    for package_issue in vul_details.packageIssue:
      current_issue_not_fixed = (package_issue.fixedLocation.version.kind ==
                                 messages.Version.KindValueValuesEnum.MAXIMUM)

      self.pkg_vulnerabilities.append(VulzAnalysis.PackageVersion(
          package_issue.affectedLocation, package_issue.fixedLocation,
          not_fixed=current_issue_not_fixed))
      self.patch_not_available = (current_issue_not_fixed or
                                  self.patch_not_available)

  def __str__(self):
    repr_str = ['\nVulnerability: {0}'.format(self.vulnerability)]
    for vulnerability in self.pkg_vulnerabilities:
      repr_str.append(str(vulnerability))
    repr_str.append('Severity: {0}'.format(self.severity))
    # TODO(user) Display related url after b/32774264 is fixed.
    return '\n'.join(repr_str)


class BaseImageAnalysis(object):
  """Class defining Base image Analysis Data."""

  def __init__(self, derived_image):
    self.base_image_url = derived_image.baseResourceUrl
    self.distance = derived_image.distance

  def __str__(self):
    return self.base_image_url


class BuildDetails(object):
  """Class Defining Build Details."""

  def __init__(self, build_details):
    self.create_time = build_details.provenance.createTime
    provenance = build_details.provenance
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
    git_info = ''
    if self.git_sha and self.repo_name:
      git_info = '\nRepository: {repo_name}@{git_sha}'.format(
          repo_name=self.repo_name, git_sha=self.git_sha)
    return ('\nCreate Time: {create_time}'
            '\nCreator: {creator}'
            '\nLogsBucket: {l_bucket}'
            '{git_info}\n').format(create_time=self.create_time,
                                   creator=self.creator,
                                   l_bucket=self.logs_bucket,
                                   git_info=git_info)


class ContainerAnalysisData(object):
  """Class defining all container analysis data."""

  def __init__(self):
    self.vulz_analysis = collections.defaultdict(list)
    self.image_analysis = collections.defaultdict(list)
    self.build_details = []
    self.total_vulnerability_found = 0
    self.not_fixed_vulnerability_count = 0

  def add_record(self, occurrence):
    messages = apis.GetMessagesModule('containeranalysis', 'v1alpha1')
    if (occurrence.kind ==
        messages.Occurrence.KindValueValuesEnum.PACKAGE_VULNERABILITY):
      vulz = VulzAnalysis(occurrence.noteName, occurrence.vulnerabilityDetails)
      self.total_vulnerability_found += len(vulz.pkg_vulnerabilities)
      if not vulz.patch_not_available:
        self.vulz_analysis['FixesAvailable'].append(vulz)
      else:
        self.not_fixed_vulnerability_count += len(vulz.pkg_vulnerabilities)
        self.vulz_analysis['NoFixesAvailable'].append(vulz)
    elif occurrence.kind == messages.Occurrence.KindValueValuesEnum.IMAGE_BASIS:
      base_image = BaseImageAnalysis(occurrence.derivedImage)
      self.image_analysis[base_image.distance].append(base_image)
    elif (occurrence.kind ==
          messages.Occurrence.KindValueValuesEnum.BUILD_DETAILS):
      self.build_details.append(BuildDetails(occurrence.buildDetails))

  def __str__(self):
    obj_str = []
    if self.build_details:
      obj_str.append('\nBuild Details')
      obj_str.extend([str(obj) for obj in self.build_details])
    if self.image_analysis:
      obj_str.append('Base Resource Urls\n')
      for key in sorted(self.image_analysis.keys(), reverse=True):
        obj_str.append('Distance: {key}\nBase Image(s): {obj_str}'.format(
            key=key,
            obj_str=', '.join(str(item) for item in self.image_analysis[key])
        ))
    if self.vulz_analysis:
      obj_str.append('\nVulnerability Analysis Data')
      for key in sorted(self.vulz_analysis.keys(), reverse=True):
        obj_str.extend([str(item) for item in self.vulz_analysis[key]])
    return '{obj_str}\n'.format(obj_str='\n'.join(obj_str))
