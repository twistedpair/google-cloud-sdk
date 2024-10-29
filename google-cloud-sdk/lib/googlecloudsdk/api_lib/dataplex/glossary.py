# -*- coding: utf-8 -*- #
# Copyright 2024 Google Inc. All Rights Reserved.
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
"""Client for interaction with Glossary API CRUD DATAPLEX."""


from googlecloudsdk.api_lib.dataplex import util as dataplex_api


def GenerateGlossaryForCreateRequest(args):
  """Create Glossary Request."""
  module = dataplex_api.GetMessageModule()
  request = module.GoogleCloudDataplexV1Glossary(
      description=args.description,
      displayName=args.display_name,
      labels=dataplex_api.CreateLabels(
          module.GoogleCloudDataplexV1Glossary, args
      ),
  )
  return request


def WaitForOperation(operation):
  """Waits for the given google.longrunning.Operation to complete."""
  return dataplex_api.WaitForOperation(
      operation, dataplex_api.GetClientInstance().projects_locations_glossaries
  )
