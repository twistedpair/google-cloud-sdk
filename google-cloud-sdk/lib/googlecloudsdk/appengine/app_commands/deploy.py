
# Copyright 2013 Google Inc. All Rights Reserved.

"""The gcloud app deploy command."""

import argparse

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.docker import constants
from googlecloudsdk.third_party.apis.cloudbuild import v1 as cloudbuild_v1

from googlecloudsdk.appengine.lib import appengine_api_client
from googlecloudsdk.appengine.lib import appengine_client
from googlecloudsdk.appengine.lib import cloud_storage
from googlecloudsdk.appengine.lib import deploy_app_command_util
from googlecloudsdk.appengine.lib import deploy_command_util
from googlecloudsdk.appengine.lib import flags
from googlecloudsdk.appengine.lib import metric_names
from googlecloudsdk.appengine.lib import util
from googlecloudsdk.appengine.lib import yaml_parsing


DEPLOY_MESSAGE_TEMPLATE = """\
{project}/{module} (from [{file}])
     Deployed URL: [{url}]
"""
PROMOTE_MESSAGE = """\
     (add --promote if you also want to make this module available from
     [{default_url}])
"""

MULTIPLE_MODULES_MESSAGE = """\
In a future release, the `gcloud preview app deploy` command will no longer
support deploying multiple modules in the same invocation. Instead, please
deploy each module individually.
"""

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
  # TODO(user): Have modules and configs be able to print themselves.  We
  # do this right now because we actually need to pass a yaml file to appcfg.
  # Until we can make a call with the correct values for project and version
  # it is weird to override those values in the yaml parsing code (because
  # it does not carry through to the actual file contents).
  deployed_urls = {}
  if len(app_config.Modules()) > 1:
    log.warn(MULTIPLE_MODULES_MESSAGE)
  if app_config.Modules():
    printer = console_io.ListPrinter(
        'You are about to deploy the following modules:')
    deploy_messages = []
    for module, info in app_config.Modules().iteritems():
      use_ssl = deploy_command_util.UseSsl(info.parsed.handlers)
      version = None if promote else version
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
    parser.add_argument(
        'deployables', nargs='+',
        help='The yaml files for the modules or configurations you want to '
        'deploy.')
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

  @property
  def use_admin_api(self):
    """Whether to use the admin api for legacy deployments."""
    return properties.VALUES.app.use_appengine_api.GetBool()

  def Run(self, args):
    if args.env_vars:
      log.warn('The env-vars flag is deprecated, and will soon be removed.')
    # Do this up-front to print applicable warnings early
    promote = deploy_command_util.GetPromoteFromArgs(args)

    project = properties.VALUES.core.project.Get(required=True)
    use_cloud_build = properties.VALUES.app.use_cloud_build.GetBool()

    app_config = yaml_parsing.AppConfigSet(
        args.deployables, project, args.version or util.GenerateVersionId())

    remote_build = True
    docker_build_property = properties.VALUES.app.docker_build.Get()
    if args.docker_build:
      remote_build = args.docker_build == 'remote'
    elif docker_build_property:
      remote_build = docker_build_property == 'remote'

    # This will either be args.version or a generated version.  Either way, if
    # any yaml file has a version in it, it must match that version.
    version = app_config.Version()

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

    code_bucket = None
    if use_cloud_build:
      # If using Argo CloudBuild, we'll need to upload source to a GCS bucket.
      code_bucket = self._GetCodeBucket(api_client, args)

    modules = app_config.Modules()
    if args.image_url:
      if len(modules) != 1:
        raise exceptions.ToolException(
            'No more than one module may be deployed when using the '
            'image-url flag')
      for registry in constants.ALL_SUPPORTED_REGISTRIES:
        if args.image_url.startswith(registry):
          break
      else:
        raise exceptions.ToolException(
            '%s is not in a supported registry.  Supported registries are %s' %
            (args.image_url,
             constants.ALL_SUPPORTED_REGISTRIES))
      module = modules.keys()[0]
      images = {module: args.image_url}
    else:
      images = deploy_command_util.BuildAndPushDockerImages(modules,
                                                            version,
                                                            gae_client,
                                                            cloudbuild_client,
                                                            code_bucket,
                                                            self.cli,
                                                            remote_build)

    deployment_manifests = {}
    if app_config.NonHermeticModules() and self.use_admin_api:
      # TODO(user): Consider doing this in parallel with
      # BuildAndPushDockerImage.
      code_bucket = self._GetCodeBucket(api_client, args)
      metrics.CustomTimedEvent(metric_names.GET_CODE_BUCKET)
      log.debug('Using bucket [{b}].'.format(b=code_bucket))
      if not code_bucket:
        raise exceptions.ToolException(('Could not retrieve the default Google '
                                        'Cloud Storage bucket for [{a}]. '
                                        'Please try again or use the [bucket] '
                                        'argument.').format(a=project))
      deployment_manifests = deploy_app_command_util.CopyFilesToCodeBucket(
          app_config.NonHermeticModules().items(), code_bucket)
      metrics.CustomTimedEvent(metric_names.COPY_APP_FILES)

    # Now do deployment.
    for (module, info) in app_config.Modules().iteritems():
      message = 'Updating module [{module}]'.format(module=module)
      with console_io.ProgressTracker(message):
        if args.force:
          gae_client.CancelDeployment(module=module, version=version)
          metrics.CustomTimedEvent(metric_names.CANCEL_DEPLOYMENT)

        if info.is_hermetic or self.use_admin_api:
          api_client.DeployModule(module, version, info,
                                  deployment_manifests.get(module),
                                  images.get(module))
          metrics.CustomTimedEvent(metric_names.DEPLOY_API)
        else:
          gae_client.DeployModule(module, version, info.parsed, info.file)
          metrics.CustomTimedEvent(metric_names.DEPLOY_ADMIN_CONSOLE)

        if promote:
          if info.is_hermetic or self.use_admin_api:
            api_client.SetDefaultVersion(module, version)
            metrics.CustomTimedEvent(metric_names.SET_DEFAULT_VERSION_API)
          else:
            gae_client.SetDefaultVersion(modules=[module], version=version)
            metrics.CustomTimedEvent(
                metric_names.SET_DEFAULT_VERSION_ADMIN_CONSOLE)

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
