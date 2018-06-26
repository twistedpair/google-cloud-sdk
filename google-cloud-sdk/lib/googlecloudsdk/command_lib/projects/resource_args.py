# -*- coding: utf-8 -*- #
# Copyright 2018 Google Inc. All Rights Reserved.
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
"""Common resource attributes that can be reused."""

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.core import properties


PROJECT_ATTRIBUTE_CONFIG = concepts.ResourceParameterAttributeConfig(
    name='project',
    help_text='The Cloud project for the {resource}.',
    fallthroughs=[
        # Typically argument fallthroughs should be configured at the command
        # level, but the --project flag is currently available in every command.
        deps.ArgFallthrough('--project'),
        deps.PropertyFallthrough(properties.VALUES.core.project)])
