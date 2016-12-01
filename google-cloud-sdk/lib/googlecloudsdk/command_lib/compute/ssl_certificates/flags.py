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
"""Flags and helpers for the compute ssl-certificates commands."""

from googlecloudsdk.command_lib.compute import flags as compute_flags


def SslCertificateArgument(required=True):
  return compute_flags.ResourceArgument(
      resource_name='ssl certificate',
      completion_resource_id='compute.sslCertificates',
      plural=False,
      required=required,
      global_collection='compute.sslCertificates',
      short_help='The name of the SSL certificate.')


def SslCertificateArgumentForOtherResource(resource, required=True):
  return compute_flags.ResourceArgument(
      name='--ssl-certificate',
      resource_name='ssl certificate',
      completion_resource_id='compute.sslCertificates',
      plural=False,
      required=required,
      global_collection='compute.sslCertificates',
      short_help=('A reference to an SSL certificate resource that is used for '
                  'server-side authentication.'),
      detailed_help="""\
        A reference to an SSL certificate resource that is used for
        server-side authentication. The SSL certificate must exist and cannot
        be deleted while referenced by a {0}.
        """.format(resource))
