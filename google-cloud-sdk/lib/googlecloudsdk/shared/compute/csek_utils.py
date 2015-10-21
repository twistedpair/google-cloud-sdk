# Copyright 2014 Google Inc. All Rights Reserved.
"""Utility functions for managing customer supplied encryption keys."""

import abc
import base64
import json
import re

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import exceptions as core_exceptions


EXPECTED_RECORD_KEY_KEYS = set(['uri', 'key', 'key-type'])
BASE64_RAW_KEY_LENGTH_IN_CHARS = 44
BASE64_RSA_ENCRYPTED_KEY_LENGTH_IN_CHARS = 344


class InvalidKeyFileException(core_exceptions.Error):
  """There's a problem in a CSEK file."""

  def __init__(self, base_message):
    super(InvalidKeyFileException, self).__init__(
        '{0}'.format(base_message))
    # TODO(jeffvaughan) Update this message to include
    # a lint to friendly documentation.


class BadPatternException(InvalidKeyFileException):
  """A (e.g.) url pattern is bad and why."""

  def __init__(self, pattern_type, pattern):
    self.pattern_type = pattern_type
    self.pattern = pattern
    super(BadPatternException, self).__init__(
        'Invalid value for [{0}] pattern: [{1}]'.format(
            self.pattern_type,
            self.pattern))


class InvalidKeyExceptionNoContext(InvalidKeyFileException):
  """Indicate that a particular key is bad and why."""

  def __init__(self, key, issue):
    self.key = key
    self.issue = issue
    super(InvalidKeyExceptionNoContext, self).__init__(
        'Invalid key, [{0}] : {1}'.format(
            self.key,
            self.issue))


class InvalidKeyException(InvalidKeyFileException):
  """Indicate that a particular key is bad, why, and where."""

  def __init__(self, key, key_id, issue):
    self.key = key
    self.key_id = key_id
    self.issue = issue
    super(InvalidKeyException, self).__init__(
        'Invalid key, [{0}], for [{1}]: {2}'.format(
            self.key,
            self.key_id,
            self.issue))


def ValidateKey(base64_encoded_string, expected_key_length):
  """ValidateKey(s, k) returns None or raises InvalidKeyExceptionNoContext."""

  if expected_key_length < 1:
    raise ValueError('ValidateKey requires expected_key_length > 1.  Got {0}'
                     .format(expected_key_length))

  if len(base64_encoded_string) != expected_key_length:
    raise InvalidKeyExceptionNoContext(
        base64_encoded_string,
        'Key should contain {0} characters (including padding), '
        'but is [{1}] characters long.'.format(
            expected_key_length,
            len(base64_encoded_string)))

  if base64_encoded_string[-1] != '=':
    raise InvalidKeyExceptionNoContext(
        base64_encoded_string,
        'Bad padding.  Keys should end with an \'=\' character.')

  try:
    base64_encoded_string_as_str = base64_encoded_string.encode('ascii')
  except UnicodeDecodeError:
    raise InvalidKeyExceptionNoContext(
        base64_encoded_string,
        'Key contains non-ascii characters.')

  if not re.match(r'^[a-zA-Z0-9+/=]*$', base64_encoded_string_as_str):
    raise InvalidKeyExceptionNoContext(
        base64_encoded_string_as_str,
        'Key contains unexpected characters. Base64 encoded strings '
        'contain only letters (upper or lower case), numbers, '
        'plusses \'+\', slashes \'/\', or equality signs \'=\'.')

  try:
    base64.b64decode(base64_encoded_string_as_str)
  except TypeError as t:
    raise InvalidKeyExceptionNoContext(
        base64_encoded_string,
        'Key is not valid base64: [{0}].'.format(t.message))


class CsekKeyBase(object):
  """A class representing for Csek keys."""

  __metaclass__ = abc.ABCMeta

  def __init__(self, key_material):
    ValidateKey(key_material, expected_key_length=self.GetKeyLength())
    self._key_material = key_material

  @staticmethod
  def MakeKey(key_material, key_type):

    if key_type == 'raw':
      return CsekRawKey(key_material)

    if key_type == 'rsa-encrypted':
      return CsekRsaEncryptedKey(key_material)

    raise BadKeyTypeException(key_type)

  @abc.abstractmethod
  def GetKeyLength(self):
    raise NotImplementedError('GetKeyLength() must be overridden.')

  @abc.abstractmethod
  def ToMessage(self):
    raise NotImplementedError('ToMessage() must be overridden.')

  @property
  def key_material(self):
    return self._key_material


