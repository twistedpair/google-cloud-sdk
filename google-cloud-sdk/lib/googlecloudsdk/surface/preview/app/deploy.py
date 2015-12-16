
# Copyright 2013 Google Inc. All Rights Reserved.

"""The gcloud app deploy command."""

import argparse
import json
import os

from googlecloudsdk.api_lib.app import appengine_api_client
from googlecloudsdk.api_lib.app import appengine_client
from googlecloudsdk.api_lib.app import cloud_storage
from googlecloudsdk.api_lib.app import deploy_app_command_util
from googlecloudsdk.api_lib.app import deploy_command_util
from googlecloudsdk.api_lib.app import flags
from googlecloudsdk.api_lib.app import metric_names
from googlecloudsdk.api_lib.app import util
from googlecloudsdk.api_lib.app import yaml_parsing
from googlecloudsdk.api_lib.app.ext_runtimes import fingerprinting
from googlecloudsdk.api_lib.app.runtimes import fingerprinter
from googlecloudsdk.api_lib.source import context_util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.docker import constants
from googlecloudsdk.third_party.apis.cloudbuild import v1 as cloudbuild_v1


DEPLOY_MESSAGE_TEMPLATE = """\
{project}/{module} (from [{file}])
     Deployed URL: [{url}]
"""
# We can't reliably calculate the URL for domain scoped projects, so don't show
# it.
DEPLOY_MESSAGE_DOMAIN_SCOPED_TEMPLATE = """\
{project}/{module} (from [{file}])
"""
PROMOTE_MESSAGE = """\
     (add --promote if you also want to make this module available from
     [{default_url}])
"""


class DeployError(exceptions.Error):
  """Base class for app deploy failures."""


class RepoInfoLoadError(DeployError):
  """Indicates a failure to load a source context file."""

  def __init__(self, filename, inner_exception):
    self.filename = filename
    self.inner_exception = inner_exception

  def __str__(self):
    return 'Could not read repo info file {0}: {1}'.format(
        self.filename, self.inner_exception)


class MultiDeployError(DeployError):
  """Indicates a failed attempt to deploy multiple image urls."""

  def __str__(self):
    return ('No more than one module may be deployed when using the '
            'image-url flag')


class NoRepoInfoWithImageUrlError(DeployError):
  """The user tried to specify a repo info file with a docker image."""

  def __str__(self):
    return 'The --repo-info-file option is not compatible with --image_url.'


class UnsupportedRegistryError(DeployError):
  """Indicates an attempt to use an unsuported registry."""

  def __init__(self, image_url):
    self.image_url = image_url

  def __str__(self):
    return ('{0} is not in a supported registry.  Supported registries are '
            '{1}'.format(self.image_url, constants.ALL_SUPPORTED_REGISTRIES))


class DefaultBucketAccessError(DeployError):
  """Indicates a failed attempt to access a project's default bucket."""

  def __init__(self, project):
    self.project = project

  def __str__(self):
    return (
        'Could not retrieve the default Google Cloud Storage bucket for [{a}]. '
        'Please try again or use the [bucket] argument.').format(a=self.project)


DEFAULT_DEPLOYABLE = 'app.yaml'


def _DisplayProposedDeployment(project, app_config, version, promote):
  """Prints the details of the proposed deployment.

  Args:
    project: the name of the current project
    app_config: the application configuration to be deployed
    version: the version identifier of the application to be deployed
    promote: whether the newly deployed version will receive all traffic
      (this affects deployed URLs)

  Returns:
    dict (str->str), a mapping of module names to deployed module URLs

  This includes information on to-be-deployed modules (including module name,
  version number, and deployed URLs) as well as configurations.
  """
  # TODO(markpell): Have modules and configs be able to print themselves.  We
  # do this right now because we actually need to pass a yaml file to appcfg.
  # Until we can make a call with the correct values for project and version
  # it is weird to override those values in the yaml parsing code (because
  # it does not carry through to the actual file contents).
  deployed_urls = {}
  if app_config.Modules():
    printer = console_io.ListPrinter(
        'You are about to deploy the following modules:')
    deploy_messages = []
    for module, info in app_config.Modules().iteritems():
      use_ssl = deploy_command_util.UseSsl(info.parsed.handlers)
      version = None if promote else version
      if ':' in project:
        deploy_message = DEPLOY_MESSAGE_DOMAIN_SCOPED_TEMPLATE.format(
            project=project, module=module, file=info.file)
      else:
        url = deploy_command_util.GetAppHostname(
            project, module=info.module, version=version, use_ssl=use_ssl)
        deployed_urls[module] = url
        deploy_message = DEPLOY_MESSAGE_TEMPLATE.format(
            project=project, module=module, file=info.file, url=url)
      if not promote:
        default_url = deploy_command_util.GetAppHostname(
            project, module=info.module, use_ssl=use_ssl)
        deploy_message += PROMOTE_MESSAGE.format(default_url=default_url)
      deploy_messages.append(deploy_message)
    printer.Print(deploy_messages, output_stream=log.status)

  if app_config.Configs():
    printer = console_io.ListPrinter(
        'You are about to deploy the following configurations:')
    printer.Print(
        ['{0}/{1}  (from [{2}])'.format(project, c.config, c.file)
         for c in app_config.Configs().values()], output_stream=log.status)

  return deployed_urls


