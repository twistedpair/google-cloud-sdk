# Copyright 2015 Google Inc. All Rights Reserved.

"""The implementation of generating a source context file."""

import json
import os
import re
import subprocess

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.util import compat26
from googlecloudsdk.core.util import files


_REMOTE_URL_PATTERN = r'remote\.(.*)\.url'

_CLOUD_REPO_PATTERN = (
    r'^https://'
    '(?P<hostname>[^/]*)/'
    '(?P<id_type>p|id)/'
    '(?P<project_or_repo_id>[^/?#]+)'
    '(/r/(?P<repo_name>[^/?#]+))?'
    '([/#?].*)?')


class GenerateSourceContextError(exceptions.Error):
  """An error occurred while trying to create the source context."""
  pass


def CalculateExtendedSourceContexts(source_directory):
  """Generate extended source contexts for a directory.

  Scans the remotes and revision of the git repository at source_directory,
  returning one or more ExtendedSourceContext-compatible dictionaries describing
  the repositories.

  Currently, this function will return only the Google-hosted repository
  associated with the directory, if one exists.

  Args:
    source_directory: The path to directory containing the source code.
  Returns:
    One or more ExtendedSourceContext-compatible dictionaries describing
    the remote repository or repositories associated with the given directory.
  Raises:
    GenerateSourceContextError: if source context could not be generated.
  """

  # First get all of the remote URLs from the source directory.
  remote_urls = _GetGitRemoteUrls(source_directory)
  if not remote_urls:
    raise GenerateSourceContextError(
        'Could not list remote URLs from source directory: %s' %
        source_directory)

  # Then get the current revision.
  source_revision = _GetGitHeadRevision(source_directory)
  if not source_revision:
    raise GenerateSourceContextError(
        'Could not find HEAD revision from the source directory: %s' %
        source_directory)

  # Now find any remote URLs that match a Google-hosted source context.
  source_contexts = []
  for remote_url in remote_urls.itervalues():
    source_context = _ParseSourceContext(remote_url, source_revision)
    # Only add this to the list if it parsed correctly, and hasn't been seen.
    # We'd like to do this in O(1) using a set, but Python doesn't hash dicts.
    # The number of remotes should be small anyway, so keep it simple.
    if source_context and source_context not in source_contexts:
      source_contexts.append(source_context)

  # If source context is still None or ambiguous, we have no context to go by.
  if not source_contexts:
    raise GenerateSourceContextError(
        'Could not find any repository in the remote URLs for source '
        'directory: %s' % source_directory)
  return source_contexts


def BestSourceContext(source_contexts, source_directory):
  """Returns the "best" source context from a list of contexts.

  "Best" here means:

  * The Cloud Repo context, if there is exactly one such.
  * The Git Repo context, if there is no Cloud Repo context.
  * If the above conditions are not met, raise an error.

  Args:
    source_contexts: An array of source contexts.
    source_directory: The source location (for error messages).
  Returns:
    A single source context.
  Raises:
    GenerateSourceContextError: if source context could not be generated.
  """
  source_context = None
  must_be_cloud = False
  for ext_ctx in source_contexts:
    candidate = ext_ctx['context']
    if not source_context:
      source_context = candidate
      continue
    if 'cloudRepo' in candidate.keys():
      if 'cloudRepo' in source_context.keys():
        raise GenerateSourceContextError(
            'Found multiple Google Cloud Repositories in the remote URLs for '
            'source directory: %s' % source_directory)
      source_context = candidate
    else:
      # This is a Git context, and we've seen at least one other context.
      # If there's a cloud repo context as well, we'll return that, but if
      # not, we need to fail.
      must_be_cloud = True
  if must_be_cloud and 'cloudRepo' not in source_context.keys():
    raise GenerateSourceContextError(
        'Found multiple Git Repositories (and no Google Cloud Repository) in '
        'the remote URLs for source directory: %s' % source_directory)
  return source_context


def GenerateSourceContext(source_directory, output_file):
  """Generate a source context JSON blob.

  Scans the remotes and revision of the git repository at source_directory,
  which (in a successful case) results in a JSON blob as output_file.

  Args:
    source_directory: The path to directory containing the source code.
    output_file: Output file for the source context JSON blob.
  Raises:
    GenerateSourceContextError: if source context could not be generated.
  """

  source_contexts = CalculateExtendedSourceContexts(source_directory)
  source_context = BestSourceContext(source_contexts, source_directory)

  # Spit out the JSON source context blob.
  output_file = os.path.abspath(output_file)
  output_dir, unused_name = os.path.split(output_file)
  files.MakeDir(output_dir)
  with open(output_file, 'w') as f:
    json.dump(source_context, f, indent=2, sort_keys=True)


