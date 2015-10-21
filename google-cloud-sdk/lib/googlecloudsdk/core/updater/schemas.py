# Copyright 2013 Google Inc. All Rights Reserved.

"""Contains object representations of the JSON data for components."""

import datetime

from googlecloudsdk.core.util import platforms


class Error(Exception):
  """Base exception for the schemas module."""
  pass


class ParseError(Error):
  """An error for when a component snapshot cannot be parsed."""
  pass


class DictionaryParser(object):
  """A helper class to parse elements out of a JSON dictionary."""

  def __init__(self, cls, dictionary):
    """Initializes the parser.

    Args:
      cls: class, The class that is doing the parsing (used for error messages).
      dictionary: dict, The JSON dictionary to parse.
    """
    self.__cls = cls
    self.__dictionary = dictionary
    self.__args = {}

  def Args(self):
    """Gets the dictionary of all parsed arguments.

    Returns:
      dict, The dictionary of field name to value for all parsed arguments.
    """
    return self.__args

  def _Get(self, field, default, required):
    if required and field not in self.__dictionary:
      raise ParseError('Required field [{0}] not found while parsing [{1}]'
                       .format(field, self.__cls))
    return self.__dictionary.get(field, default)

  def Parse(self, field, required=False, default=None, func=None):
    """Parses a single element out of the dictionary.

    Args:
      field: str, The name of the field to parse.
      required: bool, If the field must be present or not (False by default).
      default: str or dict, The value to use if a non-required field is not
        present.
      func: An optional function to call with the value before returning (if
        value is not None).  It takes a single parameter and returns a single
        new value to be used instead.

    Raises:
      ParseError: If a required field is not found or if the field parsed is a
        list.
    """
    value = self._Get(field, default, required)
    if value is not None:
      if isinstance(value, list):
        raise ParseError('Did not expect a list for field [{field}] in '
                         'component [{component}]'.format(
                             field=field, component=self.__cls))
      if func:
        value = func(value)
    self.__args[field] = value

  def ParseList(self, field, required=False, default=None, func=None):
    """Parses a element out of the dictionary that is a list of items.

    Args:
      field: str, The name of the field to parse.
      required: bool, If the field must be present or not (False by default).
      default: str or dict, The value to use if a non-required field is not
        present.
      func: An optional function to call with each value in the parsed list
        before returning (if the list is not None).  It takes a single parameter
        and returns a single new value to be used instead.

    Raises:
      ParseError: If a required field is not found or if the field parsed is
        not a list.
    """
    value = self._Get(field, default, required)
    if value:
      if not isinstance(value, list):
        raise ParseError('Expected a list for field [{0}] in component [{1}]'
                         .format(field, self.__cls))
      if func:
        value = [func(v) for v in value]
    self.__args[field] = value


class DictionaryWriter(object):
  """Class to help writing these objects back out to a dictionary."""

  def __init__(self, obj):
    self.__obj = obj
    self.__dictionary = {}

  @staticmethod
  def AttributeGetter(attrib):
    def Inner(obj):
      if obj is None:
        return None
      return getattr(obj, attrib)
    return Inner

  def Write(self, field, func=None):
    """Writes the given field to the dictionary.

    This gets the value of the attribute named field from self, and writes that
    to the dictionary.  The field is not written if the value is not set.

    Args:
      field: str, The field name.
      func: An optional function to call on the value of the field before
        writing it to the dictionary.
    """
    value = getattr(self.__obj, field)
    if value is None:
      return

    if func:
      value = func(value)
    self.__dictionary[field] = value

  def WriteList(self, field, func=None):
    """Writes the given list field to the dictionary.

    This gets the value of the attribute named field from self, and writes that
    to the dictionary.  The field is not written if the value is not set.

    Args:
      field: str, The field name.
      func: An optional function to call on each value in the list before
        writing it to the dictionary.
    """
    def ListMapper(values):
      return [func(v) for v in values]
    list_func = ListMapper if func else None
    self.Write(field, func=list_func)

  def Dictionary(self):
    return self.__dictionary


