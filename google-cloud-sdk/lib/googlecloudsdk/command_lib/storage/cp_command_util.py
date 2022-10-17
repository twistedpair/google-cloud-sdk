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

import contextlib
import os

from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.storage import encryption_util
from googlecloudsdk.command_lib.storage import flags
from googlecloudsdk.command_lib.storage import name_expansion
from googlecloudsdk.command_lib.storage import plurality_checkable_iterator
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
decompressed on download by gcloud stroage because of the `no-transform`
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


def add_cp_flags(parser):
  """Adds flags to cp, mv, or other cp-based commands."""
  parser.add_argument('source', nargs='*', help='The source path(s) to copy.')
  parser.add_argument('destination', help='The destination path.')
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
  parser.add_argument(
      '--ignore-symlinks',
      action='store_true',
      help='Ignore file symlinks instead of copying what they point to.'
      ' Symlinks pointing to directories will always be ignored.')
  parser.add_argument('-L', '--manifest-path', help=_MANIFEST_HELP_TEXT)
  parser.add_argument(
      '-n',
      '--no-clobber',
      action='store_true',
      help='Do not overwrite existing files or objects at the destination.'
      ' Skipped items will be printed. This option performs an additional GET'
      ' request for cloud objects before attempting an upload.')
  parser.add_argument(
      '-P',
      '--preserve-posix',
      action='store_true',
      help=_PRESERVE_POSIX_HELP_TEXT)
  parser.add_argument(
      '-v',
      '--print-created-message',
      action='store_true',
      help='Prints the version-specific URL for each copied object.')
  parser.add_argument(
      '--read-paths-from-stdin',
      '-I',
      action='store_true',
      help='Read the list of resources to copy from stdin. No need to enter'
      ' a source argument if this flag is present.\nExample:'
      ' "storage cp -I gs://bucket/destination"\n'
      ' Note: To copy the contents of one file directly from stdin, use "-"'
      ' as the source argument without the "-I" flag.')
  parser.add_argument(
      '-U',
      '--skip-unsupported',
      action='store_true',
      help='Skip objects with unsupported object types.')
  parser.add_argument(
      '-s',
      '--storage-class',
      help='Specify the storage class of the destination object. If not'
      ' specified, the default storage class of the destination bucket is'
      ' used. This option is not valid for copying to non-cloud destinations.')

  gzip_flags_group = parser.add_group(mutex=True)
  gzip_flags_group.add_argument(
      '-J',
      '--gzip-in-flight-all',
      action='store_true',
      help=_GZIP_IN_FLIGHT_ALL_HELP_TEXT)
  gzip_flags_group.add_argument(
      '-j',
      '--gzip-in-flight',
      metavar='FILE_EXTENSIONS',
      type=arg_parsers.ArgList(),
      help=_GZIP_IN_FLIGHT_EXTENSIONS_HELP_TEXT)
  gzip_flags_group.add_argument(
      '-Z',
      '--gzip-local-all',
      action='store_true',
      help=_GZIP_LOCAL_ALL_HELP_TEXT)
  gzip_flags_group.add_argument(
      '-z',
      '--gzip-local',
      metavar='FILE_EXTENSIONS',
      type=arg_parsers.ArgList(),
      help=_GZIP_LOCAL_EXTENSIONS_HELP_TEXT)

  flags.add_continue_on_error_flag(parser)
  flags.add_precondition_flags(parser)
  flags.add_object_acl_setter_flags(parser)
  flags.add_object_metadata_flags(parser)
  flags.add_encryption_flags(parser)


def _validate_args(args, raw_destination_url):
  """Raises errors if invalid flags are passed."""
  if args.no_clobber and args.if_generation_match:
    raise ValueError(
        'Cannot specify both generation precondition and no-clobber.')

  if (isinstance(raw_destination_url, storage_url.FileUrl) and
      args.storage_class):
    raise ValueError(
        'Cannot specify storage class for a non-cloud destination: {}'.format(
            raw_destination_url))


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
  configured_for_parallelism = (
      properties.VALUES.storage.process_count.GetInt() != 1 or
      properties.VALUES.storage.thread_count.GetInt() != 1)

  if args.all_versions:
    if configured_for_parallelism:
      log.warning(
          'Using sequential instead of parallel task execution. This will'
          ' maintain version ordering when copying all versions of an object.')
    return False

  if raw_destination_url.is_stream:
    if configured_for_parallelism:
      log.warning(
          'Using sequential instead of parallel task execution to write to a'
          ' stream.')
    return False

  # Only the first url needs to be checked since multiple sources aren't
  # allowed with stdin.
  if first_source_url.is_stdio:
    if configured_for_parallelism:
      log.warning('Using sequential instead of parallel task execution to'
                  ' transfer from stdin.')
    return False

  return True


def run_cp(args, delete_source=False):
  """Runs implementation of cp surface with tweaks for similar commands."""
  raw_destination_url = storage_url.storage_url_from_string(args.destination)
  _validate_args(args, raw_destination_url)

  encryption_util.initialize_key_store(args)

  if args.preserve_acl:
    fields_scope = cloud_api.FieldsScope.FULL
  else:
    fields_scope = cloud_api.FieldsScope.NO_ACL

  raw_source_string_iterator = (
      plurality_checkable_iterator.PluralityCheckableIterator(
          stdin_iterator.get_urls_iterable(args.source,
                                           args.read_paths_from_stdin)))

  source_expansion_iterator = name_expansion.NameExpansionIterator(
      raw_source_string_iterator,
      all_versions=args.all_versions,
      fields_scope=fields_scope,
      ignore_symlinks=args.ignore_symlinks,
      recursion_requested=name_expansion.RecursionSetting.YES
      if args.recursive else name_expansion.RecursionSetting.NO_WITH_WARNING)

  if raw_destination_url.is_stdio:
    task_status_queue = None
  else:
    task_status_queue = task_graph_executor.multiprocessing_context.Queue()

  first_raw_source_string = raw_source_string_iterator.peek()
  first_source_url = storage_url.storage_url_from_string(
      first_raw_source_string)
  parallelizable = _is_parallelizable(args, raw_destination_url,
                                      first_source_url)

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
    )

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
