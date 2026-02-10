# -*- coding: utf-8 -*- #
# Copyright 2026 Google LLC. All Rights Reserved.
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
"""Request processor for Edge Cloud Zone surface arguments."""


from googlecloudsdk.calliope import exceptions


def SetParentForZonesList(ref, args, request):
  """Sets the parent field in the request for zone list."""
  del ref

  if args.IsSpecified('project'):
    request.parent = f'projects/{args.project}/locations/{args.location}'
  elif args.IsSpecified('organization'):
    request.parent = (
        f'organizations/{args.organization}/locations/{args.location}'
    )
  else:
    raise exceptions.OneOfArgumentsRequiredException(
        ['--organization', '--project'],
        'Error: Either --organization or --project must be specified.'
    )
  return request


def SetNameForZoneDescribe(ref, args, request):
  """Sets the name field in the request for zone describe."""
  del ref

  if args.IsSpecified('project'):
    request.name = (
        f'projects/{args.project}/locations/{args.location}/zones/{args.zone}'
    )
  elif args.IsSpecified('organization'):
    request.name = (
        f'organizations/{args.organization}/locations/{args.location}/zones/{args.zone}'
    )
  else:
    raise exceptions.OneOfArgumentsRequiredException(
        ['--organization', '--project'],
        'Error: Either --organization or --project must be specified.'
    )
  return request


