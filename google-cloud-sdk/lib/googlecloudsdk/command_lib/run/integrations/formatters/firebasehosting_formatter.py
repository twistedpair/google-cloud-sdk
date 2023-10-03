# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Fallback formatter for Cloud Run Integrations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from apitools.base.py import encoding
from googlecloudsdk.command_lib.run.integrations.formatters import default_formatter as default
from googlecloudsdk.core import properties


class FirebaseHostingFormatter(default.DefaultFormatter):
  """Formatter for firebase-hosting integration."""

  def CallToAction(self, record):
    """Call to action to add domains and ingress.

    Args:
      record: integration_printer.Record class that just holds data.

    Returns:
      A formatted string of the call to action message,
      or None if no call to action is required.
    """
    fbh_config = encoding.MessageToDict(record.resource.config)
    site_id = fbh_config.get('siteId')

    project = properties.VALUES.core.project.Get(required=True)
    return (
        'To configure free custom domain mappings for this site, visit the'
        ' Firebase console at'
        ' https://console.firebase.google.com/project/{}/hosting/sites/{}\nTo'
        ' make this site publicly available, make sure the Cloud Run service'
        " has ingress configured to allow 'All' traffic. Learn more at"
        ' https://cloud.google.com/run/docs/securing/ingress'.format(
            project, site_id
        )
    )
