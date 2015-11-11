# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing images."""
import argparse

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import constants
from googlecloudsdk.api_lib.compute import request_helper


class List(base_classes.BaseLister):
  """List Google Compute Engine images."""

  @staticmethod
  def Args(parser):
    base_classes.BaseLister.Args(parser)

    parser.add_argument(
        '--show-deprecated',
        action='store_true',
        help='If provided, deprecated images are shown.')

    if constants.PREVIEW_IMAGE_PROJECTS:
      preview_image_projects = (
          '{0}.'.format(', '.join(constants.PREVIEW_IMAGE_PROJECTS)))
    else:
      preview_image_projects = '(none)'

    preview_images = parser.add_argument(
        '--preview-images',
        action='store_true',
        default=False,
        help='Show images that are in limited preview.')
    preview_images.detailed_help = """\
       Show images that are in limited preview. The preview image projects
       are: {0}
       """.format(preview_image_projects)
    # --show-preview-images for backwards compatibility. --preview-images for
    # consistency with --standard-images.
    parser.add_argument(
        '--show-preview-images',
        dest='preview_images',
        action='store_true',
        help=argparse.SUPPRESS)

    standard_images = parser.add_argument(
        '--standard-images',
        action='store_true',
        default=True,
        help='Show images from well-known image projects.')
    standard_images.detailed_help = """\
       Show images from well-known image projects.  The well known image
       projects are: {0}.
       """.format(', '.join(constants.PUBLIC_IMAGE_PROJECTS))

  @property
  def service(self):
    return self.compute.images

  @property
  def resource_type(self):
    return 'images'

  def GetResources(self, args, errors):
    """Yields images from (potentially) multiple projects."""
    filter_expr = self.GetFilterExpr(args)

    image_projects = [self.project]

    if args.standard_images:
      image_projects.extend(constants.PUBLIC_IMAGE_PROJECTS)

    if args.preview_images:
      image_projects.extend(constants.PREVIEW_IMAGE_PROJECTS)

    requests = []
    for project in image_projects:
      requests.append(
          (self.service,
           'List',
           self.messages.ComputeImagesListRequest(
               filter=filter_expr,
               maxResults=constants.MAX_RESULTS_PER_PAGE,
               project=project)))

    images = request_helper.MakeRequests(
        requests=requests,
        http=self.http,
        batch_url=self.batch_url,
        errors=errors,
        custom_get_requests=None)

    for image in images:
      if not image.deprecated or args.show_deprecated:
        yield image


List.detailed_help = base_classes.GetGlobalListerHelp('images')
