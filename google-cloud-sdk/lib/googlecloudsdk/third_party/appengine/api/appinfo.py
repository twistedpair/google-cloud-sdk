# Copyright 2007 Google Inc. All Rights Reserved.
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

"""AppInfo tools.

Library for working with AppInfo records in memory, store and load from
configuration files.
"""


# WARNING: This file is externally viewable by our users.  All comments from
# this file will be stripped.  The docstrings will NOT.  Do not put sensitive
# information in docstrings.  If you must communicate internal information in
# this source file, please place them in comments only.

# Parts of the code in this file are duplicated in
# //java/com/google/apphosting/admin/legacy/...
# This is part of an ongoing effort to replace the deployment API.
# Until we can delete this code, please check to see if your changes need
# to be reflected in the java code. For questions, talk to clouser@ or



import logging
import os
import re
import string
import sys
import wsgiref.util

# pylint: disable=g-import-not-at-top
if os.environ.get('APPENGINE_RUNTIME') == 'python27':
  from google.appengine.api import validation
  from google.appengine.api import yaml_builder
  from google.appengine.api import yaml_listener
  from google.appengine.api import yaml_object
else:
  # This case covers both Python 2.5 and unittests, which are 2.5 only.
  from googlecloudsdk.third_party.appengine.api import validation
  from googlecloudsdk.third_party.appengine.api import yaml_builder
  from googlecloudsdk.third_party.appengine.api import yaml_listener
  from googlecloudsdk.third_party.appengine.api import yaml_object

from googlecloudsdk.third_party.appengine.api import appinfo_errors
from googlecloudsdk.third_party.appengine.api import backendinfo

# pylint: enable=g-import-not-at-top

# Regular expression for matching url, file, url root regular expressions.
# url_root is identical to url except it additionally imposes not ending with *.
# TODO(user): url_root should generally allow a url but not a regex or glob.
_URL_REGEX = r'(?!\^)/.*|\..*|(\(.).*(?!\$).'
_FILES_REGEX = r'.+'
_URL_ROOT_REGEX = r'/.*'

# Regular expression for matching cache expiration deltas.
_DELTA_REGEX = r'([0-9]+)([DdHhMm]|[sS]?)'
_EXPIRATION_REGEX = r'\s*(%s)(\s+%s)*\s*' % (_DELTA_REGEX, _DELTA_REGEX)
_START_PATH = '/_ah/start'

# Regular expression for matching service names.
# TODO(arb): this may need altering so as to not leak unreleased service names
# TODO(user): Re-add sms to list of services.
_ALLOWED_SERVICES = ['mail', 'mail_bounce', 'xmpp_message', 'xmpp_subscribe',
                     'xmpp_presence', 'xmpp_error', 'channel_presence', 'rest',
                     'warmup']
_SERVICE_RE_STRING = '(' + '|'.join(_ALLOWED_SERVICES) + ')'

# Regular expression for matching page names.
_PAGE_NAME_REGEX = r'^.+$'

# Constants for interpreting expiration deltas.
_EXPIRATION_CONVERSIONS = {
    'd': 60 * 60 * 24,
    'h': 60 * 60,
    'm': 60,
    's': 1,
}

# Constant values from apphosting/base/constants.h
# TODO(user): Maybe a python constants file.
APP_ID_MAX_LEN = 100
MODULE_ID_MAX_LEN = 63
# See b/5485871 for why this is 100 and not 63.
# NOTE(user): See b/5485871 for why this is different from the
# apphosting/base/constants.h value.
MODULE_VERSION_ID_MAX_LEN = 63
MAX_URL_MAPS = 100

# The character separating the partition from the domain.
PARTITION_SEPARATOR = '~'

# The character separating the domain from the display-app-id.
DOMAIN_SEPARATOR = ':'

# The character separating major and minor versions.
VERSION_SEPARATOR = '.'

# The character separating module from module version.
MODULE_SEPARATOR = ':'

# The name of the default module
DEFAULT_MODULE = 'default'

# Regular expression for ID types. Defined in apphosting/base/id_util.cc.
PARTITION_RE_STRING_WITHOUT_SEPARATOR = (r'[a-z\d\-]{1,%d}' % APP_ID_MAX_LEN)
PARTITION_RE_STRING = (r'%s\%s' %
                       (PARTITION_RE_STRING_WITHOUT_SEPARATOR,
                        PARTITION_SEPARATOR))
DOMAIN_RE_STRING_WITHOUT_SEPARATOR = (r'(?!\-)[a-z\d\-\.]{1,%d}' %
                                      APP_ID_MAX_LEN)
DOMAIN_RE_STRING = (r'%s%s' %
                    (DOMAIN_RE_STRING_WITHOUT_SEPARATOR, DOMAIN_SEPARATOR))
DISPLAY_APP_ID_RE_STRING = r'(?!-)[a-z\d\-]{0,%d}[a-z\d]' % (APP_ID_MAX_LEN - 1)
APPLICATION_RE_STRING = (r'(?:%s)?(?:%s)?%s' %
                         (PARTITION_RE_STRING,
                          DOMAIN_RE_STRING,
                          DISPLAY_APP_ID_RE_STRING))

# NOTE(user,user): These regexes have been copied to multiple other
# locations in google.apphosting so we don't have to pull this file into
# python_lib for other modules to work in production.
# Other known locations as of 2012-03-26:
# - java/com/google/apphosting/admin/legacy/LegacyAppInfo.java
MODULE_ID_RE_STRING = r'^(?!-)[a-z\d\-]{0,%d}[a-z\d]$' % (MODULE_ID_MAX_LEN - 1)
MODULE_VERSION_ID_RE_STRING = (r'^(?!-)[a-z\d\-]{0,%d}[a-z\d]$' %
                               (MODULE_VERSION_ID_MAX_LEN - 1))

_IDLE_INSTANCES_REGEX = r'^([\d]+|automatic)$'
# Note that this regex will not allow zero-prefixed numbers, e.g. 0001.
_INSTANCES_REGEX = r'^[1-9][\d]*$'
_INSTANCE_CLASS_REGEX = r'^([fF](1|2|4|4_1G)|[bB](1|2|4|8|4_1G))$'

_CONCURRENT_REQUESTS_REGEX = r'^([1-9]\d*)$'

# This enforces that we will only accept a single decimal point of accuracy at
# the granularity of seconds and no decimal point with a granularity of
# milliseconds.
_PENDING_LATENCY_REGEX = r'^(\d+((\.\d{1,3})?s|ms)|automatic)$'

_IDLE_TIMEOUT_REGEX = r'^[\d]+(s|m)$'

GCE_RESOURCE_NAME_REGEX = r'^[a-z]([a-z\d-]{0,61}[a-z\d])?$'

ALTERNATE_HOSTNAME_SEPARATOR = '-dot-'

# Note(user): This must match api/app_config.py
BUILTIN_NAME_PREFIX = 'ah-builtin'

RUNTIME_RE_STRING = r'[a-z][a-z0-9\-]{0,29}'

API_VERSION_RE_STRING = r'[\w.]{1,32}'
ENV_RE_STRING = r'[\w.]{1,32}'

SOURCE_LANGUAGE_RE_STRING = r'[\w.\-]{1,32}'

HANDLER_STATIC_FILES = 'static_files'
HANDLER_STATIC_DIR = 'static_dir'
HANDLER_SCRIPT = 'script'
HANDLER_API_ENDPOINT = 'api_endpoint'

LOGIN_OPTIONAL = 'optional'
LOGIN_REQUIRED = 'required'
LOGIN_ADMIN = 'admin'

AUTH_FAIL_ACTION_REDIRECT = 'redirect'
AUTH_FAIL_ACTION_UNAUTHORIZED = 'unauthorized'

DATASTORE_ID_POLICY_LEGACY = 'legacy'
DATASTORE_ID_POLICY_DEFAULT = 'default'

SECURE_HTTP = 'never'
SECURE_HTTPS = 'always'
SECURE_HTTP_OR_HTTPS = 'optional'
# Used for missing values; see http://b/issue?id=2073962.
SECURE_DEFAULT = 'default'

REQUIRE_MATCHING_FILE = 'require_matching_file'

DEFAULT_SKIP_FILES = (r'^(.*/)?('
                      r'(#.*#)|'
                      r'(.*~)|'
                      r'(.*\.py[co])|'
                      r'(.*/RCS/.*)|'
                      r'(\..*)|'
                      r')$')
# Expression meaning to skip no files, which is the default for AppInclude.
SKIP_NO_FILES = r'(?!)'

DEFAULT_NOBUILD_FILES = (r'^$')

# Attributes for URLMap
LOGIN = 'login'
AUTH_FAIL_ACTION = 'auth_fail_action'
SECURE = 'secure'
URL = 'url'
POSITION = 'position'
POSITION_HEAD = 'head'
POSITION_TAIL = 'tail'
STATIC_FILES = 'static_files'
UPLOAD = 'upload'
STATIC_DIR = 'static_dir'
MIME_TYPE = 'mime_type'
SCRIPT = 'script'
EXPIRATION = 'expiration'
API_ENDPOINT = 'api_endpoint'
HTTP_HEADERS = 'http_headers'
APPLICATION_READABLE = 'application_readable'
REDIRECT_HTTP_RESPONSE_CODE = 'redirect_http_response_code'

# Attributes for AppInfoExternal
APPLICATION = 'application'
PROJECT = 'project'  # An alias for 'application'
MODULE = 'module'
SERVICE = 'service'
AUTOMATIC_SCALING = 'automatic_scaling'
MANUAL_SCALING = 'manual_scaling'
BASIC_SCALING = 'basic_scaling'
VM = 'vm'
VM_SETTINGS = 'vm_settings'
BETA_SETTINGS = 'beta_settings'
VM_HEALTH_CHECK = 'vm_health_check'
HEALTH_CHECK = 'health_check'
RESOURCES = 'resources'
NETWORK = 'network'
VERSION = 'version'
MAJOR_VERSION = 'major_version'
MINOR_VERSION = 'minor_version'
RUNTIME = 'runtime'
API_VERSION = 'api_version'
ENV = 'env'
ENTRYPOINT = 'entrypoint'
RUNTIME_CONFIG = 'runtime_config'
SOURCE_LANGUAGE = 'source_language'
BUILTINS = 'builtins'
INCLUDES = 'includes'
HANDLERS = 'handlers'
LIBRARIES = 'libraries'
DEFAULT_EXPIRATION = 'default_expiration'
SKIP_FILES = 'skip_files'
NOBUILD_FILES = 'nobuild_files'
SERVICES = 'inbound_services'
DERIVED_FILE_TYPE = 'derived_file_type'
JAVA_PRECOMPILED = 'java_precompiled'
PYTHON_PRECOMPILED = 'python_precompiled'
ADMIN_CONSOLE = 'admin_console'
ERROR_HANDLERS = 'error_handlers'
BACKENDS = 'backends'
THREADSAFE = 'threadsafe'
DATASTORE_AUTO_ID_POLICY = 'auto_id_policy'
API_CONFIG = 'api_config'
CODE_LOCK = 'code_lock'
ENV_VARIABLES = 'env_variables'