class ComponentDetails(object):
  """Encapsulates some general information about the component.

  Attributes:
    display_name: str, The user facing name of the component.
    description: str, A little more details about what the component does.
  """

  @classmethod
  def FromDictionary(cls, dictionary):
    p = DictionaryParser(cls, dictionary)
    p.Parse('display_name', required=True)
    p.Parse('description', required=True)
    return cls(**p.Args())

  def ToDictionary(self):
    w = DictionaryWriter(self)
    w.Write('display_name')
    w.Write('description')
    return w.Dictionary()

  def __init__(self, display_name, description):
    self.display_name = display_name
    self.description = description


class ComponentVersion(object):
  """Version information for the component.

  Attributes:
    build_number: int, The unique, monotonically increasing version of the
      component.
    version_string: str, The user facing version for the component.
  """

  @classmethod
  def FromDictionary(cls, dictionary):
    p = DictionaryParser(cls, dictionary)
    p.Parse('build_number', required=True)
    p.Parse('version_string', required=True)
    return cls(**p.Args())

  def ToDictionary(self):
    w = DictionaryWriter(self)
    w.Write('build_number')
    w.Write('version_string')
    return w.Dictionary()

  def __init__(self, build_number, version_string):
    self.build_number = build_number
    self.version_string = version_string


class ComponentData(object):
  """Information on the data source for the component.

  Attributes:
    type: str, The type of the source of this data (i.e. tar).
    source: str, The hosted location of the component.
    size: int, The size of the component in bytes.
    checksum: str, The hex digest of the archive file.
    contents_checksum: str, The hex digest of the contents of all files in the
      archive.
  """

  @classmethod
  def FromDictionary(cls, dictionary):
    p = DictionaryParser(cls, dictionary)
    p.Parse('type', required=True)
    p.Parse('source', required=True)
    p.Parse('size')
    p.Parse('checksum')
    p.Parse('contents_checksum')
    return cls(**p.Args())

  def ToDictionary(self):
    w = DictionaryWriter(self)
    w.Write('type')
    w.Write('source')
    w.Write('size')
    w.Write('checksum')
    w.Write('contents_checksum')
    return w.Dictionary()

  # pylint: disable=redefined-builtin, params must match JSON names
  def __init__(self, type, source, size, checksum, contents_checksum):
    self.type = type
    self.source = source
    self.size = size
    self.checksum = checksum
    self.contents_checksum = contents_checksum


