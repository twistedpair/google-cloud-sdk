# Copyright 2013 Google Inc. All Rights Reserved.
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
"""Manage parsing resource arguments for the cloud platform.

The Parse() function and Registry.Parse() method are to be used whenever a
Google Cloud Platform API resource is indicated in a command-line argument.
URLs, bare names with hints, and any other acceptable spelling for a resource
will be accepted, and a consistent python object will be returned for use in
code.
"""

import functools
import re
import types
import urllib

from apitools.base.py import base_api

from googlecloudsdk.api_lib.util import resource
from googlecloudsdk.core import apis as core_apis
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.py27 import py27_collections as collections
from googlecloudsdk.third_party.py27 import py27_copy as copy

import uritemplate

_COLLECTION_SUB_RE = r'[a-zA-Z_]+(?:\.[a-zA-Z0-9_]+)+'

_COLLECTIONPATH_RE = re.compile(
    r'(?:(?P<collection>{collection})::)?(?P<path>.+)'.format(
        collection=_COLLECTION_SUB_RE))
# The first two wildcards in this are the API and the API's version. The rest
# are parameters into a specific collection in that API/version.
_URL_RE = re.compile(r'(https?://[^/]+/[^/]+/[^/]+/)(.+)')
_METHOD_ID_RE = re.compile(r'(?P<collection>{collection})\.get'.format(
    collection=_COLLECTION_SUB_RE))
_GCS_URL_RE = re.compile('^gs://([^/]*)(?:/(.*))?$')
_GCS_URL = 'https://www.googleapis.com/storage/v1/'
_GCS_ALT_URL = 'https://storage.googleapis.com/'


class Error(Exception):
  """Exceptions for this module."""


class _ResourceWithoutGetException(Error):
  """Exception for resources with no Get method."""


class BadResolverException(Error):
  """Exception to signal that a resource has no Get method."""

  def __init__(self, param):
    super(BadResolverException, self).__init__(
        'bad resolver for [{param}]'.format(param=param))


class AmbiguousAPIException(Error):
  """Exception for when two APIs try to define a resource."""

  def __init__(self, collection, base_urls):
    super(AmbiguousAPIException, self).__init__(
        'collection [{collection}] defined in multiple APIs: {apis}'.format(
            collection=collection,
            apis=repr(base_urls)))


class AmbiguousResourcePath(Error):
  """Exception for when API path maps to two different resources."""

  def __init__(self, parser1, parser2):
    super(AmbiguousResourcePath, self).__init__(
        'There already exists parser {0} for same path, '
        'can not register another one {1}'.format(parser1, parser2))


class UserError(exceptions.Error, Error):
  """Exceptions that are caused by user input."""


class InvalidResourceException(UserError):
  """A collection-path that was given could not be parsed."""

  def __init__(self, line):
    super(InvalidResourceException, self).__init__(
        'could not parse resource: [{line}]'.format(line=line))


class WrongResourceCollectionException(UserError):
  """A command line that was given had the wrong collection."""

  def __init__(self, expected, got, path):
    super(WrongResourceCollectionException, self).__init__(
        'wrong collection: expected [{expected}], got [{got}], for '
        'path [{path}]'.format(
            expected=expected, got=got, path=path))


class WrongFieldNumberException(UserError):
  """A command line that was given had too many fields."""

  def __init__(self, path, ordered_params):
    possibilities = [
        '/'.join([p.upper() for p in ordered_params[1:]]),
        '/'.join([''] + [p.upper() for p in ordered_params]),
    ]

    if len(ordered_params) > 2:
      possibilities.insert(0, ordered_params[-1].upper())

    bits = ', '.join(possibilities)

    msg = ('wrong number of fields: [{got}] does not match any of'
           ' {bits}').format(got=path, bits=bits)
    super(WrongFieldNumberException, self).__init__(msg)


class UnknownFieldException(UserError):
  """A command line that was given did not specify a field."""

  def __init__(self, collection_path, expected):
    super(UnknownFieldException, self).__init__(
        'unknown field [{expected}] in [{path}]'.format(
            expected=expected, path=collection_path))


