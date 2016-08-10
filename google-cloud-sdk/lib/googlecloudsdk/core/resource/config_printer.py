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

import StringIO

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

  def _AddCategory(self, out, label, items):
    """Prints items in the label category to out.

    Args:
      out: The output stream.
      label: A list of label strings.
      items: The items to list for label, either dict iteritems, an enumerated
        list, or a scalar value.
    """
    top = StringIO.StringIO()
    sub = StringIO.StringIO()
    for name, value in sorted(items):
      name = unicode(name)
      try:
        values = value.iteritems()
        self._AddCategory(sub, label + [name], values)
        continue
      except AttributeError:
        pass
      if value is None:
        top.write(u'{name} (unset)\n'.format(name=name))
      elif isinstance(value, list):
        self._AddCategory(sub, label + [name], enumerate(value))
      else:
        top.write(u'{name} = {value}\n'.format(name=name, value=value))
    top_content = top.getvalue()
    sub_content = sub.getvalue()
    if label and (top_content or
                  sub_content and not sub_content.startswith('[')):
      out.write(u'[{0}]\n'.format('.'.join(label)))
    if top_content:
      out.write(top_content)
    if sub_content:
      out.write(sub_content)

  def _AddRecord(self, record, delimit=False):
    """Prints the given record to self._out in config style.

    Nothing is printed if the record is not a JSON-serializable dict.

    Args:
      record: A JSON-serializable dict.
      delimit: Ignored.
    """
    try:
      values = record.iteritems()
      self._AddCategory(self._out, [], values)
    except AttributeError:
      pass