class ComponentPlatform(object):
  """Information on the applicable platforms for the component.

  Attributes:
    operating_systems: [platforms.OperatingSystem], The operating systems this
      component is valid on.  If [] or None, it is valid on all operating
      systems.
    architectures: [platforms.Architecture], The architectures this component is
      valid on.  If [] or None, it is valid on all architectures.
  """

  @classmethod
  def FromDictionary(cls, dictionary):
    """Parses operating_systems and architectures from a dictionary."""
    p = DictionaryParser(cls, dictionary)
    # error_on_unknown=False here will prevent exception when trying to parse
    # a manifest that has OS or Arch that we don't understand.  If we can't
    # parse it, None will be put in the list.  This will allow the Matches()
    # logic below to know that a filter was actually specified, but will make
    # it impossible for our current OS or Arch to match that filter.  If the
    # filter has multiple values, we could still match even though we can't
    # parse one of the filter values.
    # pylint: disable=g-long-lambda
    p.ParseList('operating_systems',
                func=lambda value: platforms.OperatingSystem.FromId(
                    value, error_on_unknown=False))
    p.ParseList('architectures',
                func=lambda value: platforms.Architecture.FromId(
                    value, error_on_unknown=False))
    return cls(**p.Args())

  def ToDictionary(self):
    w = DictionaryWriter(self)
    w.WriteList('operating_systems',
                func=DictionaryWriter.AttributeGetter('id'))
    w.WriteList('architectures', func=DictionaryWriter.AttributeGetter('id'))
    return w.Dictionary()

  def __init__(self, operating_systems, architectures):
    """Creates a new ComponentPlatform.

    Args:
      operating_systems: list(platforms.OperatingSystem), The OSes this
        component should be installed on.  None indicates all OSes.
      architectures: list(platforms.Architecture), The processor architectures
        this component works on.  None indicates all architectures.
    """
    self.operating_systems = operating_systems
    self.architectures = architectures

  def Matches(self, platform):
    """Determines if the platform for this component matches the environment.

    For both operating system and architecture, it is a match if:
     - No filter is given (regardless of platform value)
     - A filter is given but the value in platform matches one of the values in
       the filter.

    It is a match iff both operating system and architecture match.

    Args:
      platform: platform.Platform, The platform that must be matched.  None will
        always match.

    Returns:
      True if it matches or False if not.
    """
    if not platform:
      my_os, my_arch = None, None
    else:
      my_os, my_arch = platform.operating_system, platform.architecture

    if self.operating_systems:
      # Some OS filter was specified, we must be on an OS that is in the filter.
      if not my_os or my_os not in self.operating_systems:
        return False

    if self.architectures:
      # Some arch filter was specified, we must be on an arch that is in the
      # filter.
      if not my_arch or my_arch not in self.architectures:
        return False

    return True

  def IntersectsWith(self, other):
    """Determines if this platform intersects with the other platform.

    Platforms intersect if they can both potentially be installed on the same
    system.

    Args:
      other: ComponentPlatform, The other component platform to compare against.

    Returns:
      bool, True if there is any intersection, False otherwise.
    """
    return (self.__CollectionsIntersect(self.operating_systems,
                                        other.operating_systems) and
            self.__CollectionsIntersect(self.architectures,
                                        other.architectures))

  def __CollectionsIntersect(self, collection1, collection2):
    """Determines if the two collections intersect.

    The collections intersect if either or both are None or empty, or if they
    contain an intersection of elements.

    Args:
      collection1: [] or None, The first collection.
      collection2: [] or None, The second collection.

    Returns:
      bool, True if there is an intersection, False otherwise.
    """
    # If either is None (valid for all) then they definitely intersect.
    if not collection1 or not collection2:
      return True
    # Both specify values, return if there is at least one intersecting.
    return set(collection1) & set(collection2)


class Component(object):
  """Data type for an entire component.

  Attributes:
    id: str, The unique id for this component.
    details: ComponentDetails, More descriptions of the components.
    version: ComponentVersion, Information about the version of this component.
    is_hidden: bool, True if this should be hidden from the user.
    is_required: bool, True if this component must always be installed.
    is_configuration: bool, True if this should be displayed in the packages
      section of the component manager.
    data: ComponentData, Information about where to get the component from.
    platform: ComponentPlatform, Information about what operating systems and
      architectures the compoonent is valid on.
    dependencies: [str], The other components required by this one.
  """

  @classmethod
  def FromDictionary(cls, dictionary):
    """Converts a dictionary object to an instantiated Component class.

    Args:
      dictionary: The Dictionary to to convert from.

    Returns:
      A Component object initialized from the dictionary object.
    """
    p = DictionaryParser(cls, dictionary)
    p.Parse('id', required=True)
    p.Parse('details', required=True, func=ComponentDetails.FromDictionary)
    p.Parse('version', required=True, func=ComponentVersion.FromDictionary)
    p.Parse('is_hidden', default=False)
    p.Parse('is_required', default=False)
    p.Parse('is_configuration', default=False)
    p.Parse('data', func=ComponentData.FromDictionary)
    p.Parse('platform', default={}, func=ComponentPlatform.FromDictionary)
    p.ParseList('dependencies', default=[])
    return cls(**p.Args())

  def ToDictionary(self):
    """Converts a Component object to a Dictionary object.

    Returns:
      A Dictionary object initialized from self.
    """
    w = DictionaryWriter(self)
    w.Write('id')
    w.Write('details', func=ComponentDetails.ToDictionary)
    w.Write('version', func=ComponentVersion.ToDictionary)
    w.Write('is_hidden')
    w.Write('is_required')
    w.Write('is_configuration')
    w.Write('data', func=ComponentData.ToDictionary)
    w.Write('platform', func=ComponentPlatform.ToDictionary)
    w.WriteList('dependencies')
    return w.Dictionary()

  # pylint: disable=redefined-builtin, params must match JSON names
  def __init__(self, id, details, version, dependencies, data, is_hidden,
               is_required, is_configuration, platform):
    self.id = id
    self.details = details
    self.version = version
    self.is_hidden = is_hidden
    self.is_required = is_required
    self.is_configuration = is_configuration
    self.platform = platform
    self.data = data
    self.dependencies = dependencies


