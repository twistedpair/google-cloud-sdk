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

"""Wrapper to manipulate GCP git repository."""

import errno
import os
import re
import subprocess
import textwrap

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import platforms
import uritemplate


# This regular expression is used to extract the URL of the 'origin' remote by
# scraping 'git remote show origin'.
_ORIGIN_URL_RE = re.compile(r'remote origin\n.*Fetch URL: (?P<url>.+)\n', re.M)
# This is the minimum version of git required to use credential helpers.
_HELPER_MIN = (2, 0, 1)

_TRAILING_SPACES = re.compile(r'(^|^.*[^\\ ]|^.*\\ ) *$')


class Error(exceptions.Error):
  """Exceptions for this module."""


class UnknownRepositoryAliasException(Error):
  """Exception to be thrown when a repository alias provided cannot be found."""


class CannotInitRepositoryException(Error):
  """Exception to be thrown when a repository cannot be created."""


class CannotFetchRepositoryException(Error):
  """Exception to be thrown when a repository cannot be fetched."""


class GitVersionException(Error):
  """Exceptions for when git version is too old."""

  def __init__(self, fmtstr, cur_version, min_version):
    self.cur_version = cur_version
    super(GitVersionException, self).__init__(
        fmtstr.format(cur_version=cur_version, min_version=min_version))


class InvalidGitException(Error):
  """Exceptions for when git version is empty or invalid."""

  def __init__(self, message):
    super(InvalidGitException, self).__init__(message)


class GcloudIsNotInPath(Error):
  """Exception for when the gcloud cannot be found."""


def CheckGitVersion(version_lower_bound=None):
  """Returns true when version of git is >= min_version.

  Args:
    version_lower_bound: (int,int,int), The lowest allowed version, or None to
      just check for the presence of git.

  Returns:
    True if version >= min_version.

  Raises:
    GitVersionException: if `git` was found, but the version is incorrect.
    InvalidGitException: if `git` was found, but the output of `git version` is
      not as expected.
    NoGitException: if `git` was not found.
  """
  try:
    output = subprocess.check_output(['git', 'version'])
    if not output:
      raise InvalidGitException('The git version string is empty.')
    if not output.startswith('git version '):
      raise InvalidGitException(('The git version string must start with '
                                 'git version .'))
    match = re.search(r'(\d+)\.(\d+)\.(\d+)', output)
    if not match:
      raise InvalidGitException('The git version string must contain a '
                                'version number.')

    cur_version = match.group(1, 2, 3)
    current_version = tuple([int(item) for item in cur_version])
    if version_lower_bound and current_version < version_lower_bound:
      min_version = '.'.join(str(i) for i in version_lower_bound)
      raise GitVersionException(
          ('Your git version {cur_version} is older than the minimum version '
           '{min_version}. Please install a newer version of git.'),
          output, min_version)
  except OSError as e:
    if e.errno == errno.ENOENT:
      raise NoGitException()
    raise
  return True


class NoGitException(Error):
  """Exceptions for when git is not available."""

  def __init__(self):
    super(NoGitException, self).__init__(
        textwrap.dedent("""\
        Cannot find git. Please install git and try again.

        You can find git installers at [http://git-scm.com/downloads], or use
        your favorite package manager to install it on your computer. Make sure
        it can be found on your system PATH.
        """))


def _GetRepositoryURI(project, alias):
  """Get the URI for a repository, given its project and alias.

  Args:
    project: str, The project name.
    alias: str, The repository alias.

  Returns:
    str, The repository URI.
  """
  return uritemplate.expand(
      'https://source.developers.google.com/p/{project}/r/{alias}',
      {'project': project, 'alias': alias})


def _GetGcloudScript(full_path=False):
  """Get name of the gcloud script.

  Args:
    full_path: boolean, True if the gcloud full path should be used if free
      of spaces.

  Returns:
    str, command to use to execute gcloud

  Raises:
    GcloudIsNotInPath: if gcloud is not found in the path
  """

  if (platforms.OperatingSystem.Current() ==
      platforms.OperatingSystem.WINDOWS):
    gcloud_ext = '.cmd'
  else:
    gcloud_ext = ''

  gcloud_name = 'gcloud'
  gcloud = files.FindExecutableOnPath(gcloud_name, pathext=[gcloud_ext])

  if not gcloud:
    raise GcloudIsNotInPath(
        'Could not verify that gcloud is in the PATH. '
        'Please make sure the Cloud SDK bin folder is in PATH.')
  if full_path:
    if not re.match(r'[-a-zA-Z0-9_/]+$', gcloud):
      log.warn(
          textwrap.dedent("""\
          You specified the option to use the full gcloud path in the git
          credential.helper, but the path contains non alphanumberic characters
          so the credential helper may not work correctly."""))
    return gcloud
  else:
    return gcloud_name + gcloud_ext


