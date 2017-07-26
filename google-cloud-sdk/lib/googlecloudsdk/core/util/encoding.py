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

"""A module for dealing with unknown string and environment encodings."""

import sys


def Decode(string, encoding=None):
  """Returns string with non-ascii characters decoded decoded to UNICODE.

  UTF-8, the suggested encoding, and the usual suspects will be attempted in
  order. If the string is pure ASCII or UNICODE then it is returned unchanged.

  Args:
    string: A string or object that has str() and unicode() methods that may
      contain an encoding incompatible with the standard output encoding.
    encoding: The suggested encoding if known.

  Returns:
    The string with non-ASCII characters decoded to UNICODE.
  """
  if isinstance(string, unicode):
    # Our work is done here.
    return string

  try:
    # Just return the string if its pure ASCII.
    string.decode('ascii')
    return string
  except AttributeError:
    # The string does not have a decode method.
    try:
      return unicode(string)
    except (TypeError, UnicodeError):
      # The string cannot be converted to unicode -- default to str() which will
      # catch objects with special __str__ methods.
      string = str(string)
  except UnicodeError:
    # The string is not ASCII encoded.
    pass

  # Try the suggested encoding if specified.
  if encoding:
    try:
      return string.decode(encoding)
    except UnicodeError:
      # Bad suggestion.
      pass

  # Try UTF-8 because the other encodings could be extended ASCII. It would
  # be exceptional if a valid extended ascii encoding with extended chars
  # were also a valid UITF-8 encoding.
  try:
    return string.decode('utf8')
  except UnicodeError:
    # Not a UTF-8 encoding.
    pass

  # Try the filesystem encoding.
  try:
    return string.decode(sys.getfilesystemencoding())
  except UnicodeError:
    # string is not encoded for filesystem paths.
    pass

  # Try the system default encoding.
  try:
    return string.decode(sys.getdefaultencoding())
  except UnicodeError:
    # string is not encoded using the default encoding.
    pass

  # We don't know the string encoding.
  # This works around a Python str.encode() "feature" that throws
  # an ASCII *decode* exception on str strings that contain 8th bit set
  # bytes. For example, this sequence throws an exception:
  #   string = '\xdc'  # iso-8859-1 'Ü'
  #   string = string.encode('ascii', 'backslashreplace')
  # even though 'backslashreplace' is documented to handle encoding
  # errors. We work around the problem by first decoding the str string
  # from an 8-bit encoding to unicode, selecting any 8-bit encoding that
  # uses all 256 bytes (such as ISO-8559-1):
  #   string = string.decode('iso-8859-1')
  # Using this produces a sequence that works:
  #   string = '\xdc'
  #   string = string.decode('iso-8859-1')
  #   string = string.encode('ascii', 'backslashreplace')
  return string.decode('iso-8859-1')


def GetEncodedValue(env, name, default=None):
  """Returns the decoded value of the env var name.

  Args:
    env: {str: str}, The env dict.
    name: str, The env var name.
    default: The value to return if name is not in env.

  Returns:
    The decoded value of the env var name.
  """
  value = env.get(name)
  return default if value is None else Decode(value)


def SetEncodedValue(env, name, value):
  """Sets the value of name in env to an encoded value.

  Args:
    env: {str: str}, The env dict.
    name: str, The env var name.
    value: str or unicode, The value for name. If None then name is removed from
      env.
  """
  # Python 2 *and* 3 unicode support falls apart at filesystem/argv/environment
  # boundaries. The encoding used for filesystem paths and environment variable
  # names/values is under user control on most systems. With one of those values
  # in hand there is no way to tell exactly how the value was encoded. We get
  # some reasonable hints from sys.getfilesystemencoding() or
  # sys.getdefaultencoding() and use them to encode values that the receiving
  # process will have a chance at decoding. Leaving the values as unicode
  # strings will cause os module Unicode exceptions. What good is a language
  # unicode model when the module support could care less?
  if value is None:
    env.pop(name, None)
    return
  if isinstance(value, unicode):
    encoding = sys.getfilesystemencoding() or sys.getdefaultencoding()
    value = value.encode(encoding)
  env[name] = value

