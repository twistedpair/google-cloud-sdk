# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Utilities for the `gcloud feedback` command."""

import os
import re
import urllib

from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_attr_os


ISSUE_TRACKER_URL = 'https://code.google.com/p/google-cloud-sdk/issues'
NEW_ISSUE_URL = 'https://code.google.com/p/google-cloud-sdk/issues/entry'

# The new issue URL has a maximum length, so we need to limit the length of
# pre-filled form fields
MAX_URL_LENGTH = 2106


COMMENT_TEMPLATE = """\
{formatted_command}What steps will reproduce the problem?


What is the expected output? What do you see instead?


Please provide any additional information below.


{formatted_traceback}Installation information:

{gcloud_info}\
"""


TRUNCATED_INFO_MESSAGE = '[output truncated]'


def _FormatNewIssueUrl(comment, status='New', summary=''):
  params = {
      'status': status,
      'summary': summary,
      'comment': comment,
  }
  return NEW_ISSUE_URL + '?' + urllib.urlencode(params)


def OpenInBrowser(url):
  # pylint: disable=g-import-not-at-top
  # Import in here for performance reasons
  import webbrowser
  # pylint: enable=g-import-not-at-top
  webbrowser.open_new_tab(url)


def _UrlEncodeLen(string):
  """Return the length of string when URL-encoded."""
  # urlencode turns a dict into a string of 'key=value' pairs. We use a blank
  # key and don't want to count the '='.
  encoded = urllib.urlencode({'': string})[1:]
  return len(encoded)


def _FormatStackTrace(first_entry, rest):
  return '\n'.join([first_entry, '  [...]'] + rest)


_STACKTRACE_LINES_PER_ENTRY = 2


def _ShortenStacktrace(stacktrace, url_encoded_length):
  """Cut out the middle entries of the stack trace to a given length.

  For instance:

  >>> stacktrace = '''
  ...   File "foo.py", line 10, in run
  ...     result = bar.run()
  ...   File "bar.py", line 11, in run
  ...     result = baz.run()
  ...   File "baz.py", line 12, in run
  ...     result = qux.run()
  ...   File "qux.py", line 13, in run
  ...     raise Exception(':(')
  ... '''
  >>> _ShortenStacktrace(stacktrace, 300) == '''\
  ...   File "foo.py", line 10, in run
  ...     result = bar.run()
  ...   [...]
  ...   File "baz.py", line 12, in run
  ...      result = qux.run()
  ...   File "qux.py", line 13, in run
  ...      raise Exception(':(')
  ... '''
  True


  Args:
    stacktrace: str, the formatted stacktrace (as Python prints by default)
    url_encoded_length: int, the length to shorten the stacktrace to (when
        URL-encoded).

  Returns:
    str, the shortened stacktrace.
  """
  # A stacktrace consists of several entries, each of which is a pair of lines.
  # The first describes the file containing the line of source in the stack
  # trace; the second shows the line of source in the stack trace as it appears
  # in the source.
  stacktrace = stacktrace.strip('\n')
  lines = stacktrace.split('\n')
  entries = ['\n'.join(lines[i:i+_STACKTRACE_LINES_PER_ENTRY]) for i in
             range(0, len(lines), _STACKTRACE_LINES_PER_ENTRY)]

  if _UrlEncodeLen(stacktrace) <= url_encoded_length:
    return stacktrace

  rest = entries[1:]
  while (_UrlEncodeLen(_FormatStackTrace(entries[0], rest)) >
         url_encoded_length) and len(rest) > 1:
    rest = rest[1:]
  # If we've eliminated the entire middle of the stacktrace and it's still
  # longer than the max allowed length, nothing we can do beyond that. We'll
  # return the short-as-possible stacktrace and let the caller deal with it.
  return _FormatStackTrace(entries[0], rest)


# Pattern for splitting the formatted issue comment into the parts that fall
# before and after the stacktrace, as well as the stacktrace itself.
EXTRACT_STACKTRACE_PATTERN = (
    r'(?P<pre_stacktrace>(?:.|\n)*Traceback \(most recent call last\):\n)'
    r'(?P<stacktrace>(?:.|\n)*?)'
    r'(?P<exception>\n\w(?:.|\n)*)')


def _ShortenIssueBody(comment, url_encoded_length):
  """Shortens the comment to be at most the given length (URL-encoded).

  Does one of two things:

  (1) If the whole stacktrace and everything before it fits within the
      URL-encoded max length, truncates the remainder of the comment (which
      should include e.g. the output of `gcloud info`.
  (2) Otherwise, chop out the middle of the stacktrace until it fits. (See
      _ShortenStacktrace docstring for an example). If the stacktrace cannot be
      shortened in this manner, revert to (1).

  Args:
    comment: str, the formatted comment for inclusion before shortening.
    url_encoded_length: the max length of the comment after shortening (when
        comment is URL-encoded).

  Returns:
    (str, str): the shortened comment and a message containing the parts of the
    comment that were omitted by the shortening process.
  """
  # * critical_info contains all of the critical information: the name of the
  # command, the stacktrace, and places for the user to provide additional
  # information.
  # * optional_info is the less essential `gcloud info output`.
  critical_info, middle, optional_info = comment.partition(
      'Installation information:\n')
  optional_info = middle + optional_info
  # We need to count the message about truncating the output towards our total
  # character count.
  max_str_len = (url_encoded_length -
                 _UrlEncodeLen(TRUNCATED_INFO_MESSAGE + '\n'))
  if _UrlEncodeLen(critical_info) <= max_str_len:
    # Case (1) from the docstring
    return _UrlTruncateLines(comment, max_str_len)
  else:
    # Case (2) from the docstring
    match = re.search(EXTRACT_STACKTRACE_PATTERN, critical_info)
    pre_stacktrace = match.groupdict()['pre_stacktrace']
    stacktrace = match.groupdict()['stacktrace']
    exception = match.groupdict()['exception']

    max_stacktrace_len = (
        url_encoded_length -
        _UrlEncodeLen(pre_stacktrace + exception + TRUNCATED_INFO_MESSAGE))
    shortened_stacktrace = _ShortenStacktrace(stacktrace, max_stacktrace_len)
    included = (pre_stacktrace + shortened_stacktrace + exception +
                TRUNCATED_INFO_MESSAGE)
    excluded = ('Full stack trace:\n' + stacktrace + exception + optional_info)
    if _UrlEncodeLen(included) > max_str_len:
      included = _UrlTruncateLines(included + optional_info, max_str_len)[0]
    return included, excluded