SOURCE_REPO_RE_STRING = r'^[a-z][a-z0-9\-\+\.]*:[^#]*$'
SOURCE_REVISION_RE_STRING = r'^[0-9a-fA-F]+$'

# Maximum size of all source references (in bytes) for a deployment.
SOURCE_REFERENCES_MAX_SIZE = 2048

INSTANCE_CLASS = 'instance_class'

# Attributes for Standard App Engine (only) AutomaticScaling.
MINIMUM_PENDING_LATENCY = 'min_pending_latency'
MAXIMUM_PENDING_LATENCY = 'max_pending_latency'
MINIMUM_IDLE_INSTANCES = 'min_idle_instances'
MAXIMUM_IDLE_INSTANCES = 'max_idle_instances'
MAXIMUM_CONCURRENT_REQUEST = 'max_concurrent_requests'

# Attributes for Managed VMs (only) AutomaticScaling. These are very
# different than Standard App Engine because scaling settings are
# mapped to Cloud Autoscaler (as opposed to the clone scheduler). See
# AutoscalingConfig in
MIN_NUM_INSTANCES = 'min_num_instances'
MAX_NUM_INSTANCES = 'max_num_instances'
COOL_DOWN_PERIOD_SEC = 'cool_down_period_sec'
CPU_UTILIZATION = 'cpu_utilization'
CPU_UTILIZATION_UTILIZATION = 'target_utilization'
CPU_UTILIZATION_AGGREGATION_WINDOW_LENGTH_SEC = 'aggregation_window_length_sec'
# Managed VMs Richer Autoscaling. These (MVMs only) scaling settings
# are supported for both vm:true and env:2|flex, but are not yet
# publicly documented.
TARGET_NETWORK_SENT_BYTES_PER_SEC = 'target_network_sent_bytes_per_sec'
TARGET_NETWORK_SENT_PACKETS_PER_SEC = 'target_network_sent_packets_per_sec'
TARGET_NETWORK_RECEIVED_BYTES_PER_SEC = 'target_network_received_bytes_per_sec'
TARGET_NETWORK_RECEIVED_PACKETS_PER_SEC = (
    'target_network_received_packets_per_sec')
TARGET_DISK_WRITE_BYTES_PER_SEC = 'target_disk_write_bytes_per_sec'
TARGET_DISK_WRITE_OPS_PER_SEC = 'target_disk_write_ops_per_sec'
TARGET_DISK_READ_BYTES_PER_SEC = 'target_disk_read_bytes_per_sec'
TARGET_DISK_READ_OPS_PER_SEC = 'target_disk_read_ops_per_sec'
TARGET_REQUEST_COUNT_PER_SEC = 'target_request_count_per_sec'
TARGET_CONCURRENT_REQUESTS = 'target_concurrent_requests'


# Attributes for ManualScaling
INSTANCES = 'instances'

# Attributes for BasicScaling
MAX_INSTANCES = 'max_instances'
IDLE_TIMEOUT = 'idle_timeout'

# Attributes for AdminConsole
PAGES = 'pages'
NAME = 'name'

# Attributes for ErrorHandlers
ERROR_CODE = 'error_code'
FILE = 'file'
_ERROR_CODE_REGEX = r'(default|over_quota|dos_api_denial|timeout)'

# Attributes for BuiltinHandler
ON = 'on'
ON_ALIASES = ['yes', 'y', 'True', 't', '1', 'true']
OFF = 'off'
OFF_ALIASES = ['no', 'n', 'False', 'f', '0', 'false']

# Attributes for VmHealthCheck. Please refer to message VmHealthCheck in
# request_path and port are not configurable yet.
ENABLE_HEALTH_CHECK = 'enable_health_check'
CHECK_INTERVAL_SEC = 'check_interval_sec'
TIMEOUT_SEC = 'timeout_sec'
UNHEALTHY_THRESHOLD = 'unhealthy_threshold'
HEALTHY_THRESHOLD = 'healthy_threshold'
RESTART_THRESHOLD = 'restart_threshold'
HOST = 'host'

# Attributes for Resources.
CPU = 'cpu'
MEMORY_GB = 'memory_gb'
DISK_SIZE_GB = 'disk_size_gb'

# Attributes for Network.
FORWARDED_PORTS = 'forwarded_ports'
INSTANCE_TAG = 'instance_tag'
NETWORK_NAME = 'name'


class _VersionedLibrary(object):
  """A versioned library supported by App Engine."""

  def __init__(self,
               name,
               url,
               description,
               supported_versions,
               latest_version,
               default_version=None,
               deprecated_versions=None,
               experimental_versions=None):
    """Initializer for _VersionedLibrary.

    Args:
      name: The name of the library e.g. "django".
      url: The URL for the library's project page e.g.
          "http://www.djangoproject.com/".
      description: A short description of the library e.g. "A framework...".
      supported_versions: A list of supported version names ordered by release
          date e.g. ["v1", "v2", "v3"].
      latest_version: The version of the library that will be used when
          customers specify "latest." The rule of thumb is that this should
          be the newest version that is neither deprecated nor experimental
          (although may be experimental if all supported versions are either
          deprecated or experimental).
      default_version: The version of the library that is enabled by default
          in the Python 2.7 runtime or None if the library is not available by
          default e.g. "v1".
      deprecated_versions: A list of the versions of the library that have been
          deprecated e.g. ["v1", "v2"].
      experimental_versions: A list of the versions of the library that are
          current experimental e.g. ["v1"].
    """
    self.name = name
    self.url = url
    self.description = description
    self.supported_versions = supported_versions
    self.latest_version = latest_version
    self.default_version = default_version
    self.deprecated_versions = deprecated_versions or []
    self.experimental_versions = experimental_versions or []

  @property
  def non_deprecated_versions(self):
    return [version for version in self.supported_versions
            if version not in self.deprecated_versions]


_SUPPORTED_LIBRARIES = [
    _VersionedLibrary(
        'django',
        'http://www.djangoproject.com/',
        'A full-featured web application framework for Python.',
        ['1.2', '1.3', '1.4', '1.5', '1.9'],
        latest_version='1.4',
        ),
    _VersionedLibrary(
        'endpoints',
        'https://developers.google.com/appengine/docs/python/endpoints/',
        'Libraries for building APIs in an App Engine application.',
        ['1.0'],
        latest_version='1.0',
        ),
    _VersionedLibrary(
        'jinja2',
        'http://jinja.pocoo.org/docs/',
        'A modern and designer friendly templating language for Python.',
        ['2.6'],
        latest_version='2.6',
        ),
    _VersionedLibrary(
        'lxml',
        'http://lxml.de/',
        'A Pythonic binding for the C libraries libxml2 and libxslt.',
        ['2.3', '2.3.5'],
        latest_version='2.3',
        experimental_versions=['2.3.5'],
        ),
    _VersionedLibrary(
        'markupsafe',
        'http://pypi.python.org/pypi/MarkupSafe',
        'A XML/HTML/XHTML markup safe string for Python.',
        ['0.15', '0.23'],
        latest_version='0.15',
        ),
    _VersionedLibrary(
        'matplotlib',
        'http://matplotlib.org/',
        'A 2D plotting library which produces publication-quality figures.',
        ['1.2.0'],
        latest_version='1.2.0',
        ),
    _VersionedLibrary(
        'MySQLdb',
        'http://mysql-python.sourceforge.net/',
        'A Python DB API v2.0 compatible interface to MySQL.',
        ['1.2.4b4', '1.2.4', '1.2.5'],
        latest_version='1.2.5',
        experimental_versions=['1.2.4b4', '1.2.4', '1.2.5']
        ),
    _VersionedLibrary(
        'numpy',
        'http://numpy.scipy.org/',
        'A general-purpose library for array-processing.',
        ['1.6.1'],
        latest_version='1.6.1',
        ),
    _VersionedLibrary(
        'PIL',
        'http://www.pythonware.com/library/pil/handbook/',
        'A library for creating and transforming images.',
        ['1.1.7'],
        latest_version='1.1.7',
        ),
    _VersionedLibrary(
        'protorpc',
        'https://code.google.com/p/google-protorpc/',
        'A framework for implementing HTTP-based remote procedure call (RPC) '
        'services.',
        ['1.0'],
        latest_version='1.0',
        default_version='1.0',
        ),
    _VersionedLibrary(
        'pytz',
        'https://pypi.python.org/pypi/pytz?',
        'A library for cross-platform timezone calculations',
        ['2016.4'],
        latest_version='2016.4',
        default_version='2016.4',
        ),
    _VersionedLibrary(
        'crcmod',
        'http://crcmod.sourceforge.net/',
        'A library for generating Cyclic Redundancy Checks (CRC).',
        ['1.7'],
        latest_version='1.7',
        ),

    _VersionedLibrary(
        'PyAMF',
        'http://pyamf.appspot.com/index.html',
        'A library that provides (AMF) Action Message Format functionality.',
        ['0.6.1', '0.7.2'],
        latest_version='0.6.1',
        experimental_versions=['0.7.2'],
        ),
    _VersionedLibrary(
        'pycrypto',
        'https://www.dlitz.net/software/pycrypto/',
        'A library of cryptography functions such as random number generation.',
        ['2.3', '2.6', '2.6.1'],
        latest_version='2.6',
        ),
    _VersionedLibrary(
        'setuptools',
        'http://pypi.python.org/pypi/setuptools',
        'A library that provides package and module discovery capabilities.',
        ['0.6c11'],
        latest_version='0.6c11',
        ),
    _VersionedLibrary(
        'ssl',
        'http://docs.python.org/dev/library/ssl.html',
        'The SSL socket wrapper built-in module.',
        ['2.7', '2.7.11'],
        latest_version='2.7',
        ),
    _VersionedLibrary(
        'webapp2',
        'http://webapp-improved.appspot.com/',
        'A lightweight Python web framework.',
        ['2.3', '2.5.1', '2.5.2'],
        latest_version='2.5.2',
        default_version='2.3',
        deprecated_versions=['2.3']
        ),
    _VersionedLibrary(
        'webob',
        'http://www.webob.org/',
        'A library that provides wrappers around the WSGI request environment.',
        ['1.1.1', '1.2.3'],
        latest_version='1.2.3',
        default_version='1.1.1',
        ),
    _VersionedLibrary(
        'yaml',
        'http://www.yaml.org/',
        'A library for YAML serialization and deserialization.',
        ['3.10'],
        latest_version='3.10',
        default_version='3.10'
        ),
    ]

_NAME_TO_SUPPORTED_LIBRARY = dict((library.name, library)
                                  for library in _SUPPORTED_LIBRARIES)

# A mapping from third-party name/version to a list of that library's
# dependencies.
REQUIRED_LIBRARIES = {
    ('jinja2', '2.6'): [('markupsafe', '0.15'), ('setuptools', '0.6c11')],
    ('jinja2', 'latest'): [('markupsafe', 'latest'), ('setuptools', 'latest')],
    ('matplotlib', '1.2.0'): [('numpy', '1.6.1')],
    ('matplotlib', 'latest'): [('numpy', 'latest')],
}

