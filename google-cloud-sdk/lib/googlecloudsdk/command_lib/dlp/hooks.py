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
"""Argument processors for DLP surface arguments."""
from __future__ import absolute_import
from __future__ import unicode_literals

import io
import os

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


_DLP_API = 'dlp'
_DLP_API_VERSION = 'v2'

_COLOR_SPEC_ERROR_SUFFIX = """\
Colors should be specified as a string of `r,g,b` float values in the interval
[0,1] representing the amount of red, green, and blue in the color,
respectively. For example, `black = 0,0,0`, `red = 1.0,0,0`,
`white = 1.0,1.0,1.0`, and so on.
"""

VALID_IMAGE_EXTENSIONS = {
    'n_a': 'IMAGE',
    '.png': 'IMAGE_PNG',
    '.jpeg': 'IMAGE_JPEG',
    '.jpg': 'IMAGE_JPEG',
    '.svg': 'IMAGE_SVG',
    '.bmp': 'IMAGE_BMP'
}


class ImageFileError(exceptions.Error):
  """Error if an image file is improperly formatted or missing."""


class RedactColorError(exceptions.Error):
  """Error if a redact color is improperly formatted or missing."""


# Misc/Helper Functions
def _GetMessageClass(msg_type_name):
  msg = apis.GetMessagesModule(_DLP_API, _DLP_API_VERSION)
  return getattr(msg, msg_type_name)


def ValidateExtension(extension):
  if not extension:  # No extension is ok.
    return True
  # But if provided it should match expected values
  return extension and (extension in VALID_IMAGE_EXTENSIONS)


def _ConvertColorValue(color):
  j = float(color)
  if j > 1.0 or j < 0.0:
    raise ValueError('Invalid Color.')

  return j


def ValidateAndParseColors(value):
  """Validates that values has proper format and returns parsed components."""
  values = value.split(',')

  if len(values) == 3:
    try:
      return [_ConvertColorValue(x) for x in values]
    except ValueError:
      raise RedactColorError('Invalid Color Value(s) [{}]. '
                             '{}'.format(value, _COLOR_SPEC_ERROR_SUFFIX))
  else:
    raise RedactColorError('You must specify exactly 3 color values [{}]. '
                           '{}'.format(value, _COLOR_SPEC_ERROR_SUFFIX))


# Types
def InfoType(value):  # Defines elment type for infoTypes collection on request
  """Return GooglePrivacyDlpV2InfoType message for a parsed value."""
  infotype = _GetMessageClass('GooglePrivacyDlpV2InfoType')
  return infotype(name=value)


# Request Hooks
def SetRequestParent(ref, args, request):
  """Set parent value for a DlpProjectsContentInspectRequest."""
  del ref
  parent = args.project or properties.VALUES.core.project.Get(required=True)
  project_ref = resources.REGISTRY.Parse(parent, collection='dlp.projects')
  request.parent = project_ref.RelativeName()
  return request


# Argument Processors
def GetReplaceTextTransform(value):
  replace_config = _GetMessageClass('GooglePrivacyDlpV2ReplaceValueConfig')
  value_holder = _GetMessageClass('GooglePrivacyDlpV2Value')
  return replace_config(newValue=value_holder(stringValue=value))


def GetInfoTypeTransform(value):
  del value
  infotype_config = _GetMessageClass(
      'GooglePrivacyDlpV2ReplaceWithInfoTypeConfig')
  return infotype_config()


def GetRedactTransform(value):
  del value
  redact_config = _GetMessageClass('GooglePrivacyDlpV2RedactConfig')
  return redact_config()


def GetImageFromFile(path):
  """Builds a GooglePrivacyDlpV2ByteContentItem message from a path.

  Will attempt to set message.type from file extension (if present).

  Args:
    path: the path arg given to the command.

  Raises:
    ImageFileError: if the image path does not exist and does not have a valid
    extension.

  Returns:
    GooglePrivacyDlpV2ByteContentItem: an message containing image data for
    the API on the image to analyze.
  """
  extension = os.path.splitext(path)[-1].lower()
  extension = extension or 'n_a'
  image_item = _GetMessageClass('GooglePrivacyDlpV2ByteContentItem')
  if os.path.isfile(path) and ValidateExtension(extension):
    with io.open(path, 'rb') as content_file:
      enum_val = arg_utils.ChoiceToEnum(VALID_IMAGE_EXTENSIONS[extension],
                                        image_item.TypeValueValuesEnum)
      image = image_item(data=content_file.read(), type=enum_val)
  else:
    raise ImageFileError(
        'The image path [{}] does not exist or has an invalid extension. '
        'Must be one of [jpg, jpeg, png, bmp or svg]. '
        'Please double-check your input and try again.'.format(path))
  return image


def GetRedactColorFromString(color_string):
  color_msg = _GetMessageClass('GooglePrivacyDlpV2Color')
  red, green, blue = ValidateAndParseColors(color_string)
  return color_msg(red=red, blue=blue, green=green)
