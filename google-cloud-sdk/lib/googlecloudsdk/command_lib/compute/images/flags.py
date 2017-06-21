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

"""Flags and helpers for the compute backend-buckets commands."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import flags as compute_flags

_SOURCE_DISK_DETAILED_HELP = """\
        A source disk to create the image from. The value for this option can be
        the name of a disk with the zone specified via ``--source-disk-zone''
        flag.
"""
_REPLACEMENT_DISK_DETAILED_HELP = """\
       Specifies a Compute Engine image as a replacement for the image
       being phased out. Users of the deprecated image will be advised to switch
       to this replacement. For example, *--replacement example-image* or
       *--replacement projects/google/global/images/example-image*.
       """

_SOURCE_DISK_ZONE_EXPLANATION = compute_flags.ZONE_PROPERTY_EXPLANATION

LIST_FORMAT = """\
    table(
      name,
      selfLink.map().scope(projects).segment(0):label=PROJECT,
      family,
      deprecated.state:label=DEPRECATED,
      status
    )"""


def MakeDiskImageArg(plural=False):
  return compute_flags.ResourceArgument(
      resource_name='disk image',
      name='image_name',
      completion_resource_id='compute.images',
      plural=plural,
      global_collection='compute.images')


def MakeForceCreateArg():
  return base.Argument(
      '--force-create',
      action='store_true',
      default=False,
      help="""\
          By default, image creation fails when it is created from a disk that
          is attached to a running instance. When this flag is used, image
          creation from disk will proceed even if the disk is in use.
          """)

REPLACEMENT_DISK_IMAGE_ARG = compute_flags.ResourceArgument(
    resource_name='disk image',
    name='--replacement',
    completion_resource_id='compute.images',
    global_collection='compute.images',
    required=False,
    short_help='Specifies a Compute Engine image as a replacement.',
    detailed_help=_REPLACEMENT_DISK_DETAILED_HELP)

SOURCE_DISK_ARG = compute_flags.ResourceArgument(
    resource_name='source disk',
    name='--source-disk',
    completion_resource_id='compute.disks',
    zonal_collection='compute.disks',
    short_help='The deprecation state to set on the image.',
    detailed_help=_SOURCE_DISK_DETAILED_HELP,
    zone_explanation=_SOURCE_DISK_ZONE_EXPLANATION,
    required=False)


def AddCommonArgs(parser):
  """Add common image creation args."""
  parser.add_argument(
      '--description',
      help=('An optional, textual description for the image being created.'))

  parser.add_argument(
      '--family',
      help=('The family of the image. When creating an instance or disk, '
            'specifying a family will cause the latest non-deprecated image '
            'in the family to be used.')
  )

  parser.add_argument(
      '--licenses',
      type=arg_parsers.ArgList(),
      help='Comma-separated list of URIs to license resources.')


def AddCommonSourcesArgs(parser, sources_group):
  """Add common args for specifying the source for image creation."""
  sources_group.add_argument(
      '--source-uri',
      help="""\
      The full Google Cloud Storage URI where the disk image is stored.
      This file must be a gzip-compressed tarball whose name ends in
      ``.tar.gz''.
      """)

  SOURCE_DISK_ARG.AddArgument(parser, mutex_group=sources_group)


def AddCloningImagesArgs(parser, sources_group):
  """Add args to support image cloning."""
  sources_group.add_argument(
      '--source-image',
      help="""\
      The name of an image to clone. May be used with
      ``--source-image-project'' to clone an image in a different
      project.
      """)

  sources_group.add_argument(
      '--source-image-family',
      help="""\
      The family of the source image. This will cause the latest non-
      deprecated image in the family to be used as the source image.
      May be used with ``--source-image-project'' to refer to an image
      family in a different project.
      """)

  parser.add_argument(
      '--source-image-project',
      help="""\
      The project name of the source image. Must also specify either
      ``--source-image'' or ``--source-image-family'' when using
      this flag.
      """)


def AddGuestOsFeaturesArg(parser, guest_os_features):
  """Add the guest-os-features arg."""
  if not guest_os_features:
    return
  parser.add_argument(
      '--guest-os-features',
      metavar='GUEST_OS_FEATURE',
      type=arg_parsers.ArgList(element_type=lambda x: x.upper(),
                               choices=guest_os_features),
      help=('One or more features supported by the OS in the image.'))


def ValidateSourceArgs(args, sources):
  """Validate that there is one, and only one, source for creating an image."""
  sources_error_message = 'Please specify a source for image creation.'

  # Get the list of source arguments
  source_arg_list = [getattr(args, s.replace('-', '_')) for s in sources]
  # Count the number of source arguments that are specified.
  source_arg_count = sum(bool(a) for a in source_arg_list)

  source_arg_names = ['--' + s for s in sources]

  if source_arg_count > 1:
    raise exceptions.ConflictingArgumentsException(*source_arg_names)

  if source_arg_count < 1:
    raise exceptions.MinimumArgumentException(source_arg_names,
                                              sources_error_message)

