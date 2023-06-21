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
"""Factory for SessionTemplateConfig message."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


class SessionTemplateConfigFactory(object):
  """Factory for SessionTemplateConfig message.

  Factory to add SessionTemplateConfig message arguments to argument parser and
  create SessionTemplateConfig message from parsed arguments.
  """

  def __init__(self, dataproc):
    """Factory for SessionTemplateConfig message.

    Args:
      dataproc: A api_lib.dataproc.Dataproc instance.
    """
    self.dataproc = dataproc

  def GetMessage(self, args):
    """Builds a SessionTemplateConfig message according to user settings.

    Args:
      args: Parsed arguments.

    Returns:
      SessionTemplateConfig: A SessionTemplateConfig message instance.
    """
    session_template_config = self.dataproc.messages.SessionTemplateConfig()
    if args.session_template:
      session_template_config.templateUri = args.session_template

    return session_template_config


def AddArguments(parser):
  """Adds arguments related to SessionTemplateConfig message to the given parser."""
  parser.add_argument(
      '--session-template',
      help=('Session template to use.'))