class SchemaVersion(object):
  """Information about the schema version of this snapshot file.

  Attributes:
    version: int, The schema version number.  A different number is considered
      incompatible.
    no_update: bool, True if this installation should not attempted to be
      updated.
    message: str, A message to display to the user if they are updating to this
      new schema version.
    url: str, The URL to grab a fresh Cloud SDK bundle.
  """

  @classmethod
  def FromDictionary(cls, dictionary):
    p = DictionaryParser(cls, dictionary)
    p.Parse('version', required=True)
    p.Parse('no_update', default=False)
    p.Parse('message')
    p.Parse('url', required=True)
    return cls(**p.Args())

  def ToDictionary(self):
    w = DictionaryWriter(self)
    w.Write('version')
    w.Write('no_update')
    w.Write('message')
    w.Write('url')
    return w.Dictionary()

  def __init__(self, version, no_update, message, url):
    self.version = version
    self.no_update = no_update
    self.message = message
    self.url = url


class SDKDefinition(object):
  """Top level object for then entire component snapshot.

  Attributes:
    revision: int, The unique, monotonically increasing version of the snapshot.
    release_notes_url: string, The URL where the latest release notes can be
      downloaded.
    version: str, The version name of this release (i.e. 1.2.3).  This shoudl be
      used only for informative purposes during an udpate (to say what verison
      you are updating to).
    components: [Component], The component definitions.
  """

  REVISION_FORMAT_STRING = '%Y%m%d%H%M%S'

  @classmethod
  def FromDictionary(cls, dictionary):
    p = cls._ParseBase(dictionary)
    p.Parse('revision', required=True)
    p.Parse('release_notes_url')
    p.Parse('version')
    p.ParseList('components', required=True, func=Component.FromDictionary)
    return cls(**p.Args())

  @classmethod
  def SchemaVersion(cls, dictionary):
    return cls._ParseBase(dictionary).Args()['schema_version']

  @classmethod
  def _ParseBase(cls, dictionary):
    p = DictionaryParser(cls, dictionary)
    p.Parse('schema_version', default={'version': 1, 'url': ''},
            func=SchemaVersion.FromDictionary)
    return p

  def ToDictionary(self):
    w = DictionaryWriter(self)
    w.Write('revision')
    w.Write('release_notes_url')
    w.Write('version')
    w.Write('schema_version', func=SchemaVersion.ToDictionary)
    w.WriteList('components', func=Component.ToDictionary)
    return w.Dictionary()

  def __init__(self, revision, schema_version, release_notes_url, version,
               components):
    self.revision = revision
    self.schema_version = schema_version
    self.release_notes_url = release_notes_url
    self.version = version
    self.components = components

  def LastUpdatedString(self):
    try:
      last_updated = datetime.datetime.strptime(
          str(self.revision), SDKDefinition.REVISION_FORMAT_STRING)
      return last_updated.strftime('%Y/%m/%d')
    except ValueError:
      return 'Unknown'

  def Merge(self, sdk_def):
    current_components = dict((c.id, c) for c in self.components)
    for c in sdk_def.components:
      if c.id in current_components:
        self.components.remove(current_components[c.id])
        current_components[c.id] = c
      self.components.append(c)