class CsekRawKey(CsekKeyBase):
  """Class representing raw Csek keys."""

  def GetKeyLength(self):
    return BASE64_RAW_KEY_LENGTH_IN_CHARS

  def ToMessage(self, compute_client):
    return compute_client.MESSAGES_MODULE.CustomerEncryptionKey(
        rawKey=str(self.key_material))


class CsekRsaEncryptedKey(CsekKeyBase):
  """Class representing rsa encrypted Csek keys."""

  def GetKeyLength(self):
    return BASE64_RSA_ENCRYPTED_KEY_LENGTH_IN_CHARS

  def ToMessage(self, compute_client):
    return compute_client.MESSAGES_MODULE.CustomerEncryptionKey(
        rsaEncryptedKey=str(self.key_material))


class BadKeyTypeException(InvalidKeyFileException):
  """A key type is bad and why."""

  def __init__(self, key_type):
    self.key_type = key_type
    super(BadKeyTypeException, self).__init__(
        'Invalid key type [{0}].'.format(self.key_type))


class MissingCsekKeyException(exceptions.ToolException):

  def __init__(self, resource):
    super(MissingCsekKeyException, self).__init__(
        'Key required for resource [{0}], but none found.'.format(resource))


def AddCsekKeyArgs(parser, flags_about_creation=True):
  """Adds arguments related to csek keys."""

  csek_key_file = parser.add_argument(
      '--csek-key-file',
      help='Path to a csek key file',
      metavar='FILE')
  csek_key_file.detailed_help = (
      'Path to a csek key file, mapping GCE resources to user managed '
      'keys to be used when creating, mounting, or snapshotting disks. ')
  # TODO(jeffvaughan)
  # Argument - indicates the key file should be read from stdin.'

  if flags_about_creation:
    require_csek_key_create = parser.add_argument(
        '--require-csek-key-create',
        action='store_true',
        default=True,
        help='Create resources protected by csek key.')
    require_csek_key_create.detailed_help = (
        'When invoked with --csek-key-file gcloud will refuse to create '
        'resources not protected by a user managed key in the key file.  This '
        'is intended to prevent incorrect gcloud invocations from accidentally '
        'creating resources with no user managed key.  Disabling the check '
        'allows creation of resources without csek keys.')


class UriPattern(object):
  """A uri-based pattern that maybe be matched against resource objects."""

  def __init__(self, path_as_string):
    if not path_as_string.startswith('http'):
      raise BadPatternException('uri', path_as_string)
    self._path_as_string = path_as_string

  def Matches(self, resource):
    """Tests if its argument matches the pattern."""
    return self._path_as_string == resource.SelfLink()

  def __str__(self):
    return 'Uri Pattern: ' + self._path_as_string