class UnknownCollectionException(UserError):
  """A command line that was given did not specify a collection."""

  def __init__(self, line):
    super(UnknownCollectionException, self).__init__(
        'unknown collection for [{line}]'.format(line=line))


class InvalidCollectionException(UserError):
  """A command line that was given did not specify a collection."""

  def __init__(self, collection):
    super(InvalidCollectionException, self).__init__(
        'unknown collection [{collection}]'.format(collection=collection))


class _ResourceParser(object):
  """Class that turns command-line arguments into a cloud resource message."""

  def __init__(self, params_defaults_func, collection_info):
    """Create a _ResourceParser for a given collection.

    Args:
      params_defaults_func: func(param)->value.
      collection_info: resource.CollectionInfo, description for collection.
    """
    self.params_defaults_func = params_defaults_func
    self.collection_info = collection_info

  def ParseCollectionPath(self, collection_path, kwargs, resolve,
                          base_url=None):
    """Given a command line and some keyword args, get the resource.

    Args:
      collection_path: str, The human-typed collection-path from the command
          line. Can be None to indicate all params should be taken from kwargs.
      kwargs: {str:(str or func()->str)}, flags (available from context) or
          resolvers that can help parse this resource. If the fields in
          collection-path do not provide all the necessary information,
          kwargs will be searched for what remains.
      resolve: bool, If True, call the resource's .Resolve() method before
          returning, ensuring that all of the resource parameters are defined.
          If False, don't call them, under the assumption that it will be called
          later.
      base_url: use this base url (endpoint) for the resource, if not provided
          default corresponding api version base url will be used.

    Returns:
      protorpc.messages.Message, The object containing info about this resource.

    Raises:
      InvalidResourceException: If the provided collection-path is malformed.
      WrongResourceCollectionException: If the collection-path specified the
          wrong collection.
      WrongFieldNumberException: If the collection-path's path provided too many
          fields.
      UnknownFieldException: If the collection-path's path did not provide
          enough fields.
    """
    if collection_path is not None:
      fields = self._GetFieldsForKnownCollection(collection_path)
    else:
      fields = [None] * len(self.collection_info.params)

    # Build up the resource params from kwargs or the fields in the
    # collection-path.
    request = self.collection_info.request_type()
    for param, field in zip(self.collection_info.params, fields):
      setattr(request, param, field)

    ref = Resource(
        self.collection_info.full_name, self.collection_info.path, request,
        self.collection_info.params, kwargs,
        collection_path, base_url or self.collection_info.base_url,
        self.params_defaults_func)

    if resolve:
      ref.Resolve()

    return ref

  def _GetFieldsForKnownCollection(self, collection_path):
    """Get the ordered fields for the provided collection-path.

    Args:
      collection_path: str, The not-None string provided on the command line.

    Returns:
      [str], The ordered list of URL params corresponding to this parser's
      resource type.

    Raises:
      InvalidResourceException: If the provided collection-path is malformed.
      WrongResourceCollectionException: If the collection-path specified the
          wrong collection.
      WrongFieldNumberException: If the collection-path's path provided too many
          fields.
      UnknownFieldException: If the collection-path's path did not provide
          enough fields.
    """

    match = _COLLECTIONPATH_RE.match(collection_path)
    if not match:
      # Right now it is impossible for this exception to be raised: the
      # regular expression matches all strings. But we will leave it in
      # in case that ever changes.
      raise InvalidResourceException(collection_path)
    collection, path = match.groups()

    if collection and collection != self.collection_info.full_name:
      raise WrongResourceCollectionException(
          expected=self.collection_info.full_name,
          got=collection, path=collection_path)

    # collection-paths that begin with a slash must have an entry for all
    # ordered params, especially including the project.
    has_project = path.startswith('/')

    # Pending b/17727265, path might contain multiple items after being split
    # on a '/'.
    fields = path.split('/')

    if has_project:
      # first token must be empty, but we already recorded the fact that the
      # next token must be the project
      fields = fields[1:]

    total_param_count = len(self.collection_info.params)

    if has_project and total_param_count != len(fields):
      raise WrongFieldNumberException(
          path=path, ordered_params=self.collection_info.params)

    # Check if there were too many fields provided.
    if len(fields) > total_param_count:
      raise WrongFieldNumberException(
          path=path, ordered_params=self.collection_info.params)

    # If the project is not included, we can either have only one or all-but-one
    # token. So, just simple names or everything that isn't the project.
    if not has_project and len(fields) not in [1, total_param_count - 1]:
      raise WrongFieldNumberException(
          path=path, ordered_params=self.collection_info.params)

    num_missing = total_param_count - len(fields)
    # pad the beginning with Nones so we don't have to count backwards.
    fields = [None] * num_missing + fields

    # Did the user enter a literal empty argument at any stage?
    if '' in fields:
      raise WrongFieldNumberException(
          path=path, ordered_params=self.collection_info.params)

    return fields

  def __str__(self):
    path_str = ''
    for param in self.collection_info.params:
      path_str = '[{path}]/{param}'.format(path=path_str, param=param)
    return '[{collection}::]{path}'.format(
        collection=self.collection_info.full_name, path=path_str)


