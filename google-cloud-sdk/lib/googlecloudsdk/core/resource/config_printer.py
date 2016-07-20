# Copyright 2015 Google Inc. All Rights Reserved.
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

"""config format resource printer."""

from googlecloudsdk.core.resource import resource_printer_base


class ConfigPrinter(resource_printer_base.ResourcePrinter):
  """Prints a dictionary of dictionaries in config style.

  A dictionary of dictionaries in config style.
  """

  def __init__(self, *args, **kwargs):
    super(ConfigPrinter, self).__init__(*args, retain_none_values=True,
                                        **kwargs)
    # Print the title if specified.
    if 'title' in self.attributes:
      self._out.write(self.attributes['title'] + u'\n')

  def _AddRecord(self, record, delimit=False):
    """Immediately prints the given record in config style.

    Args:
      record: A JSON-serializable dict of dicts.
      delimit: Ignored.
    """
    for category, values in sorted(record.iteritems()):
      self._out.write(u'[{category}]\n'.format(category=category))
      for name, value in sorted(values.iteritems()):
        if value is None:
          self._out.write(u'{name} (unset)\n'.format(name=name))
        else:
          self._out.write(u'{name} = {value}\n'.format(name=name, value=value))