def _NormalizeToUnixPath(path, strip=True):
  """Returns a path with '/' for the directory separator.

  The regular expressions used in .gitignore processing use '/' as the directory
  separator, but many APIs will convert '/' to '\' on Windows. This method can
  be used to ensure consistent name formation on any platform. (To date, '/'
  and '\' are the only directory separators in commond use). We can't just use
  normpath, because '\' has special meaning in regular expressions.

  Note that there is a potential corner case here when a Unix file name contains
  a backslash. The worst case effect here is that such a file might not be
  ignored when it should.

  Args:
    path: The path to normalize.
    strip: If True, also strip any trailing '/' characters.
  Returns:
    The normalized path.
  """
  path = path.replace(os.sep, '/')
  if strip and path != '/':
    return path.rstrip('/')
  else:
    return path


def _HasSystemCredHelper():
  """Determine whether there is a system-wide credential helper set.

  Returns:
    True if a non-cloud system credential helper is set.

  Raises:
    NoGitException: if `git` was not found.
  """
  try:
    stdout = subprocess.check_output(
        ['git', 'config', '--system', '--list'], stderr=subprocess.STDOUT)
    return (re.search(r'^credential.helper=.', stdout, re.MULTILINE) and
            not re.search(r'^credential.helper=!gcloud', stdout, re.MULTILINE))
  except OSError as e:
    if e.errno == errno.ENOENT:
      raise NoGitException()
    return False
  except subprocess.CalledProcessError:
    return False


