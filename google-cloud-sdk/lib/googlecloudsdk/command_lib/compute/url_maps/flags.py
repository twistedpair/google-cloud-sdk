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
"""Flags and helpers for the compute url-maps commands."""

from googlecloudsdk.command_lib.compute import flags as compute_flags

DEFAULT_LIST_FORMAT = """\
    table(
      name,
      defaultService
    )"""


def UrlMapArgument(required=True, plural=False):
  return compute_flags.ResourceArgument(
      name='url_map_name',
      resource_name='URL map',
      completion_resource_id='compute.urlMaps',
      plural=plural,
      required=required,
      global_collection='compute.urlMaps')


def UrlMapArgumentForTargetProxy(required=True, proxy_type='HTTP'):
  return compute_flags.ResourceArgument(
      name='--url-map',
      resource_name='url map',
      completion_resource_id='compute.urlMaps',
      plural=False,
      required=required,
      global_collection='compute.urlMaps',
      short_help=(
          'A reference to a URL map resource that defines the mapping of '
          'URLs to backend services.'),
      detailed_help="""\
        A reference to a URL map resource that defines the mapping of
        URLs to backend services. The URL map must exist and cannot be
        deleted while referenced by a target {0} proxy.
        """.format(proxy_type))
