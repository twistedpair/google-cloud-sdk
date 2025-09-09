# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Printer for just printing contexts of an object."""

import json
from googlecloudsdk.api_lib.storage.gcs_json import metadata_util
from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage.resources import gcs_resource_reference
from googlecloudsdk.command_lib.storage.resources import resource_reference
from googlecloudsdk.core.resource import custom_printer_base
from googlecloudsdk.core.resource import resource_printer


CONTEXT_ONLY_PRINTER_FORMAT = "contextsonly"
RESOURCE_FORMAT = """{storage_url}:
Custom Contexts:
{custom_contexts}"""


class ContextsOnlyPrinter(custom_printer_base.CustomPrinterBase):
  """Prints just the URL and attached contexts in customized format.

  This printer is intended to be used with the `gcloud storage objects list`
  and `gcloud storage objects describe` command and only works with
  ObjectResource objects.
  """

  @staticmethod
  def Register():
    resource_printer.RegisterFormatter(
        CONTEXT_ONLY_PRINTER_FORMAT,
        ContextsOnlyPrinter,
        hidden=True,
    )

  def Transform(self, resp):
    """Transforms ObjectResource data into a customized format.

    Args:
      resp: a dictionary object representing the ObjectResource.

    Returns:
      str, The ObjectResource data in a customized format.

    Example output:
      gs://rahman-bucket/dir/file.txt#1755111082179286:
      Custom Contexts:
        ram : tam
        sam : bam
    """
    if isinstance(resp, resource_reference.Resource) and not isinstance(
        resp, gcs_resource_reference.GcsObjectResource
    ):
      # Ideally this should never happen in production.
      raise errors.Error("Invalid formatter for non-gcs-object resources.")
    elif not isinstance(resp, resource_reference.Resource):
      raise errors.Error(
          "You cannot combine contextsonly formatter with other"
          " formatters such as --uri, --stat or --raw."
      )

    url_string = resp.storage_url
    custom_contexts = resp.contexts if resp.contexts else {}
    custom_contexts_to_print = {
        key: value[metadata_util.CONTEXT_VALUE_LITERAL]
        for key, value in custom_contexts.items()
        if value[metadata_util.CONTEXT_TYPE_LITERAL]
        == metadata_util.ContextType.CUSTOM.value
    }
    return RESOURCE_FORMAT.format(
        storage_url=url_string,
        custom_contexts=json.dumps(custom_contexts_to_print, indent=2),
    )