_USE_VERSION_FORMAT = ('use one of: "%s"')


# See RFC 2616 section 2.2.
_HTTP_SEPARATOR_CHARS = frozenset('()<>@,;:\\"/[]?={} \t')
_HTTP_TOKEN_CHARS = frozenset(string.printable[:-5]) - _HTTP_SEPARATOR_CHARS
_HTTP_TOKEN_RE = re.compile('[%s]+$' % re.escape(''.join(_HTTP_TOKEN_CHARS)))

# Source: http://www.cs.tut.fi/~jkorpela/http.html
_HTTP_REQUEST_HEADERS = frozenset([
    'accept',
    'accept-charset',
    'accept-encoding',
    'accept-language',
    'authorization',
    'expect',
    'from',
    'host',
    'if-match',
    'if-modified-since',
    'if-none-match',
    'if-range',
    'if-unmodified-since',
    'max-forwards',
    'proxy-authorization',
    'range',
    'referer',
    'te',
    'user-agent',
])

# The minimum cookie length (i.e. number of bytes) that HTTP clients should
# support, per RFCs 2109 and 2965.
_MAX_COOKIE_LENGTH = 4096

# trailing NULL character, which is why this is not 2048.
_MAX_URL_LENGTH = 2047

# We allow certain headers to be larger than the normal limit of 8192 bytes.
_MAX_HEADER_SIZE_FOR_EXEMPTED_HEADERS = 10240

_CANNED_RUNTIMES = ('contrib-dart', 'dart', 'go', 'php', 'php55', 'python',
                    'python27', 'python-compat', 'java', 'java7', 'vm',
                    'custom', 'nodejs', 'ruby')
_all_runtimes = _CANNED_RUNTIMES


def GetAllRuntimes():
  """Returns the list of all valid runtimes.

  This can include third-party runtimes as well as canned runtimes.

  Returns:
    Tuple of strings.
  """
  return _all_runtimes


class HandlerBase(validation.Validated):
  """Base class for URLMap and ApiConfigHandler."""
  ATTRIBUTES = {
      # Common fields.
      URL: validation.Optional(_URL_REGEX),
      LOGIN: validation.Options(LOGIN_OPTIONAL,
                                LOGIN_REQUIRED,
                                LOGIN_ADMIN,
                                default=LOGIN_OPTIONAL),

      AUTH_FAIL_ACTION: validation.Options(AUTH_FAIL_ACTION_REDIRECT,
                                           AUTH_FAIL_ACTION_UNAUTHORIZED,
                                           default=AUTH_FAIL_ACTION_REDIRECT),

      SECURE: validation.Options(SECURE_HTTP,
                                 SECURE_HTTPS,
                                 SECURE_HTTP_OR_HTTPS,
                                 SECURE_DEFAULT,
                                 default=SECURE_DEFAULT),

      # Python/CGI fields.
      HANDLER_SCRIPT: validation.Optional(_FILES_REGEX)
  }


class HttpHeadersDict(validation.ValidatedDict):
  """A dict that limits keys and values what http_headers allows.

  http_headers is an static handler key i.e. it applies to handlers with
  static_dir or static_files keys. An example of how http_headers is used is

  handlers:
  - url: /static
    static_dir: static
    http_headers:
      X-Foo-Header: foo value
      X-Bar-Header: bar value
  """

  DISALLOWED_HEADERS = frozenset([
      # TODO(user): I don't think there's any reason to disallow users
      # from setting Content-Encoding, but other parts of the system prevent
      # this; therefore, we disallow it here. See the following discussion:
      'content-encoding',
      'content-length',
      'date',
      'server'
  ])

  MAX_HEADER_LENGTH = 500
  MAX_HEADER_VALUE_LENGTHS = {
      'content-security-policy': _MAX_HEADER_SIZE_FOR_EXEMPTED_HEADERS,
      'x-content-security-policy': _MAX_HEADER_SIZE_FOR_EXEMPTED_HEADERS,
      'x-webkit-csp': _MAX_HEADER_SIZE_FOR_EXEMPTED_HEADERS,
      'content-security-policy-report-only':
          _MAX_HEADER_SIZE_FOR_EXEMPTED_HEADERS,
      'set-cookie': _MAX_COOKIE_LENGTH,
      'set-cookie2': _MAX_COOKIE_LENGTH,
      'location': _MAX_URL_LENGTH}
  MAX_LEN = 500

  class KeyValidator(validation.Validator):
    """Ensures that keys in HttpHeadersDict i.e. header names are valid.

    An instance is used as HttpHeadersDict's KEY_VALIDATOR.
    """

    def Validate(self, name, unused_key=None):
      """Returns argument, or raises an exception if it is invalid.

      HTTP header names are defined by RFC 2616 section 4.2.

      Args:
        name: HTTP header field value.
        unused_key: Unused.

      Returns:
        name argument, unchanged.

      Raises:
        appinfo_errors.InvalidHttpHeaderName: argument cannot be used as an HTTP
          header name.
      """
      original_name = name

      # Make sure only ASCII data is used.
      if isinstance(name, unicode):
        try:
          name = name.encode('ascii')
        except UnicodeEncodeError:
          raise appinfo_errors.InvalidHttpHeaderName(
              'HTTP header values must not contain non-ASCII data')

      # HTTP headers are case-insensitive.
      name = name.lower()

      if not _HTTP_TOKEN_RE.match(name):
        raise appinfo_errors.InvalidHttpHeaderName(
            'An HTTP header must be a non-empty RFC 2616 token.')

      # Request headers shouldn't be used in responses.
      if name in _HTTP_REQUEST_HEADERS:
        raise appinfo_errors.InvalidHttpHeaderName(
            '%r can only be used in HTTP requests, not responses.'
            % original_name)

      # Make sure that none of the reserved prefixes is used.
      if name.startswith('x-appengine'):
        raise appinfo_errors.InvalidHttpHeaderName(
            'HTTP header names that begin with X-Appengine are reserved.')

      if wsgiref.util.is_hop_by_hop(name):
        raise appinfo_errors.InvalidHttpHeaderName(
            'Only use end-to-end headers may be used. See RFC 2616 section'
            ' 13.5.1.')

      if name in HttpHeadersDict.DISALLOWED_HEADERS:
        raise appinfo_errors.InvalidHttpHeaderName(
            '%s is a disallowed header.' % name)

      return original_name

  class ValueValidator(validation.Validator):
    """Ensures that values in HttpHeadersDict i.e. header values are valid.

    An instance is used as HttpHeadersDict's VALUE_VALIDATOR.
    """

    def Validate(self, value, key=None):
      """Returns value, or raises an exception if it is invalid.

      According to RFC 2616 section 4.2, header field values must consist "of
      either *TEXT or combinations of token, separators, and quoted-string".

      TEXT = <any OCTET except CTLs, but including LWS>

      Args:
        value: HTTP header field value.
        key: HTTP header field name.

      Returns:
        value argument.

      Raises:
        appinfo_errors.InvalidHttpHeaderValue: argument cannot be used as an
          HTTP header value.
      """
      # Make sure only ASCII data is used.
      if isinstance(value, unicode):
        try:
          value = value.encode('ascii')
        except UnicodeEncodeError:
          raise appinfo_errors.InvalidHttpHeaderValue(
              'HTTP header values must not contain non-ASCII data')

      # HTTP headers are case-insensitive.
      key = key.lower()

      # TODO(user): This is the same check that appserver performs, but it
      # could be stronger. e.g. '"foo' should not be considered valid, because
      # HTTP does not allow unclosed double quote marks in header values, per
      # RFC 2616 section 4.2.
      printable = set(string.printable[:-5])
      if not all(char in printable for char in value):
        raise appinfo_errors.InvalidHttpHeaderValue(
            'HTTP header field values must consist of printable characters.')

      HttpHeadersDict.ValueValidator.AssertHeaderNotTooLong(key, value)

      return value

    @staticmethod
    def AssertHeaderNotTooLong(name, value):
      header_length = len('%s: %s\r\n' % (name, value))

      # The >= operator here is a little counter-intuitive. The reason for it is
      # that I'm trying to follow the HTTPProto::IsValidHeader implementation.
      if header_length >= HttpHeadersDict.MAX_HEADER_LENGTH:
        # If execution reaches this point, it generally means the header is too
        # long, but there are a few exceptions, which are listed in the next
        # dict.
        try:
          max_len = HttpHeadersDict.MAX_HEADER_VALUE_LENGTHS[name]
        except KeyError:
          raise appinfo_errors.InvalidHttpHeaderValue(
              'HTTP header (name + value) is too long.')

        # We are dealing with one of the exceptional headers with larger maximum
        # value lengths.
        if len(value) > max_len:
          insert = name, len(value), max_len
          raise appinfo_errors.InvalidHttpHeaderValue(
              '%r header value has length %d, which exceed the maximum allowed,'
              ' %d.' % insert)

  KEY_VALIDATOR = KeyValidator()
  VALUE_VALIDATOR = ValueValidator()

  def Get(self, header_name):
    """Gets a header value.

    Args:
      header_name: HTTP header name to look for.

    Returns:
      A header value that corresponds to header_name. If more than one such
      value is in self, one of the values is selected arbitrarily, and
      returned. The selection is not deterministic.
    """
    for name in self:
      if name.lower() == header_name.lower():
        return self[name]

  # TODO(user): Perhaps, this functionality should be part of
  # validation.ValidatedDict .
  def __setitem__(self, key, value):
    is_addition = self.Get(key) is None
    if is_addition and len(self) >= self.MAX_LEN:
      raise appinfo_errors.TooManyHttpHeaders(
          'Tried to add another header when the current set of HTTP headers'
          ' already has the maximum allowed number of headers, %d.'
          % HttpHeadersDict.MAX_LEN)
    super(HttpHeadersDict, self).__setitem__(key, value)


