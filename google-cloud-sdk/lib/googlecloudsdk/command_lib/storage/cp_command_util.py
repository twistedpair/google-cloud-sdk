# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Generic logic for cp and mv command surfaces.

Uses command surface tests. Ex: cp_test.py, not cp_command_util_test.py.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import contextlib
import os

from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.storage import encryption_util
from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage import errors_util
from googlecloudsdk.command_lib.storage import flags
from googlecloudsdk.command_lib.storage import folder_util
from googlecloudsdk.command_lib.storage import name_expansion
from googlecloudsdk.command_lib.storage import plurality_checkable_iterator
from googlecloudsdk.command_lib.storage import rm_command_util
from googlecloudsdk.command_lib.storage import stdin_iterator
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage import user_request_args_factory
from googlecloudsdk.command_lib.storage.tasks import task_executor
from googlecloudsdk.command_lib.storage.tasks import task_graph_executor
from googlecloudsdk.command_lib.storage.tasks import task_status
from googlecloudsdk.command_lib.storage.tasks.cp import copy_task_iterator
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import platforms

_ALL_VERSIONS_HELP_TEXT = """\
Copy all source versions from a source bucket or folder. If not set, only the
live version of each source object is copied.

Note: This option is only useful when the destination bucket has Object
Versioning enabled. Additionally, the generation numbers of copied versions do
not necessarily match the order of the original generation numbers.
"""
# TODO(b/223800321): Maybe offer ability to limit parallel encoding workers.
_GZIP_IN_FLIGHT_EXTENSIONS_HELP_TEXT = """\
Applies gzip transport encoding to any file upload whose
extension matches the input extension list. This is useful when
uploading files with compressible content such as .js, .css,
or .html files. This also saves network bandwidth while
leaving the data uncompressed in Cloud Storage.

When you specify the `--gzip-in-flight` option, files being
uploaded are compressed in-memory and on-the-wire only. Both the local
files and Cloud Storage objects remain uncompressed. The
uploaded objects retain the `Content-Type` and name of the
original files."""
_GZIP_IN_FLIGHT_ALL_HELP_TEXT = """\
Applies gzip transport encoding to file uploads. This option
works like the `--gzip-in-flight` option described above,
but it applies to all uploaded files, regardless of extension.

CAUTION: If some of the source files don't compress well, such
as binary data, using this option may result in longer uploads."""
_GZIP_LOCAL_EXTENSIONS_HELP_TEXT = """\
Applies gzip content encoding to any file upload whose
extension matches the input extension list. This is useful when
uploading files with compressible content such as .js, .css,
or .html files. This saves network bandwidth and space in Cloud Storage.

When you specify the `--gzip-local` option, the data from
files is compressed before it is uploaded, but the original files are left
uncompressed on the local disk. The uploaded objects retain the `Content-Type`
and name of the original files. However, the `Content-Encoding` metadata
is set to `gzip` and the `Cache-Control` metadata set to `no-transform`.
The data remains compressed on Cloud Storage servers and will not be
decompressed on download by gcloud storage because of the `no-transform`
field.

Since the local gzip option compresses data prior to upload, it is not subject
to the same compression buffer bottleneck of the in-flight gzip option."""
_GZIP_LOCAL_ALL_HELP_TEXT = """\
Applies gzip content encoding to file uploads. This option
works like the `--gzip-local` option described above,
but it applies to all uploaded files, regardless of extension.

CAUTION: If some of the source files don't compress well, such as binary data,
using this option may result in files taking up more space in the cloud than
they would if left uncompressed."""
_MANIFEST_HELP_TEXT = """\
Outputs a manifest log file with detailed information about each item that
was copied. This manifest contains the following information for each item:

- Source path.
- Destination path.
- Source size.
- Bytes transferred.
- MD5 hash.
- Transfer start time and date in UTC and ISO 8601 format.
- Transfer completion time and date in UTC and ISO 8601 format.
- Final result of the attempted transfer: OK, error, or skipped.
- Details, if any.

If the manifest file already exists, gcloud storage appends log items to the
existing file.

Objects that are marked as "OK" or "skipped" in the existing manifest file
are not retried by future commands. Objects marked as "error" are retried.
"""
_PRESERVE_POSIX_HELP_TEXT = """\
Causes POSIX attributes to be preserved when objects are copied. With this feature enabled,
gcloud storage will copy several fields provided by the stat command:
access time, modification time, owner UID, owner group GID, and the mode
(permissions) of the file.

For uploads, these attributes are read off of local files and stored in the
cloud as custom metadata. For downloads, custom cloud metadata is set as POSIX
attributes on files after they are downloaded.

On Windows, this flag will only set and restore access time and modification
time because Windows doesn't have a notion of POSIX UID, GID, and mode.
"""
_PRESERVE_SYMLINKS_HELP_TEST = """\
Preserve symlinks instead of copying what they point to. With this feature
enabled, uploaded symlinks will be represented as placeholders in the cloud
whose content consists of the linked path. Inversely, such placeholders will be
converted to symlinks when downloaded while this feature is enabled, as
described at https://cloud.google.com/storage-transfer/docs/metadata-preservation#posix_to.

Directory symlinks are only followed if this flag is specified.

CAUTION: No validation is applied to the symlink target paths. Once downloaded,
preserved symlinks will point to whatever path was specified by the placeholder,
regardless of the location or permissions of the path, or whether it actually
exists.

This feature is not supported on Windows.
"""


