# -*- coding: utf-8 -*- #
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

"""Cloud SDK markdown document linter renderer."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io

from googlecloudsdk.core.document_renderers import text_renderer


class LinterRenderer(text_renderer.TextRenderer):
  """Renders markdown to a list of lines where there is a linter error."""

  _HEADINGS_TO_LINT = ['NAME', 'EXAMPLES', 'DESCRIPTION']
  _NAME_WORD_LIMIT = 15
  _PERSONAL_PRONOUNS = [' me ', ' we ', ' I ', ' us ', ' he ', ' she ', ' him ',
                        ' her ', ' them ', ' they ']

  def __init__(self, *args, **kwargs):
    super(LinterRenderer, self).__init__(*args, **kwargs)
    self._file_out = self._out  # the output file inherited from TextRenderer
    self._null_out = io.StringIO()
    self._buffer = io.StringIO()
    self._out = self._buffer
    self._analyze = {'NAME': self._analyze_name,
                     'EXAMPLES': self._analyze_examples,
                     'DESCRIPTION': self._analyze_description}
    self._heading = ''
    self._prev_heading = ''
    self.example = False
    self.command_name = ''
    self.name_section = ''
    self.length_of_command_name = 0

  def _CaptureOutput(self, heading):
    # check if buffer is full from previous heading
    if self._buffer.getvalue() and self._prev_heading:
      self._Analyze(self._prev_heading, self._buffer.getvalue())
      ## refresh the StringIO()
      self._buffer = io.StringIO()
    self._out = self._buffer
    # save heading so can get it next time
    self._prev_heading = self._heading

  def _DiscardOutput(self, heading):
    self._out = self._null_out

  def _Analyze(self, heading, section):
    self._analyze[heading](section)

  def check_for_personal_pronouns(self, section):
    warnings = ''
    for pronoun in self._PERSONAL_PRONOUNS:
      if pronoun in section:
        warnings += '\nPlease remove personal pronouns.'
        break
    return warnings

  def Finish(self):
    if self._buffer.getvalue() and self._prev_heading:
      self._Analyze(self._prev_heading, self._buffer.getvalue())
    self._buffer.close()
    self._null_out.close()
    # This needs to be checked depending on the command's position in cli tree
    if not self.example:
      self._file_out.write('Refer to the detailed style guide: '
                           'go/cloud-sdk-help-guide#examples\nThis is the '
                           'analysis for EXAMPLES:\nYou have not included an '
                           'example.\n\n')

  def Heading(self, level, heading):
    self._heading = heading
    if heading in self._HEADINGS_TO_LINT:
      self._CaptureOutput(heading)
    else:
      self._DiscardOutput(heading)

  def _analyze_name(self, section):
    self.command_name = section.strip().split(' - ')[0]
    self.name_section = section.strip().split(' - ')[1].lower()
    self.length_of_command_name = len(self.command_name)
    warnings = self.check_for_personal_pronouns(section)

    # if more than 15 words
    if len(section.split()) > self._NAME_WORD_LIMIT:
      warnings += '\nPlease shorten the NAME section to less than '
      warnings += str(self._NAME_WORD_LIMIT) + ' words.'
    if warnings:
      # TODO(b/119550825): remove the go/ link from open source code
      self._file_out.write('Refer to the detailed style guide: '
                           'go/cloud-sdk-help-guide#name\nThis is the '
                           'analysis for NAME:')
      self._file_out.write(warnings + '\n\n')
    else:
      self._file_out.write('There are no errors for the NAME section.\n\n')

  def _analyze_examples(self, section):
    self.example = True
    warnings = self.check_for_personal_pronouns(section)
    if warnings:
      # TODO(b/119550825): remove the go/ link from open source code
      self._file_out.write('Refer to the detailed style guide: '
                           'go/cloud-sdk-help-guide#examples\n'
                           'This is the analysis for EXAMPLES:')
      self._file_out.write(warnings + '\n\n')
    else:
      self._file_out.write('There are no errors for the EXAMPLES '
                           'section.\n\n')

  def _analyze_description(self, section):
    warnings = self.check_for_personal_pronouns(section)
    if warnings:
      # TODO(b/119550825): remove the go/ link from open source code
      self._file_out.write('Refer to the detailed style guide: '
                           'go/cloud-sdk-help-guide#description\n'
                           'This is the analysis for DESCRIPTION:')
      self._file_out.write(warnings + '\n\n')
    else:
      self._file_out.write('There are no errors for the DESCRIPTION '
                           'section.\n\n')
