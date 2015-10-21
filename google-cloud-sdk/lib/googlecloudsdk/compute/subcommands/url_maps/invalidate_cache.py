# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for cache invalidation."""

from googlecloudsdk.calliope import base

from googlecloudsdk.shared.compute import base_classes


@base.Hidden
@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class InvalidateCache(base_classes.NoOutputAsyncMutator):
  """Invalidate specified cached objects for a URL map."""

  @staticmethod
  def Args(parser):
    path = parser.add_argument(
        '--path',
        required=True,
        help=('Specifies the set of paths within the URL map to '
              'invalidate.'))

    path.detailed_help = """\
        A path specifying which objects to invalidate. PATH must start with
        ``/'' and the only place a ``*'' is allowed is at the end following a
        ``/''. It will be matched against URL paths, which do not include
        scheme, host, or any text after the first ``?'' or ``#'' (and those
        characters are not allowed here). For example, for the URL
        ``https://example.com/whatever/x.html?a=b'', the path is
        ``/whatever/x.html''.

        If PATH ends with ``*'', the preceding string is a prefix, and all URLs
        whose paths begin with it will be invalidated. If PATH doesn't end with
        ``*'', then only URLs with exactly that path will be invalidated.

        Examples:
        - ``'', ``*'', anything that doesn't start with ``/'': error
        - ``/'': just the root URL
        - ``/*'': everything
        - ``/x/y'': ``/x/y'' only (and not ``/x/y/'')
        - ``/x/y/'': ``/x/y/'' only (and not ``/x/y'')
        - ``/x/y/*'': ``/x/y/'' and everything under it
        """

    parser.add_argument('urlmap', help='The name of the URL map.')

  @property
  def method(self):
    return 'InvalidateCache'

  @property
  def service(self):
    return self.compute.urlMaps

  def CreateRequests(self, args):
    """Returns a list of requests necessary for cache invalidations."""
    url_map_ref = self.CreateGlobalReference(
        args.urlmap, resource_type='urlMaps')
    request = self.messages.ComputeUrlMapsInvalidateCacheRequest(
        project=self.project,
        urlMap=url_map_ref.Name(),
        cacheInvalidationRule=self.messages.CacheInvalidationRule(
            path=args.path))

    return [request]


InvalidateCache.detailed_help = {
    'brief': 'Invalidate specified cached objects for a URL map',
    'DESCRIPTION': """
        *{command}* is used to request that Google's caches revalidate the
        resources at a particular URL path or set of URL paths on their next
        access.

        *{command}* may succeed even if no content is cached for some or all
        URLs with the given path.
        """,
}