def _CallGit(cwd, *args):
  """Calls git with the given args, in the given working directory.

  Args:
    cwd: The working directory for the command.
    *args: Any arguments for the git command.
  Returns:
    The raw output of the command, or None if the command failed.
  """
  try:
    return compat26.subprocess.check_output(['git'] + list(args), cwd=cwd)
  except subprocess.CalledProcessError as e:
    log.debug('Could not call git with args %s: %s', args, e)
    return None


def _GetGitRemoteUrlConfigs(source_directory):
  """Calls git to output every configured remote URL.

  Args:
    source_directory: The path to directory containing the source code.
  Returns:
    The raw output of the command, or None if the command failed.
  """
  return _CallGit(
      source_directory, 'config', '--get-regexp', _REMOTE_URL_PATTERN)


def _GetGitRemoteUrls(source_directory):
  """Finds the list of git remotes for the given source directory.

  Args:
    source_directory: The path to directory containing the source code.
  Returns:
    A dictionary of remote name to remote URL, empty if no remotes are found.
  """
  remote_url_config_output = _GetGitRemoteUrlConfigs(source_directory)
  if not remote_url_config_output:
    return {}

  result = {}
  config_lines = remote_url_config_output.split('\n')
  for config_line in config_lines:
    if not config_line:
      continue  # Skip blank lines.

    # Each line looks like "remote.<name>.url <url>.
    config_line_parts = config_line.split(' ')
    if len(config_line_parts) != 2:
      log.debug('Skipping unexpected config line, incorrect segments: %s',
                config_line)
      continue

    # Extract the two parts, then find the name of the remote.
    remote_url_config_name = config_line_parts[0]
    remote_url = config_line_parts[1]
    remote_url_name_match = re.match(
        _REMOTE_URL_PATTERN, remote_url_config_name)
    if not remote_url_name_match:
      log.debug('Skipping unexpected config line, could not match remote: %s',
                config_line)
      continue
    remote_url_name = remote_url_name_match.group(1)

    result[remote_url_name] = remote_url
  return result


def _GetGitHeadRevision(source_directory):
  """Finds the current HEAD revision for the given source directory.

  Args:
    source_directory: The path to directory containing the source code.
  Returns:
    The HEAD revision of the current branch, or None if the command failed.
  """
  raw_output = _CallGit(source_directory, 'rev-parse', 'HEAD')
  return raw_output.strip() if raw_output else None


def _ParseSourceContext(remote_url, source_revision):
  """Parses the URL into a source context blob, if the URL is a git or GCP repo.

  Args:
    remote_url: The remote URL to parse.
    source_revision: The current revision of the source directory.
  Returns:
    An ExtendedSourceContext suitable for JSON.
  """
  # Assume it's a Git URL unless proven otherwise.
  context = None

  # Now try to interpret the input as a Cloud Repo URL, and change context
  # accordingly if it looks like one. Assume any seemingly malformed URL is
  # a valid Git URL, since the inputs to this function always come from Git.
  #
  # A cloud repo URL can take three forms:
  # 1: https://<hostname>/id/<repo_id>
  # 2: https://<hostname>/p/<project_id>
  # 3: https://<hostname>/p/<project_id>/r/<repo_name>
  #
  # There are two repo ID types. The first type is the direct repo ID,
  # <repo_id>, which uniquely identifies a repository. The second is the pair
  # (<project_id>, <repo_name>) which also uniquely identifies a repository.
  #
  # Case 2 is equivalent to case 3 with <repo_name> defaulting to "default".
  match = re.match(_CLOUD_REPO_PATTERN, remote_url)
  if match:
    # It looks like a GCP repo URL. Extract the repo ID blob from it.
    id_type = match.group('id_type')
    if id_type == 'id':
      raw_repo_id = match.group('project_or_repo_id')
      # A GCP URL with an ID can't have a repo specification. If it has
      # one, it's either malformed or it's a Git URL from some other service.
      if not match.group('repo_name'):
        context = {
            'cloudRepo': {
                'repoId': {
                    'uid': raw_repo_id
                },
                'revisionId': source_revision}}
    elif id_type == 'p':
      # Treat it as a project name plus an optional repo name.
      project_id = match.group('project_or_repo_id')
      repo_name = match.group('repo_name') or 'default'
      context = {
          'cloudRepo': {
              'repoId': {
                  'projectRepoId': {
                      'projectId': project_id,
                      'repoName': repo_name}},
              'revisionId': source_revision}}
    # else it doesn't look like a GCP URL

  if not context:
    context = {'git': {'url': remote_url, 'revisionId': source_revision}}

  return {'context': context, 'labels': {'category': 'remote_repo'}}
