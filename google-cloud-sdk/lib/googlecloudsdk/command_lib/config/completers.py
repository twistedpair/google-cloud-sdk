# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Argcomplete completers for various config related things."""


from googlecloudsdk.core import properties
from googlecloudsdk.core.configurations import named_configs


def PropertiesCompleter(prefix, **unused_kwargs):
  """An argcomplete completer for property and section names."""
  all_sections = properties.VALUES.AllSections()
  options = []

  if '/' in prefix:
    # Section has been specified, only return properties under that section.
    parts = prefix.split('/', 1)
    section = parts[0]
    prefix = parts[1]
    if section in all_sections:
      section_str = section + '/'
      props = properties.VALUES.Section(section).AllProperties()
      options.extend([section_str + p for p in props if p.startswith(prefix)])
  else:
    # No section.  Return matching sections and properties in the default
    # group.
    options.extend([s + '/' for s in all_sections if s.startswith(prefix)])
    section = properties.VALUES.default_section.name
    props = properties.VALUES.Section(section).AllProperties()
    options.extend([p for p in props if p.startswith(prefix)])

  return options


def NamedConfigCompleter(prefix, **unused_kwargs):
  """An argcomplete completer for existing named configuration names."""
  configs = named_configs.ConfigurationStore.AllConfigs().keys()
  return [c for c in configs if c.startswith(prefix)]
