# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Library for ignoring files for upload.

This library very closely mimics the semantics of Git's gitignore file:
https://git-scm.com/docs/gitignore

See `gcloud topic gcloudignore` for details.

A typical use would be:

  file_chooser = gcloudignore.GetFileChooserForDir(upload_directory)
  for f in file_chooser.GetIncludedFiles('some/path'):
    print 'uploading {}'.format(f)
    # actually do the upload, too
"""
import collections
import fnmatch
import os
import re

import enum

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import files


IGNORE_FILE_NAME = '.gcloudignore'
GIT_FILES = ['.git', '.gitignore']
DEFAULT_IGNORE_FILE = """\
# This file specifies files that are *not* uploaded to Google Cloud Platform
# using gcloud. It follows the same syntax as .gitignore, with the addition of
# "#!include" directives (which insert the entries of the given .gitignore-style
# file at that point).
#
# For more information, run:
#   $ gcloud topic gcloudignore
#
.gcloudignore
# If you would like to upload your .git directory, .gitignore file or files
# from your .gitignore file, remove the corresponding line
# below:
.git
.gitignore
"""
_GCLOUDIGNORE_PATH_SEP = '/'
_ENDS_IN_ODD_NUMBER_SLASHES_RE = r'(?<!\\)\\(\\\\)*$'


class InternalParserError(Exception):
  """An internal error in gcloudignore parsing."""


class InvalidLineError(InternalParserError):
  """Error indicating that a line of the ignore file was invalid."""


class BadFileError(InternalParserError):
  """Error indicating that a provided file was invalid."""


class BadIncludedFileError(exceptions.Error):
  """Error indicating that a provided file was invalid."""


class Match(enum.Enum):
  """Indicates whether a ignore pattern matches or explicitly includes a path.

  INCLUDE: path matches, and is included
  IGNORE: path matches, and is ignored
  NO_MATCH: file is not matched
  """

  INCLUDE = 1
  IGNORE = 2
  NO_MATCH = 3


def _HandleSpaces(line):
  """Handles spaces in a line.

  In particular, deals with trailing spaces (which are stripped unless
  escaped) and escaped spaces throughout the line (which are unescaped).

  Args:
    line: str, the line

  Returns:
    str, the line with spaces handled
  """
  def _Rstrip(line):
    """Strips unescaped trailing spaces."""
    # First, make the string into "tokens": a backslash followed by any
    # character is one token; any other character is a token on its own.
    tokens = []
    i = 0
    while i < len(line):
      curr = line[i]
      if curr == '\\':
        if i + 1 >= len(line):
          tokens.append(curr)
          break  # Pass through trailing backslash
        tokens.append(curr + line[i+1])
        i += 2
      else:
        tokens.append(curr)
        i += 1

    # Then, strip the trailing space tokens.
    res = []
    only_seen_spaces = True
    for curr in reversed(tokens):
      if only_seen_spaces and curr == ' ':
        continue
      only_seen_spaces = False
      res.append(curr)

    return ''.join(reversed(res))

  def _UnescapeSpaces(line):
    """Unescapes all spaces in a line."""
    return line.replace('\\ ', ' ')

  return _UnescapeSpaces(_Rstrip(line))


def _Unescape(line):
  r"""Unescapes a line.

  The escape character is '\'. An escaped backslash turns into one backslash;
  any other escaped character is ignored.

  Args:
    line: str, the line to unescape

  Returns:
    str, the unescaped line

  """
  return re.sub(r'\\([^\\])', r'\1', line).replace('\\\\', '\\')


def _GetPathPrefixes(path):
  """Returns all prefixes for the given path, inclusive.

  That is, for 'foo/bar/baz', returns ['', 'foo', 'foo/bar' 'foo/bar/baz'].

  Args:
    path: str, the path for which to get prefixes.

  Returns:
    list of str, the prefixes.
  """
  path_prefixes = [path]
  path_reminder = True
  # Apparently which one is empty when operating on top-level directory depends
  # on your configuration.
  while path and path_reminder:
    path, path_reminder = os.path.split(path)
    path_prefixes.insert(0, path)
  return path_prefixes


class Pattern(object):
  """An ignore-file pattern.

  Corresponds to one non-blank, non-comment line in the ignore-file.

  See https://git-scm.com/docs/gitignore for full syntax specification.

  If it matches a string, will return Match.IGNORE (or Match.INCLUDE if
  negated).
  """

  def __init__(self, pattern, negated=False, must_be_dir=False):
    self.pattern = pattern
    self.negated = negated
    self.must_be_dir = must_be_dir

  def _MatchesHelper(self, pattern_parts, path):
    """Determines whether the given pattern matches the given path.

    Args:
      pattern_parts: list of str, the list of pattern parts that must all match
        the path.
      path: str, the path to match.

    Returns:
      bool, whether the patch matches the pattern_parts (Matches() will convert
        this into a Match value).
    """
    # This method works right-to-left. It checks that the right-most pattern
    # part matches the right-most path part, and that the remaining pattern
    # matches the remaining path.
    if not pattern_parts:
      # We've reached the end of the pattern! Success.
      return True
    if path is None:
      # Distinguish between '*' and '/*'. The former should match '' (the root
      # directory) but the latter should not.
      return False

    pattern_part = pattern_parts[-1]
    remaining_pattern = pattern_parts[:-1]
    if path:  # normpath turns '' into '.', which confuses fnmatch later
      path = os.path.normpath(path)
    remaining_path, path_part = os.path.split(path)
    if not path_part:
      # See note above.
      remaining_path = None

    if pattern_part == '**':
      # If the path would match the remaining pattern_parts after skipping 0-all
      # of the trailing path parts, the whole pattern matches.
      #
      # That is, if we have `<pattern>/**` as a pattern and `foo/bar` as our
      # path, if any of ``, `foo`, and `foo/bar` match `<pattern>`, we return
      # true.
      path_prefixes = _GetPathPrefixes(path)
      # '**' patterns only match against the full path (essentially, they have
      # an implicit '/' at the front of the pattern). An empty string at the
      # beginning of remaining_pattern simulates this.
      #
      # pylint: disable=g-explicit-bool-comparison
      # In this case, it's much clearer to show what we're checking for.
      if not (remaining_pattern and remaining_pattern[0] == ''):
        remaining_pattern.insert(0, '')
      # pylint: enable=g-explicit-bool-comparison
      return any(self._MatchesHelper(remaining_pattern, prefix) for prefix
                 in path_prefixes)

    if not fnmatch.fnmatch(path_part, pattern_part):
      # If the current pattern part doesn't match the current path part, the
      # whole pattern can't match the whole path. Give up!
      return False

    return self._MatchesHelper(remaining_pattern, remaining_path)

  def Matches(self, path, is_dir=False):
    """Returns a Match for this pattern and the given path."""
    if self.must_be_dir and not is_dir:
      return Match.NO_MATCH
    if self._MatchesHelper(self.pattern.split('/'), path):
      return Match.INCLUDE if self.negated else Match.IGNORE
    else:
      return Match.NO_MATCH

  @classmethod
  def FromString(cls, line):
    """Creates a pattern for an individual line of an ignore file.

    Windows-style newlines must be removed.

    Args:
      line: str, The line to parse.

    Returns:
      Pattern.

    Raises:
      InvalidLineError: if the line was invalid (comment, blank, contains
        invalid consecutive stars).
    """
    if line.startswith('#'):
      raise InvalidLineError('Line [{}] begins with `#`.'.format(line))
    if line.startswith('!'):
      line = line[1:]
      negated = True
    else:
      negated = False
    if line.endswith('/'):
      line = line[:-1]
      must_be_dir = True
    else:
      must_be_dir = False
    line = _HandleSpaces(line)
    if re.search(_ENDS_IN_ODD_NUMBER_SLASHES_RE, line):
      raise InvalidLineError(
          'Line [{}] ends in an odd number of [\\]s.'.format(line))
    line = _Unescape(line)
    if not line:
      raise InvalidLineError('Line [{}] is blank.'.format(line))
    return cls(line, negated=negated, must_be_dir=must_be_dir)


class FileChooser(object):
  """A FileChooser determines which files in a directory to upload.

  It's a fancy way of constructing a predicate (IsIncluded) along with a
  convenience method for walking a directory (GetIncludedFiles) and listing
  files to be uploaded based on that predicate.

  How the predicate operates is based on a gcloudignore file (see module
  docstring for details).
  """

  _INCLUDE_DIRECTIVE = '!include:'

  def __init__(self, patterns):
    self.patterns = patterns

  def IsIncluded(self, path, is_dir=False):
    """Returns whether the given file/directory should be included.

    This is determined according to the rules at
    https://git-scm.com/docs/gitignore.

    In particular:
    - the method goes through pattern-by-pattern in-order
    - any matches of a parent directory on a particular pattern propagate to its
      children
    - if a parent directory is ignored, its children cannot be re-included

    Args:
      path: str, the path (relative to the root upload directory) to test.
      is_dir: bool, whether the path is a directory (not a file or symlink).

    Returns:
      bool, whether the file should be uploaded
    """
    path_prefixes = _GetPathPrefixes(path)
    path_prefix_map = collections.OrderedDict(
        [(prefix, Match.NO_MATCH) for prefix in path_prefixes])
    for pattern in self.patterns:
      parent_match = Match.NO_MATCH
      for path_prefix in path_prefix_map:
        if parent_match is not Match.NO_MATCH:
          match = parent_match
        else:
          # All prefixes except the path itself are directories.
          is_prefix_dir = path_prefix != path or is_dir
          match = pattern.Matches(path_prefix, is_dir=is_prefix_dir)
        if match is not Match.NO_MATCH:
          path_prefix_map[path_prefix] = match
        parent_match = match
        if path_prefix_map[path_prefix] is Match.IGNORE:
          parent_match = Match.IGNORE

    included = path_prefix_map[path] is not Match.IGNORE
    if not included:
      log.debug('Skipping file [{}]'.format(path))
    return included

  def GetIncludedFiles(self, upload_directory, include_dirs=True):
    """Yields the files in the given directory that this FileChooser includes.

    Args:
      upload_directory: str, the path of the directory to upload.
      include_dirs: bool, whether to include directories

    Yields:
      str, the files and directories that should be uploaded.
    """
    for dirpath, dirnames, filenames in os.walk(upload_directory):
      if dirpath == upload_directory:
        relpath = ''
      else:
        relpath = os.path.relpath(dirpath, upload_directory)
      for filename in filenames:
        file_relpath = os.path.join(relpath, filename)
        if self.IsIncluded(file_relpath):
          yield file_relpath
      for dirname in dirnames[:]:  # make a copy since we modify the original
        file_relpath = os.path.join(relpath, dirname)
        # Don't treat symlinks as directories, even though os.walk does.
        is_dir = not os.path.islink(os.path.join(dirpath, dirname))
        if self.IsIncluded(file_relpath, is_dir=is_dir):
          if include_dirs:
            yield file_relpath
        else:
          # Don't bother recursing into skipped directories
          dirnames.remove(dirname)

  @classmethod
  def FromString(cls, text, recurse=0, dirname=None):
    """Constructs a FileChooser from the given string.

    See `gcloud topic gcloudignore` for details.

    Args:
      text: str, the string (many lines, in the format specified in the
        documentation).
      recurse: int, how many layers of "#!include" directives to respect. 0
        means don't respect the directives, 1 means to respect the directives,
        but *not* in any "#!include"d files, etc.
      dirname: str, the base directory from which to "#!include"

    Raises:
      BadIncludedFileError: if a file being included does not exist or is not
        in the same directory.

    Returns:
      FileChooser.
    """
    patterns = []
    for line in text.splitlines():
      if line.startswith('#'):
        if line[1:].lstrip().startswith(cls._INCLUDE_DIRECTIVE):
          patterns.extend(cls._GetIncludedPatterns(line, dirname, recurse))
        continue  # lines beginning with '#' are comments
      line_with_spaces_gone = _HandleSpaces(line)
      if (not line_with_spaces_gone or
          re.search(_ENDS_IN_ODD_NUMBER_SLASHES_RE, line_with_spaces_gone)):
        continue  # blank line or trailing / both get ignored
      patterns.append(Pattern.FromString(line))
    return cls(patterns)

  @classmethod
  def _GetIncludedPatterns(cls, line, dirname, recurse):
    """Gets the patterns from an '#!include' line.

    Args:
      line: str, the line containing the '#!include' directive
      dirname: str, the name of the base directory from which to include files
      recurse: int, how many layers of "#!include" directives to respect. 0
        means don't respect the directives, 1 means to respect the directives,
        but *not* in any "#!include"d files, etc.

    Returns:
      list of Pattern, the patterns recursively included from the specified
        file.

    Raises:
      ValueError: if dirname is not provided
      BadIncludedFileError: if the file being included does not exist or is not
        in the same directory.
    """
    if not dirname:
      raise ValueError('dirname must be provided in order to include a file.')
    start_idx = line.find(cls._INCLUDE_DIRECTIVE)
    included_file = line[start_idx + len(cls._INCLUDE_DIRECTIVE):]
    if _GCLOUDIGNORE_PATH_SEP in included_file:
      raise BadIncludedFileError(
          'May only include files in the same directory.')
    if not recurse:
      log.info('Not respecting `#!include` directive: [%s].', line)
      return []

    included_path = os.path.join(dirname, included_file)
    try:
      return cls.FromFile(included_path, recurse - 1).patterns
    except BadFileError as err:
      raise BadIncludedFileError(err.message)

  @classmethod
  def FromFile(cls, ignore_file_path, recurse=1):
    """Constructs a FileChooser from the given file path.

    See `gcloud topic gcloudignore` for details.

    Args:
      ignore_file_path: str, the path to the file in .gcloudignore format.
      recurse: int, how many layers of "#!include" directives to respect. 0
        means don't respect the directives, 1 means to respect the directives,
        but *not* in any "#!include"d files, etc.

    Raises:
      BadIncludedFileError: if the file being included does not exist or is not
        in the same directory.

    Returns:
      FileChooser.
    """
    try:
      with open(ignore_file_path, 'rb') as f:
        text = f.read()
    except IOError as err:
      raise BadFileError(
          'Could not read ignore file [{}]: {}'.format(ignore_file_path, err))
    return cls.FromString(text, dirname=os.path.dirname(ignore_file_path),
                          recurse=recurse)


def AnyFileOrDirExists(directory, names):
  files_to_check = [os.path.join(directory, name) for name in names]
  return any(map(os.path.exists, files_to_check))


def _GitFilesExist(directory):
  return AnyFileOrDirExists(directory, GIT_FILES)


def _GetIgnoreFileContents(default_ignore_file,
                           directory,
                           include_gitignore=True):
  ignore_file_contents = default_ignore_file
  if include_gitignore and os.path.exists(
      os.path.join(directory, '.gitignore')):
    ignore_file_contents += '#!include:.gitignore\n'
  return ignore_file_contents


def GetFileChooserForDir(
    directory, default_ignore_file=DEFAULT_IGNORE_FILE, write_on_disk=True,
    gcloud_ignore_creation_predicate=_GitFilesExist, include_gitignore=True):
  """Gets the FileChooser object for the given directory.

  In order of preference:
  - Uses .gcloudignore file in the top-level directory.
  - Evaluates creation predicate to determine whether to generate .gcloudignore.
    include_gitignore determines whether the generated .gcloudignore will
    include the user's .gitignore if one exists. If the directory is not
    writable, the file chooser corresponding to the ignore file that would have
    been generated is used.
  - If the creation predicate evaluates to false, returned FileChooser
    will choose all files.

  Args:
    directory: str, the path of the top-level directory to upload
    default_ignore_file: str, the ignore file to use if one is not found (and
      the directory has Git files).
    write_on_disk: bool, whether to save the generated gcloudignore to disk.
    gcloud_ignore_creation_predicate: one argument function, indicating if a
      .gcloudignore file should be created. The argument is the path of the
      directory that would contain the .gcloudignore file. By default
      .gcloudignore file will be created if and only if the directory contains
      .gitignore file or .git directory.
    include_gitignore: bool, whether the generated gcloudignore should include
      the user's .gitignore if present.

  Raises:
    BadIncludedFileError: if a file being included does not exist or is not in
      the same directory.

  Returns:
    FileChooser: the FileChooser for the directory. If there is no .gcloudignore
    file and it can't be created the returned FileChooser will choose all files.
  """
  if not properties.VALUES.gcloudignore.enabled.GetBool():
    log.info('Not using a .gcloudignore file since gcloudignore is globally '
             'disabled.')
    return FileChooser([])
  gcloudignore_path = os.path.join(directory, IGNORE_FILE_NAME)
  try:
    chooser = FileChooser.FromFile(gcloudignore_path)
  except BadFileError:
    pass
  else:
    log.info('Using .gcloudignore file at [{}].'.format(gcloudignore_path))
    return chooser
  if not gcloud_ignore_creation_predicate(directory):
    log.info('Not using a .gcloudignore file.')
    return FileChooser([])

  ignore_contents = _GetIgnoreFileContents(default_ignore_file, directory,
                                           include_gitignore)
  log.info('Using default gcloudignore file:\n{0}\n{1}\n{0}'.format(
      '--------------------------------------------------', ignore_contents))
  if write_on_disk:
    try:
      files.WriteFileContents(gcloudignore_path, ignore_contents,
                              overwrite=False)
    except files.Error as err:
      log.info('Could not write .gcloudignore file: {}'.format(err))
    else:
      log.status.Print('Created .gcloudignore file. See `gcloud topic '
                       'gcloudignore` for details.')
  return FileChooser.FromString(ignore_contents, recurse=1, dirname=directory)