class CsekKeyStore(object):
  """Represents a map from resource patterns to keys."""

  # Members
  # self._state: dictionary from UriPattern to an instance of (a subclass of)
  # CsekKeyBase

  @staticmethod
  def FromFile(fname):
    """FromFile loads a CsekKeyStore from a file.

    Args:
      fname: str, the name of a file intended to contain a well-formed key file

    Returns:
      A MaterKeyStore, if found

    Raises:
      exceptions.BadFileException: there's a problem reading fname
      exceptions.InvalidKeyFileException: the key file failed to parse
        or was otherwise invalid
    """

    with open(fname) as infile:
      content = infile.read()

    return CsekKeyStore(content)

  @staticmethod
  def FromArgs(args):
    """FromFile attempts to load a CsekKeyStore from a command's args.

    Args:
      args: CLI args with a csek_key_file field set

    Returns:
      A CsekKeyStore, if a valid key file name is provided as csek_key_file
      None, if args.csek_key_file is None

    Raises:
      exceptions.BadFileException: there's a problem reading fname
      exceptions.InvalidKeyFileException: the key file failed to parse
        or was otherwise invalid
    """
    assert hasattr(args, 'csek_key_file')

    if args.csek_key_file is None:
      return None

    return CsekKeyStore.FromFile(args.csek_key_file)

  @staticmethod
  def _ParseAndValidate(s):
    """_ParseAndValidate(s) inteprets s as a csek key file.

    Args:
      s: str, an input to parse

    Returns:
      a valid state object

    Raises:
      InvalidKeyFileException: if the input doesn't parse or is not well-formed.
    """

    assert type(s) is str
    state = {}

    try:
      records = json.loads(s)

      if type(records) is not list:
        raise InvalidKeyFileException(
            'Key file\'s top-level element must be a JSON list.')

      for key_record in records:
        if type(key_record) is not dict:
          raise InvalidKeyFileException(
              'Key file records must be JSON objects, but [{0}] found.'.format(
                  json.dumps(key_record)))

        if set(key_record.keys()) != EXPECTED_RECORD_KEY_KEYS:
          raise InvalidKeyFileException(
              'Record [{0}] has incorrect json keys; [{1}] expected'.format(
                  json.dumps(key_record),
                  ','.join(EXPECTED_RECORD_KEY_KEYS)))

        pattern = UriPattern(key_record['uri'])

        try:
          state[pattern] = CsekKeyBase.MakeKey(
              key_material=key_record['key'], key_type=key_record['key-type'])
        except InvalidKeyExceptionNoContext as e:
          raise InvalidKeyException(key=e.key, key_id=pattern, issue=e.issue)

    except ValueError as e:
      raise InvalidKeyFileException(*e.args)

    assert type(state) is dict
    return state

  def __len__(self):
    return len(self.state)

  def LookupKey(self, resource, raise_if_missing=False):
    """Search for the unique key corresponding to a given resource.

    Args:
      resource: the resource to find a key for.
      raise_if_missing: bool, raise an exception if the resource is not found.

    Returns: CsekKeyBase, corresponding to the resource, or None if not found
      and not raise_if_missing.

    Raises:
      InvalidKeyFileException: if there are two records matching the resource.
      MissingCsekKeyException: if raise_if_missing and no key is found
        for the provided resoure.
    """

    assert type(self.state) is dict
    search_state = (None, None)

    for pat, key in self.state.iteritems():
      if pat.Matches(resource):
        # TODO(jeffvaughan) what's the best thing to do if there are multiple
        # matches?
        if search_state[0]:
          raise exceptions.InvalidKeyFileException(
              'Uri patterns [{0}] and [{1}] both match '
              'resource [{2}].  Bailing out.'.format(
                  search_state[0], pat, str(resource)))

        search_state = (pat, key)

    if raise_if_missing and (search_state[1] is None):
      raise MissingCsekKeyException(resource)

    return search_state[1]

  def __init__(self, json_string):
    self.state = CsekKeyStore._ParseAndValidate(json_string)


# Functions below make it easy for clients to operate on values that possibly
# either CsekKeyStores or None or else CsekKeyBases or None.  Fellow functional
# programming geeks: basically we're faking the Maybe monad.
def MaybeToMessage(csek_key_or_none, compute):
  return csek_key_or_none.ToMessage(compute) if csek_key_or_none else None


def MaybeLookupKey(csek_keys_or_none, resource):
  if csek_keys_or_none and resource:
    return csek_keys_or_none.LookupKey(resource)

  return None


def MaybeLookupKeyMessage(csek_keys_or_none, resource, compute_client):
  maybe_key = MaybeLookupKey(csek_keys_or_none, resource)
  return MaybeToMessage(maybe_key, compute_client)


def MaybeLookupKeys(csek_keys_or_none, resources):
  return [MaybeLookupKey(csek_keys_or_none, r) for r in resources]


def MaybeLookupKeyMessages(csek_keys_or_none, resources, compute_client):
  return [MaybeToMessage(k, compute_client) for k in
          MaybeLookupKeys(csek_keys_or_none, resources)]


def MaybeLookupKeysByUri(csek_keys_or_none, parser, uris):
  return MaybeLookupKeys(
      csek_keys_or_none,
      [(parser.Parse(u) if u else None) for u in uris])


def MaybeLookupKeyMessagesByUri(csek_keys_or_none, parser,
                                uris, compute_client):
  return [MaybeToMessage(k, compute_client) for k in
          MaybeLookupKeysByUri(csek_keys_or_none, parser, uris)]