def add_gzip_in_flight_flags(parser):
  """Adds flags for gzip parsing in flight."""
  parser.add_argument(
      '-J',
      '--gzip-in-flight-all',
      action='store_true',
      help=_GZIP_IN_FLIGHT_ALL_HELP_TEXT,
  )
  parser.add_argument(
      '-j',
      '--gzip-in-flight',
      metavar='FILE_EXTENSIONS',
      type=arg_parsers.ArgList(),
      help=_GZIP_IN_FLIGHT_EXTENSIONS_HELP_TEXT,
  )


def add_include_managed_folders_flag(parser, hns_feature_warning=False):
  """Adds --include-managed-folders flag to the parser.

  Args:
    parser: (parser_arguments.ArgumentInterceptor): Parser passed to surface.
    hns_feature_warning: (bool) Whether to add a warning for HNS buckets to the
      flag.
  """
  # Adding an hns_features_warning flag to add a warning about
  # --include-managed-folders flag only for commands that are supporting
  # HNS buckets right now.
  hns_feature_warning_help_text = (
      'Includes managed folders in command operations. For'
      ' transfers, gcloud storage will set up managed folders in the'
      ' destination with the same IAM policy bindings as the source.'
      ' Managed folders are only included with recursive cloud-to-cloud'
      ' transfers.'
      ' Please note that for hierarchical namespace buckets,'
      ' managed folders are always included. Hence this flag would not be'
      ' applicable to hierarchical namespace buckets.'
  )
  help_text = (
      'Includes managed folders in command operations. For'
      ' transfers, gcloud storage will set up managed folders in the'
      ' destination with the same IAM policy bindings as the source.'
      ' Managed folders are only included with recursive cloud-to-cloud'
      ' transfers.'
  )
  parser.add_argument(
      '--include-managed-folders',
      action='store_true',
      default=False,
      help=hns_feature_warning_help_text if hns_feature_warning else help_text,
  )


def add_ignore_symlinks_flag(parser_or_group, default=False):
  """Adds flag for skipping copying symlinks."""
  parser_or_group.add_argument(
      '--ignore-symlinks',
      action='store_true',
      default=default,
      help=(
          'Ignore file symlinks instead of copying what they point to.'
      ),
  )


def add_preserve_symlinks_flag(parser_or_group, default=False):
  """Adds flag for preserving symlinks."""
  parser_or_group.add_argument(
      '--preserve-symlinks',
      action='store_true',
      default=default,
      help=_PRESERVE_SYMLINKS_HELP_TEST,
  )


