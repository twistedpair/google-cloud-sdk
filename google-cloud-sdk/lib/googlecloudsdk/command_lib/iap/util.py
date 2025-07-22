# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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

"""Utils for IAP commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.iap import util as iap_api
from googlecloudsdk.calliope import exceptions as calliope_exc
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.command_lib.iap import exceptions as iap_exc
from googlecloudsdk.core import properties


APP_ENGINE_RESOURCE_TYPE = 'app-engine'
BACKEND_SERVICES_RESOURCE_TYPE = 'backend-services'
WEB_RESOURCE_TYPE = 'iap_web'
COMPUTE_RESOURCE_TYPE = 'compute'
ORG_RESOURCE_TYPE = 'organization'
FOLDER_RESOURCE_TYPE = 'folder'
FORWARDING_RULE_RESOURCE_TYPE = 'forwarding-rule'
CLOUD_RUN_RESOURCE_TYPE = 'cloud-run'
WEB_ENABLE_DISABLE_RESOURCE_TYPE_ENUM = (
    APP_ENGINE_RESOURCE_TYPE,
    BACKEND_SERVICES_RESOURCE_TYPE,
)
IAM_RESOURCE_TYPE_ENUM = (
    APP_ENGINE_RESOURCE_TYPE,
    BACKEND_SERVICES_RESOURCE_TYPE,
    FORWARDING_RULE_RESOURCE_TYPE,
)
IAM_RESOURCE_TYPE_ENUM_ALPHA_BETA = (
    APP_ENGINE_RESOURCE_TYPE,
    BACKEND_SERVICES_RESOURCE_TYPE,
    FORWARDING_RULE_RESOURCE_TYPE,
    CLOUD_RUN_RESOURCE_TYPE,
)
SETTING_RESOURCE_TYPE_ENUM = (
    APP_ENGINE_RESOURCE_TYPE,
    WEB_RESOURCE_TYPE,
    COMPUTE_RESOURCE_TYPE,
    ORG_RESOURCE_TYPE,
    FOLDER_RESOURCE_TYPE,
    BACKEND_SERVICES_RESOURCE_TYPE,
    FORWARDING_RULE_RESOURCE_TYPE,
)
SETTING_RESOURCE_TYPE_ENUM_ALPHA_BETA = (
    APP_ENGINE_RESOURCE_TYPE,
    WEB_RESOURCE_TYPE,
    COMPUTE_RESOURCE_TYPE,
    ORG_RESOURCE_TYPE,
    FOLDER_RESOURCE_TYPE,
    FORWARDING_RULE_RESOURCE_TYPE,
    CLOUD_RUN_RESOURCE_TYPE,
    BACKEND_SERVICES_RESOURCE_TYPE,
)


def AddIamDestGroupArgs(parser):
  """Adds DestGroup args for managing IAM policies.

  Args:
    parser: An argparse.ArgumentParser-like object. It is mocked out in order to
      capture some information, but behaves like an ArgumentParser.
  """
  parser.add_argument(
      '--dest-group',
      required=True,
      help='Name of the Destination Group.')
  parser.add_argument(
      '--region',
      required=True,
      help='Region of the Destination Group.')


def AddDestGroupArgs(parser):
  """Adds DestGroup args for managing the resource.

  Args:
    parser: An argparse.ArgumentParser-like object. It is mocked out in order to
      capture some information, but behaves like an ArgumentParser.
  """
  parser.add_argument(
      'group_name',
      help='Name of the Destination Group.')
  parser.add_argument(
      '--region',
      metavar='REGION',
      required=True,
      help='Region of the Destination Group.')


def AddDestGroupCreateIpAndFqdnArgs(parser):
  """Adds IP and FQDN args for DestGroup Create command.

  Args:
    parser: An argparse.ArgumentParser-like object. It is mocked out in order to
      capture some information, but behaves like an ArgumentParser.
  """
  parser.add_argument(
      '--ip-range-list',
      help='List of ip-ranges in the Destination Group.')
  parser.add_argument(
      '--fqdn-list',
      help='List of FQDNs in the Destination Group.')


def AddDestGroupUpdateIpAndFqdnArgs(parser):
  """Adds IP and FQDN args for DestGroup Update command.

  Args:
    parser: An argparse.ArgumentParser-like object. It is mocked out in order to
      capture some information, but behaves like an ArgumentParser.
  """
  group = parser.add_group(required=True)
  group.add_argument(
      '--ip-range-list',
      help='List of ip-ranges in the Destination Group.')
  group.add_argument(
      '--fqdn-list',
      help='List of FQDNs in the Destination Group.')


def AddDestGroupListRegionArgs(parser):
  """Adds Region arg for DestGroup List command.

  Args:
    parser: An argparse.ArgumentParser-like object. It is mocked out in order to
      capture some information, but behaves like an ArgumentParser.
  """
  parser.add_argument(
      '--region',
      metavar='REGION',
      required=False,
      help='Region of the Destination Group, will list all regions by default',
      default='-',
  )


def AddIapIamResourceArgs(
    parser, support_cloud_run=False
):
  """Adds flags for an IAP IAM resource.

  Args:
    parser: An argparse.ArgumentParser-like object. It is mocked out in order to
      capture some information, but behaves like an ArgumentParser.
    support_cloud_run: bool, provide support to cloud-run resource-type.
  """
  group = parser.add_group()

  if support_cloud_run:
    group.add_argument(
        '--resource-type',
        choices=IAM_RESOURCE_TYPE_ENUM_ALPHA_BETA,
        help='Resource type of the IAP resource.',
    )
  else:
    group.add_argument(
        '--resource-type',
        choices=IAM_RESOURCE_TYPE_ENUM,
        help='Resource type of the IAP resource.',
    )
  group.add_argument('--service', help='Service name.')
  if support_cloud_run:
    group.add_argument(
        '--region',
        help=(
            'Region name. Not applicable for `resource-type=app-engine`.'
            ' Required when `resource-type=backend-services` and regional'
            ' scoped. Not applicable for global backend-services. Required when'
            ' `resource-type=cloud-run`.'
        ),
    )
  else:
    group.add_argument(
        '--region',
        help=(
            'Region name. Should only be specified with'
            ' `--resource-type=backend-services` if it is a regional scoped.'
            ' Not applicable for global scoped backend services.'
        ),
    )
  group.add_argument(
      '--version',
      help=(
          'Service version. Should only be specified with '
          '`--resource-type=app-engine`.'
      ),
  )


def AddIapResourceArgs(parser):
  """Adds flags for an IAP resource.

  Args:
    parser: An argparse.ArgumentParser-like object. It is mocked out in order to
      capture some information, but behaves like an ArgumentParser.
  """
  group = parser.add_group()
  group.add_argument(
      '--resource-type',
      required=True,
      choices=WEB_ENABLE_DISABLE_RESOURCE_TYPE_ENUM,
      help='Resource type of the IAP resource.')
  group.add_argument(
      '--service',
      help='Service name. Required with `--resource-type=backend-services`.')
  group.add_argument(
      '--region',
      help=(
          "Region name. Not applicable for ``app-engine''. Optional when"
          " ``resource-type'' is ``compute''."
      ),
  )


def AddIapSettingArg(
    parser, support_cloud_run=False
):
  """Adds flags for an IAP settings resource.

  Args:
    parser: An argparse.ArgumentParser-like object. It is mocked out in order to
      capture some information, but behaves like an ArgumentParser.
    support_cloud_run: bool, provide support to cloud-run resource-type.
  """
  group = parser.add_group()
  group.add_argument('--organization', help='Organization ID.')
  group.add_argument('--folder', help='Folder ID.')
  group.add_argument('--project', help='Project ID.')

  if support_cloud_run:
    group.add_argument(
        '--resource-type',
        choices=SETTING_RESOURCE_TYPE_ENUM_ALPHA_BETA,
        help=(
            'Resource type of the IAP resource. For Backend Services, you can'
            ' use both `compute` and `backend-services` as resource type.'
        ),
    )
  else:
    group.add_argument(
        '--resource-type',
        choices=SETTING_RESOURCE_TYPE_ENUM,
        help=(
            'Resource type of the IAP resource. For Backend Services, you can'
            ' use both `compute` and `backend-services` as resource type.'
        ),
    )

  group.add_argument(
      '--service',
      help=(
          'Service name. Optional when `resource-type` is `compute` or'
          ' `app-engine`.'
      ),
  )
  if support_cloud_run:
    group.add_argument(
        '--region',
        help=(
            'Region name. Not applicable for `app-engine`. Required when'
            ' `resource-type=compute` and regional scoped. Not'
            ' applicable for global scoped compute. Required when'
            ' `resource-type=cloud-run`.'
        ),
    )
  else:
    group.add_argument(
        '--region',
        help=(
            'Region name. Not applicable for `app-engine`. Required when'
            ' `resource-type=compute` and regional scoped. Not'
            ' applicable for global scoped compute.'
        ),
    )
  group.add_argument(
      '--version',
      help=(
          'Version name. Not applicable for `compute`. Optional when'
          ' `resource-type=app-engine`.'
      ),
  )


def AddOauthClientArgs(parser):
  """Adds OAuth client args.

  Args:
    parser: An argparse.ArgumentParser-like object. It is mocked out in order to
      capture some information, but behaves like an ArgumentParser.
  """
  group = parser.add_group()
  group.add_argument(
      '--oauth2-client-id',
      required=True,
      help='OAuth 2.0 client ID to use.')
  group.add_argument(
      '--oauth2-client-secret',
      required=True,
      help='OAuth 2.0 client secret to use.')


def AddAddIamPolicyBindingArgs(parser):
  iam_util.AddArgsForAddIamPolicyBinding(
      parser,
      add_condition=True)


def AddRemoveIamPolicyBindingArgs(parser):
  iam_util.AddArgsForRemoveIamPolicyBinding(
      parser,
      add_condition=True)


def AddIAMPolicyFileArg(parser):
  """Adds flags for an IAM policy file.

  Args:
    parser: An argparse.ArgumentParser-like object. It is mocked out in order to
      capture some information, but behaves like an ArgumentParser.
  """
  parser.add_argument(
      'policy_file', help='JSON or YAML file containing the IAM policy.')


def AddIapSettingFileArg(parser):
  """Add flags for the IAP setting file.

  Args:
    parser: An argparse.ArgumentParser-like object. It is mocked out in order to
      capture some information, but behaves like an ArgumentParser.
  """
  parser.add_argument(
      'setting_file',
      help="""JSON or YAML file containing the IAP resource settings.