class Resource(object):
  """Information about a Cloud resource."""

  def __init__(self, collection, relative_path, request,
               ordered_params, resolvers,
               collection_path, endpoint_url, param_defaults):
    """Create a Resource object that may be partially resolved.

    To allow resolving of unknown params to happen after parse-time, the
    param resolution code is in this class rather than the _ResourceParser
    class.

    Args:
      collection: str, The collection name for this resource.
      relative_path: str, relative path uri template.
      request: protorpc.messages.Message (not imported) subclass, An instance
          of a request that can be used to fetch the actual entity in the
          collection.
      ordered_params: [str], The list of parameters that define this resource.
      resolvers: {str:(str or func()->str)}, The resolution functions that can
          be used to fill in values that were not specified in the command line.
      collection_path: str, The original command-line argument used to create
          this Resource.
      endpoint_url: str, service endpoint url for this resource.
      param_defaults: func(param) -> default value for given parameter
          in ordered_params.
    """
    self.__collection = collection
    self._relative_path = relative_path
    self.__request = request
    self.__name = None
    self.__self_link = None
    self.__ordered_params = ordered_params
    self.__resolvers = resolvers
    self.__collection_path = collection_path
    self._endpoint_url = endpoint_url
    self._param_defaults = param_defaults
    for param in ordered_params:
      setattr(self, param, getattr(request, param))

  def Collection(self):
    return self.__collection

  def Name(self):
    self.Resolve()
    return self.__name

  def SelfLink(self):
    self.Resolve()
    return self.__self_link

  def WeakSelfLink(self):
    """Returns a self link containing '*'s for unset parameters."""
    self.WeakResolve()
    return self.__self_link

  def Request(self):
    for param in self.__ordered_params:
      setattr(self.__request, param, getattr(self, param))
    return self.__request

  def Resolve(self):
    """Resolve unknown parameters for this resource.

    Raises:
      UnknownFieldException: If, after resolving, one of the fields is still
          unknown.
    """
    self.WeakResolve()
    for param in self.__ordered_params:
      if not getattr(self, param, None):
        raise UnknownFieldException(self.__collection_path, param)

  def WeakResolve(self):
    """Attempts to resolve unknown parameters for this resource.

       Unknown parameters are left as None.
    """
    for param in self.__ordered_params:
      if getattr(self, param, None):
        continue

      # First try the resolvers given to this resource explicitly.
      resolver = self.__resolvers.get(param)
      if resolver:
        if callable(resolver):
          setattr(self, param, resolver())
        else:
          setattr(self, param, resolver)
        continue

      # Then try the registered defaults.
      try:
        setattr(self, param, self._param_defaults(param))
      except properties.RequiredPropertyError:
        # If property lookup fails, that's ok.  Just don't resolve anything.
        pass

    effective_params = dict(
        [(k, getattr(self, k) or '*') for k in self.__ordered_params])

    self.__self_link = '%s%s' % (
        self._endpoint_url,
        uritemplate.expand(self._relative_path, effective_params))

    if (self.Collection().startswith('compute.') or
        self.Collection().startswith('clouduseraccounts.') or
        self.Collection().startswith('storage.')):
      # TODO(user): Unquote URLs for compute, clouduseraccounts, and
      # storage pending b/15425944.
      self.__self_link = urllib.unquote(self.__self_link)

    if self.__ordered_params:
      # The last param is defined to be the resource's "name", and is the only
      # part of the resource that cannot be inferred by a resolver or other
      # context, and MUST be provided in the argument.
      self.__name = getattr(self, self.__ordered_params[-1])

  def __str__(self):
    return self.SelfLink()
    # TODO(user): Possibly change what is returned, here.
    # path = '/'.join([getattr(self, param) for param in self.__ordered_params])
    # return '{collection}::{path}'.format(
    #     collection=self.__collection, path=path)

  def __eq__(self, other):
    if isinstance(other, Resource):
      return self.SelfLink() == other.SelfLink()
    return False