class URLMap(HandlerBase):
  """Mapping from URLs to handlers.

  This class acts like something of a union type.  Its purpose is to
  describe a mapping between a set of URLs and their handlers.  What
  handler type a given instance has is determined by which handler-id
  attribute is used.

  Each mapping can have one and only one handler type.  Attempting to
  use more than one handler-id attribute will cause an UnknownHandlerType
  to be raised during validation.  Failure to provide any handler-id
  attributes will cause MissingHandlerType to be raised during validation.

  The regular expression used by the url field will be used to match against
  the entire URL path and query string of the request.  This means that
  partial maps will not be matched.  Specifying a url, say /admin, is the
  same as matching against the regular expression '^/admin$'.  Don't begin
  your matching url with ^ or end them with $.  These regular expressions
  won't be accepted and will raise ValueError.

  Attributes:
    login: Whether or not login is required to access URL.  Defaults to
      'optional'.
    secure: Restriction on the protocol which can be used to serve
            this URL/handler (HTTP, HTTPS or either).
    url: Regular expression used to fully match against the request URLs path.
      See Special Cases for using static_dir.
    static_files: Handler id attribute that maps URL to the appropriate
      file.  Can use back regex references to the string matched to url.
    upload: Regular expression used by the application configuration
      program to know which files are uploaded as blobs.  It's very
      difficult to determine this using just the url and static_files
      so this attribute must be included.  Required when defining a
      static_files mapping.
      A matching file name must fully match against the upload regex, similar
      to how url is matched against the request path.  Do not begin upload
      with ^ or end it with $.
    static_dir: Handler id that maps the provided url to a sub-directory
      within the application directory.  See Special Cases.
    mime_type: When used with static_files and static_dir the mime-type
      of files served from those directories are overridden with this
      value.
    script: Handler id that maps URLs to scipt handler within the application
      directory that will run using CGI.
    position: Used in AppInclude objects to specify whether a handler
      should be inserted at the beginning of the primary handler list or at the
      end.  If 'tail' is specified, the handler is inserted at the end,
      otherwise, the handler is inserted at the beginning.  This means that
      'head' is the effective default.
    expiration: When used with static files and directories, the time delta to
      use for cache expiration. Has the form '4d 5h 30m 15s', where each letter
      signifies days, hours, minutes, and seconds, respectively. The 's' for
      seconds may be omitted. Only one amount must be specified, combining
      multiple amounts is optional. Example good values: '10', '1d 6h',
      '1h 30m', '7d 7d 7d', '5m 30'.
    api_endpoint: Handler id that identifies endpoint as an API endpoint,
      calls that terminate here will be handled by the api serving framework.

  Special cases:
    When defining a static_dir handler, do not use a regular expression
    in the url attribute.  Both the url and static_dir attributes are
    automatically mapped to these equivalents:

      <url>/(.*)
      <static_dir>/\1

    For example:

      url: /images
      static_dir: images_folder

    Is the same as this static_files declaration:

      url: /images/(.*)
      static_files: images_folder/\1
      upload: images_folder/(.*)
  """
  ATTRIBUTES = {
      # Static file fields.
      # File mappings are allowed to have regex back references.
      HANDLER_STATIC_FILES: validation.Optional(_FILES_REGEX),
      UPLOAD: validation.Optional(_FILES_REGEX),
      APPLICATION_READABLE: validation.Optional(bool),

      # Static directory fields.
      HANDLER_STATIC_DIR: validation.Optional(_FILES_REGEX),

      # Used in both static mappings.
      MIME_TYPE: validation.Optional(str),
      EXPIRATION: validation.Optional(_EXPIRATION_REGEX),
      REQUIRE_MATCHING_FILE: validation.Optional(bool),
      HTTP_HEADERS: validation.Optional(HttpHeadersDict),

      # Python/CGI fields.
      POSITION: validation.Optional(validation.Options(POSITION_HEAD,
                                                       POSITION_TAIL)),

      HANDLER_API_ENDPOINT: validation.Optional(validation.Options(
          (ON, ON_ALIASES),
          (OFF, OFF_ALIASES))),

      REDIRECT_HTTP_RESPONSE_CODE: validation.Optional(validation.Options(
          '301', '302', '303', '307')),
  }
  ATTRIBUTES.update(HandlerBase.ATTRIBUTES)

  COMMON_FIELDS = set([
      URL, LOGIN, AUTH_FAIL_ACTION, SECURE, REDIRECT_HTTP_RESPONSE_CODE])

  # The keys of this map are attributes which can be used to identify each
  # mapping type in addition to the handler identifying attribute itself.
  ALLOWED_FIELDS = {
      HANDLER_STATIC_FILES: (MIME_TYPE, UPLOAD, EXPIRATION,
                             REQUIRE_MATCHING_FILE, HTTP_HEADERS,
                             APPLICATION_READABLE),
      HANDLER_STATIC_DIR: (MIME_TYPE, EXPIRATION, REQUIRE_MATCHING_FILE,
                           HTTP_HEADERS, APPLICATION_READABLE),
      HANDLER_SCRIPT: (POSITION),
      HANDLER_API_ENDPOINT: (POSITION, SCRIPT),
  }

  def GetHandler(self):
    """Get handler for mapping.

    Returns:
      Value of the handler (determined by handler id attribute).
    """
    return getattr(self, self.GetHandlerType())

  def GetHandlerType(self):
    """Get handler type of mapping.

    Returns:
      Handler type determined by which handler id attribute is set.

    Raises:
      UnknownHandlerType: when none of the no handler id attributes are set.

      UnexpectedHandlerAttribute: when an unexpected attribute is set for the
        discovered handler type.

      HandlerTypeMissingAttribute: when the handler is missing a
        required attribute for its handler type.

      MissingHandlerAttribute: when a URL handler is missing an attribute
    """
    # Special case for the api_endpoint handler as it may have a 'script'
    # attribute as well.
    if getattr(self, HANDLER_API_ENDPOINT) is not None:
      # Matched id attribute, break out of loop.
      mapping_type = HANDLER_API_ENDPOINT
    else:
      for id_field in URLMap.ALLOWED_FIELDS.iterkeys():
        # Attributes always exist as defined by ATTRIBUTES.
        if getattr(self, id_field) is not None:
          # Matched id attribute, break out of loop.
          mapping_type = id_field
          break
      else:
        # If no mapping type is found raise exception.
        raise appinfo_errors.UnknownHandlerType(
            'Unknown url handler type.\n%s' % str(self))

    allowed_fields = URLMap.ALLOWED_FIELDS[mapping_type]

    # Make sure that none of the set attributes on this handler
    # are not allowed for the discovered handler type.
    for attribute in self.ATTRIBUTES.iterkeys():
      if (getattr(self, attribute) is not None and
          not (attribute in allowed_fields or
               attribute in URLMap.COMMON_FIELDS or
               attribute == mapping_type)):
        raise appinfo_errors.UnexpectedHandlerAttribute(
            'Unexpected attribute "%s" for mapping type %s.' %
            (attribute, mapping_type))

    # Also check that static file map has 'upload'.
    # NOTE: Add REQUIRED_FIELDS along with ALLOWED_FIELDS if any more
    # exceptional cases arise.
    if mapping_type == HANDLER_STATIC_FILES and not self.upload:
      raise appinfo_errors.MissingHandlerAttribute(
          'Missing "%s" attribute for URL "%s".' % (UPLOAD, self.url))

    return mapping_type

  def CheckInitialized(self):
    """Adds additional checking to make sure handler has correct fields.

    In addition to normal ValidatedCheck calls GetHandlerType
    which validates all the handler fields are configured
    properly.

    Raises:
      UnknownHandlerType: when none of the no handler id attributes are set.
      UnexpectedHandlerAttribute: when an unexpected attribute is set for the
        discovered handler type.
      HandlerTypeMissingAttribute: when the handler is missing a required
        attribute for its handler type.
      ContentTypeSpecifiedMultipleTimes: when mime_type is inconsistent with
        http_headers.
    """
    super(URLMap, self).CheckInitialized()
    if self.GetHandlerType() in (STATIC_DIR, STATIC_FILES):
      # re how headers that affect caching interact per RFC 2616:
      #
      # Section 13.1.3 says that when there is "apparent conflict between
      # [Cache-Control] header values, the most restrictive interpretation is
      # applied".
      #
      # Section 14.21 says that Cache-Control: max-age overrides Expires
      # headers.
      #
      # Section 14.32 says that Pragma: no-cache has no meaning in responses;
      # therefore, we do not need to be concerned about that header here.
      self.AssertUniqueContentType()

  def AssertUniqueContentType(self):
    """Makes sure that self.http_headers is consistent with self.mime_type.

    Assumes self is a static handler i.e. either self.static_dir or
    self.static_files is set (to not None).

    Raises:
      appinfo_errors.ContentTypeSpecifiedMultipleTimes: Raised when
        self.http_headers contains a Content-Type header, and self.mime_type is
        set. For example, the following configuration would be rejected:

          handlers:
          - url: /static
            static_dir: static
            mime_type: text/html
            http_headers:
              content-type: text/html

        As this example shows, a configuration will be rejected when
        http_headers and mime_type specify a content type, even when they
        specify the same content type.
    """
    used_both_fields = self.mime_type and self.http_headers
    if not used_both_fields:
      return

    content_type = self.http_headers.Get('Content-Type')
    if content_type is not None:
      raise appinfo_errors.ContentTypeSpecifiedMultipleTimes(
          'http_header specified a Content-Type header of %r in a handler that'
          ' also specified a mime_type of %r.' % (content_type, self.mime_type))

  def FixSecureDefaults(self):
    """Force omitted 'secure: ...' handler fields to 'secure: optional'.

    The effect is that handler.secure is never equal to the (nominal)
    default.

    See http://b/issue?id=2073962.
    """
    if self.secure == SECURE_DEFAULT:
      self.secure = SECURE_HTTP_OR_HTTPS

  def WarnReservedURLs(self):
    """Generates a warning for reserved URLs.

    See:
    https://developers.google.com/appengine/docs/python/config/appconfig#Reserved_URLs
    """
    if self.url == '/form':
      logging.warning(
          'The URL path "/form" is reserved and will not be matched.')

  def ErrorOnPositionForAppInfo(self):
    """Raises an error if position is specified outside of AppInclude objects.

    Raises:
      PositionUsedInAppYamlHandler: when position attribute is specified for an
      app.yaml file instead of an include.yaml file.
    """
    if self.position:
      raise appinfo_errors.PositionUsedInAppYamlHandler(
          'The position attribute was specified for this handler, but this is '
          'an app.yaml file.  Position attribute is only valid for '
          'include.yaml files.')


class AdminConsolePage(validation.Validated):
  """Class representing admin console page in AdminConsole object.
  """
  ATTRIBUTES = {
      URL: _URL_REGEX,
      NAME: _PAGE_NAME_REGEX,
  }


class AdminConsole(validation.Validated):
  """Class representing admin console directives in application info.
  """
  ATTRIBUTES = {
      PAGES: validation.Optional(validation.Repeated(AdminConsolePage)),
  }

  @classmethod
  def Merge(cls, adminconsole_one, adminconsole_two):
    """Return the result of merging two AdminConsole objects."""
    # Right now this method only needs to worry about the pages attribute of
    # AdminConsole.  However, since this object is valid as part of an
    # AppInclude object, any objects added to AdminConsole in the future must
    # also be merged.  Rather than burying the merge logic in the process of
    # merging two AppInclude objects, it is centralized here.  If you modify
    # the AdminConsole object to support other objects, you must also modify
    # this method to support merging those additional objects.

    if not adminconsole_one or not adminconsole_two:
      return adminconsole_one or adminconsole_two

    if adminconsole_one.pages:
      if adminconsole_two.pages:
        adminconsole_one.pages.extend(adminconsole_two.pages)
    else:
      adminconsole_one.pages = adminconsole_two.pages

    return adminconsole_one


class ErrorHandlers(validation.Validated):
  """Class representing error handler directives in application info.
  """
  ATTRIBUTES = {
      ERROR_CODE: validation.Optional(_ERROR_CODE_REGEX),
      FILE: _FILES_REGEX,
      MIME_TYPE: validation.Optional(str),
  }


