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
"""Converter related function for Ops Agents Policy."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import textwrap

from googlecloudsdk.api_lib.compute.instances.ops_agents import ops_agents_policy as agent_policy


class _PackageTemplates(
    collections.namedtuple('_PackageTemplates',
                           ('repo', 'install_with_version'))):
  pass


class _AgentTemplates(
    collections.namedtuple(
        '_AgentTemplates',
        ('yum_package', 'apt_package', 'zypper_package', 'run_agent', 'repo_id',
         'display_name', 'recipe_name', 'current_major_version'))):
  pass


_AGENT_TEMPLATES = {
    'logging':
        _AgentTemplates(
            yum_package=_PackageTemplates(
                repo={
                    'all': 'google-cloud-logging-el%s-x86_64-all',
                    '1.*.*': 'google-cloud-logging-el%s-x86_64-1'
                },
                install_with_version=textwrap.dedent("""\
                    sudo yum remove google-fluentd
                    sudo yum install -y 'google-fluentd%s'"""),
            ),
            zypper_package=_PackageTemplates(
                repo={
                    'all': 'google-cloud-logging-sles%s-x86_64-all',
                    '1.*.*': 'google-cloud-logging-sles%s-x86_64-1'
                },
                install_with_version=textwrap.dedent("""\
                    sudo zypper remove google-fluentd
                    sudo zypper install -y 'google-fluentd%s'"""),
            ),
            apt_package=_PackageTemplates(
                repo={
                    'all': 'google-cloud-logging-%s-all',
                    '1.*.*': 'google-cloud-logging-%s-1'
                },
                install_with_version=textwrap.dedent("""\
                    sudo apt-get remove google-fluentd
                    sudo apt-get install -y 'google-fluentd%s'"""),
            ),
            repo_id='google-cloud-logging',
            display_name='Google Cloud Logging Agent Repository',
            run_agent=textwrap.dedent("""\
                    #!/bin/bash
                    sleep 5m
                    %(install)s"""),
            recipe_name='set-google-fluentd-version',
            current_major_version='1.*.*',
        ),
    'metrics':
        _AgentTemplates(
            yum_package=_PackageTemplates(
                repo={
                    'all': 'google-cloud-monitoring-el%s-x86_64-all',
                    '5.*.*': 'google-cloud-monitoring-el%s-x86_64-5',
                    '6.*.*': 'google-cloud-monitoring-el%s-x86_64-6'
                },
                install_with_version=textwrap.dedent("""\
                    sudo yum remove stackdriver-agent
                    sudo yum install -y 'stackdriver-agent%s'"""),
            ),
            zypper_package=_PackageTemplates(
                repo={
                    'all': 'google-cloud-monitoring-sles%s-x86_64-all',
                    '5.*.*': 'google-cloud-monitoring-sles%s-x86_64-5',
                    '6.*.*': 'google-cloud-monitoring-sles%s-x86_64-6'
                },
                install_with_version=textwrap.dedent("""\
                    sudo zypper remove stackdriver-agent
                    sudo zypper install -y 'stackdriver-agent%s'"""),
            ),
            apt_package=_PackageTemplates(
                repo={
                    'all': 'google-cloud-monitoring-%s-all',
                    '5.*.*': 'google-cloud-monitoring-%s-5',
                    '6.*.*': 'google-cloud-monitoring-%s-6'
                },
                install_with_version=textwrap.dedent("""\
                    sudo apt-get remove stackdriver-agent
                    sudo apt-get install -y 'stackdriver-agent%s'"""),
            ),
            repo_id='google-cloud-monitoring',
            display_name='Google Cloud Monitoring Agent Repository',
            run_agent=textwrap.dedent("""\
                    #!/bin/bash
                    sleep 5m
                    %(install)s"""),
            recipe_name='set-stackdriver-agent-version',
            current_major_version='6.*.*',
        ),
}

_APT_CODENAMES = {
    '8': 'jessie',
    '9': 'stretch',
    '10': 'buster',
    '16.04': 'xenial',
    '18.04': 'bionic',
    '19.10': 'eoan',
    '20.04': 'focal',
}

_SUSE_OS = ('sles-sap', 'sles')

_APT_OS = ('debian', 'ubuntu')


def _CreatePackages(messages, agents, os_type):
  """Create OS Agent guest policy packages from Ops Agent policy agent field."""
  packages = []
  for agent in agents or []:
    if agent.type is agent_policy.OpsAgentPolicy.Agent.Type.LOGGING:
      packages.append(
          _CreatePackage(messages, 'google-fluentd', agent.package_state,
                         agent.enable_autoupgrade))
      packages.append(
          _CreatePackage(messages, 'google-fluentd-catch-all-config',
                         agent.package_state, agent.enable_autoupgrade))
      # apt os will start the service automatically without the start-service.
      if os_type.short_name not in _APT_OS:
        packages.append(
            _CreatePackage(messages, 'google-fluentd-start-service',
                           agent.package_state, agent.enable_autoupgrade))

    if agent.type is agent_policy.OpsAgentPolicy.Agent.Type.METRICS:
      packages.append(
          _CreatePackage(messages, 'stackdriver-agent', agent.package_state,
                         agent.enable_autoupgrade))
      # apt os will start the service automatically without the start-service.
      if os_type.short_name not in _APT_OS:
        packages.append(
            _CreatePackage(messages, 'stackdriver-agent-start-service',
                           agent.package_state, agent.enable_autoupgrade))
  return packages


def _CreatePackage(messages, pkg_name, agent_pkg_state, agent_autoupgrade):
  """Creates package in guest policy.

  Args:
    messages: os config guest policy API messages.
    pkg_name: package name.
    agent_pkg_state: package states.
    agent_autoupgrade: True or False.

  Returns:
    package in guest policy.
  """
  states = messages.Package.DesiredStateValueValuesEnum
  desired_state = None
  if agent_pkg_state is agent_policy.OpsAgentPolicy.Agent.PackageState.INSTALLED:
    if agent_autoupgrade:
      desired_state = states.UPDATED
    else:
      desired_state = states.INSTALLED
  elif agent_pkg_state is agent_policy.OpsAgentPolicy.Agent.PackageState.REMOVED:
    desired_state = states.REMOVED
  return messages.Package(name=pkg_name, desiredState=desired_state)


def _CreatePackageRepositories(messages, os_type, agents):
  """Create package repositories in guest policy.

  Args:
    messages: os config guest policy api messages.
    os_type: it contains os_version, os_shortname.
    agents: list of agents which contains version, package_state, type of
      {logging,metrics}.

  Returns:
    package repos in guest policy.
  """
  package_repos = None
  if os_type.short_name in _APT_OS:
    package_repos = _CreateAptPkgRepos(
        messages, _APT_CODENAMES.get(os_type.version), agents)
  elif os_type.short_name in {'rhel', 'centos'}:
    version = os_type.version.split('.')[0]
    version = version.split('*')[0]
    package_repos = _CreateYumPkgRepos(messages, version, agents)
  elif os_type.short_name in _SUSE_OS:
    version = os_type.version.split('.')[0]
    version = version.split('*')[0]
    package_repos = _CreateZypperPkgRepos(messages, version, agents)
  return package_repos


def _CreateZypperPkgRepos(messages, repo_distro, agents):
  zypper_pkg_repos = []
  for agent in agents:
    template = _AGENT_TEMPLATES[agent.type]
    repo_key = agent.version if '*.*' in agent.version else 'all'
    repo_name = template.zypper_package.repo[repo_key] % repo_distro
    zypper_pkg_repos.append(
        _CreateZypperPkgRepo(messages, template.repo_id, template.display_name,
                             repo_name))
  return zypper_pkg_repos


def _CreateZypperPkgRepo(messages, repo_id, display_name, repo_name):
  """Create a zypper repo in guest policy.

  Args:
    messages: os config guest policy api messages.
    repo_id: 'google-cloud-logging' or 'google-cloud-monitoring'.
    display_name: 'Google Cloud Logging Agent Repository' or 'Google Cloud
      Monitoring Agent Repository'.
    repo_name: repository name.

  Returns:
    zypper repos in guest policy.
  """
  return messages.PackageRepository(
      zypper=messages.ZypperRepository(
          id=repo_id,
          displayName=display_name,
          baseUrl='https://packages.cloud.google.com/yum/repos/%s' % repo_name,
          gpgKeys=[
              'https://packages.cloud.google.com/yum/doc/yum-key.gpg',
              'https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg'
          ]))


def _CreateYumPkgRepos(messages, repo_distro, agents):
  yum_pkg_repos = []
  for agent in agents:
    template = _AGENT_TEMPLATES[agent.type]
    repo_key = agent.version if '*.*' in agent.version else 'all'
    repo_name = template.yum_package.repo[repo_key] % repo_distro
    yum_pkg_repos.append(
        _CreateYumPkgRepo(messages, template.repo_id, template.display_name,
                          repo_name))
  return yum_pkg_repos


def _CreateYumPkgRepo(messages, repo_id, display_name, repo_name):
  """Create a yum repo in guest policy.

  Args:
    messages: os config guest policy api messages.
    repo_id: 'google-cloud-logging' or 'google-cloud-monitoring'.
    display_name: 'Google Cloud Logging Agent Repository' or 'Google Cloud
      Monitoring Agent Repository'.
    repo_name: repository name.

  Returns:
    yum repos in guest policy.
  """
  return messages.PackageRepository(
      yum=messages.YumRepository(
          id=repo_id,
          displayName=display_name,
          baseUrl='https://packages.cloud.google.com/yum/repos/%s' % repo_name,
          gpgKeys=[
              'https://packages.cloud.google.com/yum/doc/yum-key.gpg',
              'https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg'
          ]))


def _CreateAptPkgRepos(messages, repo_distro, agents):
  apt_pkg_repos = []
  for agent in agents or []:
    repo_key = agent.version if '*.*' in agent.version else 'all'
    repo_name = _AGENT_TEMPLATES[agent.type].apt_package.repo.get(
        repo_key) % repo_distro
    apt_pkg_repos.append(_CreateAptPkgRepo(messages, repo_name))
  return apt_pkg_repos


def _CreateAptPkgRepo(messages, repo_name):
  """Create an apt repo in guest policy.

  Args:
    messages: os config guest policy api messages.
    repo_name: repository name.

  Returns:
    An apt repo in guest policy.
  """
  return messages.PackageRepository(
      apt=messages.AptRepository(
          uri='https://packages.cloud.google.com/apt',
          distribution=repo_name,
          components=['main'],
          gpgKey='https://packages.cloud.google.com/apt/doc/apt-key.gpg'))


def _CreateOstypes(messages, assignment_os_types):
  os_types = []
  for assignment_os_type in assignment_os_types or []:
    os_type = messages.AssignmentOsType(
        osShortName=assignment_os_type.short_name,
        osVersion=assignment_os_type.version)
    os_types.append(os_type)
  return os_types


def _CreateGroupLabel(messages, assignment_group_labels):
  """Create guest policy group labels.

  Args:
    messages: os config guest policy api messages.
    assignment_group_labels: List of dict of key: value pair.

  Returns:
    group_labels in guest policy.
  """
  group_labels = []
  for group_label in assignment_group_labels or []:
    pairs = [
        messages.AssignmentGroupLabel.LabelsValue.AdditionalProperty(
            key=key, value=value) for key, value in group_label.items()
    ]
    group_labels.append(
        messages.AssignmentGroupLabel(
            labels=messages.AssignmentGroupLabel.LabelsValue(
                additionalProperties=pairs)))
  return group_labels


def _CreateAssignment(messages, assignment_group_labels, assignment_os_types,
                      assignment_zones, assignment_instances):
  """Creates a Assignment message from its components."""
  return messages.Assignment(
      groupLabels=_CreateGroupLabel(messages, assignment_group_labels),
      zones=assignment_zones or [],
      instances=assignment_instances or [],
      osTypes=_CreateOstypes(messages, assignment_os_types))


def _GetRecipeVersion(prev_recipes, recipe_name):
  for recipe in prev_recipes or []:
    if recipe.name == recipe_name:
      return str(int(recipe.version)+1)
  return '0'


def _CreateRecipes(messages, agents, os_type, prev_recipes):
  """Create recipes in guest policy.

  Args:
    messages: os config guest policy api messages.
    agents: ops agent policy agents.
    os_type: ops agent policy os_type.
    prev_recipes: a list of SoftwareRecipe.

  Returns:
    Recipes in guest policy
  """
  recipes = []
  for agent in agents or []:
    recipes.append(
        _CreateRecipe(messages, _CreateStepInScript(messages, agent, os_type),
                      _AGENT_TEMPLATES[agent.type].recipe_name,
                      _GetRecipeVersion(prev_recipes,
                                        _AGENT_TEMPLATES[agent.type].recipe_name
                                        )
                      )
        )
  return recipes


def _CreateRecipe(messages, run_script, recipe_name, version):
  return messages.SoftwareRecipe(
      desiredState=messages.SoftwareRecipe.DesiredStateValueValuesEnum.UPDATED,
      installSteps=[run_script],
      name=recipe_name,
      version=version)


def _CreateStepInScript(messages, agent, os_type):
  """Create scriptRun step in guest policy recipe section.

  Args:
    messages: os config guest policy api messages.
    agent: logging or metrics agent.
    os_type: it contains os_version, os_short_name.

  Returns:
    step of script to be ran in Recipe section.
  """
  step = messages.SoftwareRecipeStep()
  step.scriptRun = messages.SoftwareRecipeStepRunScript()

  if os_type.short_name in {'centos', 'rhel'}:
    os_version = os_type.version.split('.')[0]
    if agent.version == 'latest':
      agent_version = ''
    elif '*.*' in agent.version:
      agent_version = '-%s' % agent.version.replace('*.*', '*')
    else:
      agent_version = '-%s.el%s' % (agent.version, os_version)
    run_script = _AGENT_TEMPLATES[
        agent.type].yum_package.install_with_version % agent_version
  if os_type.short_name in _APT_OS:
    if agent.version == 'latest':
      agent_version = ''
    elif '*.*' in agent.version:
      agent_version = '=%s' % agent.version.replace('*.*', '*')
    else:
      agent_version = '=%s' % agent.version
    run_script = _AGENT_TEMPLATES[
        agent.type].apt_package.install_with_version % agent_version
  if os_type.short_name in _SUSE_OS:
    if agent.version == 'latest':
      agent_version = ''
    elif '*.*' in agent.version:
      agent_version = '<%s' % str(int(agent.version.split('.')[0])+1)+'.*'
    else:
      agent_version = '=%s' % agent.version
    run_script = _AGENT_TEMPLATES[
        agent.type].zypper_package.install_with_version % agent_version
  step.scriptRun.script = _AGENT_TEMPLATES[agent.type].run_agent % {
      'install': run_script
  }
  return step


def _CreateDescription(agents, description):
  """Create description in guest policy.

  Args:
    agents: agents in ops agent policy.
    description: description in ops agent policy.

  Returns:
    description in guest policy.
  """
  description_template = ('{"type": "ops-agents","description": "%s","agents": '
                          '[%s]}')

  agent_contents = [agent.ToJson() for agent in agents or []]

  return description_template % (description, ','.join(agent_contents))


def _SetAgentVersion(agents):
  for agent in agents or []:
    if agent.version in {'current-major', None, ''}:
      agent.version = _AGENT_TEMPLATES[agent.type].current_major_version


def ConvertOpsAgentPolicyToGuestPolicy(messages, ops_agents_policy,
                                       prev_recipes=None):
  """Converts Ops Agent policy to OS Config guest policy."""
  ops_agents_policy_assignment = ops_agents_policy.assignment
  _SetAgentVersion(ops_agents_policy.agents)
  # TODO(b/159365920): once os config supports multi repos, remove indexing [0].
  guest_policy = messages.GuestPolicy(
      description=_CreateDescription(ops_agents_policy.agents,
                                     ops_agents_policy.description),
      assignment=_CreateAssignment(messages,
                                   ops_agents_policy_assignment.group_labels,
                                   ops_agents_policy_assignment.os_types,
                                   ops_agents_policy_assignment.zones,
                                   ops_agents_policy_assignment.instances),
      packages=_CreatePackages(messages, ops_agents_policy.agents,
                               ops_agents_policy_assignment.os_types[0]),
      packageRepositories=_CreatePackageRepositories(
          messages, ops_agents_policy_assignment.os_types[0],
          ops_agents_policy.agents),
      recipes=_CreateRecipes(messages, ops_agents_policy.agents,
                             ops_agents_policy.assignment.os_types[0],
                             prev_recipes))

  return guest_policy