def add_cp_mv_rsync_flags(parser, release_track=base.ReleaseTrack.GA):
  """Adds flags shared by cp, mv, and rsync."""
  flags.add_additional_headers_flag(parser)
  flags.add_continue_on_error_flag(parser)
  flags.add_object_metadata_flags(parser, release_track=release_track)
  flags.add_precondition_flags(parser)
  parser.add_argument(
      '--content-md5',
      metavar='MD5_DIGEST',
      help=('Manually specified MD5 hash digest for the contents of an uploaded'
            ' file. This flag cannot be used when uploading multiple files. The'
            ' custom digest is used by the cloud provider for validation.'))
  parser.add_argument(
      '-n',
      '--no-clobber',
      action='store_true',
      help=(
          'Do not overwrite existing files or objects at the destination.'
          ' Skipped items will be printed. This option may perform an'
          ' additional GET request for cloud objects before attempting an'
          ' upload.'
      ),
  )
  parser.add_argument(
      '-P',
      '--preserve-posix',
      action='store_true',
      help=_PRESERVE_POSIX_HELP_TEXT,
  )
  parser.add_argument(
      '-U',
      '--skip-unsupported',
      action='store_true',
      help='Skip objects with unsupported object types.',
  )


def add_cp_and_mv_flags(parser, release_track=base.ReleaseTrack.GA):
  """Adds flags to cp, mv, or other cp-based commands."""
  parser.add_argument('source', nargs='*', help='The source path(s) to copy.')
  parser.add_argument('destination', help='The destination path.')
  add_cp_mv_rsync_flags(parser, release_track=release_track)
  parser.add_argument(
      '-A', '--all-versions', action='store_true', help=_ALL_VERSIONS_HELP_TEXT)
  parser.add_argument(
      '--do-not-decompress',
      action='store_true',
      help='Do not automatically decompress downloaded gzip files.')
  parser.add_argument(
      '-D',
      '--daisy-chain',
      action='store_true',
      help='Copy in "daisy chain" mode, which means copying an object by'
      ' first downloading it to the machine where the command is run, then'
      ' uploading it to the destination bucket. The default mode is a "copy'
      ' in the cloud," where data is copied without uploading or downloading.'
      ' During a copy in the cloud, a source composite object remains'
      ' composite at its destination. However, you can use daisy chain mode'
      ' to change a composite object into a non-composite object.'
      ' Note: Daisy chain mode is automatically used when copying between'
      ' providers.')
  add_include_managed_folders_flag(parser, hns_feature_warning=True)
  symlinks_group = parser.add_group(
      mutex=True,
      help=(
          'Flags to influence behavior when handling symlinks. Only one value'
          ' may be set.'
      ),
  )
  add_ignore_symlinks_flag(symlinks_group)
  add_preserve_symlinks_flag(symlinks_group)
  parser.add_argument('-L', '--manifest-path', help=_MANIFEST_HELP_TEXT)
  parser.add_argument(
      '-v',
      '--print-created-message',
      action='store_true',
      help='Prints the version-specific URL for each copied object.')
  parser.add_argument(
      '-s',
      '--storage-class',
      help='Specify the storage class of the destination object. If not'
      ' specified, the default storage class of the destination bucket is'
      ' used. This option is not valid for copying to non-cloud destinations.')

  gzip_flags_group = parser.add_group(mutex=True)
  add_gzip_in_flight_flags(gzip_flags_group)
  gzip_flags_group.add_argument(
      '-Z',
      '--gzip-local-all',
      action='store_true',
      help=_GZIP_LOCAL_ALL_HELP_TEXT,
  )
  gzip_flags_group.add_argument(
      '-z',
      '--gzip-local',
      metavar='FILE_EXTENSIONS',
      type=arg_parsers.ArgList(),
      help=_GZIP_LOCAL_EXTENSIONS_HELP_TEXT,
  )

  acl_flags_group = parser.add_group()
  flags.add_predefined_acl_flag(acl_flags_group)
  flags.add_preserve_acl_flag(acl_flags_group)
  flags.add_encryption_flags(parser)
  flags.add_read_paths_from_stdin_flag(
      parser,
      help_text=(
          'Read the list of resources to copy from stdin. No need to enter'
          ' a source argument if this flag is present.\nExample:'
          ' "storage cp -I gs://bucket/destination"\n'
          ' Note: To copy the contents of one file directly from stdin, use "-"'
          ' as the source argument without the "-I" flag.'
      ),
  )