class GitIgnoreHandler(object):
  """Processes .gitignore rules.

  This class handles .gitignore files over a directory hierarchy, applying
  rules recursively. It is intended to be a full implementation of the rules
  described at https://git-scm.com/docs/gitignore, though it is much less
  restrictive about re-inclusion of files (at the cost of requiring a scan
  of fully-excluded directories).

  It does not handle the core.excludesFile setting in the user's .gitconfig.
  """

  def __init__(self):
    self._ignore_rules = {}
    self. _ProcessIgnoreFile(os.path.expanduser('~/.config/git/ignore'), '/')

  def AddIgnoreRules(self, path, rules):
    """Adds rules for ignoring files under the given path.

    Args:
      path: The path where the rules apply.
      rules: A list of (RegEx, Bool) pairs indicating that files matching the
        RegEx should (or should not) be ignored. (A True value indicates files
        matching the pattern should be ignored). The patterns will be compared
        to full path names, and should specify '/' as the directory specifier,
        regardless of platform.
    """
    self._ignore_rules[_NormalizeToUnixPath(path)] = rules

  def ProcessGitIgnore(self, path):
    """Processes the .gitignore file (if any) in the given path.

      Updates the internal path->rules mapping based on the .gitignore file.

    Args:
      path: The path to a directory which may contain a .gitignore file.
    """
    self._ProcessIgnoreFile(os.path.join(path, '.git/info/exclude'), path)
    self._ProcessIgnoreFile(os.path.join(path, '.gitignore'), path)

  def ShouldIgnoreFile(self, path):
    """Test if a file should be ignored based on the given patterns.

    Compares the path to each pattern in ignore_patterns, in order. If it
    matches a pattern whose Bool is True, the file should be excluded unless it
    also matches a later pattern which has a bool of False. Similarly, if a name
    matches a pattern with a Bool that is False, it should be included
    unless it also matches a later pattern which has a bool of True.

    Args:
      path: The file name to test.
    Returns:
      True if the file should be ignored, False otherwise.
    """
    # Normalize separators, but leave any trailing '/' to allow explicit
    # directory matches.
    path = _NormalizeToUnixPath(path, strip=False)
    rules = self._GetRules(path)
    ret = False
    for pattern, should_ignore in rules:
      if pattern.match(path):
        log.debug('{0}: matches {1} => ignore=={2}'.format(
            path, pattern.pattern, should_ignore))
        ret = should_ignore
    return ret

  def GetFiles(self, root):
    """Yields all files in the given directory tree which should not be ignored.

    Args:
      root: The directory to walk
    Yields:
      [path] The full path to every file under the given root directory which
        should not be ignored.
    """
    for base, _, file_list in os.walk(root):
      self.ProcessGitIgnore(base)
      for f in file_list:
        # Exclude file_list based on the .gitignore rules.
        filename = os.path.join(base, f)
        if not self.ShouldIgnoreFile(filename):
          yield filename

  def _ProcessIgnoreFile(self, git_ignore_file, target_dir):
    """Processes a .gitignore file.

      Updates the internal path->rules mapping based on the .gitignore file.

    Args:
      git_ignore_file: The path to a directory a .gitignore file which may not
        exist.
      target_dir: The directory where the rules in the gitignore file apply.
    """
    if not os.path.exists(git_ignore_file):
      return
    path = _NormalizeToUnixPath(target_dir)
    log.debug('Processing {0}'.format(git_ignore_file))
    ret = []
    with open(git_ignore_file, 'r') as f:
      for line in f:
        pattern, should_ignore = self._ParseLine(line, path)
        if pattern:
          ret.append((pattern, should_ignore))
    if path in self._ignore_rules:
      self._ignore_rules[path].extend(ret)
    else:
      self._ignore_rules[path] = ret

  def _GetRules(self, path):
    """Returns the set of rules that apply to a given path.

    Searches all parent paths for rules, returning the concatenation of all the
    rules.

    Args:
      path: The path to check.

    Returns:
      A list of (RegEx, Bool) pairs indicating file name patterns to include/
      exclude.
    """
    # Build an array of the parent directories of the given path, from root
    # down. On Windows, drive letters will be handled as if they were
    # directories under root.
    dirs = ['/']
    pos = str.find(path, '/')
    if pos == 0:
      pos = str.find(path, '/', 1)
    while pos != -1:
      dirs.append(path[0:pos])
      pos = str.find(path, '/', pos+1)
    dirs.append(path)
    rules = []
    for d in dirs:
      if d in self._ignore_rules:
        log.debug('{0}: Applying rules for {1}'.format(path, d))
        rules.extend(self._ignore_rules[d])
    return rules

  def _ParseLine(self, line, basedir):
    """Process a line from a .gitignore file.

    Args:
      line: A line from a .gitignore file.
      basedir: The directory containing the .gitignore file.
    Returns:
      (Regex, Bool)
      A regular expression corresponding to the line and a flag indicating
      whether matching files should be excluded (True) or included (False).
      Regex will be None if the line contains no filename pattern.
    """
    # Skip comments (which must be at the start of the line)
    if line[0] == '#':
      return (None, True)
    line = line.strip('\n')
    # Strip trailing spaces not preceded by '\'
    line = _TRAILING_SPACES.sub(r'\g<1>', line)
    # Skip blank lines
    if not line:
      return (None, True)
    # Special handling for leading '!' or **
    pos = 0
    should_ignore = True
    if line[0] == '!':
      pos += 1
      should_ignore = False

    # Patterns containing "/" apply only under the base directory, while
    # other patterns apply in any directory.
    if '/' in line:
      pattern = re.escape(basedir) + '/'
    else:
      pattern = '.*/'

    # Convert the rest of the line to a python regex. We can't just use
    # fnmatch.translate, because it doesn't handle globs, **, or escape
    # characters the way we want.
    while pos < len(line):
      part, advance = self._ParseElement(line, pos)
      pattern += part
      pos += advance
    pattern += '$'
    log.debug(
        'Ignore "{0}" => r\'{1}\': {2}'.format(line, pattern, should_ignore))
    return re.compile(pattern), should_ignore

  def _ParseElement(self, line, pos):
    """Parses a single element of an ignore line.

    An element may be a character, a wildcard, or a brace expression.

    Args:
      line: The line being parsed.
      pos: The position to start parsing.
    Returns:
      (RegEx, int)
      The regular expression equivalent to the element and the number of
      characters consumed from the line.
    """
    current = line[pos]
    advance = 1
    if current == '*':
      if line[pos:pos+2] == '**':
        if line[pos:pos+3] == '**/':
          # Match any number of directories, followed by '/'
          advance = 3
          current = r'(.*/)?'
        else:
          # Match the entire directory tree, recursively.
          advance = 2
          current = r'.*'
      else:
        # Match a single file or directory name
        current = r'[^/]*'
    elif current == '?':
      # Match a single character in a file or directory name.
      current = '[^/]'
    elif current == '\\':
      # Copy escaped characters into the output.
      current = line[pos:pos+2]
      advance = 2
    # Note that although .gitignore claims to use shell-style globs, it does
    # not use shell-style quoting, and does not handle braces. A double quote
    # matches a literal double quote, brace matches literal brace, quotes do
    # not suppress * globbing, etc.
    return current, advance