class BuiltinHandler(validation.Validated):
  """Class representing builtin handler directives in application info.

  Permits arbitrary keys but their values must be described by the
  validation.Options object returned by ATTRIBUTES.
  """

  # Validated is a somewhat complicated class.  It actually maintains two
  # dictionaries: the ATTRIBUTES dictionary and an internal __dict__ object
  # which maintains key value pairs.
  #
  # The normal flow is that a key must exist in ATTRIBUTES in order to be able
  # to be inserted into __dict__.  So that's why we force the
  # ATTRIBUTES.__contains__ method to always return true; we want to accept any
  # attribute.  Once the method returns true, then its value will be fetched,
  # which returns ATTRIBUTES[key]; that's why we override ATTRIBUTES.__getitem__
  # to return the validator for a BuiltinHandler object.
  #
  # This is where it gets tricky. Once the validator object is returned, then
  # __dict__[key] is set to the validated object for that key.  However, when
  # CheckInitialized() is called, it uses iteritems from ATTRIBUTES in order to
  # generate a list of keys to validate. This expects the BuiltinHandler
  # instance to contain every item in ATTRIBUTES, which contains every builtin
  # name see so far by any BuiltinHandler. To work around this, __getattr__
  # always returns None for public attribute names. Note that __getattr__ is
  # only called if __dict__ does not contain the key. Thus, the single builtin
  # value set is validated.
  #
  # What's important to know is that in this implementation, only the keys in
  # ATTRIBUTES matter, and only the values in __dict__ matter.  The values in
  # ATTRIBUTES and the keys in __dict__ are both ignored.  The key in __dict__
  # is only used for the __getattr__ function, but to find out what keys are
  # available, only ATTRIBUTES is ever read.

  class DynamicAttributes(dict):
    """Provide a dictionary object that will always claim to have a key.

    This dictionary returns a fixed value for any get operation.  The fixed
    value passed in as a constructor parameter should be a
    validation.Validated object.
    """

    def __init__(self, return_value, **parameters):
      self.__return_value = return_value
      dict.__init__(self, parameters)

    def __contains__(self, _):
      return True

    def __getitem__(self, _):
      return self.__return_value

  ATTRIBUTES = DynamicAttributes(
      validation.Optional(validation.Options((ON, ON_ALIASES),
                                             (OFF, OFF_ALIASES))))

  def __init__(self, **attributes):
    """Ensure that all BuiltinHandler objects at least have attribute 'default'.
    """
    self.builtin_name = ''
    super(BuiltinHandler, self).__init__(**attributes)

  def __setattr__(self, key, value):
    """Permit ATTRIBUTES.iteritems() to return set of items that have values.

    Whenever validate calls iteritems(), it is always called on ATTRIBUTES,
    not on __dict__, so this override is important to ensure that functions
    such as ToYAML() return the correct set of keys.

    Raises:
      MultipleBuiltinsSpecified: when more than one builtin is defined in a list
      element.
    """
    if key == 'builtin_name':
      object.__setattr__(self, key, value)
    elif not self.builtin_name:
      self.ATTRIBUTES[key] = ''
      self.builtin_name = key
      super(BuiltinHandler, self).__setattr__(key, value)
    else:
      # so the object can only be set once.  If later attributes are desired of
      # a different form, this clause should be used to catch whenever more than
      # one object does not match a predefined attribute name.
      raise appinfo_errors.MultipleBuiltinsSpecified(
          'More than one builtin defined in list element.  Each new builtin '
          'should be prefixed by "-".')

  def __getattr__(self, key):
    if key.startswith('_'):
      # __getattr__ is only called for attributes that don't exist in the
      # instance dict.
      raise AttributeError
    return None

  def ToDict(self):
    """Convert BuiltinHander object to a dictionary.

    Returns:
      dictionary of the form: {builtin_handler_name: on/off}
    """
    return {self.builtin_name: getattr(self, self.builtin_name)}

  @classmethod
  def IsDefined(cls, builtins_list, builtin_name):
    """Find if a builtin is defined in a given list of builtin handler objects.

    Args:
      builtins_list: list of BuiltinHandler objects (typically yaml.builtins)
      builtin_name: name of builtin to find whether or not it is defined

    Returns:
      true if builtin_name is defined by a member of builtins_list,
      false otherwise
    """
    for b in builtins_list:
      if b.builtin_name == builtin_name:
        return True
    return False

  @classmethod
  def ListToTuples(cls, builtins_list):
    """Converts a list of BuiltinHandler objects to a list of (name, status)."""
    return [(b.builtin_name, getattr(b, b.builtin_name)) for b in builtins_list]

  @classmethod
  def Validate(cls, builtins_list, runtime=None):
    """Verify that all BuiltinHandler objects are valid and not repeated.

    Args:
      builtins_list: list of BuiltinHandler objects to validate.
      runtime: if set then warnings are generated for builtins that have been
          deprecated in the given runtime.

    Raises:
      InvalidBuiltinFormat: if the name of a Builtinhandler object
          cannot be determined.
      DuplicateBuiltinsSpecified: if a builtin handler name is used
          more than once in the list.
    """
    seen = set()
    for b in builtins_list:
      if not b.builtin_name:
        raise appinfo_errors.InvalidBuiltinFormat(
            'Name of builtin for list object %s could not be determined.'
            % b)
      if b.builtin_name in seen:
        raise appinfo_errors.DuplicateBuiltinsSpecified(
            'Builtin %s was specified more than once in one yaml file.'
            % b.builtin_name)

      # This checking must be done here rather than in apphosting/ext/builtins
      # because apphosting/ext/builtins cannot differentiate between between
      # builtins specified in app.yaml versus ones added in a builtin include.
      # There is a hole here where warnings are not generated for
      # deprecated builtins that appear in user-created include files.
      if b.builtin_name == 'datastore_admin' and runtime == 'python':
        logging.warning(
            'The datastore_admin builtin is deprecated. You can find '
            'information on how to enable it through the Administrative '
            'Console here: '
            'http://developers.google.com/appengine/docs/adminconsole/'
            'datastoreadmin.html')
      elif b.builtin_name == 'mapreduce' and runtime == 'python':
        logging.warning(
            'The mapreduce builtin is deprecated. You can find more '
            'information on how to configure and use it here: '
            'http://developers.google.com/appengine/docs/python/dataprocessing/'
            'overview.html')

      seen.add(b.builtin_name)


class ApiConfigHandler(HandlerBase):
  """Class representing api_config handler directives in application info."""
  ATTRIBUTES = HandlerBase.ATTRIBUTES
  ATTRIBUTES.update({
      # Make URL and SCRIPT required for api_config stanza
      URL: validation.Regex(_URL_REGEX),
      HANDLER_SCRIPT: validation.Regex(_FILES_REGEX)
  })


class Library(validation.Validated):
  """Class representing the configuration of a single library."""

  ATTRIBUTES = {'name': validation.Type(str),
                'version': validation.Type(str)}

  def CheckInitialized(self):
    """Raises if the library configuration is not valid."""
    super(Library, self).CheckInitialized()
    if self.name not in _NAME_TO_SUPPORTED_LIBRARY:
      raise appinfo_errors.InvalidLibraryName(
          'the library "%s" is not supported' % self.name)
    supported_library = _NAME_TO_SUPPORTED_LIBRARY[self.name]
    if self.version == 'latest':
      self.version = supported_library.latest_version
    elif self.version not in supported_library.supported_versions:
      raise appinfo_errors.InvalidLibraryVersion(
          ('%s version "%s" is not supported, ' + _USE_VERSION_FORMAT) % (
              self.name,
              self.version,
              '", "'.join(supported_library.non_deprecated_versions)))
    elif self.version in supported_library.deprecated_versions:
      use_vers = '", "'.join(supported_library.non_deprecated_versions)
      logging.warning(
          '%s version "%s" is deprecated, ' + _USE_VERSION_FORMAT,
          self.name,
          self.version,
          use_vers)


class CpuUtilization(validation.Validated):
  """Class representing the configuration of VM CPU utilization."""

  ATTRIBUTES = {
      CPU_UTILIZATION_UTILIZATION: validation.Optional(
          validation.Range(1e-6, 1.0, float)),
      CPU_UTILIZATION_AGGREGATION_WINDOW_LENGTH_SEC: validation.Optional(
          validation.Range(1, sys.maxint)),
  }


class AutomaticScaling(validation.Validated):
  """Class representing automatic scaling settings in the AppInfoExternal."""
  ATTRIBUTES = {
      MINIMUM_IDLE_INSTANCES: validation.Optional(_IDLE_INSTANCES_REGEX),
      MAXIMUM_IDLE_INSTANCES: validation.Optional(_IDLE_INSTANCES_REGEX),
      MINIMUM_PENDING_LATENCY: validation.Optional(_PENDING_LATENCY_REGEX),
      MAXIMUM_PENDING_LATENCY: validation.Optional(_PENDING_LATENCY_REGEX),
      MAXIMUM_CONCURRENT_REQUEST: validation.Optional(
          _CONCURRENT_REQUESTS_REGEX),
      # Attributes for VM-based AutomaticScaling.
      MIN_NUM_INSTANCES: validation.Optional(validation.Range(1, sys.maxint)),
      MAX_NUM_INSTANCES: validation.Optional(validation.Range(1, sys.maxint)),
      COOL_DOWN_PERIOD_SEC: validation.Optional(
          validation.Range(60, sys.maxint, int)),
      CPU_UTILIZATION: validation.Optional(CpuUtilization),
      TARGET_NETWORK_SENT_BYTES_PER_SEC:
      validation.Optional(validation.Range(1, sys.maxint)),
      TARGET_NETWORK_SENT_PACKETS_PER_SEC:
      validation.Optional(validation.Range(1, sys.maxint)),
      TARGET_NETWORK_RECEIVED_BYTES_PER_SEC:
      validation.Optional(validation.Range(1, sys.maxint)),
      TARGET_NETWORK_RECEIVED_PACKETS_PER_SEC:
      validation.Optional(validation.Range(1, sys.maxint)),
      TARGET_DISK_WRITE_BYTES_PER_SEC:
      validation.Optional(validation.Range(1, sys.maxint)),
      TARGET_DISK_WRITE_OPS_PER_SEC:
      validation.Optional(validation.Range(1, sys.maxint)),
      TARGET_DISK_READ_BYTES_PER_SEC:
      validation.Optional(validation.Range(1, sys.maxint)),
      TARGET_DISK_READ_OPS_PER_SEC:
      validation.Optional(validation.Range(1, sys.maxint)),
      TARGET_REQUEST_COUNT_PER_SEC:
      validation.Optional(validation.Range(1, sys.maxint)),
      TARGET_CONCURRENT_REQUESTS:
      validation.Optional(validation.Range(1, sys.maxint)),
  }


class ManualScaling(validation.Validated):
  """Class representing manual scaling settings in the AppInfoExternal."""
  ATTRIBUTES = {
      INSTANCES: validation.Regex(_INSTANCES_REGEX),
  }


class BasicScaling(validation.Validated):
  """Class representing basic scaling settings in the AppInfoExternal."""
  ATTRIBUTES = {
      MAX_INSTANCES: validation.Regex(_INSTANCES_REGEX),
      IDLE_TIMEOUT: validation.Optional(_IDLE_TIMEOUT_REGEX),
  }


