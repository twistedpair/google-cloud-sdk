# Copyright 2015 Google Inc. All Rights Reserved.

"""Command to assist user in submitting feedback about gcloud.

Does one of two things:

1. If invoked in the context of a recent gcloud crash (i.e. an exception that
was not caught anywhere in the Cloud SDK), will direct the user to the Cloud SDK
bug tracker, with a partly pre-filled form.

2. Otherwise, directs the user to either the Cloud SDK bug tracker,
StackOverflow, or the Cloud SDK groups page.
"""

import os
import re
import textwrap
import urllib

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_attr_os
from googlecloudsdk.core.console import console_io
from googlecloudsdk.shared.sdktool import info_holder


STACKOVERFLOW_URL = 'http://stackoverflow.com/questions/tagged/gcloud'
GROUPS_PAGE_URL = ('https://groups.google.com/forum/?fromgroups#!forum/'
                   'google-cloud-sdk')
ISSUE_TRACKER_URL = 'https://code.google.com/p/google-cloud-sdk/issues'
NEW_ISSUE_URL = 'https://code.google.com/p/google-cloud-sdk/issues/entry'

# The new issue URL has a maximum length, so we need to limit the length of
# pre-filled form fields
MAX_URL_LENGTH = 2106


FEEDBACK_MESSAGE = """\

We appreciate your feedback.

If you have a question, post it on Stack Overflow using the "gcloud" tag at
[{0}].

For general feedback, use our groups page
[{1}],
send a mail to [google-cloud-sdk@googlegroups.com] or visit the [#gcloud] IRC
channel on freenode.
""".format(STACKOVERFLOW_URL, GROUPS_PAGE_URL)


FEEDBACK_PROMPT = """\
Would you like to file a bug using our issue tracker site at [{0}] \
(will open a new browser tab)?\
""".format(ISSUE_TRACKER_URL)


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


def _GetDivider(text=''):
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


def _PrintQuiet(info_str, log_data):
  """Print message referring to various feedback resources for quiet execution.

  Args:
    info_str: str, the output of `gcloud info`
    log_data: info_holder.LogData, log data for the provided log file
  """
  if log_data:
    if not log_data.traceback:
      log.Print(('Please consider including the log file [{0}] in any '
                 'feedback you submit.').format(log_data.filename))

  log.Print(textwrap.dedent("""\

      If you have a question, post it on Stack Overflow using the "gcloud" tag
      at [{0}].

      For general feedback, use our groups page
      [{1}],
      send a mail to [google-cloud-sdk@googlegroups.com], or visit the [#gcloud]
      IRC channel on freenode.

      If you have found a bug, file it using our issue tracker site at
      [{2}].

      Please include the following information when filing a bug report:\
      """).format(STACKOVERFLOW_URL, GROUPS_PAGE_URL, ISSUE_TRACKER_URL))
  divider = _GetDivider()
  log.Print(divider)
  if log_data and log_data.traceback:
    log.Print(log_data.traceback)
  log.Print(info_str.strip())
  log.Print(divider)


def _SuggestIncludeRecentLogs():
  recent_runs = info_holder.LogsInfo().GetRecentRuns()
  if recent_runs:
    idx = console_io.PromptChoice(
        recent_runs + ['None of these'], default=0,
        message=('Which recent gcloud invocation would you like to provide '
                 'feedback about?'))
    if idx < len(recent_runs):
      return recent_runs[idx]


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
  if all([path.startswith(prefix + '/') for path in paths]):
    return prefix + '/'
  else:
    return os.path.dirname(prefix) + '/'


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


def _OpenNewIssueInBrowser(info, log_data):
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
    truncated, remaining = _UrlTruncateLines(comment, max_info_len)
    log.warn('The output of gcloud info is too long to pre-populate the '
             'new issue form.')
    log.warn('Truncating included information. '
             'Please consider including the remainder:')
    log.status.Print(
        _GetDivider('TRUNCATED INFORMATION (PLEASE CONSIDER INCLUDING)'))
    log.status.Print(remaining.strip())
    log.status.Print(_GetDivider())
    url = _FormatNewIssueUrl(truncated)
  OpenInBrowser(url)
  log.status.Print('Opening your browser to a new Google Cloud SDK issue.')


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Feedback(base.Command):
  """Provide feedback to the Google Cloud SDK team.

  The Google Cloud SDK team offers support through a number of channels:

  * Google Cloud SDK Issue Tracker
  * Stack Overflow "#gcloud" tag
  * google-cloud-sdk Google group

  This command lists the available channels and facilitates getting help through
  one of them by opening a web browser to the relevant page, possibly with
  information relevant to the current install and configuration pre-populated in
  form fields on that page.
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--log-file',
        help='Path to the log file from a prior gcloud run.')

  def Run(self, args):
    info = info_holder.InfoHolder()
    log_data = None
    if args.log_file:
      try:
        log_data = info_holder.LogData.FromFile(args.log_file)
      except IOError as err:
        log.warn('Error reading the specified file [{0}]: '
                 '{1}\n'.format(args.log_file, err))
    if args.quiet:
      _PrintQuiet(str(info), log_data)
    else:
      log.status.Print(FEEDBACK_MESSAGE)
      if not log_data:
        log_data = _SuggestIncludeRecentLogs()
      if console_io.PromptContinue(prompt_string=FEEDBACK_PROMPT):
        _OpenNewIssueInBrowser(info, log_data)