class Git(object):
  """Represents project git repo."""

  def __init__(self, project_id, repo_name, uri=None):
    """Clone a repository associated with a Google Cloud Project.

    Looks up the URL of the indicated repository, and clones it to alias.

    Args:
      project_id: str, The name of the project that has a repository associated
          with it.
      repo_name: str, The name of the repository to clone.
      uri: str, The URI of the repository to clone, or None if it will be
          inferred from the name.

    Raises:
      UnknownRepositoryAliasException: If the repo name is not known to be
          associated with the project.
    """
    self._project_id = project_id
    self._repo_name = repo_name
    self._uri = uri or _GetRepositoryURI(project_id, repo_name)
    if not self._uri:
      raise UnknownRepositoryAliasException()

  def GetName(self):
    return self._repo_name

  def Clone(self, destination_path, dry_run=False, full_path=False):
    """Clone a git repository into a gcloud workspace.

    If the resulting clone does not have a .gcloud directory, create one. Also,
    sets the credential.helper to use the gcloud credential helper.

    Args:
      destination_path: str, The relative path for the repository clone.
      dry_run: bool, If true do not run but print commands instead.
      full_path: bool, If true use the full path to gcloud.

    Returns:
      str, The absolute path of cloned repository.

    Raises:
      CannotInitRepositoryException: If there is already a file or directory in
          the way of creating this repository.
      CannotFetchRepositoryException: If there is a problem fetching the
          repository from the remote host, or if the repository is otherwise
          misconfigured.
    """
    abs_repository_path = os.path.abspath(destination_path)
    if os.path.exists(abs_repository_path):
      CheckGitVersion()  # Do this here, before we start running git commands
      if os.listdir(abs_repository_path):
        # Raise exception if dir is not empty and not a git repository
        raise CannotInitRepositoryException(
            'Directory path specified exists and is not empty')
    # Make a brand new repository if directory does not exist or
    # clone if directory exists and is empty
    try:
      credentialed_hosts = ['source.developers.google.com']
      extra = properties.VALUES.core.credentialed_hosted_repo_domains.Get()
      if extra:
        credentialed_hosts.extend(extra.split(','))
      if any(
          self._uri.startswith('https://' + host)
          for host in credentialed_hosts):
        # If this is a Google-hosted repo, clone with the cred helper.
        try:
          CheckGitVersion(_HELPER_MIN)
        except GitVersionException as e:
          helper_min = '.'.join(str(i) for i in _HELPER_MIN)
          log.warn(textwrap.dedent("""\
          You are cloning a Google-hosted repository with a
          {current} which is older than {min_version}. If you upgrade
          to {min_version} or later, gcloud can handle authentication to
          this repository. Otherwise, to authenticate, use your Google
          account and the password found by running the following command.
           $ gcloud auth print-access-token""".format(
               current=e.cur_version, min_version=helper_min)))
          cmd = ['git', 'clone', self._uri, abs_repository_path]
        else:
          if _HasSystemCredHelper():
            log.warn(
                textwrap.dedent("""\
            If your system's credential.helper requests a password, choose
            cancel."""))
          cmd = ['git', 'clone', self._uri, abs_repository_path,
                 '--config',
                 # Use git alias "!shell command" syntax so we can configure
                 # the helper with options. Also git-credential is not
                 # prefixed when it starts with "!".
                 # See https://git-scm.com/docs/git-config
                 'credential.helper=!{0} auth git-helper --account={1} '
                 '--ignore-unknown $@'
                 .format(_GetGcloudScript(full_path),
                         properties.VALUES.core.account.Get(required=True))]
        self._RunCommand(cmd, dry_run)
      else:
        # Otherwise, just do a simple clone. We do this clone, without the
        # credential helper, because a user may have already set a default
        # credential helper that would know the repo's auth info.
        subprocess.check_call(
            ['git', 'clone', self._uri, abs_repository_path])
    except subprocess.CalledProcessError as e:
      raise CannotFetchRepositoryException(e)
    return abs_repository_path

  def _RunCommand(self, cmd, dry_run):
    log.debug('Executing %s', cmd)
    if dry_run:
      log.out.Print(' '.join(cmd))
    else:
      subprocess.check_call(cmd)