class RuntimeConfig(validation.ValidatedDict):
  """Class for "vanilla" runtime configuration.

  Fields used vary by runtime, so we delegate validation to the per-runtime
  build processes.

  These are intended to be used during Dockerfile generation, not after VM boot.
  """

  KEY_VALIDATOR = validation.Regex('[a-zA-Z_][a-zA-Z0-9_]*')
  VALUE_VALIDATOR = str


class VmSettings(validation.ValidatedDict):
  """Class for VM settings.

  We don't validate these further here.  They're validated server side.
  """

  KEY_VALIDATOR = validation.Regex('[a-zA-Z_][a-zA-Z0-9_]*')
  VALUE_VALIDATOR = str

  @classmethod
  def Merge(cls, vm_settings_one, vm_settings_two):
    # Note that VmSettings.copy() results in a dict.
    result_vm_settings = (vm_settings_two or {}).copy()
    # TODO(user): Apply merge logic when feature is fully defined.
    # For now, we will merge the two dict and vm_setting_one will win
    # if key collides.
    result_vm_settings.update(vm_settings_one or {})
    return VmSettings(**result_vm_settings) if result_vm_settings else None


class BetaSettings(VmSettings):
  """Class for Beta (internal or unreleased) settings.

  This class is meant to replace VmSettings eventually.
  All new beta settings must be registered in shared_constants.py.

  We don't validate these further here.  They're validated server side.
  """

  @classmethod
  def Merge(cls, beta_settings_one, beta_settings_two):
    merged = VmSettings.Merge(beta_settings_one, beta_settings_two)
    return BetaSettings(**merged.ToDict()) if merged else None


class EnvironmentVariables(validation.ValidatedDict):
  """Class representing a mapping of environment variable key value pairs."""

  KEY_VALIDATOR = validation.Regex('[a-zA-Z_][a-zA-Z0-9_]*')
  VALUE_VALIDATOR = str

  @classmethod
  def Merge(cls, env_variables_one, env_variables_two):
    """Merges to EnvironmentVariables instances.

    Args:
      env_variables_one: The first EnvironmentVariables instance or None.
      env_variables_two: The second EnvironmentVariables instance or None.

    Returns:
      The merged EnvironmentVariables instance, or None if both input instances
      are None or empty.

    If a variable is specified by both instances, the value from
    env_variables_two is used.
    """
    # Note that EnvironmentVariables.copy() results in a dict.
    result_env_variables = (env_variables_one or {}).copy()
    result_env_variables.update(env_variables_two or {})
    return (EnvironmentVariables(**result_env_variables)
            if result_env_variables else None)


def ValidateSourceReference(ref):
  """Determines if a source reference is valid.

  Args:
    ref: A source reference in a [repository_uri#]revision form.

  Raises:
    ValidationError: when the reference is malformed.
  """
  repo_revision = ref.split('#', 1)
  revision_id = repo_revision[-1]
  if not re.match(SOURCE_REVISION_RE_STRING, revision_id):
    raise validation.ValidationError('Bad revision identifier: %s' %
                                     revision_id)

  if len(repo_revision) == 2:
    uri = repo_revision[0]
    if not re.match(SOURCE_REPO_RE_STRING, uri):
      raise validation.ValidationError('Bad repository URI: %s' % uri)


def ValidateCombinedSourceReferencesString(source_refs):
  """Determines if source_refs contains a valid list of source references.

  Args:
    source_refs: A multi-line string containing one source reference per line.

  Raises:
    ValidationError: when the reference is malformed.
  """
  if len(source_refs) > SOURCE_REFERENCES_MAX_SIZE:
    raise validation.ValidationError(
        'Total source reference(s) size exceeds the limit: %d > %d' % (
            len(source_refs), SOURCE_REFERENCES_MAX_SIZE))

  for ref in source_refs.splitlines():
    ValidateSourceReference(ref.strip())


class HealthCheck(validation.Validated):
  """Class representing the health check configuration.

  """
  ATTRIBUTES = {
      ENABLE_HEALTH_CHECK: validation.Optional(validation.TYPE_BOOL),
      CHECK_INTERVAL_SEC: validation.Optional(validation.Range(0, sys.maxint)),
      TIMEOUT_SEC: validation.Optional(validation.Range(0, sys.maxint)),
      UNHEALTHY_THRESHOLD: validation.Optional(validation.Range(0, sys.maxint)),
      HEALTHY_THRESHOLD: validation.Optional(validation.Range(0, sys.maxint)),
      RESTART_THRESHOLD: validation.Optional(validation.Range(0, sys.maxint)),
      HOST: validation.Optional(validation.TYPE_STR)}


class VmHealthCheck(HealthCheck):
  """Class representing the configuration of VM health check.

     This class is deprecated and will be removed (use HealthCheck).
  """
  pass


class Resources(validation.Validated):
  """Class representing the configuration of VM resources."""

  ATTRIBUTES = {
      CPU: validation.Optional(validation.TYPE_FLOAT),
      MEMORY_GB: validation.Optional(validation.TYPE_FLOAT),
      DISK_SIZE_GB: validation.Optional(validation.TYPE_INT)
  }


class Network(validation.Validated):
  """Class representing the VM network configuration."""

  ATTRIBUTES = {
      # A list of port mappings in the form 'port' or 'external:internal'.
      FORWARDED_PORTS: validation.Optional(validation.Repeated(validation.Regex(
          '[0-9]+(:[0-9]+)?(/(udp|tcp))?'))),

      INSTANCE_TAG: validation.Optional(validation.Regex(
          GCE_RESOURCE_NAME_REGEX)),

      NETWORK_NAME: validation.Optional(validation.Regex(
          GCE_RESOURCE_NAME_REGEX)),
  }


class AppInclude(validation.Validated):
  """Class representing the contents of an included app.yaml file.

  Used for both builtins and includes directives.
  """

  # TODO(user): It probably makes sense to have a scheme where we do a
  # deep-copy of fields from AppInfoExternal when setting the ATTRIBUTES here.
  # Right now it's just copypasta.
  ATTRIBUTES = {
      BUILTINS: validation.Optional(validation.Repeated(BuiltinHandler)),
      INCLUDES: validation.Optional(validation.Type(list)),
      HANDLERS: validation.Optional(validation.Repeated(URLMap), default=[]),
      ADMIN_CONSOLE: validation.Optional(AdminConsole),
      MANUAL_SCALING: validation.Optional(ManualScaling),
      VM: validation.Optional(bool),
      VM_SETTINGS: validation.Optional(VmSettings),
      BETA_SETTINGS: validation.Optional(BetaSettings),
      ENV_VARIABLES: validation.Optional(EnvironmentVariables),
      SKIP_FILES: validation.RegexStr(default=SKIP_NO_FILES),
      # TODO(user): add LIBRARIES here when we have a good story for
      # handling contradictory library requests.
  }

  @classmethod
  def MergeManualScaling(cls, appinclude_one, appinclude_two):
    """Takes the greater of <manual_scaling.instances> from the args.

    Note that appinclude_one is mutated to be the merged result in this process.

    Also, this function needs to be updated if ManualScaling gets additional
    fields.

    Args:
      appinclude_one: object one to merge. Must have a "manual_scaling" field
        which contains a ManualScaling().
      appinclude_two: object two to merge. Must have a "manual_scaling" field
        which contains a ManualScaling().

    Returns:
      Object that is the result of merging
      appinclude_one.manual_scaling.instances and
      appinclude_two.manual_scaling.instances. I.e., <appinclude_one>
      after the mutations are complete.
    """

    def _Instances(appinclude):
      if appinclude.manual_scaling:
        if appinclude.manual_scaling.instances:
          return int(appinclude.manual_scaling.instances)
      return None

    # We only want to mutate a param if at least one of the given
    # arguments has manual_scaling.instances set.
    instances = max(_Instances(appinclude_one), _Instances(appinclude_two))
    if instances is not None:
      appinclude_one.manual_scaling = ManualScaling(instances=str(instances))
    return appinclude_one

  @classmethod
  def _CommonMergeOps(cls, one, two):
    """This function performs common merge operations."""
    # Merge ManualScaling.
    AppInclude.MergeManualScaling(one, two)

    # Merge AdminConsole objects.
    one.admin_console = AdminConsole.Merge(one.admin_console,
                                           two.admin_console)

    # Preserve the specific value of one.vm (None or False) when neither
    # are True.
    one.vm = two.vm or one.vm

    # Merge VmSettings objects.
    one.vm_settings = VmSettings.Merge(one.vm_settings,
                                       two.vm_settings)

    # Merge BetaSettings objects.
    if hasattr(one, 'beta_settings'):
      one.beta_settings = BetaSettings.Merge(one.beta_settings,
                                             two.beta_settings)

    # Merge EnvironmentVariables objects. The values in two.env_variables
    # override the ones in one.env_variables in case of conflict.
    one.env_variables = EnvironmentVariables.Merge(one.env_variables,
                                                   two.env_variables)

    one.skip_files = cls.MergeSkipFiles(one.skip_files, two.skip_files)

    return one

  @classmethod
  def MergeAppYamlAppInclude(cls, appyaml, appinclude):
    """This function merges an app.yaml file with referenced builtins/includes.
    """
    # All merge operations should occur in this function or in functions
    # referenced from this one.  That makes it much easier to understand what
    # goes wrong when included files are not merged correctly.

    if not appinclude:
      return appyaml

    # Merge handlers while paying attention to position attribute.
    if appinclude.handlers:
      tail = appyaml.handlers or []
      appyaml.handlers = []

      for h in appinclude.handlers:
        if not h.position or h.position == 'head':
          appyaml.handlers.append(h)
        else:
          tail.append(h)
        # Get rid of the position attribute since we no longer need it, and is
        # technically invalid to include in the resulting merged app.yaml file
        # that will be sent when deploying the application.
        h.position = None

      appyaml.handlers.extend(tail)

    appyaml = cls._CommonMergeOps(appyaml, appinclude)
    appyaml.NormalizeVmSettings()
    return appyaml

  @classmethod
  def MergeAppIncludes(cls, appinclude_one, appinclude_two):
    """Merges the non-referential state of the provided AppInclude.

    That is, builtins and includes directives are not preserved, but
    any static objects are copied into an aggregate AppInclude object that
    preserves the directives of both provided AppInclude objects.

    Note that appinclude_one is mutated to be the merged result in this process.

    Args:
      appinclude_one: object one to merge
      appinclude_two: object two to merge

    Returns:
      AppInclude object that is the result of merging the static directives of
      appinclude_one and appinclude_two. I.e., <appinclude_one> after the
      mutations are complete.
    """

    # If one or both appinclude objects were None, return the object which was
    # not None or return None.
    if not appinclude_one or not appinclude_two:
      return appinclude_one or appinclude_two
    # Now, both appincludes are non-None.

    # Merge handlers.
    if appinclude_one.handlers:
      if appinclude_two.handlers:
        appinclude_one.handlers.extend(appinclude_two.handlers)
    else:
      appinclude_one.handlers = appinclude_two.handlers

    return cls._CommonMergeOps(appinclude_one, appinclude_two)

  @staticmethod
  def MergeSkipFiles(skip_files_one, skip_files_two):
    if skip_files_one == SKIP_NO_FILES:
      return skip_files_two
    if skip_files_two == SKIP_NO_FILES:
      return skip_files_one
    return validation.RegexStr().Validate(
        [skip_files_one, skip_files_two], SKIP_FILES)
    # We exploit the handling of RegexStr where regex properties can be
    # specified as a list of regexes that are then joined with |.


