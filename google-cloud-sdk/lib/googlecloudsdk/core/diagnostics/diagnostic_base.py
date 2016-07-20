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

"""Base classes for diagnostics."""

from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io


class Diagnostic(object):
  """Base class for diagnostics."""

  _MAX_RETRIES = 5

  def __init__(self, intro, title, checklist):
    self._intro = intro
    self._title = title
    self._checklist = checklist

  def RunChecks(self):
    """Runs one or more checks, tries fixes, and outputs results.

    Returns:
      bool: Whether the diagnostic ultimately passed.
    """
    self._Print(self._intro)

    num_checks_ran, num_checks_passed = 0, 0
    for check in self._checklist:
      num_checks_ran += 1
      result, fixer = self._RunCheck(check)
      # If the initial check failed, and a fixer is available try to fix issue
      # and recheck.
      num_retries = 0
      while not result.passed and fixer and num_retries < self._MAX_RETRIES:
        num_retries += 1
        result, fixer = self._RetryRunCheck(check, result, fixer)

      if not result.passed and fixer and num_retries == self._MAX_RETRIES:
        log.warn('Unable to fix {0} failure after {1} attempts.'.format(
            self._title, num_retries))
      if result.passed:
        num_checks_passed += 1

    passed = (num_checks_passed == num_checks_ran)
    summary_message = '{0} ({1}/{2} check{3}) {4}.\n'.format(
        self._title,
        num_checks_passed,
        num_checks_ran,
        '' if num_checks_ran == 1 else 's',
        'passed' if passed else 'failed')
    self._Print(summary_message, as_error=not passed)
    return passed

  def _RunCheck(self, check, first_run=True):
    with console_io.ProgressTracker('{0} {1}'.format(
        'Checking' if first_run else 'Rechecking', check.issue)):
      result, fixer = check.Check(first_run=first_run)
    self._PrintResult(result)
    return result, fixer

  def _RetryRunCheck(self, check, result, fixer):
    should_check_again = fixer()
    if should_check_again:
      return self._RunCheck(check, first_run=False)
    return result, None

  def _Print(self, message, as_error=False):
    logger = log.status.Print if not as_error else log.error
    logger(message)

  def _PrintResult(self, result):
    self._Print(result.message, not result.passed)