def add_recursion_flag(parser):
  """Adds flag for copying with recursion.

  Not used by mv.

  Args:
    parser (parser_arguments.ArgumentInterceptor): Parser passed to surface.
  """
  parser.add_argument(
      '-R',
      '-r',
      '--recursive',
      action='store_true',
      help=(
          'Recursively copy the contents of any directories that match the'
          ' source path expression.'
      ),
  )


def validate_include_managed_folders(
    args, raw_source_urls, raw_destination_url
):
  """Validates that arguments are consistent with managed folder operations."""
  # TODO(b/304524534): Replace with args.include_managed_folders.
  if not args.include_managed_folders:
    return

  if isinstance(raw_destination_url, storage_url.FileUrl):
    raise errors.Error(
        'Cannot include managed folders with a non-cloud destination: {}'
        .format(raw_destination_url)
    )

  if getattr(args, 'read_paths_from_stdin', None):
    raise errors.Error(
        'Cannot include managed folders when reading paths from stdin, as this'
        ' would require storing all paths passed to gcloud storage in memory.'
    )

  for url_string in raw_source_urls:
    url = storage_url.storage_url_from_string(url_string)
    if isinstance(url, storage_url.FileUrl):
      raise errors.Error(
          'Cannot include managed folders with a non-cloud source: {}'.format(
              url
          )
      )

  if not args.recursive:
    raise errors.Error(
        'Cannot include managed folders unless recursion is enabled.'
    )

  errors_util.raise_error_if_not_gcs(args.command_path, raw_destination_url)


def _validate_args(args, raw_destination_url):
  """Raises errors if invalid flags are passed."""
  if args.no_clobber and args.if_generation_match:
    raise errors.Error(
        'Cannot specify both generation precondition and no-clobber.'
    )

  if args.preserve_symlinks and platforms.OperatingSystem.IsWindows():
    raise errors.Error('Symlink preservation is not supported for Windows.')

  if (isinstance(raw_destination_url, storage_url.FileUrl) and
      args.storage_class):
    raise errors.Error(
        'Cannot specify storage class for a non-cloud destination: {}'.format(
            raw_destination_url
        )
    )
  validate_include_managed_folders(args, args.source, raw_destination_url)


@contextlib.contextmanager
def _get_shared_stream(args, raw_destination_url):
  """Context manager for streams used in streaming downloads.

  Warns the user when downloading to a named pipe.

  Args:
    args (parser_extensions.Namespace): Flags passed by the user.
    raw_destination_url (storage_url.StorageUrl): The destination of the
      transfer. May contain unexpanded wildcards.

  Yields:
    A stream used for downloads, or None if the transfer is not a streaming
    download. The stream is closed by the context manager if it is not stdout.
  """
  if raw_destination_url.is_stdio:
    yield os.fdopen(1, 'wb')
  elif raw_destination_url.is_stream:
    log.warning('Downloading to a pipe.'
                ' This command may stall until the pipe is read.')
    with files.BinaryFileWriter(args.destination) as stream:
      yield stream
  else:
    yield None


