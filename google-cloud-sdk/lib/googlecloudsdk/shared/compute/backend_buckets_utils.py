# Copyright 2015 Google Inc. All Rights Reserved.
"""Code that's shared between multiple backend-buckets subcommands."""


def AddUpdatableArgs(parser):
  """Adds top-level backend bucket arguments that can be updated."""
  parser.add_argument(
      'name',
      help='The name of the backend bucket.')

  parser.add_argument(
      '--description',
      help='An optional, textual description for the backend bucket.')

  gcs_bucket_name = parser.add_argument(
      '--gcs-bucket-name',
      help=('The name of the GCS Bucket to use.'))
  gcs_bucket_name.detailed_help = """\
      TODO(eriel): Add details here.
      """