def _CopyNestedDictSpine(maybe_dictionary):
  if type(maybe_dictionary) is types.DictType:
    result = {}
    for key, val in maybe_dictionary.iteritems():
      result[key] = _CopyNestedDictSpine(val)
    return result
  else:
    return maybe_dictionary


def _APINameAndVersionFromURL(url):
  """Get the API name and version from a resource url.

  Args:
    url: str, The resource (possibly overriden) endpoint url.

  Returns:
    (str, str): The API name. and version
  """
  default_enpoint_url = core_apis.GetDefaultEndpointUrl(url)
  return core_apis.SplitDefaultEndpointUrl(default_enpoint_url)


def _APINameFromCollection(collection):
  """Get the API name from a collection name like 'api.parents.children'.

  Args:
    collection: str, The collection name.

  Returns:
    str: The API name.
  """
  return collection.split('.')[0]


class Registry(object):
  """Keep a list of all the resource collections and their parsing functions.

  Attributes:
    parsers_by_collection: {str: {str: {str: _ResourceParser}}}, All the
        resource parsers indexed by their api name, api version
        and collection name.
    parsers_by_url: Deeply-nested dict. The first key is the API's URL root,
        and each key after that is one of the remaining tokens which can be
        either a constant or a parameter name. At the end, a key of None
        indicates the value is a _ResourceParser.
    default_param_funcs: Triply-nested dict. The first key is the param name,
        the second is the api name, and the third is the collection name. The
        value is a function that can be called to find values for params that
        aren't specified already. If the collection key is None, it matches
        all collections.
    registered_apis: {str: set}, All the api versions that have been registered.
        For instance, {'compute': {'v1', 'beta', 'alpha'}}.
  """

  def __init__(self, parsers_by_collection=None, parsers_by_url=None,
               default_param_funcs=None, registered_apis=None):
    self.parsers_by_collection = parsers_by_collection or {}
    self.parsers_by_url = parsers_by_url or {}
    self.default_param_funcs = default_param_funcs or {}
    self.registered_apis = registered_apis or collections.defaultdict(set)

  def _Clone(self):
    return Registry(
        parsers_by_collection=_CopyNestedDictSpine(self.parsers_by_collection),
        parsers_by_url=_CopyNestedDictSpine(self.parsers_by_url),
        default_param_funcs=_CopyNestedDictSpine(self.default_param_funcs),
        registered_apis=copy.deepcopy(self.registered_apis))

  def _RegisterAPIByName(self, api_name, api_version=None):
    """Register the given API if it has not been registered already.

    Args:
      api_name: str, The API name.
      api_version: if available, the version of the API being registered.
    Returns:
      api version which was registered.
    """
    registered_versions = self.registered_apis.get(api_name, set([]))
    if not api_version:
      if len(registered_versions) == 1:
        api_version = next(iter(registered_versions))
      else:
        api_version = core_apis.GetDefaultVersion(api_name)
    if api_version and api_version in registered_versions:
      # This API version has been registered.
      return api_version

    api_client = core_apis.GetClientInstance(api_name, api_version,
                                             no_http=True)
    self._RegisterAPI(api_name, api_version, api_client)
    return api_version

  def _RegisterAPI(self, api_name, api_version, api_client):
    """Register a generated API with this registry.

    Args:
      api_name: str, The API name under which register resources of api_client.
      api_version: str, Use this api version to registerr resources.
      api_client: base_api.BaseApiClient, The client for a Google Cloud API.
    """
    for service in _GetApiServices(api_client):
      try:
        collection = _GetServiceCollection(
            api_name, api_version, api_client, service)
      except _ResourceWithoutGetException:
        pass
      else:
        self._RegisterCollection(collection)
    self.registered_apis[api_name].add(api_version)

  def _RegisterCollection(self, collection_info):
    """Registers given collection with registry.

    Args:
      collection_info: CollectionInfo, description of resource collection.
    Raises:
      AmbiguousAPIException: If the API defines a collection that has already
          been added.
      AmbiguousResourcePath: If api uses same path for multiple resources.
    """
    api_name = collection_info.api_name
    api_version = collection_info.api_version
    parser = _ResourceParser(
        functools.partial(self.GetParamDefault, api_name, collection_info.name),
        collection_info)

    collection_parsers = (self.parsers_by_collection.setdefault(api_name, {})
                          .setdefault(api_version, {}))
    existing_parser = collection_parsers.get(collection_info.full_name)
    if existing_parser is not None:
      raise AmbiguousAPIException(collection_info.full_name,
                                  [collection_info.base_url,
                                   existing_parser.collection_info.base_url])
    collection_parsers[collection_info.full_name] = parser

    tokens = [api_name, api_version] + collection_info.path.split('/')

    # Build up a search tree to match URLs against URL templates.
    # The tree will branch at each URL segment, where the first segment
    # is the API's base url, and each subsequent segment is a token in
    # the instance's get method's relative path. At the leaf, a key of
    # None indicates that the URL can finish here, and provides the parser
    # for this resource.
    cur_level = self.parsers_by_url
    while tokens:
      token = tokens.pop(0)
      if token not in cur_level:
        cur_level[token] = {}
      cur_level = cur_level[token]
    if None in cur_level:
      raise AmbiguousResourcePath(cur_level[None], parser)

    cur_level[None] = parser

  def _SwitchAPI(self, api):
    """Replace the registration of one version of an API with another.

    This method will remove references to the previous version of the provided
    API from self.parsers_by_collection, but leave self.parsers_by_url intact.

    Args:
      api: base_api.BaseApiClient, The client for a Google Cloud API.
    """
    api_name, api_version, _ = _APINameAndVersionFromURL(api.url)
    if api_version is None:
      # For some apis url does not contain api version, and
      # is part of collection path.
      api_version = api._VERSION  # pylint:disable=protected-access
    if api_name in self.parsers_by_collection:
      del self.parsers_by_collection[api_name]
    if api_name in self.parsers_by_url:
      del self.parsers_by_url[api_name]

    self.registered_apis[api_name].clear()

    self._RegisterAPI(api_name, api_version, api)

  def CloneAndSwitchAPIs(self, *apis):
    """Clone registry and replace any given apis."""
    reg = self._Clone()
    for _, version_collections in reg.parsers_by_collection.iteritems():
      for _, collection_parsers in version_collections.iteritems():
        for _, parser in collection_parsers.iteritems():
          parser.param_defaults_func = functools.partial(
              reg.GetParamDefault,
              parser.collection_info.api_name,
              parser.collection_info.name)

    def _UpdateParser(dict_or_parser):
      if type(dict_or_parser) is types.DictType:
        for _, val in dict_or_parser.iteritems():
          _UpdateParser(val)
      else:
        dict_or_parser.param_default_func = functools.partial(
            reg.GetParamDefault,
            dict_or_parser.collection_info.api_name,
            dict_or_parser.collection_info.name)
    _UpdateParser(reg.parsers_by_url)
    for api in apis:
      reg._SwitchAPI(api)  # pylint:disable=protected-access
    return reg

  def SetParamDefault(self, api, collection, param, resolver):
    """Provide a function that will be used to fill in missing values.

    Args:
      api: str, The name of the API that func will apply to.
      collection: str, The name of the collection that func will apploy to. Can
          be None to indicate all collections within the API.
      param: str, The param that can be satisfied with func, if no value is
          provided by the path.
      resolver: str or func()->str, A function that returns a string or raises
          an exception that tells the user how to fix the problem, or the value
          itself.

    Raises:
      ValueError: If api or param is None.
    """
    if not api:
      raise ValueError('provided api cannot be None')
    if not param:
      raise ValueError('provided param cannot be None')
    if param not in self.default_param_funcs:
      self.default_param_funcs[param] = {}
    api_collection_funcs = self.default_param_funcs[param]
    if api not in api_collection_funcs:
      api_collection_funcs[api] = {}
    collection_funcs = api_collection_funcs[api]
    collection_funcs[collection] = resolver

  def GetParamDefault(self, api, collection, param):
    """Return the default value for the specified parameter.

    Args:
      api: str, The name of the API that param is part of.
      collection: str, The name of the collection to query. Can be None to
          indicate all collections within the API.
      param: str, The param to return a default for.

    Raises:
      ValueError: If api or param is None.

    Returns:
      The default value for a parameter or None if there is no default.
    """
    if not api:
      raise ValueError('provided api cannot be None')
    if not param:
      raise ValueError('provided param cannot be None')
    api_collection_funcs = self.default_param_funcs.get(param)
    if not api_collection_funcs:
      return None
    collection_funcs = api_collection_funcs.get(api)
    if not collection_funcs:
      return None
    if collection in collection_funcs:
      resolver = collection_funcs[collection]
    elif None in collection_funcs:
      resolver = collection_funcs[None]
    else:
      return None
    return resolver() if callable(resolver) else resolver

  def ParseCollectionPath(self, collection, collection_path, kwargs,
                          resolve=True):
    """Parse a collection path into a Resource.

    Args:
      collection: str, the name/id for the resource from commandline argument.
      collection_path: str, The human-typed collection-path from the command
          line. Can be None to indicate all params should be taken from kwargs.
      kwargs: {str:(str or func()->str)}, flags (available from context) or
          resolvers that can help parse this resource. If the fields in
          collection-path do not provide all the necessary information,
          kwargs will be searched for what remains.
      resolve: bool, If True, call the resource's .Resolve() method before
          returning, ensuring that all of the resource parameters are defined.
          If False, don't call them, under the assumption that it will be called
          later.
    Returns:
      protorpc.messages.Message, The object containing info about this resource.

    Raises:
      InvalidCollectionException: If the provided collection-path is malformed.

    """
    # Register relevant API if necessary and possible
    api_name = _APINameFromCollection(collection)
    api_version = self._RegisterAPIByName(api_name)

    parser = (self.parsers_by_collection
              .get(api_name, {}).get(api_version, {}).get(collection, None))
    if parser is None:
      raise InvalidCollectionException(collection)

    # Use current override endpoint for this resource name.
    endpoint_override_property = getattr(
        properties.VALUES.api_endpoint_overrides, api_name, None)
    base_url = None
    if endpoint_override_property is not None:
      base_url = endpoint_override_property.Get()
    return parser.ParseCollectionPath(
        collection_path, kwargs, resolve, base_url)

  def ParseURL(self, url):
    """Parse a URL into a Resource.

    This method does not yet handle "api.google.com" in place of
    "www.googleapis.com/api/version".

    Searches self.parsers_by_url to find a _ResourceParser. The parsers_by_url
    attribute is a deeply nested dictionary, where each key corresponds to
    a URL segment. The first segment is an API's base URL (eg.
    "https://www.googleapis.com/compute/v1/"), and after that it's each
    remaining token in the URL, split on '/'. Then a path down the tree is
    followed, keyed by the extracted pieces of the provided URL. If the key in
    the tree is a literal string, like "project" in .../project/{project}/...,
    the token from the URL must match exactly. If it's a parameter, like
    "{project}", then any token can match it, and that token is stored in a
    dict of params to with the associated key ("project" in this case). If there
    are no URL tokens left, and one of the keys at the current level is None,
    the None points to a _ResourceParser that can turn the collected
    params into a Resource.

    Args:
      url: str, The URL of the resource.

    Returns:
      Resource, The resource indicated by the provided URL.

    Raises:
      InvalidResourceException: If the provided URL could not be turned into
          a cloud resource.
    """
    match = _URL_RE.match(url)
    if not match:
      raise InvalidResourceException('unknown API host: [{0}]'.format(url))

    api_name, api_version, resource_path = _APINameAndVersionFromURL(url)
    tokens = [api_name, api_version] + resource_path.split('/')
    endpoint = url[:-len(resource_path)]
    params = {}

    # Register relevant API if necessary and possible
    try:
      self._RegisterAPIByName(api_name, api_version=api_version)
    except (core_apis.UnknownAPIError, core_apis.UnknownVersionError):
      # The caught InvalidResourceException has a less detailed message.
      raise InvalidResourceException(url)

    cur_level = self.parsers_by_url
    for i, token in enumerate(tokens):
      if token in cur_level:
        # If the literal token is already here, follow it down.
        cur_level = cur_level[token]
      elif len(cur_level) == 1:
        # If the literal token is not here, and there is only one key, it must
        # be a parameter that will be added to the params dict.
        param = cur_level.keys()[0]
        if not param.startswith('{') or not param.endswith('}'):
          raise InvalidResourceException(url)

        next_level = cur_level[param]
        if len(next_level) == 1 and None in next_level:
          # This is the last parameter so we can combine the remaining tokens.
          token = '/'.join(tokens[i:])
          params[param[1:-1]] = urllib.unquote(token)
          cur_level = next_level
          break

        # Clean up the provided value
        params[param[1:-1]] = urllib.unquote(token)

        # Keep digging down.
        cur_level = next_level
      else:
        # If the token we want isn't here, and there isn't a single parameter,
        # the URL we've been given doesn't match anything we know about.
        raise InvalidResourceException(url)
      # Note: This will break if there are multiple parameters that could be
      # specified at a given level. As far as I can tell, this never happens and
      # never should happen. But in theory it's possible so we'll keep an eye
      # out for this issue.

      # No more tokens, so look for a parser.
    if None not in cur_level:
      raise InvalidResourceException(url)
    parser = cur_level[None]
    return parser.ParseCollectionPath(
        None, params, resolve=True, base_url=endpoint)

  def ParseStorageURL(self, url):
    """Parse gs://bucket/object_path into storage.v1 api resource."""
    match = _GCS_URL_RE.match(url)
    if not match:
      raise InvalidResourceException('Invalid storage url: [{0}]'.format(url))
    if match.group(2):
      return self.ParseCollectionPath(
          collection='storage.objects',
          collection_path=None,
          kwargs={'bucket': match.group(1), 'object': match.group(2)})

    return self.ParseCollectionPath(
        collection='storage.buckets',
        collection_path=None,
        kwargs={'bucket': match.group(1)})

  def Parse(self, line, params=None, collection=None,
            enforce_collection=True, resolve=True):
    """Parse a Cloud resource from a command line.

    Args:
      line: str, The argument provided on the command line.
      params: {str:(str or func()->str)}, flags (available from context) or
        resolvers that can help parse this resource. If the fields in
        collection-path do not provide all the necessary information, params
        will be searched for what remains.
      collection: str, The resource's collection, or None if it should be
        inferred from the line.
      enforce_collection: bool, fail unless parsed resource is of this
        specified collection, this is applicable only if line is URL.
      resolve: bool, If True, call the resource's .Resolve() method before
          returning, ensuring that all of the resource parameters are defined.
          If False, don't call them, under the assumption that it will be called
          later.

    Returns:
      A resource object.

    Raises:
      InvalidResourceException: If the line is invalid.
      UnknownCollectionException: If no collection is provided or can be
          inferred.
      WrongResourceCollectionException: If the provided URL points into a
          collection other than the one specified.
    """
    if line:
      if line.startswith('https://') or line.startswith('http://'):
        try:
          ref = self.ParseURL(line)
        except InvalidResourceException:
          # TODO(b/29573201): Make sure ParseURL handles this logic by default.
          bucket = None
          if line.startswith(_GCS_URL):
            bucket_prefix, bucket, object_prefix, objectpath = (
                line[len(_GCS_URL):].split('/', 3))
            if (bucket_prefix, object_prefix) != ('b', 'o'):
              raise
          elif line.startswith(_GCS_ALT_URL):
            line = line[len(_GCS_ALT_URL):]
            if '/' in line:
              bucket, objectpath = line.split('/', 1)
            else:
              return self.ParseCollectionPath(
                  collection='storage.buckets',
                  collection_path=None,
                  kwargs={'bucket': line})
          if bucket is not None:
            return self.ParseCollectionPath(
                collection='storage.objects',
                collection_path=None,
                kwargs={'bucket': bucket, 'object': objectpath})
          raise
        # TODO(user): consider not doing this here.
        # Validation of the argument is a distict concern.
        if (enforce_collection and collection and
            ref.Collection() != collection):
          raise WrongResourceCollectionException(
              expected=collection,
              got=ref.Collection(),
              path=ref.SelfLink())
        return ref
      elif line.startswith('gs://'):
        return self.ParseStorageURL(line)

    if not collection:
      match = _COLLECTIONPATH_RE.match(line)
      if not match:
        raise InvalidResourceException(line)
      collection, unused_path = match.groups()
      if not collection:
        raise UnknownCollectionException(line)
    # Special handle storage collection paths.
    if collection == 'storage.objects':
      p = dict(params or {})
      if 'bucket' not in p or 'object' not in p:
        if '/' not in line:
          raise InvalidResourceException(
              'Expected bucket/object in "{0}"'.format(line))
        p['bucket'], p['object'] = line.split('/', 1)

      return self.ParseCollectionPath(
          collection='storage.objects',
          collection_path=None,
          kwargs=p)

    return self.ParseCollectionPath(collection, line, params or {}, resolve)

  def Create(self, collection, **params):
    """Create a Resource from known collection and params.

    Args:
      collection: str, The name of the collection the resource belongs to.
      **params: {str:str}, The values for each of the resource params.

    Returns:
      Resource, The constructed resource.
    """
    return self.Parse(None, collection=collection, params=params)