def _is_parallelizable(args, raw_destination_url, first_source_url):
  """Determines whether a a `cp` workload is parallelizable.

  Logs warnings if gcloud storage is configured to parallelize workloads, but
  doing so is not possible.

  Args:
    args (parser_extensions.Namespace): Flags passed by the user.
    raw_destination_url (storage_url.StorageUrl): The destination of the
      transfer. May contain unexpanded wildcards.
    first_source_url (storage_url.StorageUrl): The first source URL passed by
      the user. May contain unexpanded wildcards.

  Returns:
    True if the transfer is parallelizable, False otherwise.
  """
  # Only warn the user about sequential execution when they have explicitly
  # requested parallelism in some dimension (process or thread count).
  parallelism_properties = {
      properties.VALUES.storage.process_count.GetInt(),
      properties.VALUES.storage.thread_count.GetInt(),
  }
  requested_parallelism = bool(parallelism_properties - {None, 1})  # any are >1

  if args.all_versions:
    if requested_parallelism:
      log.warning(
          'Using sequential instead of parallel task execution. This will'
          ' maintain version ordering when copying all versions of an object.')
    return False

  if raw_destination_url.is_stream:
    if requested_parallelism:
      log.warning(
          'Using sequential instead of parallel task execution to write to a'
          ' stream.')
    return False

  # Only the first url needs to be checked since multiple sources aren't
  # allowed with stdin.
  if first_source_url.is_stdio:
    if requested_parallelism:
      log.warning('Using sequential instead of parallel task execution to'
                  ' transfer from stdin.')
    return False

  return True


def _execute_copy_tasks(
    args,
    delete_source,
    parallelizable,
    raw_destination_url,
    source_expansion_iterator,
    folders_only=False,
):
  """Returns appropriate exit code after creating and executing copy tasks."""
  if raw_destination_url.is_stdio:
    task_status_queue = None
  else:
    task_status_queue = task_graph_executor.multiprocessing_context.Queue()

  user_request_args = (
      user_request_args_factory.get_user_request_args_from_command_args(
          args, metadata_type=user_request_args_factory.MetadataType.OBJECT))

  with _get_shared_stream(args, raw_destination_url) as shared_stream:
    task_iterator = copy_task_iterator.CopyTaskIterator(
        source_expansion_iterator,
        args.destination,
        custom_md5_digest=args.content_md5,
        delete_source=delete_source,
        do_not_decompress=args.do_not_decompress,
        force_daisy_chain=args.daisy_chain,
        print_created_message=args.print_created_message,
        shared_stream=shared_stream,
        skip_unsupported=args.skip_unsupported,
        task_status_queue=task_status_queue,
        user_request_args=user_request_args,
        folders_only=folders_only,
    )

    if folders_only:
      task_iterator = plurality_checkable_iterator.PluralityCheckableIterator(
          task_iterator
      )

      if task_iterator.is_empty():
        # If there are no Folder Tasks, we need not proceed when we want to only
        # proceed to work with folders.
        return 0

    return task_executor.execute_tasks(
        task_iterator,
        parallelizable=parallelizable,
        task_status_queue=task_status_queue,
        progress_manager_args=task_status.ProgressManagerArgs(
            task_status.IncrementType.FILES_AND_BYTES,
            manifest_path=user_request_args.manifest_path,
        ),
        continue_on_error=args.continue_on_error,
    )


def _get_managed_folder_iterator(args, url_found_match_tracker):
  return name_expansion.NameExpansionIterator(
      args.source,
      managed_folder_setting=(
          folder_util.ManagedFolderSetting.LIST_WITHOUT_OBJECTS
      ),
      folder_setting=folder_util.FolderSetting.DO_NOT_LIST,
      raise_error_for_unmatched_urls=False,
      recursion_requested=name_expansion.RecursionSetting.YES,
      url_found_match_tracker=url_found_match_tracker,
  )


