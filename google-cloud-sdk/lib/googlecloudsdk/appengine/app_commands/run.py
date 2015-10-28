# Copyright 2013 Google Inc. All Rights Reserved.

"""The Run command."""

import argparse
import os

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.updater import update_manager

from googlecloudsdk.appengine.lib import dev_appserver_adapter
from googlecloudsdk.appengine.lib import yaml_parsing
from googlecloudsdk.appengine.lib.images import util


_RUNTIME_COMPONENTS = {
    'java': 'app-engine-java',
    'php55': 'app-engine-php',
}
_WARNING_RUNTIMES = {
    'go': ('The Cloud SDK no longer ships runtimes for Go apps.  Please use '
           'the Go SDK that can be found at: '
           'https://cloud.google.com/appengine/downloads'),
    'php': ('The Cloud SDK no longer ships runtimes for PHP 5.4.  Please set '
            'your runtime to be "php55".')
}


class Run(base.Command):
  """(DEPRECATED) Run one or more modules in the local development application server.

  This comamand is deprecated, and will soon be removed. Please use
  `dev_appserver.py` (in the same directory as the `gcloud` command) instead.

  This command is used to run one or more of your modules in the local
  development application server.  This allows you to test and debug your app
  before deploying.  As an input it takes one or more ``RUNNABLES'' that should
  be run locally.  A ``RUNNABLE'' can be a module's .yaml file, or a directory.
  If given a directory, all modules found will be run.  You can run multiple
  modules at the same time, even if they are implemented in different languages.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To run a single module, run:

            $ {command} ~/my_app/app.yaml

          To run multiple modules, run:

            $ {command} ~/my_app/app.yaml ~/my_app/another_module.yaml

          OR

            $ {command} ~/my_app/

          To run a Java module, please use Maven and the gcloud-maven-plugin:
          https://cloud.google.com/appengine/docs/java/managed-vms/maven
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'runnables',
        metavar='RUNNABLES',
        nargs='+',
        help='The yaml files for the modules you want to run.  This also '
        'accepts any yaml configuration files needed to run your modules.')

    parser.add_argument(
        '--host',
        type=arg_parsers.HostPort.Parse,
        default=properties.VALUES.app.host.Get(),
        help='The host and port on which to start the local '
        'web server (in the format host:port)')
    parser.add_argument(
        '--admin-host',
        type=arg_parsers.HostPort.Parse,
        default=properties.VALUES.app.admin_host.Get(),
        help='The host and port on which to start the admin '
        'server (in the format host:port)')
    parser.add_argument(
        '--api-host',
        type=arg_parsers.HostPort.Parse,
        default=properties.VALUES.app.api_host.Get(),
        help='The host and port on which to start the API '
        'server (in the format host:port)')
    parser.add_argument(
        '--log-level',
        help='The minimum verbosity of logs from your app that '
        'will be displayed in the terminal. (debug, info, '
        'warning, critical, error)  Defaults to current '
        'verbosity setting.')
    parser.add_argument(
        '--auth-domain', default='gmail.com',
        help='Name of the authorization domain to use')
    parser.add_argument(
        '--max-module-instances',
        help='The maximum number of runtime instances that can '
        'be started for a particular module - the value can be '
        'an integer, in which case all modules are limited to '
        'that number of instances, or a comma-separated list '
        'of module:max_instances, e.g. default:5,backend:3')
    parser.add_argument(
        '--custom-entrypoint',
        help='Specify an entrypoint for custom runtime modules. This is '
        'required when such modules are present. Include "{port}" in the '
        'string (without quotes) to pass the port number in as an argument. '
        'For instance: --custom_entrypoint="gunicorn -b localhost:{port} '
        'mymodule:application"')

    gcs = parser.add_argument_group('Google Cloud Storage')
    gcs.add_argument(
        '--enable-cloud-datastore',
        action='store_true', default=False,
        help=argparse.SUPPRESS)
    gcs.add_argument(
        '--default-gcs-bucket-name',
        help='Default Google Cloud Storage bucket name')

    # App Identity flags.
    appidentity = parser.add_argument_group('App Identity API')
    appidentity.add_argument(
        '--appidentity-email-address',
        help='Email address associated with a service account '
        'that has a downloadable key. May be None for no local '
        'application identity.')
    appidentity.add_argument(
        '--appidentity-private-key-path',
        help='Path to private key file associated with service '
        'account (.pem format). Must be set if '
        'appidentity-email-address is set.')

    # Python flags.
    python = parser.add_argument_group(
        'Python Language Support',
        'Flags controlling how modules written in Python are run')
    python.add_argument(
        '--python-startup-script',
        help='The script to run at the startup of new Python '
        'runtime instances (useful for tools such as debuggers)')

    # Java flags.
    java = parser.add_argument_group(
        'Java Language Support',
        'Flags controlling how modules written in Java are run')
    java.add_argument(
        '--jvm-flag', action='append',
        help='Additional arguments to pass to the java command when launching '
        'an instance of the app. May be specified more than once.'
        ' Example: --jvm-flag=-Xmx1024m --jvm-flag=-Xms256m')

    # PHP flags.
    php = parser.add_argument_group(
        'PHP Language Support',
        'Flags controlling how modules written in PHP are run')
    php.add_argument(
        '--php-executable-path',
        help='The full path to the PHP executable to use to run your PHP '
        'module.')

    # Blobstore.
    blobstore = parser.add_argument_group('Blobstore')
    blobstore.add_argument(
        '--blobstore-path',
        help='Path to directory used to store blob contents '
        '(defaults to a subdirectory of --storage-path if not set)')

    # Datastore.
    datastore = parser.add_argument_group('Datastore')
    datastore.add_argument(
        '--storage-path',
        help='The default location for storing application data. Can be '
        'overridden for specific kinds of data using --datastore-path, '
        '--blobstore-path, and/or --logs-path')
    datastore.add_argument(
        '--datastore-path',
        help='Path to a file used to store datastore contents '
        '(defaults to a file in --storage-path if not set)')
    datastore.add_argument(
        '--clear-datastore',
        action='store_true', default=False,
        help='Clear the datastore on startup')
    datastore.add_argument(
        '--datastore-consistency-policy',
        default='time',
        choices=['consistent', 'random', 'time'],
        help='The policy to apply when deciding whether a '
        'datastore write should appear in global queries')
    datastore.add_argument(
        '--require-indexes',
        action='store_true', default=False,
        help='Generate an error on datastore queries that '
        'require a composite index not found in index.yaml')

    # Logs.
    logs = parser.add_argument_group('App Logs')
    logs.add_argument(
        '--logs-path',
        help='Path to a file used to store request logs '
        '(defaults to a file in --storage-path if not set)')
    logs.add_argument(
        '--enable-mvm-logs',
        action='store_true', default=False,
        help='Enable logs collection and display in local Admin Console '
        'for Managed VM modules.')

    # Mail API.
    mail = parser.add_argument_group('Mail API')
    mail.add_argument(
        '--show-mail-body',
        action='store_true', default=False,
        help='Logs the contents of e-mails sent using the Mail API')
    mail.add_argument(
        '--enable-sendmail',
        action='store_true', default=False,
        help='Use the "sendmail" tool to transmit e-mail sent '
        'using the Mail API (ignored if --smtp-host is set)')
    mail.add_argument(
        '--smtp-host',
        type=arg_parsers.HostPort.Parse,
        help='The host and port of an SMTP server to use to '
        'transmit e-mail sent using the Mail API, in the format host:port')
    mail.add_argument(
        '--smtp-user',
        help='Username to use when connecting to the SMTP '
        'server specified with --smtp-host')
    mail.add_argument(
        '--smtp-password',
        help='Password to use when connecting to the SMTP '
        'server specified with --smtp-host')
    mail.add_argument(
        '--smtp-allow-tls',
        action='store_true', default=False,
        help='Allow TLS to be used when the SMTP server '
        'announces TLS support (ignored if --smtp-host is not set)')

    # Miscellaneous.
    misc = parser.add_argument_group('Miscellaneous')
    misc.add_argument(
        '--use-mtime-file-watcher',
        action='store_true', default=False,
        help='Use mtime polling for detecting source code changes - '
        'useful if modifying code from a remote machine using a distributed '
        'file system')
    misc.add_argument(
        '--allow-skipped-files',
        action='store_true', default=False,
        help='Make files specified in the app.yaml "skip_files"'
        ' or "static" clauses readable by the application.')

  _FORWARDED_OPTIONS = (
      'storage_path', 'log_level', 'auth_domain', 'max_module_instances',
      'use_mtime_file_watcher', 'enable_cloud_datastore',
      'appidentity_email_address', 'appidentity_private_key_path',
      'python_startup_script', 'blobstore_path', 'datastore_path',
      'clear_datastore', 'datastore_consistency_policy', 'require_indexes',
      'logs_path', 'show_mail_body', 'enable_sendmail', 'smtp_user',
      'smtp_password', 'smtp_allow_tls', 'allow_skipped_files',
      'default_gcs_bucket_name', 'jvm_flag', 'enable_mvm_logs',
      'custom_entrypoint'
  )

  def InstallRequiredComponents(self, modules):
    components = set(['app-engine-python'])
    for (_, info) in modules.iteritems():
      if not info.runtime:
        continue
      # Match runtimes containing this substring (i.e. java matches java, java7)
      for (runtime, component) in _RUNTIME_COMPONENTS.iteritems():
        if runtime in info.runtime:
          components.add(component)
          break
      if not info.is_vm:
        # Only show warnings for V1 runtimes.
        warning = _WARNING_RUNTIMES.get(info.runtime)
        if warning:
          log.warning(warning)
    msg = ('The following language runtimes for the modules you are about to '
           'run will now be installed: [{components}]'
           .format(components=', '.join(sorted(components))))
    update_manager.UpdateManager.EnsureInstalledAndRestart(components, msg)

  def Run(self, args):
    log.warn('The `app run` command is deprecated and will soon be removed.\n\n'
             'Please use dev_appserver.py (in the same directory as the '
             '`gcloud` command) instead.')
    app_config = yaml_parsing.AppConfigSet(args.runnables, project=None,
                                           version=None, check_version=False)
    self.InstallRequiredComponents(app_config.Modules())

    project = properties.VALUES.core.project.Get(required=True)

    runner = dev_appserver_adapter.DevAppServerAdapter()
    runner.AddGlobalFlagIfSet('application', project)
    if args.host:
      runner.AddGlobalFlagIfSet('host', args.host.host)
      runner.AddGlobalFlagIfSet('port', args.host.port)
    if args.admin_host:
      runner.AddGlobalFlagIfSet('admin_host', args.admin_host.host)
      runner.AddGlobalFlagIfSet('admin_port', args.admin_host.port)
    if args.api_host:
      runner.AddGlobalFlagIfSet('api_host', args.api_host.host)
      runner.AddGlobalFlagIfSet('api_port', args.api_host.port)
    if args.smtp_host:
      runner.AddGlobalFlagIfSet('smtp_host', args.smtp_host.host)
      runner.AddGlobalFlagIfSet('smtp_port', args.smtp_host.port)

    runner.AddGlobalFlagIfSet('skip_sdk_update_check', True)

    for option in self._FORWARDED_OPTIONS:
      runner.AddGlobalFlagIfSet(option, getattr(args, option))

    if args.php_executable_path:
      if not os.path.exists(args.php_executable_path):
        raise exceptions.ToolException(
            'The given value for --php-executable-path: [{path}] does not '
            'exist.'.format(path=args.php_executable_path))
      runner.AddGlobalFlagIfSet('php_executable_path',
                                args.php_executable_path)

    runnables = []
    for (c, info) in app_config.Configs().iteritems():
      log.err.Print(('Config [{config}] found in file [{file}]'.format(
          config=c, file=info.file)))
      runnables.append(info.file)

    for (module, info) in sorted(app_config.Modules().iteritems()):
      log.err.Print(('Module [{module}] found in file [{file}]'.format(
          module=module, file=info.file)))
      runnables.append(info.file)
    runner.Start(*runnables)
