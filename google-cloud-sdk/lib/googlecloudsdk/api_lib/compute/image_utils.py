# Copyright 2014 Google Inc. All Rights Reserved.
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
"""Common classes and functions for images."""

from googlecloudsdk.api_lib.compute import constants
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io

FAMILY_PREFIX = 'family/'


class ImageResourceFetcher(object):
  """Mixin class for displaying images."""


class ImageExpander(object):
  """Mixin class for expanding image aliases."""

  def GetMatchingImages(self, image, alias, errors):
    """Yields images from a public image project and the user's project."""
    service = self.compute.images
    requests = [
        (service,
         'List',
         self.messages.ComputeImagesListRequest(
             filter='name eq ^{0}(-.+)*-v.+'.format(alias.name_prefix),
             maxResults=constants.MAX_RESULTS_PER_PAGE,
             project=alias.project)),
        (service,
         'List',
         self.messages.ComputeImagesListRequest(
             filter='name eq ^{0}$'.format(image),
             maxResults=constants.MAX_RESULTS_PER_PAGE,
             project=self.project)),
    ]

    return request_helper.MakeRequests(
        requests=requests,
        http=self.http,
        batch_url=self.batch_url,
        errors=errors,
        custom_get_requests=None)

  def GetImage(self, image_ref):
    """Returns the image resource corresponding to the given reference."""
    errors = []
    requests = []
    name = image_ref.Name()
    if name.startswith(FAMILY_PREFIX):
      requests.append((self.compute.images,
                       'GetFromFamily',
                       self.messages.ComputeImagesGetFromFamilyRequest(
                           family=name[len(FAMILY_PREFIX):],
                           project=image_ref.project)))
    else:
      requests.append((self.compute.images,
                       'Get',
                       self.messages.ComputeImagesGetRequest(
                           image=name,
                           project=image_ref.project)))

    res = list(request_helper.MakeRequests(
        requests=requests,
        http=self.http,
        batch_url=self.batch_url,
        errors=errors,
        custom_get_requests=None))
    if errors:
      utils.RaiseToolException(
          errors,
          error_message='Could not fetch image resource:')
    return res[0]

  def ExpandImageFlag(self, args, return_image_resource=False):
    """Resolves the --image or --image-family flag value.

    If the value of --image is one of the aliases defined in the
    constants module, both the user's project and the public image
    project for the alias are queried. Otherwise, only the user's
    project is queried. If --image is an alias and --image-project is
    provided, only the given project is queried.

    Args:
      args: The command-line flags. The flags accessed are --image,
        --image-family and --image-project.
      return_image_resource: If True, always makes an API call to also
        fetch the image resource.

    Returns:
      A tuple where the first element is the self link of the image. If
        return_image_resource is False, the second element is None, otherwise
        it is the image resource.
    """

    image_ref = None
    warn_alias = True

    if args.image:
      image_ref = self.resources.Parse(
          args.image,
          collection='compute.images',
          resolve=False)
    elif args.image_family is not None:
      image_ref = self.resources.Parse(
          args.image_family,
          collection='compute.images',
          resolve=False)
      if not image_ref.image.startswith(FAMILY_PREFIX):
        image_ref.image = FAMILY_PREFIX + image_ref.image
    else:
      # TODO(b/29177598): Stop using an alias for the default image
      warn_alias = False
      image_ref = self.resources.Parse(
          constants.DEFAULT_IMAGE,
          collection='compute.images',
          resolve=False)

    # If an image project was specified, then assume that image refers
    # to an image in that project.
    if args.image_project:
      image_project_ref = self.resources.Parse(
          args.image_project,
          collection='compute.projects')
      image_ref.project = image_project_ref.Name()
      image_ref.Resolve()
      return (image_ref.SelfLink(),
              self.GetImage(image_ref) if return_image_resource else None)

    image_ref.Resolve()
    alias = constants.IMAGE_ALIASES.get(image_ref.Name())

    # Check for hidden aliases.
    if not alias:
      alias = constants.HIDDEN_IMAGE_ALIASES.get(image_ref.Name())

    # If the image name given is not an alias and no image project was
    # provided, then assume that the image value refers to an image in
    # the user's project.
    if not alias:
      return (image_ref.SelfLink(),
              self.GetImage(image_ref) if return_image_resource else None)

    # At this point, the image is an alias and now we have to find the
    # latest one among the public image project and the user's
    # project.

    if warn_alias:
      WarnAlias(alias)

    errors = []
    images = self.GetMatchingImages(image_ref.Name(), alias, errors)

    user_image = None
    public_images = []

    for image in images:
      if image.deprecated:
        continue
      if '/projects/{0}/'.format(self.project) in image.selfLink:
        user_image = image
      else:
        public_images.append(image)

    if errors or not public_images:
      # This should happen only if there is something wrong with the
      # image project (e.g., operator error) or the global control
      # plane is down.
      utils.RaiseToolException(
          errors,
          'Failed to find image for alias [{0}] in public image project [{1}].'
          .format(image_ref.Name(), alias.project))

    def GetVersion(image):
      """Extracts the "20140718" from an image name like "debian-v20140718"."""
      parts = image.name.rsplit('v', 1)
      if len(parts) != 2:
        log.debug('Skipping image with malformed name [%s].', image.name)
        return None
      return parts[1]

    public_candidate = max(public_images, key=GetVersion)
    if user_image:
      options = [user_image, public_candidate]

      idx = console_io.PromptChoice(
          options=[image.selfLink for image in options],
          default=0,
          message=('Found two possible choices for [--image] value [{0}].'
                   .format(image_ref.Name())))

      res = options[idx]

    else:
      res = public_candidate

    log.debug('Image resolved to [%s].', res.selfLink)
    return (res.selfLink, res if return_image_resource else None)


def HasWindowsLicense(resource, resource_parser):
  """Returns True if the given image or disk has a Windows license."""
  for license_uri in resource.licenses:
    license_ref = resource_parser.Parse(
        license_uri, collection='compute.licenses')
    if license_ref.project == constants.WINDOWS_IMAGE_PROJECT:
      return True
  return False


def AddImageProjectFlag(parser):
  """Adds the --image flag to the given parser."""
  image_project = parser.add_argument(
      '--image-project',
      help='The project against which all image references will be resolved.')
  image_project.detailed_help = """\
      The project against which all image and image family references will be
      resolved. See ``--image'' for more details.
      """


def WarnAlias(alias):
  """WarnAlias outputs a warning telling users to not use the given alias."""
  msg = ('Image aliases are deprecated and will be removed in a future '
         'version. ')
  if alias.family is not None:
    msg += ('Please use --image-family={family} and --image-project={project} '
            'instead.').format(family=alias.family, project=alias.project)
  else:
    msg += 'Please use --image-family and --image-project instead.'

  log.warn(msg)