def _copy_or_rename_folders(
    args, delete_source, raw_destination_url, url_found_match_tracker
):
  """Handles copies or renames specifically for Folders.

  Folders (of HNS buckets) are technically not objects. Hence the usual
  copy_object approach does not work for them.
  For renaming, while there is a specific API, it only works when renaming
  folders in the same bucket and for cross bucket renaming, we still require
  folder by folder approach.

  Hence, as a first step, in the case of rename only, this method tries to
  use the rename_folder API. If its successfully done, we need not handle
  individual folders.
  However, if that is not possible, or we are in the copy case, we need to
  handle things folder by folder and for that we have the second iterator
  and which creates a second set of copy tasks.

  Args:
    args: The command line arguments.
    delete_source: Boolean indicating if the source should be deleted after the
      copy operation. Pointing to the fact that this is a mv command.
    raw_destination_url: The destination URL.
    url_found_match_tracker: The url found match tracker.
  """
  if not (
      args.recursive
      and isinstance(raw_destination_url, storage_url.CloudUrl)
      and raw_destination_url.scheme == storage_url.ProviderPrefix.GCS
  ):
    return

  if delete_source and not args.daisy_chain:
    # Means we are copying for mv command and the user has not opted for an
    # explicit daisy chain option.
    # For such a case, for HNS buckets, we have to try to use the option of a
    # folder (and its sub-folders and objects) being renamed through
    # the rename_folder API directly.
    #
    # Since we need not care if the folder has content or not, if the input_url
    # specifies a Folder to be renamed into the same bucket, we simply call
    # RenameFolder operation on it.
    updated_sources = _filter_and_modify_source_for_folders_only(
        args.source, is_rename_folders=True
    )
    folder_rename_match_tracker = collections.OrderedDict()
    source_expansion_iterator = name_expansion.NameExpansionIterator(
        updated_sources,
        managed_folder_setting=folder_util.ManagedFolderSetting.DO_NOT_LIST,
        folder_setting=folder_util.FolderSetting.LIST_AS_FOLDERS,
        raise_error_for_unmatched_urls=False,
        recursion_requested=name_expansion.RecursionSetting.NO,
        url_found_match_tracker=folder_rename_match_tracker,
    )

    _execute_copy_tasks(
        args=args,
        delete_source=delete_source,
        parallelizable=False,
        raw_destination_url=raw_destination_url,
        source_expansion_iterator=source_expansion_iterator,
        folders_only=True,
    )
    _correct_url_found_match_tracker_for_copy_and_renames(
        args.source,
        updated_sources,
        url_found_match_tracker,
        folder_rename_match_tracker,
        is_rename_folders=True,
    )

  # In case of a rename, if the above operation happened, then this iterator
  # would be empty for the corresponding URL, hence we do not require any
  # handling for the same.
  #
  # However, in case the above rename could not be done, then we need to collect
  # information about the Folder (if it exists) and all its sub-folders and copy
  # them recursively into the destination. For renames, the deletion will then
  # automatically get handled at the end of the rename operation in the run_cp
  # method for Folders seprarately.
  updated_sources = _filter_and_modify_source_for_folders_only(
      args.source, is_rename_folders=False
  )
  folder_match_tracker = collections.OrderedDict()
  source_expansion_iterator = name_expansion.NameExpansionIterator(
      updated_sources,
      managed_folder_setting=folder_util.ManagedFolderSetting.DO_NOT_LIST,
      folder_setting=folder_util.FolderSetting.LIST_AS_FOLDERS,
      raise_error_for_unmatched_urls=False,
      recursion_requested=name_expansion.RecursionSetting.YES,
      url_found_match_tracker=folder_match_tracker,
  )

  _execute_copy_tasks(
      args=args,
      delete_source=False,
      parallelizable=False,
      raw_destination_url=raw_destination_url,
      source_expansion_iterator=source_expansion_iterator,
      folders_only=True,
  )

  _correct_url_found_match_tracker_for_copy_and_renames(
      args.source,
      updated_sources,
      url_found_match_tracker,
      folder_match_tracker,
  )


def _correct_url_found_match_tracker_for_copy_and_renames(
    original_sources,
    updated_sources,
    url_found_match_tracker,
    folders_tracker,
    is_rename_folders=False,
):
  """Corrects the results of url match tracker for copy and renames.

  Args:
    original_sources: Original sources given by the user.
    updated_sources: Updated sources after filtering and modifying for folders
      only.
    url_found_match_tracker: The common url found match tracker.
    folders_tracker: The url found match tracker we have created specifically
      for folders feature.
    is_rename_folders: Is the rename folders case.
  """
  for url in original_sources:
    if url in folders_tracker and folders_tracker[url]:
      # No need to set false values
      url_found_match_tracker[url] = folders_tracker[url]

    if url.endswith('/**') or url.endswith('/**/'):
      if is_rename_folders:
        possible_updated_url = url[:-1] if url.endswith('**') else url[:-2]
      else:
        # Because for copy folders, we remove the entire ** at the end
        # since we already have the recursion setting on. So we need to avoid
        # double recursion there.
        possible_updated_url = url[:-2] if url.endswith('**') else url[:-3]

      if (
          possible_updated_url in updated_sources
          and possible_updated_url in folders_tracker
          # No need to set false values
          and folders_tracker[possible_updated_url]
      ):
        url_found_match_tracker[url] = folders_tracker[possible_updated_url]


