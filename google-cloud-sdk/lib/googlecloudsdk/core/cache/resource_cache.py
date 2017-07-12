# Copyright 2017 Google Inc. All Rights Reserved.
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

"""The Cloud SDK resource cache.

A resource is an object maintained by a service. Each resource has a
corresponding URI. A URI is composed of one or more parameters. A
service-specific resource parser extracts the parameter tuple from a URI. A
corresponding resource formatter reconstructs the URI from the parameter tuple.

Each service has an API List request that returns the list of resource URIs
visible to the caller. Some APIs are aggregated and return the list of all URIs
for all parameter values. Other APIs are not aggregated and require one or more
of the parsed parameter tuple values to be specified in the list request. This
means that getting the list of all URIs for a non-aggregated resource requires
multiple List requests, ranging over the combination of all values for all
aggregate parameters.

A collection is list of resource URIs in a service visible to the caller. The
collection name uniqely identifies the collection and the service.

A resource cache is a persistent cache that stores parsed resource parameter
tuples for multiple collections. The data for a collection is in one or more
tables.

    +---------------------------+
    | resource cache            |
    | +-----------------------+ |
    | | collection            | |
    | | +-------------------+ | |
    | | | table             | | |
    | | | (key,...,col,...) | | |
    | | |       ...         | | |
    | | +-------------------+ | |
    | |         ...           | |
    | +-----------------------+ |
    |           ...             |
    +---------------------------+

A resource cache is implemented as a ResourceCache object that contains
Collection objects. A Collection is a virtual table that contains one or more
persistent cache tables. Each Collection is also an Updater that handles
resource parsing and updates. Updates are typically done by service List or
Query requests that populate the tables.

The Updater objects make this module resource agnostic. For example, there
could be updater objects that are not associated with a URI. The ResourceCache
doesn't care.

If the List request API for a collection aggregates then its parsed parameter
tuples are contained in one table. Otherwise the collection is stored in
multiple tables. The total number of tables is determined by the number of
aggregate parameters for the List API, and the number of values each aggregate
parameter can take on.
"""

import abc
import itertools
import os

from googlecloudsdk.core import config
from googlecloudsdk.core import log
from googlecloudsdk.core import module_util
from googlecloudsdk.core import properties
from googlecloudsdk.core.cache import exceptions
from googlecloudsdk.core.cache import file_cache
from googlecloudsdk.core.util import files

PERSISTENT_CACHE_IMPLEMENTATION = file_cache
DEFAULT_TIMEOUT = 1*60*60


def DeleteDeprecatedCache():
  """Silently deletes the deprecated resource completion cache if it exists."""
  cache_dir = config.Paths().completion_cache_dir
  if os.path.isdir(cache_dir):
    files.RmTree(cache_dir)


class ParameterInfo(object):
  """An object for accessing parameter values in the program state.

  "program state" is defined by this class.  It could include parsed command
  line arguments and properties.  The class also can also map between resource
  and program parameter names.

  Attributes:
    _additional_params: The list of parameter names not in the parsed resource.
    _updaters: A parameter_name => (Updater, aggregator) dict.
  """

  def __init__(self, additional_params=None, updaters=None):
    self._additional_params = additional_params or []
    self._updaters = updaters or {}

  def GetValue(self, parameter_name, check_properties=True):
    """Returns the program state string value for parameter_name.

    Args:
      parameter_name: The Parameter name.
      check_properties: Check the property value if True.

    Returns:
      The parameter value from the program state.
    """
    del parameter_name, check_properties
    return None

  def GetAdditionalParams(self):
    """Return the list of parameter names not in the parsed resource.

    These names are associated with the resource but not a specific parameter
    in the resource.  For example a global resource might not have a global
    Boolean parameter in the parsed resource, but its command line specification
    might require a --global flag to completly qualify the resource.

    Returns:
      The list of parameter names not in the parsed resource.
    """
    return self._additional_params

  def GetUpdater(self, parameter_name):
    """Returns the updater and aggregator property for parameter_name.

    Args:
      parameter_name: The Parameter name.

    Returns:
      An (updater, aggregator) tuple where updater is the Updater class and
      aggregator is True if this updater must be used to aggregate all resource
      values.
    """
    return self._updaters.get(parameter_name, (None, None))


class Parameter(object):
  """A parsed resource tuple parameter descriptor.

  A parameter tuple has one or more columns. Each has a Parameter descriptor.

  Attributes:
    column: The parameter tuple column index.
    name: The parameter name.
  """

  def __init__(self, column=0, name=None):
    self.column = column
    self.name = name


