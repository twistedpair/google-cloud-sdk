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

"""Module for common transport utilities, such as request wrapping."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import platform
import re
import uuid

from googlecloudsdk.core import config
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.console import console_io

from googlecloudsdk.core.util import platforms


# Alternative spellings of User-Agent header key that may appear in requests.
_NORMALIZED_USER_AGENT = b'user-agent'


def MakeUserAgentString(cmd_path=None):
  """Return a user-agent string for this request.

  Contains 'gcloud' in addition to several other product IDs used for tracing in
  metrics reporting.

  Args:
    cmd_path: str representing the current command for tracing.

  Returns:
    str, User Agent string.
  """
  return ('gcloud/{version}'
          ' command/{cmd}'
          ' invocation-id/{inv_id}'
          ' environment/{environment}'
          ' environment-version/{env_version}'
          ' interactive/{is_interactive}'
          ' from-script/{from_script}'
          ' python/{py_version}'
          ' term/{term}'
          ' {ua_fragment}').format(
              version=config.CLOUD_SDK_VERSION.replace(' ', '_'),
              cmd=(cmd_path or properties.VALUES.metrics.command_name.Get()),
              inv_id=uuid.uuid4().hex,
              environment=properties.GetMetricsEnvironment(),
              env_version=properties.VALUES.metrics.environment_version.Get(),
              is_interactive=console_io.IsInteractive(error=True,
                                                      heuristic=True),
              py_version=platform.python_version(),
              ua_fragment=platforms.Platform.Current().UserAgentFragment(),
              from_script=console_io.IsRunFromShellScript(),
              term=console_attr.GetConsoleAttr().GetTermIdentifier())


def GetDefaultTimeout():
  return properties.VALUES.core.http_timeout.GetInt() or 300


def GetTraceValue():
  """Return a value to be used for the trace header."""
  # Token to be used to route service request traces.
  trace_token = properties.VALUES.core.trace_token.Get()
  # Username to which service request traces should be sent.
  trace_email = properties.VALUES.core.trace_email.Get()
  # Enable/disable server side logging of service requests.
  trace_log = properties.VALUES.core.trace_log.GetBool()

  if trace_token:
    return 'token:{0}'.format(trace_token)
  elif trace_email:
    return 'email:{0}'.format(trace_email)
  elif trace_log:
    return 'log'
  return None


def IsTokenUri(uri):
  """Determine if the given URI is for requesting an access token."""
  if uri in ['https://accounts.google.com/o/oauth2/token',
             'https://www.googleapis.com/oauth2/v3/token',
             'https://www.googleapis.com/oauth2/v4/token',
             'https://oauth2.googleapis.com/token',
             'https://oauth2.googleapis.com/oauth2/v4/token']:
    return True

  metadata_regexp = ('metadata.google.internal/computeMetadata/.*?/instance/'
                     'service-accounts/.*?/token')

  return re.search(metadata_regexp, uri) is not None