def _filter_and_modify_source_for_folders_only(
    sources, is_rename_folders=False
):
  """Filters and modifies sources urls for the purpose of HNS bucket rename_folder.

  We filter out any source URL which is not a GCS URL as rename folders is only
  applicable to HNS buckets which is a GCS feature.
  Apart from this, if the given URL ends with a **, we change it to a single *
  to match the filesystem behaviour.
  In case of a regular Linux filesystem, a ** or a * will rename folders under
  the given path to the destination. But in case of Gcloud, we would recursively
  list all sub-directories under it and try to renma them. This is not required
  for rename_folder operations.
  Hence, by replacing them with a *, we can simply rename the given sub-folders.

  Args:
    sources: List of source URLs given by the user to the command.
    is_rename_folders: Boolean indicating if the operation is for renaming
      folders.

  Returns:
    A list of source URLs which are filtered and modified for the purpose of
    rename_folders only operation.
  """
  updated_source_list = []
  for source in sources:
    if not is_gcs_cloud_url(storage_url.storage_url_from_string(source)):
      continue
    if source.endswith('/**') or source.endswith('/**/'):
      if is_rename_folders:
        updated_source = source[:-1] if source.endswith('**') else source[:-2]
      else:
        updated_source = source[:-2] if source.endswith('**') else source[:-3]

      if updated_source not in sources:
        updated_source_list.append(updated_source)
    else:
      updated_source_list.append(source)
  return updated_source_list


def _remove_folders(args, url_found_match_tracker):
  """Helper method to remove folders from HNS buckets.

  Removing folders is only applicable for HNS buckets.
  In the case where a source is a FileURL, we will see a failure in the
  DeleteTaskIteratorFactory as we try to call is_bucket() on a FileURL.
  This happens specifically in the case where we use --no-clobber flag and where
  the destination already exists. For such cases, we would skip deletion of the
  source. So the NameExpansionIterator will contain a FileURL which the
  DeleteTaskIteratorFactory will not be able to handle.

  Hence, we are skipping a given source if it's not a CloudURL since Folders
  are only applicable to CloudURLs (which are GCS) and running any attempt to
  find and delete a Folder is of no use on any other type of URL.

  Args:
    args: User provided arguments for the command.
    url_found_match_tracker: The common url found match tracker.

  Returns:
    Exit code for the operation.
  """
  # We are only filtering and not manipulating the URLs here.
  # So if a URL is updated with a False or True result in the
  # url_found_match_tracker, then it is the correct result.
  # Hence we need to leave it as is, to be considered in later iterators
  # since we do not throw an exception here when nothing is found.
  cloud_urls = []
  for url_string in args.source:
    if is_gcs_cloud_url(storage_url.storage_url_from_string(url_string)):
      cloud_urls.append(url_string)

  if not cloud_urls:
    # Since there is no need to remove folders if there are no CloudURLs,
    # there is no point in returning a Non-Zero (failure code) since
    # nothing has technically failed.
    return 0

  folder_expansion_iterator = name_expansion.NameExpansionIterator(
      cloud_urls,
      managed_folder_setting=folder_util.ManagedFolderSetting.DO_NOT_LIST,
      folder_setting=folder_util.FolderSetting.LIST_AS_FOLDERS,
      raise_error_for_unmatched_urls=False,
      recursion_requested=name_expansion.RecursionSetting.YES,
      url_found_match_tracker=url_found_match_tracker,
  )
  return rm_command_util.remove_folders(
      folder_expansion_iterator,
      task_graph_executor.multiprocessing_context.Queue(),
  )