class Deploy(base.Command):
  """Deploy the local code and/or configuration of your app to App Engine.

  This command is used to deploy both code and configuration to the App Engine
  server.  As an input it takes one or more ``DEPLOYABLES'' that should be
  uploaded.  A ``DEPLOYABLE'' can be a module's .yaml file or a configuration's
  .yaml file.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To deploy a single module, run:

            $ {command} ~/my_app/app.yaml

          To deploy multiple modules, run:

            $ {command} ~/my_app/app.yaml ~/my_app/another_module.yaml
          """,
  }

  @staticmethod
  def Args(parser):
    """Get arguments for this command.

    Args:
      parser: argparse.ArgumentParser, the parser for this command.
    """
    flags.SERVER_FLAG.AddToParser(parser)
    parser.add_argument(
        '--version',
        help='The version of the app that will be created or replaced by this '
        'deployment.  If you do not specify a version, one will be generated '
        'for you.')
    parser.add_argument(
        '--env-vars',
        help=argparse.SUPPRESS)
    parser.add_argument(
        '--force',
        action='store_true',
        help=('Force deploying, overriding any previous in-progress '
              'deployments to this version.'))
    parser.add_argument(
        '--bucket',
        type=cloud_storage.GcsBucketArgument,
        help=argparse.SUPPRESS)
    docker_build_group = parser.add_mutually_exclusive_group()
    docker_build_group.add_argument(
        '--docker-build',
        choices=['remote', 'local'],
        default=None,
        help=("Perform a hosted ('remote') or local ('local') Docker build. To "
              "perform a local build, you must have your local docker "
              "environment configured correctly. The default is a hosted "
              "build."))
    deployables = parser.add_argument(
        'deployables', nargs='*',
        help='The yaml files for the modules or configurations you want to '
        'deploy.')
    deployables.detailed_help = (
        'The yaml files for the modules or configurations you want to deploy. '
        'If not given, defaults to `app.yaml` in the current directory. '
        'If that is not found, attempts to automatically generate necessary '
        'configuration files (such as app.yaml) in the current directory.')
    parser.add_argument(
        '--repo-info-file', metavar='filename',
        help=argparse.SUPPRESS)
    unused_repo_info_file_help = (
        'The name of a file containing source context information for the '
        'modules being deployed. If not specified, the source context '
        'information will be inferred from the directory containing the '
        'app.yaml file.')
    # TODO(b/24008797): Add this in when it's implemented.
    unused_stop_previous_version_help = (
        'Stop the previously running version when deploying a new version '
        'that receives all traffic (on by default).')
    parser.add_argument(
        '--stop-previous-version',
        action='store_true',
        default=None,
        help=argparse.SUPPRESS)
    parser.add_argument(
        '--image-url',
        help='Deploy with a specific Docker image.  Docker url must be '
        'from one of the valid gcr hostnames.')

    promote_group = parser.add_mutually_exclusive_group()
    promote_group.add_argument(
        '--promote',
        action='store_true',
        default=None,
        help='Promote the deployed version to receive all traffic.')
    promote_group.add_argument(
        '--set-default',
        default=None,
        action='store_true',
        help=('Set the deployed version to be the default serving version '
              '(deprecated; use --promote instead)'))

  def Run(self, args):
    if args.env_vars:
      log.warn('The env-vars flag is deprecated, and will soon be removed.')
    # Do this up-front to print applicable warnings early
    promote = deploy_command_util.GetPromoteFromArgs(args)

    project = properties.VALUES.core.project.Get(required=True)
    version = args.version or util.GenerateVersionId()
    use_cloud_build = properties.VALUES.app.use_cloud_build.GetBool()

    config_cleanup = None
    if args.deployables:
      app_config = yaml_parsing.AppConfigSet(args.deployables)
    else:
      if not os.path.exists(DEFAULT_DEPLOYABLE):
        console_io.PromptContinue(
            'Deployment to Google App Engine requires an app.yaml file. '
            'This command will run `gcloud preview app gen-config` to generate '
            'an app.yaml file for you in the current directory (if the current '
            'directory does not contain an App Engine module, please answer '
            '"no").', cancel_on_no=True)
        # This generates the app.yaml AND the Dockerfile (and related files).
        params = fingerprinting.Params(deploy=True)
        configurator = fingerprinter.IdentifyDirectory(os.getcwd(),
                                                       params=params)
        config_cleanup = configurator.GenerateConfigs()
        log.status.Print('\nCreated [{0}] in the current directory.\n'.format(
            DEFAULT_DEPLOYABLE))
      app_config = yaml_parsing.AppConfigSet([DEFAULT_DEPLOYABLE])

    remote_build = True
    docker_build_property = properties.VALUES.app.docker_build.Get()
    if args.docker_build:
      remote_build = args.docker_build == 'remote'
    elif docker_build_property:
      remote_build = docker_build_property == 'remote'

    gae_client = appengine_client.AppengineClient(args.server)
    api_client = appengine_api_client.GetApiClient(self.Http(timeout=None))
    log.debug('API endpoint: [{endpoint}], API version: [{version}]'.format(
        endpoint=api_client.client.url,
        version=api_client.api_version))
    cloudbuild_client = cloudbuild_v1.CloudbuildV1(http=self.Http(),
                                                   get_credentials=False)
    deployed_urls = _DisplayProposedDeployment(project, app_config, version,
                                               promote)
    if args.version or promote:
      # Prompt if there's a chance that you're overwriting something important:
      # If the version is set manually, you could be deploying over something.
      # If you're setting the new deployment to be the default version, you're
      # changing the target of the default URL.
      # Otherwise, all existing URLs will continue to work, so need to prompt.
      console_io.PromptContinue(default=True, throw_if_unattended=False,
                                cancel_on_no=True)

    log.status.Print('Beginning deployment...')

    source_contexts = []
    if args.repo_info_file:
      if args.image_url:
        raise NoRepoInfoWithImageUrlError()

      try:
        with open(args.repo_info_file, 'r') as f:
          source_contexts = json.load(f)
      except (ValueError, IOError) as ex:
        raise RepoInfoLoadError(args.repo_info_file, ex)
      if isinstance(source_contexts, dict):
        # This is an old-style source-context.json file. Convert to a new-
        # style array of extended contexts.
        source_contexts = [context_util.ExtendContextDict(source_contexts)]

    code_bucket = None
    if use_cloud_build or app_config.NonHermeticModules():
      # If using Argo CloudBuild, we'll need to upload source to a GCS bucket.
      code_bucket = self._GetCodeBucket(api_client, args)
      metrics.CustomTimedEvent(metric_names.GET_CODE_BUCKET)
      log.debug('Using bucket [{b}].'.format(b=code_bucket))
      if not code_bucket:
        raise DefaultBucketAccessError(project)

    modules = app_config.Modules()
    if args.image_url:
      if len(modules) != 1:
        raise MultiDeployError()
      for registry in constants.ALL_SUPPORTED_REGISTRIES:
        if args.image_url.startswith(registry):
          break
      else:
        raise UnsupportedRegistryError(args.image_url)
      module = modules.keys()[0]
      images = {module: args.image_url}
    else:
      images = deploy_command_util.BuildAndPushDockerImages(modules,
                                                            version,
                                                            gae_client,
                                                            cloudbuild_client,
                                                            code_bucket,
                                                            self.cli,
                                                            remote_build,
                                                            source_contexts,
                                                            config_cleanup)

    deployment_manifests = {}
    if app_config.NonHermeticModules():
      deployment_manifests = deploy_app_command_util.CopyFilesToCodeBucket(
          app_config.NonHermeticModules().items(), code_bucket, source_contexts)
      metrics.CustomTimedEvent(metric_names.COPY_APP_FILES)

    # Now do deployment.
    for (module, info) in app_config.Modules().iteritems():
      message = 'Updating module [{module}]'.format(module=module)
      with console_io.ProgressTracker(message):
        if args.force:
          log.warning('The --force argument is deprecated and no longer '
                      'required. It will be removed in a future release.')

        api_client.DeployModule(module, version, info,
                                deployment_manifests.get(module),
                                images.get(module))
        metrics.CustomTimedEvent(metric_names.DEPLOY_API)

        if promote:
          api_client.SetDefaultVersion(module, version)
          metrics.CustomTimedEvent(metric_names.SET_DEFAULT_VERSION_API)

    # Config files.
    for (c, info) in app_config.Configs().iteritems():
      message = 'Updating config [{config}]'.format(config=c)
      with console_io.ProgressTracker(message):
        gae_client.UpdateConfig(c, info.parsed)
    return deployed_urls

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    writer = log.out
    for module, url in result.items():
      writer.Print('Deployed module [{0}] to [{1}]'.format(module, url))

  def _GetCodeBucket(self, api_client, args):
    if args.bucket:
      return args.bucket
    # Attempt to retrieve the default appspot bucket, if one can be created.
    log.debug('No bucket specified, retrieving default bucket.')
    return api_client.GetApplicationCodeBucket()