def _UrlTruncateLines(string, url_encoded_length):
  """Truncates the given string to the given URL-encoded length.

  Always cuts at a newline.

  Args:
    string: str, the string to truncate
    url_encoded_length: str, the length to which to truncate

  Returns:
    tuple of (str, str), where the first str is the truncated version of the
    original string and the second str is the remainder.
  """
  lines = string.split('\n')
  included_lines = []
  excluded_lines = []
  # Adjust the max length for the truncation message in case it is needed
  max_str_len = (url_encoded_length -
                 _UrlEncodeLen(TRUNCATED_INFO_MESSAGE + '\n'))
  while (lines and
         _UrlEncodeLen('\n'.join(included_lines + lines[:1])) <= max_str_len):
    included_lines.append(lines.pop(0))
  excluded_lines = lines
  if excluded_lines:
    included_lines.append(TRUNCATED_INFO_MESSAGE)
  return '\n'.join(included_lines), '\n'.join(excluded_lines)


def GetDivider(text=''):
  """Return a console-width divider (ex: '======================' (etc.)).

  Supports messages (ex: '=== Messsage Here ===').

  Args:
    text: str, a message to display centered in the divider.

  Returns:
    str, the formatted divider
  """
  if text:
    text = ' ' + text + ' '
  width, _ = console_attr_os.GetTermSize()
  return text.center(width, '=')


# Regular expression for extracting files from a traceback
# We only care about the files that have 'google' somewhere in them, because
# they're ours
_TRACEBACK_FILE_REGEXP = r'File "(.*google.*)"'


def _CommonPrefix(paths):
  """Given a list of paths, return the longest shared directory prefix.

  We want to:
  (1) Only split at path boundaries (i.e.
      _CommonPrefix(['/foo/bar', '/foo/baz']) => '/foo' , not '/foo/b')
  (2) Ignore the path basenames, even when files are identical (i.e.
      _CommonPrefix(['/foo/bar'] * 3') => '/foo'

  For these reasons, we can't just us os.path.commonprefix.

  Args:
    paths: list of str, list of path names

  Returns:
    str, common prefix
  """
  prefix = os.path.commonprefix(map(os.path.dirname, paths))
  if not prefix:
    return prefix
  if all([path.startswith(prefix + os.path.sep) for path in paths]):
    return prefix + os.path.sep
  else:
    return os.path.dirname(prefix) + os.path.sep


def _FormatIssueBody(info, log_data=None):
  """Construct a useful issue body with which to pre-populate the issue tracker.

  Args:
    info: InfoHolder, holds information about the Cloud SDK install
    log_data: LogData, parsed log data for a gcloud run

  Returns:
    str, issue comment body
  """
  gcloud_info = str(info)

  formatted_command = ''
  if log_data and log_data.command:
    formatted_command = 'Issue running command [{0}].\n\n'.format(
        log_data.command)

  formatted_traceback = ''
  if log_data and log_data.traceback:
    # Because we have a limited number of characters to work with (see
    # MAX_URL_LENGTH), we reduce the size of the traceback by stripping out the
    # installation root. We'll still know what files are being talked about.
    traceback_files = re.findall(_TRACEBACK_FILE_REGEXP, log_data.traceback)
    common_prefix = _CommonPrefix(traceback_files)
    formatted_traceback = log_data.traceback.replace(common_prefix, '') + '\n\n'

  return COMMENT_TEMPLATE.format(formatted_command=formatted_command,
                                 gcloud_info=gcloud_info.strip(),
                                 formatted_traceback=formatted_traceback)


def OpenNewIssueInBrowser(info, log_data):
  """Opens a new tab in the web browser to the new issue page for Cloud SDK.

  The page will be pre-populated with relevant information.

  Args:
    info: InfoHolder, the data from of `gcloud info`
    log_data: LogData, parsed representation of a recent log
  """
  comment = _FormatIssueBody(info, log_data)
  url = _FormatNewIssueUrl(comment)
  if len(url) > MAX_URL_LENGTH:
    max_info_len = MAX_URL_LENGTH - len(_FormatNewIssueUrl(''))
    truncated, remaining = _ShortenIssueBody(comment, max_info_len)
    log.warn('Truncating included information. '
             'Please consider including the remainder:')
    divider_text = 'TRUNCATED INFORMATION (PLEASE CONSIDER INCLUDING)'
    log.status.Print(GetDivider(divider_text))
    log.status.Print(remaining.strip())
    log.status.Print(GetDivider('END ' + divider_text))
    log.warn('The output of gcloud info is too long to pre-populate the '
             'new issue form.')
    log.warn('Please consider including the remainder (above).')
    url = _FormatNewIssueUrl(truncated)
  OpenInBrowser(url)
  log.status.Print('Opening your browser to a new Google Cloud SDK issue.')
  log.status.Print("If your browser doesn't open, please file an issue: " +
                   ISSUE_TRACKER_URL)