class AppInfoExternal(validation.Validated):
  """Class representing users application info.

  This class is passed to a yaml_object builder to provide the validation
  for the application information file format parser.

  Attributes:
    application: Unique identifier for application.
    version: Application's major version.
    runtime: Runtime used by application.
    api_version: Which version of APIs to use.
    source_language: Optional specification of the source language.
      For example we specify "php-quercus" if this is a Java app
      that was generated from PHP source using Quercus
    handlers: List of URL handlers.
    default_expiration: Default time delta to use for cache expiration for
      all static files, unless they have their own specific 'expiration' set.
      See the URLMap.expiration field's documentation for more information.
    skip_files: An re object.  Files that match this regular expression will
      not be uploaded by appcfg.py.  For example:
        skip_files: |
          .svn.*|
          #.*#
    nobuild_files: An re object.  Files that match this regular expression will
      not be built into the app.  Go only.
    api_config: URL root and script/servlet path for enhanced api serving
  """

  ATTRIBUTES = {
      # Regular expressions for these attributes are defined in
      # //apphosting/base/id_util.cc.
      APPLICATION: validation.Optional(APPLICATION_RE_STRING),
      # An alias for APPLICATION.
      PROJECT: validation.Optional(APPLICATION_RE_STRING),
      MODULE: validation.Optional(MODULE_ID_RE_STRING),
      # 'service' will replace 'module' soon
      SERVICE: validation.Optional(MODULE_ID_RE_STRING),
      VERSION: validation.Optional(MODULE_VERSION_ID_RE_STRING),
      RUNTIME: validation.Optional(RUNTIME_RE_STRING),
      # A new api_version requires a release of the dev_appserver, so it
      # is ok to hardcode the version names here.
      API_VERSION: validation.Optional(API_VERSION_RE_STRING),
      # The App Engine environment to run this version in. (VM vs. non-VM, etc.)
      ENV: validation.Optional(ENV_RE_STRING),
      # The SDK will use this for generated Dockerfiles
      ENTRYPOINT: validation.Optional(validation.Type(str)),
      RUNTIME_CONFIG: validation.Optional(RuntimeConfig),
      INSTANCE_CLASS: validation.Optional(_INSTANCE_CLASS_REGEX),
      SOURCE_LANGUAGE: validation.Optional(
          validation.Regex(SOURCE_LANGUAGE_RE_STRING)),
      AUTOMATIC_SCALING: validation.Optional(AutomaticScaling),
      MANUAL_SCALING: validation.Optional(ManualScaling),
      BASIC_SCALING: validation.Optional(BasicScaling),
      VM: validation.Optional(bool),
      VM_SETTINGS: validation.Optional(VmSettings),  # Deprecated
      BETA_SETTINGS: validation.Optional(BetaSettings),
      VM_HEALTH_CHECK: validation.Optional(VmHealthCheck),  # Deprecated
      HEALTH_CHECK: validation.Optional(HealthCheck),
      RESOURCES: validation.Optional(Resources),
      NETWORK: validation.Optional(Network),
      BUILTINS: validation.Optional(validation.Repeated(BuiltinHandler)),
      INCLUDES: validation.Optional(validation.Type(list)),
      HANDLERS: validation.Optional(validation.Repeated(URLMap), default=[]),
      LIBRARIES: validation.Optional(validation.Repeated(Library)),
      # TODO(arb): change to a regex when validation.Repeated supports it
      SERVICES: validation.Optional(validation.Repeated(
          validation.Regex(_SERVICE_RE_STRING))),
      DEFAULT_EXPIRATION: validation.Optional(_EXPIRATION_REGEX),
      SKIP_FILES: validation.RegexStr(default=DEFAULT_SKIP_FILES),
      NOBUILD_FILES: validation.RegexStr(default=DEFAULT_NOBUILD_FILES),
      DERIVED_FILE_TYPE: validation.Optional(validation.Repeated(
          validation.Options(JAVA_PRECOMPILED, PYTHON_PRECOMPILED))),
      ADMIN_CONSOLE: validation.Optional(AdminConsole),
      ERROR_HANDLERS: validation.Optional(validation.Repeated(ErrorHandlers)),
      BACKENDS: validation.Optional(validation.Repeated(
          backendinfo.BackendEntry)),
      THREADSAFE: validation.Optional(bool),
      DATASTORE_AUTO_ID_POLICY: validation.Optional(
          validation.Options(DATASTORE_ID_POLICY_LEGACY,
                             DATASTORE_ID_POLICY_DEFAULT)),
      API_CONFIG: validation.Optional(ApiConfigHandler),
      CODE_LOCK: validation.Optional(bool),
      ENV_VARIABLES: validation.Optional(EnvironmentVariables),
  }

  def CheckInitialized(self):
    """Performs non-regex-based validation.

    The following are verified:
      - At least one url mapping is provided in the URL mappers.
      - Number of url mappers doesn't exceed MAX_URL_MAPS.
      - Major version does not contain the string -dot-.
      - If api_endpoints are defined, an api_config stanza must be defined.
      - If the runtime is python27 and threadsafe is set, then no CGI handlers
        can be used.
      - That the version name doesn't start with BUILTIN_NAME_PREFIX
      - If redirect_http_response_code exists, it is in the list of valid 300s.
      - That module and service aren't both set

    Raises:
      DuplicateLibrary: if the name library name is specified more than once.
      MissingURLMapping: if no URLMap object is present in the object.
      TooManyURLMappings: if there are too many URLMap entries.
      MissingApiConfig: if api_endpoints exist without an api_config.
      MissingThreadsafe: if threadsafe is not set but the runtime requires it.
      ThreadsafeWithCgiHandler: if the runtime is python27, threadsafe is set
          and CGI handlers are specified.
      TooManyScalingSettingsError: if more than one scaling settings block is
          present.
      RuntimeDoesNotSupportLibraries: if libraries clause is used for a runtime
          that does not support it (e.g. python25).
      ModuleAndServiceDefined: if both 'module' and 'service' keywords are used.
    """
    super(AppInfoExternal, self).CheckInitialized()
    if self.runtime is None and not self.IsVm():
      raise appinfo_errors.MissingRuntimeError(
          'You must specify a "runtime" field for non-vm applications.')
    elif self.runtime is None:
      # Default optional to custom (we don't do that in attributes just so
      # we know that it's been defaulted)
      self.runtime = 'custom'
    if (not self.handlers and not self.builtins and not self.includes
        and not self.IsVm()):
      raise appinfo_errors.MissingURLMapping(
          'No URLMap entries found in application configuration')
    if self.handlers and len(self.handlers) > MAX_URL_MAPS:
      raise appinfo_errors.TooManyURLMappings(
          'Found more than %d URLMap entries in application configuration' %
          MAX_URL_MAPS)
    if self.service and self.module:
      raise appinfo_errors.ModuleAndServiceDefined(
          'Cannot define both "module" and "service" in configuration')

    vm_runtime_python27 = (
        self.runtime == 'vm' and
        (hasattr(self, 'vm_settings') and
         self.vm_settings and
         self.vm_settings.get('vm_runtime') == 'python27') or
        (hasattr(self, 'beta_settings') and
         self.beta_settings and
         self.beta_settings.get('vm_runtime') == 'python27'))

    if (self.threadsafe is None and
        (self.runtime == 'python27' or vm_runtime_python27)):
      raise appinfo_errors.MissingThreadsafe(
          'threadsafe must be present and set to a true or false YAML value')

    if self.auto_id_policy == DATASTORE_ID_POLICY_LEGACY:
      datastore_auto_ids_url = ('http://developers.google.com/'
                                'appengine/docs/python/datastore/'
                                'entities#Kinds_and_Identifiers')
      appcfg_auto_ids_url = ('http://developers.google.com/appengine/docs/'
                             'python/config/appconfig#auto_id_policy')
      logging.warning(
          "You have set the datastore auto_id_policy to 'legacy'. It is "
          "recommended that you select 'default' instead.\n"
          "Legacy auto ids are deprecated. You can continue to allocate\n"
          "legacy ids manually using the allocate_ids() API functions.\n"
          "For more information see:\n"
          + datastore_auto_ids_url + '\n' + appcfg_auto_ids_url + '\n')

    if (hasattr(self, 'beta_settings') and self.beta_settings
        and self.beta_settings.get('source_reference')):
      ValidateCombinedSourceReferencesString(
          self.beta_settings.get('source_reference'))

    if self.libraries:
      if not (vm_runtime_python27 or self.runtime == 'python27'):
        raise appinfo_errors.RuntimeDoesNotSupportLibraries(
            'libraries entries are only supported by the "python27" runtime')

      library_names = [library.name for library in self.libraries]
      for library_name in library_names:
        if library_names.count(library_name) > 1:
          raise appinfo_errors.DuplicateLibrary(
              'Duplicate library entry for %s' % library_name)

    if self.version and self.version.find(ALTERNATE_HOSTNAME_SEPARATOR) != -1:
      raise validation.ValidationError(
          'Version "%s" cannot contain the string "%s"' % (
              self.version, ALTERNATE_HOSTNAME_SEPARATOR))
    if self.version and self.version.startswith(BUILTIN_NAME_PREFIX):
      raise validation.ValidationError(
          ('Version "%s" cannot start with "%s" because it is a '
           'reserved version name prefix.') % (self.version,
                                               BUILTIN_NAME_PREFIX))
    if self.handlers:
      api_endpoints = [handler.url for handler in self.handlers
                       if handler.GetHandlerType() == HANDLER_API_ENDPOINT]
      if api_endpoints and not self.api_config:
        raise appinfo_errors.MissingApiConfig(
            'An api_endpoint handler was specified, but the required '
            'api_config stanza was not configured.')
      if self.threadsafe and self.runtime == 'python27':
        # VMEngines can handle python25 handlers, so we don't include
        # vm_runtime_python27 in the if statement above.
        for handler in self.handlers:
          if (handler.script and (handler.script.endswith('.py') or
                                  '/' in handler.script)):
            raise appinfo_errors.ThreadsafeWithCgiHandler(
                'threadsafe cannot be enabled with CGI handler: %s' %
                handler.script)
    if sum([bool(self.automatic_scaling),
            bool(self.manual_scaling),
            bool(self.basic_scaling)]) > 1:
      raise appinfo_errors.TooManyScalingSettingsError(
          "There may be only one of 'automatic_scaling', 'manual_scaling', "
          "or 'basic_scaling'.")

  def GetAllLibraries(self):
    """Returns a list of all Library instances active for this configuration.

    Returns:
      The list of active Library instances for this configuration. This includes
      directly-specified libraries as well as any required dependencies.
    """
    if not self.libraries:
      return []

    library_names = set(library.name for library in self.libraries)
    required_libraries = []

    for library in self.libraries:
      for required_name, required_version in REQUIRED_LIBRARIES.get(
          (library.name, library.version), []):
        if required_name not in library_names:
          required_libraries.append(Library(name=required_name,
                                            version=required_version))

    return [Library(**library.ToDict())
            for library in self.libraries + required_libraries]

  def GetNormalizedLibraries(self):
    """Returns a list of normalized Library instances for this configuration.

    Returns:
      The list of active Library instances for this configuration. This includes
      directly-specified libraries, their required dependencies as well as any
      libraries enabled by default. Any libraries with "latest" as their version
      will be replaced with the latest available version.
    """
    libraries = self.GetAllLibraries()
    enabled_libraries = set(library.name for library in libraries)
    for library in _SUPPORTED_LIBRARIES:
      if library.default_version and library.name not in enabled_libraries:
        libraries.append(Library(name=library.name,
                                 version=library.default_version))
    return libraries

  def ApplyBackendSettings(self, backend_name):
    """Applies settings from the indicated backend to the AppInfoExternal.

    Backend entries may contain directives that modify other parts of the
    app.yaml, such as the 'start' directive, which adds a handler for the start
    request.  This method performs those modifications.

    Args:
      backend_name: The name of a backend defined in 'backends'.

    Raises:
      BackendNotFound: if the indicated backend was not listed in 'backends'.
      DuplicateBackend: if backend is found more than once in 'backends'.
    """
    if backend_name is None:
      return

    if self.backends is None:
      raise appinfo_errors.BackendNotFound

    self.version = backend_name

    match = None
    for backend in self.backends:
      if backend.name != backend_name:
        continue
      if match:
        raise appinfo_errors.DuplicateBackend
      else:
        match = backend

    if match is None:
      raise appinfo_errors.BackendNotFound

    if match.start is None:
      return

    start_handler = URLMap(url=_START_PATH, script=match.start)
    self.handlers.insert(0, start_handler)

  def GetEffectiveRuntime(self):
    """Returns the app's runtime, resolving VMs to the underlying vm_runtime.

    Returns:
      The effective runtime: the value of beta/vm_settings.vm_runtime if
      runtime is "vm", or runtime otherwise.
    """
    if (self.runtime == 'vm' and hasattr(self, 'vm_settings')
        and self.vm_settings is not None):
      return self.vm_settings.get('vm_runtime')
    if (self.runtime == 'vm' and hasattr(self, 'beta_settings')
        and self.beta_settings is not None):
      return self.beta_settings.get('vm_runtime')
    return self.runtime

  def SetEffectiveRuntime(self, runtime):
    """Sets the runtime while respecting vm runtimes rules for runtime settings.

    Args:
       runtime: The runtime to use.
    """
    if self.IsVm():
      if not self.vm_settings:
        self.vm_settings = VmSettings()

      # Patch up vm runtime setting. Copy 'runtime' to 'vm_runtime' and
      # set runtime to the string 'vm'.
      self.vm_settings['vm_runtime'] = runtime
      self.runtime = 'vm'
    else:
      self.runtime = runtime

  def NormalizeVmSettings(self):
    """Normalize Vm settings.
    """
    # NOTE(user): In the input files, 'vm' is not a type of runtime, but
    # rather is specified as "vm: true|false". In the code, 'vm'
    # is represented as a value of AppInfoExternal.runtime.
    # NOTE(user): This hack is only being applied after the parsing of
    # AppInfoExternal. If the 'vm' attribute can ever be specified in the
    # AppInclude, then this processing will need to be done there too.
    if self.IsVm():
      if not self.vm_settings:
        self.vm_settings = VmSettings()

      if 'vm_runtime' not in self.vm_settings:
        self.SetEffectiveRuntime(self.runtime)

      # Copy fields that are automatically added by the SDK or this class
      # to beta_settings.
      if hasattr(self, 'beta_settings') and self.beta_settings:
        # Only copy if beta_settings already exists, because we have logic in
        # appversion.py to discard all of vm_settings if anything is in
        # beta_settings.  So we won't create an empty one just to add these
        # fields.
        for field in ['vm_runtime',
                      'has_docker_image',
                      'image',
                      'module_yaml_path']:
          if field not in self.beta_settings and field in self.vm_settings:
            self.beta_settings[field] = self.vm_settings[field]

  # TODO(user): env replaces vm. Remove vm when field is removed.
  def IsVm(self):
    return (self.vm or
            self.env in ['2', 'flex', 'flexible'])

