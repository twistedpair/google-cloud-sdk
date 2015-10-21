# Copyright 2015 Google Inc. All Rights Reserved.

"""A command that reads JSON data and lists it."""

import json
import sys

from googlecloudsdk.calliope import base
from googlecloudsdk.core.resource import resource_filter
from googlecloudsdk.core.resource import resource_lex
from googlecloudsdk.core.resource import resource_printer
from googlecloudsdk.core.resource import resource_property


class Aggregator(object):
  """Aggregates a field in an iterable object to a single list.

  The returned object is another iterable.

  Example:
    iterable = Aggregator(iterable, key)
    for item in iterable:
      VisitEachItemInEachResourceList(item)

  Attributes:
    _iterable: The original iterable.
    _key: The lexed key name.
    _list: The current list.
    _stop: If True then the object is not iterable and it has already been
      returned.
  """

  def __init__(self, iterable, key):
    self._iterable = iterable
    self._key = key
    self._list = []
    self._index = 0
    self._stop = False

  def __iter__(self):
    return self

  def _NextItem(self):
    """Returns the next item from self._iterable.

    Raises:
      StopIteration when self._iterable is exhausted.

    Returns:
      The next item from self._iterable.
    """
    try:
      # Object is a generator or iterator.
      return self._iterable.next()
    except AttributeError:
      pass
    try:
      # Object is a list.
      return self._iterable.pop(0)
    except (AttributeError, KeyError, TypeError):
      pass
    except IndexError:
      raise StopIteration
    # Object is not iterable -- treat it as the only item.
    if self._iterable is None or self._stop:
      raise StopIteration
    self._stop = True
    return self._iterable

  def next(self):
    """Returns the next item in the aggregated list."""
    while self._index >= len(self._list):
      obj = self._NextItem()
      self._list = resource_property.Get(obj, self._key) or []
      if not isinstance(self._list, list):
        self._list = [self._list]
      self._index = 0
    item = self._list[self._index]
    self._index += 1
    return item


class ListFromJson(base.Command):
  """Read JSON data and list it on the standard output.

  *{command}* is a test harness for the output resource *--aggregate*,
  *--filter* and *--format* flags. It behaves like any other `gcloud ... list`
  command with respect to those flags.

  The input JSON data is either a single resource object or a list of resource
  objects of the same type. The resources are printed on the standard output.
  The default output format is *json*.
  """

  @staticmethod
  def Args(parser):
    # TODO(gsfowler): Drop --aggregate when the --aggregate global flag lands.
    parser.add_argument(
        '--aggregate',
        metavar='KEY',
        default=None,
        help=('Aggregate the lists named by KEY into a single list'
              ' that can be controlled by *--filter* and *--format*.'))
    # TODO(gsfowler): Drop --filter when the --filter global flag lands.
    parser.add_argument(
        '--filter',
        default=None,
        help=('A resource filter expression. Only resource items matching'
              ' the filter expression are printed. For example,'
              ' --filter="foo.bar=OK AND x.y<10".'))
    parser.add_argument(
        'json_file',
        metavar='JSON-FILE',
        nargs='?',
        default=None,
        help=('A file containing JSON data for a single resource or a list of'
              ' resources of the same type. If omitted then the standard input'
              ' is read.'))

  def Run(self, args):
    if args.json_file:
      with open(args.json_file, 'r') as f:
        resources = json.load(f)
    else:
      resources = json.load(sys.stdin)
    # TODO(gsfowler): Drop this if when the --aggregate global flag lands.
    if args.aggregate:
      key = resource_lex.Lexer(args.aggregate).Key()
      resources = Aggregator(resources, key)
    # TODO(gsfowler): Return resources here when the --filter global flag lands.
    if not args.format:
      args.format = 'json'
    if not args.filter:
      return resources
    select = resource_filter.Compile(args.filter).Evaluate
    filtered_resources = []
    if resource_property.IsListLike(resources):
      for resource in resources:
        if select(resource):
          filtered_resources.append(resource)
    elif select(resources):
      # treat non-iterable resources as a list of length 1
      filtered_resources.append(resources)
    return filtered_resources

  # TODO(gsfowler): Drop Display() when the --filter global flag lands.
  def Display(self, args, resources):
    resource_printer.Print(resources, 'json')