def is_gcs_cloud_url(url):
  """Returns True if the URL is of type CloudURL and has a GCS ProviderPrefix."""
  return (
      isinstance(url, storage_url.CloudUrl)
      and url.scheme is storage_url.ProviderPrefix.GCS
  )


def run_cp(args, delete_source=False):
  """Runs implementation of cp surface with tweaks for similar commands."""
  raw_destination_url = storage_url.storage_url_from_string(args.destination)
  _validate_args(args, raw_destination_url)
  encryption_util.initialize_key_store(args)

  url_found_match_tracker = collections.OrderedDict()

  _copy_or_rename_folders(
      args, delete_source, raw_destination_url, url_found_match_tracker
  )

  # TODO(b/304524534): Replace with args.include_managed_folders.
  if args.include_managed_folders:
    source_expansion_iterator = _get_managed_folder_iterator(
        args, url_found_match_tracker
    )
    exit_code = _execute_copy_tasks(
        args=args,
        delete_source=False,
        parallelizable=False,
        raw_destination_url=raw_destination_url,
        source_expansion_iterator=source_expansion_iterator,
    )
    if exit_code:
      # An error occurred setting up managed folders in the destination, so we
      # exit out early, as managed folders regulate permissions and we do not
      # want to copy to a location that is incorrectly configured.
      return exit_code

  raw_source_string_iterator = (
      plurality_checkable_iterator.PluralityCheckableIterator(
          stdin_iterator.get_urls_iterable(
              args.source, args.read_paths_from_stdin
          )
      )
  )
  first_source_url = storage_url.storage_url_from_string(
      raw_source_string_iterator.peek()
  )
  parallelizable = _is_parallelizable(
      args, raw_destination_url, first_source_url
  )

  if args.preserve_acl:
    fields_scope = cloud_api.FieldsScope.FULL
  else:
    fields_scope = cloud_api.FieldsScope.NO_ACL

  source_expansion_iterator = name_expansion.NameExpansionIterator(
      raw_source_string_iterator,
      fields_scope=fields_scope,
      ignore_symlinks=args.ignore_symlinks,
      managed_folder_setting=folder_util.ManagedFolderSetting.DO_NOT_LIST,
      folder_setting=folder_util.FolderSetting.LIST_AS_PREFIXES,
      object_state=flags.get_object_state_from_flags(args),
      preserve_symlinks=args.preserve_symlinks,
      recursion_requested=name_expansion.RecursionSetting.YES
      if args.recursive
      else name_expansion.RecursionSetting.NO_WITH_WARNING,
      url_found_match_tracker=url_found_match_tracker,
  )
  exit_code = _execute_copy_tasks(
      args=args,
      delete_source=delete_source,
      parallelizable=parallelizable,
      raw_destination_url=raw_destination_url,
      source_expansion_iterator=source_expansion_iterator,
  )

  if delete_source:
    folder_exit_code = _remove_folders(args, url_found_match_tracker)
    if folder_exit_code != 0:
      # Avoiding the scenario where the folder deletion succeeds and overrides
      # a failed scenario during object listings, renames, etc.
      exit_code = folder_exit_code

    if args.include_managed_folders:
      managed_folder_expansion_iterator = name_expansion.NameExpansionIterator(
          args.source,
          managed_folder_setting=folder_util.ManagedFolderSetting.LIST_WITHOUT_OBJECTS,
          folder_setting=folder_util.FolderSetting.DO_NOT_LIST,
          raise_error_for_unmatched_urls=False,
          recursion_requested=name_expansion.RecursionSetting.YES,
          url_found_match_tracker=url_found_match_tracker,
      )
      exit_code = rm_command_util.remove_managed_folders(
          args,
          managed_folder_expansion_iterator,
          task_graph_executor.multiprocessing_context.Queue(),
      )

  return exit_code