class _RuntimeParameter(Parameter):
  """A runtime Parameter.

  Attributes:
    aggregator: True if parameter is an aggregator (not aggregated by updater).
    generate: True if values must be generated for this parameter.
    table: The cache table for all possible values of the parameter.
    updater: The updater object.
    value: A default value from the program state.
  """

  def __init__(self, parameter, table, updater, value, aggregator):
    super(_RuntimeParameter, self).__init__(
        parameter.column, name=parameter.name)
    self.generate = False
    self.table = table
    self.updater = updater
    self.value = value
    self.aggregator = aggregator


class BaseUpdater(object):
  """A base object for thin updater wrappers."""


class Updater(BaseUpdater):
  """A resource cache table updater.

  An updater returns a list of parsed parameter tuples that replaces the rows in
  one cache table. It can also adjust the table timeout.

  The parameters may have their own updaters. These objects are organized as a
  tree with one resource at the root.

  Attributes:
    cache: The persistent cache object.
    collection: The resource collection name.
    columns: The number of columns in the parsed resource parameter tuple.
    parameters: A list of Parameter objects.
    timeout: The resource table timeout in seconds, 0 for no timeout (0 is easy
      to represent in a persistent cache tuple which holds strings and numbers).
  """

  __metaclass__ = abc.ABCMeta

  def __init__(self, cache=None, collection=None, columns=0, column=0,
               parameters=None, timeout=DEFAULT_TIMEOUT):
    """Updater constructor.

    Args:
      cache: The persistent cache object.
      collection: The resource collection name that (1) uniquely names the
        table(s) for the parsed resource parameters (2) is the lookup name of
        the resource URI parser. Resource collection names are unique by
        definition. Non-resource collection names must not clash with resource
        collections names. Prepending a '.' to non-resource collections names
        will avoid the clash.
      columns: The number of columns in the parsed resource parameter tuple.
        Must be >= 1.
      column: If this is an updater for an aggregate parameter then the updater
        produces a table of aggregate_resource tuples. The parent collection
        copies aggregate_resource[column] to a column in its own resource
        parameter tuple.
      parameters: A list of Parameter objects.
      timeout: The resource table timeout in seconds, 0 for no timeout.
    """
    super(Updater, self).__init__()
    self.cache = cache
    self.collection = collection
    self.columns = columns if collection else 1
    self.column = column
    self.parameters = parameters or []
    self.timeout = timeout or 0

  def _GetTableName(self):
    """Returns the table name [prefix], the module path if no collection."""
    if self.collection:
      return self.collection
    return module_util.GetModulePath(self)

  def _GetRuntimeParameters(self, parameter_info):
    """Constructs and returns the _RuntimeParameter list.

    This method constructs a muable shadow of self.parameters with updater_class
    and table instantiations. Each runtime parameter can be:

    (1) A static value derived from parameter_info.
    (2) A parameter with it's own updater_class.  The updater is used to list
        all of the possible values for the parameter.
    (3) An unknown value (None).  The possible values are contained in the
        resource cache for self.

    The Select method combines the caller supplied row template and the runtime
    parameters to filter the list of parsed resources in the resource cache.

    Args:
      parameter_info: A ParamaterInfo object for accessing parameter values in
        the program state.

    Returns:
      The runtime parameters shadow of the immutable self.parameters.
    """
    runtime_parameters = []
    for parameter in self.parameters:
      updater_class, aggregator = parameter_info.GetUpdater(parameter.name)
      if updater_class:
        # Updater object instantiation is on demand so they don't have to be
        # instantiated at import time in the static CLI tree. It also makes it
        # easier to serialize in the static CLI tree JSON object.
        updater = updater_class(cache=self.cache)
        # Instantiate the table to hold all possible values for this parameter.
        # This table is a child of the collection table. It may itself be a
        # resource object.
        table = self.cache.Table(
            updater.collection,
            columns=updater.columns,
            keys=updater.columns,
            timeout=updater.timeout)
      else:
        updater = None
        table = None
      value = parameter_info.GetValue(
          parameter.name, check_properties=aggregator)
      runtime_parameter = _RuntimeParameter(
          parameter, table, updater, value, aggregator)
      runtime_parameters.append(runtime_parameter)
    return runtime_parameters

  def ParameterInfo(self):
    """Returns the parameter info object."""
    return ParameterInfo()

  def SelectTable(self, table, row_template, parameter_info, aggregations=None):
    """Returns the list of rows matching row_template in table.

    Refreshes expired tables by calling the updater.

    Args:
      table: The persistent table object.
      row_template: A row template to match in Select().
      parameter_info: A ParamaterInfo object for accessing parameter values in
        the program state.
      aggregations: A list of aggregation Parameter objects.

    Returns:
      The list of rows matching row_template in table.
    """
    if not aggregations:
      aggregations = []
    log.info('cache table=%s aggregations=[%s]',
             table.name,
             ' '.join(['{}={}'.format(x.name, x.value) for x in aggregations]))
    try:
      return table.Select(row_template)
    except exceptions.CacheTableExpired:
      rows = self.Update(parameter_info, aggregations)
      table.DeleteRows()
      table.AddRows(rows)
      table.Validate()
      return table.Select(row_template, ignore_expiration=True)

  def Select(self, row_template, parameter_info=None):
    """Returns the list of rows matching row_template in the collection.

    All tables in the collection are in play. The row matching done by the
    cache layer conveniently prunes the number of tables accessed.

    Args:
      row_template: A row template tuple. The number of columns in the template
        must match the number of columns in the collection. A column with value
        None means match all values for the column. Each column may contain
        these wildcard characters:
          * - match any string of zero or more characters
          ? - match any character
        The matching is anchored on the left.
      parameter_info: A ParamaterInfo object for accessing parameter values in
        the program state.

    Returns:
      The list of rows that match the template row.
    """
    template = list(row_template)
    if self.columns > len(template):
      template += [None] * (self.columns - len(template))
    log.info('cache template=%s', template)
    values = []
    aggregations = []
    parameters = self._GetRuntimeParameters(parameter_info)
    for parameter in parameters:
      parameter.generate = False
      if parameter.value and template[parameter.column] in (None, '*'):
        template[parameter.column] = parameter.value
        log.info('cache parameter=%s column=%s value=%s aggregate=%s',
                 parameter.name, parameter.column, parameter.value,
                 parameter.aggregator)
        if parameter.aggregator:
          aggregations.append(parameter)
          parameter.generate = True
          values.append([parameter.value])
      elif parameter.aggregator:
        aggregations.append(parameter)
        parameter.generate = True
        sub_template = [None] * parameter.table.columns
        sub_template[parameter.updater.column] = template[parameter.column]
        rows = parameter.updater.SelectTable(
            parameter.table, sub_template, parameter_info)
        v = [row[parameter.updater.column] for row in rows]
        log.info('cache parameter=%s column=%s values=%s aggregate=%s',
                 parameter.name, parameter.column, v, parameter.aggregator)
        values.append(v)
    if not values:
      table = self.cache.Table(
          '.'.join([self._GetTableName()] + [x.value for x in aggregations]),
          columns=self.columns,
          keys=self.columns,
          timeout=self.timeout)
      return self.SelectTable(table, template, parameter_info, aggregations)
    rows = []
    for perm in itertools.product(*values):
      perm = list(perm)
      table = self.cache.Table(
          '.'.join([self._GetTableName()] + perm),
          columns=self.columns,
          keys=self.columns,
          timeout=self.timeout)
      aggregations = []
      for parameter in parameters:
        if parameter.generate:
          template[parameter.column] = perm.pop(0)
          parameter.value = template[parameter.column]
        if parameter.value:
          aggregations.append(parameter)
      rows.extend(self.SelectTable(
          table, template, parameter_info, aggregations))
    return rows

  def GetTableForRow(self, row, parameter_info=None, create=True):
    """Returns the table for row.

    Args:
      row: The fully populated resource row.
      parameter_info: A ParamaterInfo object for accessing parameter values in
        the program state.
      create: Create the table if it doesn't exist if True.

    Returns:
      The table for row.
    """
    parameters = self._GetRuntimeParameters(parameter_info)
    values = [row[p.column] for p in parameters if p.aggregator]
    return self.cache.Table(
        '.'.join([self._GetTableName()] + values),
        columns=self.columns,
        keys=self.columns,
        timeout=self.timeout,
        create=create)

  @abc.abstractmethod
  def Update(self, parameter_info=None, aggregations=None):
    """Returns the list of all current parsed resource parameters."""
    del parameter_info, aggregations


class ResourceCache(PERSISTENT_CACHE_IMPLEMENTATION.Cache):
  """A resource cache object."""

  def __init__(self, name=None, create=True):
    """ResourceCache constructor.

    Args:
      name: The persistent cache object name. If None then a default name
        conditioned on the account name is used.
          <GLOBAL_CONFIG_DIR>/cache/<ACCOUNT>/resource.cache
      create: Create the cache if it doesn't exist if True.
    """
    if not name:
      name = self.GetDefaultName()
    super(ResourceCache, self).__init__(
        name=name, create=create, version='googlecloudsdk.resource-1.0')

  @staticmethod
  def GetDefaultName():
    """Returns the default resource cache name."""
    path = [config.Paths().cache_dir]
    account = properties.VALUES.core.account.Get(required=False)
    if account:
      path.append(account)
    files.MakeDir(os.path.join(*path))
    path.append('resource.cache')
    return os.path.join(*path)
