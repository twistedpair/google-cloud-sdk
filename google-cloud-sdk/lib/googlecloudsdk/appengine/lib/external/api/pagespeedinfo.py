# Copyright 2015 Google Inc. All Rights Reserved.
#!/usr/bin/python2.4
#
# Copyright 2012 Google Inc. All Rights Reserved.

"""PageSpeed configuration tools.

Library for parsing pagespeed configuration data from app.yaml and working
with these in memory.
"""



# WARNING: This file is externally viewable by our users.  All comments from
# this file will be stripped.  The docstrings will NOT.  Do not put sensitive
# information in docstrings.  If you must communicate internal information in
# this source file, please place them in comments only.


from googlecloudsdk.appengine.lib.external.api import validation
from googlecloudsdk.appengine.lib.external.api import yaml_builder
from googlecloudsdk.appengine.lib.external.api import yaml_listener
from googlecloudsdk.appengine.lib.external.api import yaml_object

_URL_BLACKLIST_REGEX = r'http(s)?://\S{0,499}'
_REWRITER_NAME_REGEX = r'[a-zA-Z0-9_]+'
_DOMAINS_TO_REWRITE_REGEX = r'(http(s)?://)?[-a-zA-Z0-9_.*]+(:\d+)?'

URL_BLACKLIST = 'url_blacklist'
ENABLED_REWRITERS = 'enabled_rewriters'
DISABLED_REWRITERS = 'disabled_rewriters'
DOMAINS_TO_REWRITE = 'domains_to_rewrite'


class MalformedPagespeedConfiguration(Exception):
  """Configuration file for PageSpeed API is malformed."""


# Note: we don't validate the names of enabled/disabled rewriters in this code,
# since the list is subject to change (namely, we add new rewriters, and want to
# be able to make them available to users without tying ourselves to App
# Engine's release cycle, or worry about keeping the two lists in sync).
class PagespeedEntry(validation.Validated):
  """Describes the format of a pagespeed configuration from a yaml file.

  URL blacklist entries are patterns (with '?' and '*' as wildcards).  Any URLs
  that match a pattern on the blacklist will not be optimized by PageSpeed.

  Rewriter names are strings (like 'CombineCss' or 'RemoveComments') describing
  individual PageSpeed rewriters.  A full list of valid rewriter names can be
  found in the PageSpeed documentation.

  The domains-to-rewrite list is a whitelist of domain name patterns with '*' as
  a wildcard, optionally starting with 'http://' or 'https://'.  If no protocol
  is given, 'http://' is assumed.  A resource will only be rewritten if it is on
  the same domain as the HTML that references it, or if its domain is on the
  domains-to-rewrite list.
  """
  ATTRIBUTES = {
      URL_BLACKLIST: validation.Optional(
          validation.Repeated(validation.Regex(_URL_BLACKLIST_REGEX))),
      ENABLED_REWRITERS: validation.Optional(
          validation.Repeated(validation.Regex(_REWRITER_NAME_REGEX))),
      DISABLED_REWRITERS: validation.Optional(
          validation.Repeated(validation.Regex(_REWRITER_NAME_REGEX))),
      DOMAINS_TO_REWRITE: validation.Optional(
          validation.Repeated(validation.Regex(_DOMAINS_TO_REWRITE_REGEX))),
  }


def LoadPagespeedEntry(pagespeed_entry, open_fn=None):
  """Load a yaml file or string and return a PagespeedEntry.

  Args:
    pagespeed_entry: The contents of a pagespeed entry from a yaml file
      as a string, or an open file object.
    open_fn: Function for opening files. Unused.

  Returns:
    A PagespeedEntry instance which represents the contents of the parsed yaml.

  Raises:
    yaml_errors.EventError: An error occured while parsing the yaml.
    MalformedPagespeedConfiguration: The configuration is parseable but invalid.
  """
  builder = yaml_object.ObjectBuilder(PagespeedEntry)
  handler = yaml_builder.BuilderHandler(builder)
  listener = yaml_listener.EventListener(handler)
  listener.Parse(pagespeed_entry)

  parsed_yaml = handler.GetResults()
  if not parsed_yaml:
    return PagespeedEntry()

  if len(parsed_yaml) > 1:
    raise MalformedPagespeedConfiguration(
        'Multiple configuration sections in the yaml')

  return parsed_yaml[0]
