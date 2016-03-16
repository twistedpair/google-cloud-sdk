# Copyright 2014 Google Inc. All Rights Reserved.
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
"""Common classes and functions for zones."""

from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core.console import console_io


class ZoneResourceFetcher(object):
  """Mixin class for working with zones."""

  def GetZones(self, resource_refs):
    """Fetches zone resources."""
    errors = []
    requests = []
    zone_names = set()
    for resource_ref in resource_refs:
      if resource_ref.zone not in zone_names:
        zone_names.add(resource_ref.zone)
        requests.append((
            self.compute.zones,
            'Get',
            self.messages.ComputeZonesGetRequest(
                project=self.project,
                zone=resource_ref.zone)))

    res = list(request_helper.MakeRequests(
        requests=requests,
        http=self.http,
        batch_url=self.batch_url,
        errors=errors,
        custom_get_requests=None))

    if errors:
      return None
    else:
      return res

  def WarnForZonalCreation(self, resource_refs):
    """Warns the user if a zone has upcoming deprecation."""
    zones = self.GetZones(resource_refs)
    if not zones:
      return

    prompts = []
    zones_with_deprecated = []
    for zone in zones:
      if zone.deprecated:
        zones_with_deprecated.append(zone)

    if not zones_with_deprecated:
      return

    if zones_with_deprecated:
      phrases = []
      if len(zones_with_deprecated) == 1:
        phrases = ('zone is', 'this zone', 'the')
      else:
        phrases = ('zones are', 'these zones', 'their')
      title = ('\n'
               'WARNING: The following selected {0} deprecated.'
               ' All resources in {1} will be deleted after'
               ' {2} turndown date.'.format(phrases[0], phrases[1], phrases[2]))
      printable_deprecated_zones = []
      for zone in zones_with_deprecated:
        if zone.deprecated.deleted:
          printable_deprecated_zones.append(('[{0}] {1}').format(zone.name,
                                                                 zone.deprecated
                                                                 .deleted))
        else:
          printable_deprecated_zones.append('[{0}]'.format(zone.name))
      prompts.append(utils.ConstructList(title, printable_deprecated_zones))

    final_message = ' '.join(prompts)
    if not console_io.PromptContinue(message=final_message):
      raise calliope_exceptions.ToolException('Creation aborted by user.')