# TODO(user): Deglobalize this object, force gcloud to manage it on its own.
REGISTRY = Registry()


def _ClearAPIs():
  """For testing, clear out any APIs to start with a clean slate.

  """
  global REGISTRY
  REGISTRY = Registry()


def _GetApiServices(api_client):
  return [potential_service
          for potential_service in api_client.__dict__.itervalues()
          if isinstance(potential_service, base_api.BaseApiService)]


def _GetServiceCollection(api_name, api_version, api_client, service):
  """Extract collection info from given service for an API.

  Args:
    api_name: str, name of api to register under.
    api_version: str, Use this api version to registerr resources.
    api_client: base_api.BaseApiClient, The client for a Google Cloud API.
    service: base_api.BaseApiService, the service with collection.

  Returns:
    CollectionInfo for this service.
  Raises:
    _ResourceWithoutGetException: If given service does not have Get method.
  """
  try:
    method_config = service.GetMethodConfig('Get')
  except KeyError:
    raise _ResourceWithoutGetException()
  match = _METHOD_ID_RE.match(method_config.method_id)
  if not match:
    raise _ResourceWithoutGetException()

  collection = match.group('collection')
  collection = collection.split('.', 1)[1]  # drop api name
  request_type = getattr(api_client.MESSAGES_MODULE,
                         method_config.request_type_name)

  url = api_client.BASE_URL + method_config.relative_path
  _, _, path = _APINameAndVersionFromURL(url)
  base_url = url[:-len(path)]

  return resource.CollectionInfo(
      api_name, api_version,
      base_url, collection, request_type,
      path, method_config.ordered_params)
