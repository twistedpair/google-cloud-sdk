# Copyright 2014 Google Inc. All Rights Reserved.

"""Workflow to set up gcloud environment."""

import argparse
import os
import sys

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as c_exc
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io


class Init(base.Command):
  """Initialize or reinitialize gcloud."""

  detailed_help = {
      'DESCRIPTION': """\
          {description}

          {command} launches a interactive getting-started gcloud
          workflow, and replaces  `gcloud auth login` as the recommended
          command to execute after newly installing gcloud.  This workflow
          performs a variety of setup tasks, including the following:

            - launching an authorization flow or selecting credentials
            - setting properties including project, default GCE zone, and
              default GCE region
            - suggesting cloning a source repository

          Most users will run {command} to get started with gcloud. Subsequent
          {command} invocations can be use to create new gcloud configurations
          or to reinitialize existing configurations.  See `gcloud topic
          configurations` for additional information.
      """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'obsolete_project_arg',
        nargs='?',
        help=argparse.SUPPRESS)
    parser.add_argument(
        '--console-only',
        action='store_true',
        help=('Don\'t launch a browser for authentication.'))

  def Run(self, args):
    """Allows user to select configuration, and initialize it."""

    if args.obsolete_project_arg:
      raise c_exc.InvalidArgumentException(
          args.obsolete_project_arg,
          '`gcloud init` has changed and no longer takes a PROJECT argument. '
          'Please use `gcloud source repos clone` to clone this '
          'project\'s source repositories.')

    log.status.write('Welcome! This command will take you through '
                     'the configuration of gcloud.\n\n')

    if properties.VALUES.core.disable_prompts.GetBool():
      raise c_exc.InvalidArgumentException(
          'disable_prompts/--quiet',
          'gcloud init command cannot run with disabled prompts.')

    configuration_name = None
    try:
      configuration_name = self._PickConfiguration()
      if not configuration_name:
        return
      log.status.write('Your current configuration has been set to: [{0}]\n\n'
                       .format(configuration_name))

      if not self._PickAccount(args.console_only):
        return

      if not self._PickProject():
        return

      self._PickDefaultRegionAndZone()

      self._PickRepo()

      log.status.write('\ngcloud has now been configured!\n')
    finally:
      log.status.write('You can use [gcloud config] to '
                       'change more gcloud settings.\n\n')
      if configuration_name:
        log.status.write('Your current configuration is: [{0}]\n\n'
                         .format(configuration_name))
      log.status.flush()

      # Not using self._RunCmd to get command actual output.
      self.cli.Execute(['config', 'list'])

  def _PickAccount(self, console_only):
    """Checks if current credentials are valid, if not runs auth login.

    Args:
      console_only: bool, True if the auth flow shouldn't use the browser

    Returns:
      bool, True if valid credentials are setup.
    """

    auth_info = self._RunCmd(['auth', 'list'])
    if auth_info and auth_info.accounts:
      idx = console_io.PromptChoice(
          auth_info.accounts + ['Login with new credentials'],
          message='Pick credentials to use:',
          prompt_string=None)
      if idx is None:
        return None
      new_credentials = idx == len(auth_info.accounts)
    else:
      answer = console_io.PromptContinue(
          prompt_string='To continue, you must login. Would you like to login')
      if not answer:
        return False
      new_credentials = True
    if new_credentials:
      # gcloud auth login may have user interaction, do not suppress it.
      browser_args = ['--no-launch-browser'] if console_only else []
      if not self._RunCmd(['auth', 'login'],
                          ['--force', '--brief'] + browser_args,
                          disable_user_output=False):
        return None
    else:
      account = auth_info.accounts[idx]
      self._RunCmd(['config', 'set'], ['account', account])

    log.status.write('You are now logged in as: [{0}]\n\n'
                     .format(properties.VALUES.core.account.Get()))
    return True

  def _PickConfiguration(self):
    """Allows user to re-initialize, create or pick new configuration.

    Returns:
      Configuration name or None.
    """

    configs = self._RunCmd(['config', 'configurations', 'list'])
    if not configs:
      new_config_name = 'default'
      if self._RunCmd(['config', 'configurations', 'create'],
                      [new_config_name]):
        self._RunCmd(['config', 'configurations', 'activate'],
                     [new_config_name])
        properties.PropertiesFile.Invalidate()
      return new_config_name

    config_names = [cfg.name for cfg in configs]
    active_configs = [cfg.name for cfg in configs
                      if getattr(cfg, 'is_active', False)]
    if not active_configs:
      return None
    choices = []
    active_config = active_configs[0]
    log.status.write('Settings from you current configuration [{0}] are:\n'
                     .format(active_config))
    log.status.flush()
    # Not using self._RunCmd to get command actual output.
    self.cli.Execute(['config', 'list'])
    log.out.flush()
    log.status.write('\n')
    log.status.flush()
    choices.append(
        'Re-initialize this configuration [{0}] with new settings '.format(
            active_config))
    choices.append('Create a new configuration')
    config_choices = [name for name in config_names if name != active_config]
    choices.extend('Switch to and re-initialize '
                   'existing configuration: [{0}]'.format(name)
                   for name in config_choices)
    idx = console_io.PromptChoice(choices, message='Pick configuration to use:')
    if idx is None:
      return None
    if idx == 0:  # If reinitialize was selected.
      self._CleanCurrentConfiguration()
      return active_config
    if idx == 1:  # Second option is to create new configuration.
      return self._CreateConfiguration()
    config_name = config_choices[idx - 2]
    self._RunCmd(['config', 'configurations', 'activate'], [config_name])
    return config_name

  def _PickProject(self):
    """Allows user to select a project.

    Returns:
      str, project_id or None if was not selected.
    """
    projects = self._RunExperimentalCmd(['beta', 'projects', 'list'])

    if projects is None:  # Failed to get the list.
      project_id = console_io.PromptResponse(
          'Enter project id you would like to use:  ')
      if not project_id:
        return None
    else:
      projects = sorted(projects, key=lambda prj: prj.projectId)
      choices = ['[{0}]'.format(project.projectId) for project in projects]
      if not choices:
        log.status.write('\nThis account has no projects. Please create one in '
                         'developers console '
                         '(https://console.developers.google.com/project) '
                         'before running this command.\n')
        return None
      if len(choices) == 1:
        project_id = projects[0].projectId
      else:
        idx = console_io.PromptChoice(
            choices,
            message='Pick cloud project to use: ',
            prompt_string=None)
        if idx is None:
          return
        project_id = projects[idx].projectId

    self._RunCmd(['config', 'set'], ['project', project_id])
    log.status.write('Your current project has been set to: [{0}].\n\n'
                     .format(project_id))
    return project_id

  def _PickDefaultRegionAndZone(self):
    """Pulls metadata properties for region and zone and sets them in gcloud."""
    try:
      project_info = self._RunCmd(['compute', 'project-info', 'describe'])
    except c_exc.FailedSubCommand:
      log.status.write('Not setting default zone/region.\nMake sure Compute '
                       'Engine API is enabled for your project.\n\n')
      return None

    default_zone = None
    default_region = None
    if project_info is not None:
      metadata = project_info.get('commonInstanceMetadata', {})
      for item in metadata.get('items', []):
        if item['key'] == 'google-compute-default-zone':
          default_zone = item['value']
        elif item['key'] == 'google-compute-default-region':
          default_region = item['value']

    # Same logic applies to region and zone properties.
    def SetProperty(name, default_value, list_command):
      """Set named compute property to default_value or get via list command."""
      if default_value:
        log.status.write('Your project default compute {0} has been set to '
                         '[{1}].\nYou can change it by running '
                         '[gcloud config set compute/{0} NAME].\n\n'
                         .format(name, default_value['name']))
      else:
        values = self._RunCmd(list_command)
        if values is None:
          return
        values = list(values)
        idx = console_io.PromptChoice(
            ['[{0}]'.format(value['name']) for value in values]
            + ['Do not set default {0}'.format(name)],
            message=('Which compute {0} would you like '
                     'to use as project default?'.format(name)),
            prompt_string=None)
        if idx is None or idx == len(values):
          return
        default_value = values[idx]
      self._RunCmd(['config', 'set'],
                   ['compute/{0}'.format(name), default_value['name']])
      return default_value

    if default_zone:
      default_zone = self._RunCmd(['compute', 'zones', 'describe'],
                                  [default_zone])
    zone = SetProperty('zone', default_zone, ['compute', 'zones', 'list'])
    if zone and not default_region:
      default_region = zone['region']
    if default_region:
      default_region = self._RunCmd(['compute', 'regions', 'describe'],
                                    [default_region])
    SetProperty('region', default_region, ['compute', 'regions', 'list'])

  def _PickRepo(self):
    """Allows user to clone one of the projects repositories."""
    cmd = ['alpha', 'source', 'repos', 'list']
    repos = self._RunExperimentalCmd(cmd)

    if repos:
      repos = sorted(repo.name or 'default' for repo in repos)
      log.status.write(
          'This project has one or more associated git repositories.\n')
      idx = console_io.PromptChoice(
          ['[{0}]'.format(repo) for repo in repos] + ['Do not clone'],
          message='Pick repository to clone to your local machine:',
          prompt_string=None)
      if idx >= 0 and idx < len(repos):
        repo_name = repos[idx]
      else:
        return
    elif repos is None:
      log.status.write('Could not retrieve list of repos via [gcloud {0}]\n'
                       .format(' '.join(cmd)))
      log.status.write('Perhaps alpha commands are not enabled '
                       'or the repos list command failed.\n'
                       '\n')
      answer = console_io.PromptContinue(
          prompt_string='Generally projects have a repository named [default]. '
          'Would you like to try clone it?')
      if not answer:
        return
      repo_name = 'default'
    else:
      return

    self._CloneRepo(repo_name)

  def _CloneRepo(self, repo_name):
    """Queries user for output path and clones selected repo to it."""
    while True:
      clone_path = os.getcwd()
      clone_path = console_io.PromptResponse(
          'Where would you like to clone [{0}] repository to [{1}]:'
          .format(repo_name, clone_path))
      if not clone_path:
        clone_path = os.getcwd()
      if os.path.isdir(clone_path):
        break
      log.status.write('No such directory [{0}]\n'.format(clone_path))

    target_dir = os.path.join(clone_path, repo_name)
    self._RunCmd(['source', 'repos', 'clone'], [repo_name, target_dir])
    log.status.write('\nGit repository has been cloned to [{0}]\n'
                     .format(target_dir))

  def _CreateConfiguration(self):
    configuration_name = console_io.PromptResponse(
        'Enter configuration name:  ')
    new_config_name = self._RunCmd(['config', 'configurations', 'create'],
                                   [configuration_name])
    if new_config_name:
      self._RunCmd(['config', 'configurations', 'activate'],
                   [configuration_name])
      properties.PropertiesFile.Invalidate()
    return new_config_name

  def _CleanCurrentConfiguration(self):
    self._RunCmd(['config', 'unset'], ['account'])
    self._RunCmd(['config', 'unset'], ['project'])
    self._RunCmd(['config', 'unset'], ['compute/zone'])
    self._RunCmd(['config', 'unset'], ['compute/region'])

  def _RunCmd(self, cmd, params=None, disable_user_output=True):
    if not self.cli.IsValidCommand(cmd):
      log.info('Command %s does not exist.', cmd)
      return None
    if params is None:
      params = []
    args = cmd + params
    log.info('Executing: [gcloud %s]', ' '.join(args))
    try:
      # Disable output from individual commands, so that we get
      # command run results, and don't clutter output of init.
      if disable_user_output:
        args.append('--no-user-output-enabled')

      if (properties.VALUES.core.verbosity.Get() is None and
          disable_user_output):
        # Unless user explicitly set verbosity, suppress from subcommands.
        args.append('--verbosity=none')

      return self.cli.Execute(args)
    except SystemExit as exc:
      log.status.write('[{0}] has failed\n'.format(' '.join(cmd + params)))
      raise c_exc.FailedSubCommand(cmd + params, exc.code)
    except BaseException:
      log.status.write('Failed to run [{0}]\n'.format(' '.join(cmd + params)))
      raise

  def _RunExperimentalCmd(self, cmd, params=None):
    try:
      return self._RunCmd(cmd, params)
    except (Exception) as e:  # pylint:disable=broad-except
      cmd_string = ' '.join(cmd + (params or []))
      log.status.write(
          'Unexpected failure while executing [{0}]: [{1}: {2}]\n'
          'Please report by running `gcloud feedback`.\n\n'.format(
              cmd_string, type(e), e))
      log.debug('Failed to execute %s, %s, %s, %s', cmd_string, *sys.exc_info())
      return None