JSON example:

```
{
  "access_settings": {
    "oauth_settings": {
      "login_hint": {
        "value": "test_hint"
      }
    },
    "gcip_settings": {
      "tenant_ids": [
        "tenant1-p9puj",
        "tenant2-y8rxc"
      ],
      "login_page_uri": {
        "value": "https://test.com/?apiKey=abcd_efgh"
      }
    },
    "cors_settings": {
      "allow_http_options": {
        "value": true
      }
    }
  },
  "application_settings": {
    "csm_settings": {
      "rctoken_aud": {
        "value": "test_aud"
      }
    }
  }
}
```

YAML example:

```
accessSettings :
  oauthSettings:
    loginHint: test_hint
  gcipSettings:
    tenantIds:
    - tenant1-p9puj
    - tenant2-y8rxc
    loginPageUri: https://test.com/?apiKey=abcd_efgh
  corsSettings:
    allowHttpOptions: true
applicationSettings:
  csmSettings:
    rctokenAud: test_aud
```
""")


def ParseIapIamResource(
    release_track,
    args,
    support_cloud_run=False,
):
  """Parse an IAP IAM resource from the input arguments.

  Args:
    release_track: base.ReleaseTrack, release track of command.
    args: an argparse namespace. All the arguments that were provided to this
      command invocation.
    support_cloud_run: bool, whether to support cloud run.

  Raises:
    calliope_exc.InvalidArgumentException: if a provided argument does not apply
        to the specified resource type.
    iap_exc.InvalidIapIamResourceError: if an IapIamResource could not be parsed
        from the arguments.

  Returns:
    The specified IapIamResource
  """
  project = properties.VALUES.core.project.GetOrFail()
  if not args.resource_type:
    if args.service:
      raise calliope_exc.InvalidArgumentException(
          '--service',
          '`--service` cannot be specified without `--resource-type`.',
      )
    if args.region:
      raise calliope_exc.InvalidArgumentException(
          '--region',
          '`--region` cannot be specified without `--resource-type`.',
      )
    if args.version:
      raise calliope_exc.InvalidArgumentException(
          '--version',
          '`--version` cannot be specified without `--resource-type`.',
      )
    return iap_api.IAPWeb(release_track, project)
  elif args.resource_type == APP_ENGINE_RESOURCE_TYPE:
    if args.region:
      raise calliope_exc.InvalidArgumentException(
          '--region',
          '`--region` cannot be specified for `--resource-type=app-engine`.',
      )
    if args.service and args.version:
      return iap_api.AppEngineServiceVersion(
          release_track, project, args.service, args.version
      )
    elif args.service:
      return iap_api.AppEngineService(release_track, project, args.service)
    if args.version:
      raise calliope_exc.InvalidArgumentException(
          '--version', '`--version` cannot be specified without `--service`.'
      )
    return iap_api.AppEngineApplication(release_track, project)
  elif args.resource_type == BACKEND_SERVICES_RESOURCE_TYPE:
    if args.version:
      raise calliope_exc.InvalidArgumentException(
          '--version',
          '`--version` cannot be specified for '
          '`--resource-type=backend-services`.',
      )
    if args.region:
      if args.service:
        return iap_api.BackendService(
            release_track, project, args.region, args.service
        )
      else:
        return iap_api.BackendServices(release_track, project, args.region)
    elif args.service:
      return iap_api.BackendService(release_track, project, None, args.service)
    return iap_api.BackendServices(release_track, project, None)
  elif args.resource_type == FORWARDING_RULE_RESOURCE_TYPE:
    if args.version:
      raise calliope_exc.InvalidArgumentException(
          '--version',
          '`--version` cannot be specified for '
          '`--resource-type=forwarding-rule`.',
      )
    if args.service:
      return iap_api.ForwardingRule(release_track, project, args.region,
                                    args.service)
    else:
      return iap_api.ForwardingRules(release_track, project, args.region)
  elif (support_cloud_run and args.resource_type == CLOUD_RUN_RESOURCE_TYPE):
    if args.version:
      raise calliope_exc.InvalidArgumentException(
          '--version',
          '`--version` cannot be specified for '
          '`--resource-type=cloud-run`.',
      )
    if not args.region:
      raise calliope_exc.InvalidArgumentException(
          '--region',
          '`--region` must be specified for '
          '`--resource-type=cloud-run`.',
      )
    if args.service:
      return iap_api.CloudRun(release_track, project, args.region, args.service)
    else:
      return iap_api.CloudRuns(release_track, project, args.region)

  # This shouldn't be reachable, based on the IAP IAM resource parsing logic.
  raise iap_exc.InvalidIapIamResourceError('Could not parse IAP IAM resource.')


def ParseIapResource(release_track, args):
  """Parse an IAP resource from the input arguments.

  Args:
    release_track: base.ReleaseTrack, release track of command.
    args: an argparse namespace. All the arguments that were provided to this
      command invocation.

  Raises:
    calliope_exc.InvalidArgumentException: if `--version` was specified with
        resource type 'backend-services'.
    iap_exc.InvalidIapIamResourceError: if an IapIamResource could not be parsed
        from the arguments.

  Returns:
    The specified IapIamResource
  """
  project = properties.VALUES.core.project.GetOrFail()
  if args.resource_type:
    if args.resource_type == APP_ENGINE_RESOURCE_TYPE:
      if args.service:
        raise calliope_exc.InvalidArgumentException(
            '--service',
            '`--service` cannot be specified for '
            '`--resource-type=app-engine`.')
      return iap_api.AppEngineApplication(
          release_track,
          project)
    elif args.resource_type == BACKEND_SERVICES_RESOURCE_TYPE:
      if not args.service:
        raise calliope_exc.RequiredArgumentException(
            '--service',
            '`--service` must be specified for '
            '`--resource-type=backend-services`.')

      return iap_api.BackendService(
          release_track, project, args.region, args.service
      )

  raise iap_exc.InvalidIapIamResourceError('Could not parse IAP resource.')


def ParseIapSettingsResource(
    release_track,
    args,
    support_cloud_run=False
):
  """Parse an IAP setting resource from the input arguments.

  Args:
    release_track: base.ReleaseTrack, release track of command.
    args: an argparse namespace. All the arguments that were provided to this
      command invocation.
    support_cloud_run: bool, whether to support cloud run.

  Raises:
    calliope_exc.InvalidArgumentException: if `--version` was specified with
        resource type 'backend-services'.

  Returns:
    The specified IapSettingsResource
  """
  if args.organization:
    if args.resource_type:
      raise calliope_exc.InvalidArgumentException(
          '--resource-type',
          '`--resource-type` should not be specified at organization level',
      )
    if args.project:
      raise calliope_exc.InvalidArgumentException(
          '--project',
          '`--project` should not be specified at organization level',
      )
    return iap_api.IapSettingsResource(
        release_track, 'organizations/{0}'.format(args.organization)
    )
  if args.folder:
    if args.resource_type:
      raise calliope_exc.InvalidArgumentException(
          '--resource-type',
          '`--resource-type` should not be specified at folder level',
      )
    if args.project:
      raise calliope_exc.InvalidArgumentException(
          '--project', '`--project` should not be specified at folder level'
      )
    return iap_api.IapSettingsResource(
        release_track, 'folders/{0}'.format(args.folder)
    )
  if args.project:
    if args.service and not args.resource_type:
      raise calliope_exc.InvalidArgumentException(
          '--service',
          '`--service` cannot be specified without `--resource-type`.')
    if args.region and not args.resource_type:
      raise calliope_exc.InvalidArgumentException(
          '--region',
          '`--region` cannot be specified without `--resource-type`.')
    if args.version and not args.resource_type:
      raise calliope_exc.InvalidArgumentException(
          '--version',
          '`--version` cannot be specified without `--resource-type`.')

    if not args.resource_type:
      return iap_api.IapSettingsResource(
          release_track, 'projects/{0}'.format(args.project)
      )
    else:
      if args.resource_type == WEB_RESOURCE_TYPE:
        return iap_api.IapSettingsResource(
            release_track, 'projects/{0}/iap_web'.format(args.project)
        )
      elif args.resource_type == APP_ENGINE_RESOURCE_TYPE:
        if not args.service:
          return iap_api.IapSettingsResource(
              release_track,
              'projects/{0}/iap_web/appengine-{1}'.format(
                  args.project, args.project
              ),
          )
        else:
          if args.version:
            return iap_api.IapSettingsResource(
                release_track,
                'projects/{0}/iap_web/appengine-{1}/services/{2}/versions/{3}'
                .format(args.project, args.project, args.service, args.version),
            )
          else:
            return iap_api.IapSettingsResource(
                release_track,
                'projects/{0}/iap_web/appengine-{1}/services/{2}'.format(
                    args.project, args.project, args.service
                ),
            )
      elif (
          args.resource_type == COMPUTE_RESOURCE_TYPE
          or args.resource_type == BACKEND_SERVICES_RESOURCE_TYPE
      ):
        path = ['projects', args.project, 'iap_web']
        if args.region:
          path.append('compute-{}'.format(args.region))
        else:
          path.append('compute')
        if args.service:
          path.extend(['services', args.service])
        return iap_api.IapSettingsResource(release_track, '/'.join(path))
      elif (args.resource_type == FORWARDING_RULE_RESOURCE_TYPE):
        path = ['projects', args.project, 'iap_web']
        if args.version:
          raise calliope_exc.InvalidArgumentException(
              '--version',
              '`--version` cannot be specified for '
              '`--resource-type=forwarding-rule`.',
          )
        if args.region:
          path.append('forwarding_rule-{}'.format(args.region))
        else:
          path.append('forwarding_rule')
        if args.service:
          path.extend(['services', args.service])
        return iap_api.IapSettingsResource(release_track, '/'.join(path))
      elif (support_cloud_run and
            args.resource_type == CLOUD_RUN_RESOURCE_TYPE):
        path = ['projects', args.project, 'iap_web']
        if args.version:
          raise calliope_exc.InvalidArgumentException(
              '--version',
              '`--version` cannot be specified for '
              '`--resource-type=cloud-run`.',
          )
        if not args.region:
          raise calliope_exc.InvalidArgumentException(
              '--region',
              '`--region` must be specified for '
              '`--resource-type=cloud-run`.',
          )
        path.append('cloud_run-{}'.format(args.region))
        if args.service:
          path.extend(['services', args.service])
        return iap_api.IapSettingsResource(release_track, '/'.join(path))
      else:
        raise iap_exc.InvalidIapIamResourceError(
            'Unsupported IAP settings resource type.')

  raise iap_exc.InvalidIapIamResourceError(
      'Could not parse IAP settings resource.')


def ParseIapDestGroupResource(release_track, args):
  """Parses an IAP TCP DestGroup resource from the input arguments.

  Args:
    release_track: base.ReleaseTrack, release track of command.
    args: an argparse namespace. All the arguments that were provided to this
      command invocation.

  Returns:
    The specified IAP TCP DestGroup resource.
  """
  project = properties.VALUES.core.project.GetOrFail()
  group = getattr(args, 'group_name', None)
  if group is None:
    group = args.dest_group
  return iap_api.IapTunnelDestGroupResource(release_track, project, args.region,
                                            group)


def ParseIapDestGroupResourceWithNoGroupId(release_track, args):
  """Parses an IAP TCP Tunnel resource from the input arguments.

  Args:
    release_track: base.ReleaseTrack, release track of command.
    args: an argparse namespace. All the arguments that were provided to this
      command invocation.

  Returns:
    The specified IAP TCP Tunnel resource.
  """
  project = properties.VALUES.core.project.GetOrFail()
  return iap_api.IapTunnelDestGroupResource(release_track, project, args.region)