def ValidateHandlers(handlers, is_include_file=False):
  """Validates a list of handler (URLMap) objects.

  Args:
    handlers: A list of a handler (URLMap) objects.
    is_include_file: If true, indicates the we are performing validation
      for handlers in an AppInclude file, which may contain special directives.
  """
  if not handlers:
    return

  for handler in handlers:
    handler.FixSecureDefaults()
    handler.WarnReservedURLs()
    if not is_include_file:
      handler.ErrorOnPositionForAppInfo()


def LoadSingleAppInfo(app_info):
  """Load a single AppInfo object where one and only one is expected.

  Validates that the the values in the AppInfo match the validators defined
  in this file. (in particular, in AppInfoExternal.ATTRIBUTES)

  Args:
    app_info: A file-like object or string.  If it is a string, parse it as
    a configuration file.  If it is a file-like object, read in data and
    parse.

  Returns:
    An instance of AppInfoExternal as loaded from a YAML file.

  Raises:
    ValueError: if a specified service is not valid.
    EmptyConfigurationFile: when there are no documents in YAML file.
    MultipleConfigurationFile: when there is more than one document in YAML
      file.
    DuplicateBackend: if backend is found more than once in 'backends'.
    yaml_errors.EventError: if the app.yaml fails validation.
    appinfo_errors.MultipleProjectNames: if the app.yaml has both 'application'
      and 'project'.
  """
  builder = yaml_object.ObjectBuilder(AppInfoExternal)
  handler = yaml_builder.BuilderHandler(builder)
  listener = yaml_listener.EventListener(handler)
  listener.Parse(app_info)

  app_infos = handler.GetResults()
  if len(app_infos) < 1:
    raise appinfo_errors.EmptyConfigurationFile()
  if len(app_infos) > 1:
    raise appinfo_errors.MultipleConfigurationFile()

  appyaml = app_infos[0]
  ValidateHandlers(appyaml.handlers)
  if appyaml.builtins:
    BuiltinHandler.Validate(appyaml.builtins, appyaml.runtime)

  # Allow "project: name" as an alias for "application: name". If found, we
  # change the project field to None. (Deleting it would make a distinction
  # between loaded and constructed AppInfoExternal objects, since the latter
  # would still have the project field.)
  if appyaml.application and appyaml.project:
    raise appinfo_errors.MultipleProjectNames(
        'Specify one of "application: name" or "project: name"')
  elif appyaml.project:
    appyaml.application = appyaml.project
    appyaml.project = None

  appyaml.NormalizeVmSettings()
  return appyaml


class AppInfoSummary(validation.Validated):
  """This class contains only basic summary information about an app.

  It is used to pass back information about the newly created app to users
  after a new version has been created.
  """
  # NOTE(user): Before you consider adding anything to this YAML definition,
  # you must solve the issue that old SDK versions will try to parse this new
  # value with the old definition and fail.  Basically we are stuck with this
  # definition for the time being.  The parsing of the value is done in
  ATTRIBUTES = {
      APPLICATION: APPLICATION_RE_STRING,
      MAJOR_VERSION: MODULE_VERSION_ID_RE_STRING,
      MINOR_VERSION: validation.TYPE_LONG
  }


def LoadAppInclude(app_include):
  """Load a single AppInclude object where one and only one is expected.

  Args:
    app_include: A file-like object or string.  If it is a string, parse it as
    a configuration file.  If it is a file-like object, read in data and
    parse.

  Returns:
    An instance of AppInclude as loaded from a YAML file.

  Raises:
    EmptyConfigurationFile: when there are no documents in YAML file.
    MultipleConfigurationFile: when there is more than one document in YAML
    file.
  """
  builder = yaml_object.ObjectBuilder(AppInclude)
  handler = yaml_builder.BuilderHandler(builder)
  listener = yaml_listener.EventListener(handler)
  listener.Parse(app_include)

  includes = handler.GetResults()
  if len(includes) < 1:
    raise appinfo_errors.EmptyConfigurationFile()
  if len(includes) > 1:
    raise appinfo_errors.MultipleConfigurationFile()

  includeyaml = includes[0]
  if includeyaml.handlers:
    for handler in includeyaml.handlers:
      handler.FixSecureDefaults()
      handler.WarnReservedURLs()
  if includeyaml.builtins:
    BuiltinHandler.Validate(includeyaml.builtins)

  return includeyaml


def ParseExpiration(expiration):
  """Parses an expiration delta string.

  Args:
    expiration: String that matches _DELTA_REGEX.

  Returns:
    Time delta in seconds.
  """
  delta = 0
  for match in re.finditer(_DELTA_REGEX, expiration):
    amount = int(match.group(1))
    units = _EXPIRATION_CONVERSIONS.get(match.group(2).lower(), 1)
    delta += amount * units
  return delta


#####################################################################
# These regexps must be the same as those in apphosting/client/app_config.cc
# and java/com/google/appengine/tools/admin/AppVersionUpload.java

# Valid characters for a filename.
_file_path_positive_re = re.compile(r'^[ 0-9a-zA-Z\._\+/@\$-]{1,256}$')

# Forbid ., .., and leading -, _ah/ or /
_file_path_negative_1_re = re.compile(r'\.\.|^\./|\.$|/\./|^-|^_ah/|^/')

# Forbid // and trailing /
_file_path_negative_2_re = re.compile(r'//|/$')

# Forbid any use of space other than in the middle of a directory or file
# name.
_file_path_negative_3_re = re.compile(r'^ | $|/ | /')


def ValidFilename(filename):
  """Determines if filename is valid.

  filename must be a valid pathname.
  - It must contain only letters, numbers, @, _, +, /, $, ., and -.
  - It must be less than 256 chars.
  - It must not contain "/./", "/../", or "//".
  - It must not end in "/".
  - All spaces must be in the middle of a directory or file name.

  Args:
    filename: The filename to validate.

  Returns:
    An error string if the filename is invalid.  Returns '' if the filename
    is valid.
  """
  if _file_path_positive_re.match(filename) is None:
    return 'Invalid character in filename: %s' % filename
  if _file_path_negative_1_re.search(filename) is not None:
    return ('Filename cannot contain "." or ".." '
            'or start with "-" or "_ah/": %s' %
            filename)
  if _file_path_negative_2_re.search(filename) is not None:
    return 'Filename cannot have trailing / or contain //: %s' % filename
  if _file_path_negative_3_re.search(filename) is not None:
    return 'Any spaces must be in the middle of a filename: %s' % filename
  return ''
