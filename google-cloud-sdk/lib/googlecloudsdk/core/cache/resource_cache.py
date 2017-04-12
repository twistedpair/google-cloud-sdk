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
required parameters.

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
persistent cache tables. Each Collection has an updater object that
handles resource parsing and updates. Updates are done by service List requests
that populate the tables.

The Updater objects make this module resource agnostic. For example, there
could be updater objects that are not associated with a URI. The ResourceCache
doesn't care.

If the List request API for a collection aggregates then its parsed parameter
tuples are contained in one table. Otherwise the collection is stored in
multiple tables. The total number of tables is determined by the number of
required parameters for the List API, and the number of values each required
parameter can take on.
"""

import abc
import itertools
import os

from googlecloudsdk.core import config
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.cache import exceptions
from googlecloudsdk.core.cache import file_cache
from googlecloudsdk.core.util import files

PERSISTENT_CACHE_IMPLEMENTATION = file_cache


class RequiredParameter(object):
  """A parsed resource tuple required parameter descriptor.

  A parameter tuple has one or more columns. Each required column has a
  RequiredParamater object.

  Attributes:
    column: The parameter tuple column index of the required value.
    updater_class: The parameter Updater class.
    value: The default parameter value from the command line args if not None.
    name: The required parameter name.
  """

  def __init__(self, column, updater_class=None, value=None, name=None):
    """RequiredParameter constructor.

    Args:
      column: The parsed parameter column index of the required value.
      updater_class: The Updater class. This is the class of the updater for
        the values for this paramater, not the parent updater.
      value: The default value from the command line args if not None.
      name: The required value name. Used to provide default values from
        command line argument destinations or config values by the same name.
    """
    self.column = column
    self.updater_class = updater_class
    self.value = value
    self.name = name


class Updater(object):
  """A resource cache table updater.

  An updater returns a list of parsed parameter tuples that replaces the rows in
  one cache table. It can also adjust the table timeout.

  The updaters may have required parameters, and the required parameters may
  have their own updaters. These objects are organized as a tree with one
  resource at the root.

  Attributes:
    cache: The containing cache object.
    collection: The resource collection name.
    columns: The number of columns in the parsed resource parameter tuple.
    required: The list of RequiredParameter objects.
    timeout: The resource table timeout in seconds, 0 for no timeout (0 is easy
      to represent in a persistent cache tuple which holds strings and numbers).
  """

  __metaclass__ = abc.ABCMeta

  def __init__(self, cache, collection, columns, column=0, required=None,
               timeout=None):
    """Updater constructor.

    Args:
      cache: The containing cache object.
      collection: The resource collection name that (1) uniquely names the
        table(s) for the parsed resource parameters (2) is the lookup name of
        the resource URI parser. Resource collection names are unique by
        definition. Non-resource collection names must not clash with resource
        collections names. Prepending a '.' to non-resource collections names
        will avoid the clash.
      columns: The number of columns in the parsed resource parameter tuple.
        Must be >= 1.
      column: If this is an updater for a required parameter then the updater
        produces a table of required_resource tuples. The parent collection
        copies required_resource[column] to a column in its own required
        resource parameter tuple.
      required: The list of RequiredParameter objects.
      timeout: The resource table timeout in seconds, 0 for no timeout.
    """
    self.cache = cache
    self.collection = collection
    self.columns = columns
    self.column = column
    self.timeout = timeout or 0
    self.required = required or []

  @abc.abstractmethod
  def Update(self):
    """Returns the list of all current parsed resource parameters."""
    pass


class _RequiredValue(object):
  """A runtime RequiredParameter helper object.

  Attributes:
    column: The required parameter column index.
    table: The cache table for all possible values of the required parameter.
    updater: The required value updater object.
    value: A default required value from the command state.
  """

  def __init__(self, column, table, updater, value):
    """_RequiredValue constructor.

    Args:
      column: The required parameter column index.
      table: The cache table for all possible values of the required parameter.
      updater: The required value updater object.
      value: A default required value from the command state.
    """
    self.column = column
    self.table = table
    self.updater = updater
    self.value = value


class Collection(object):
  """A resource cache collection object.

  This object corresponds to a service that is identified by it's collection
  name. The updater object contains the collection name.

  Attributes:
    cache: The persistent cache object.
    required: The list of _RequiredValue objects.
    updater: The Updater object.
  """

  def __init__(self, cache, updater, create=True):
    """Collection constructor.

    Args:
      cache: The persistent cache object.
      updater: The Updater object.
      create: Create the collection if it doesn't exist if True.
    """
    self.cache = cache
    self.updater = updater
    self.required = []
    for required in self.updater.required:
      if required.updater_class:
        # Updater object instantiation is on demand so they don't have to be
        # instantiated at import time in the static CLI tree. It also makes it
        # easier to serialize in the static CLI tree JSON object.
        required_updater = required.updater_class(cache)
        # Instantiate the table to hold all possible values for this required
        # parameter. This table is a child of the collection table. It may
        # itself be a resource object.
        table = self.cache.Table(
            required_updater.collection,
            create=create,
            columns=required_updater.columns,
            keys=required_updater.columns,
            timeout=required_updater.timeout)
      else:
        required_updater = None
        table = None
      self.required.append(_RequiredValue(
          required.column, table, required_updater, required.value))

  @staticmethod
  def _SelectTable(table, updater, row_template):
    """Returns the list of rows matching row_template in table.

    Refreshes expired tables by calling the updater.

    Args:
      table: The persistent table object.
      updater: The Updater object.
      row_template: A row template to match in Select().

    Returns:
      The list of rows matching row_template in table.
    """
    try:
      return table.Select(row_template)
    except exceptions.CacheTableExpired:
      rows = updater.Update()
      table.DeleteRows()
      table.AddRows(rows)
      table.Validate()
      return table.Select(row_template, ignore_expiration=True)

  def Select(self, row_template):
    """Returns the list of rows matching row_template in the collection.

    All tables in the collection are in play. The row matching done by the
    cache layer conveniently prunes the number of tables accessed.

    Args:
      row_template: A row template tuple. The number of columns in the template
        must match the number of columns in the collection. A column with value
        None means match all values for the column. Each column may contain
        these wildcard characters:
          * - match zero or more characters
          ? - match any character
        The matching is anchored on the left.

    Returns:
      The list of rows that match the template row.
    """
    template = list(row_template)
    if self.updater.columns > len(template):
      template += [None] * (self.updater.columns - len(template))
    values = []
    for required in self.required:
      if required.value and template[required.column] in (None, '*'):
        template[required.column] = required.value
      if required.updater:
        sub_template = [None] * required.table.columns
        sub_template[required.updater.column] = template[required.column]
        rows = self._SelectTable(required.table, required.updater, sub_template)
        values.append([row[required.updater.column] for row in rows])
    log.info('row_template=%s values=%s template=%s',
             list(row_template), values, template)
    if not values:
      table = self.cache.Table(
          self.updater.collection,
          columns=self.updater.columns,
          keys=self.updater.columns,
          timeout=self.updater.timeout)
      return self._SelectTable(table, self.updater, template)
    rows = []
    for perm in itertools.product(*values):
      perm = list(perm)
      table = self.cache.Table(
          '.'.join([self.updater.collection] + perm),
          columns=self.updater.columns,
          keys=self.updater.columns,
          timeout=self.updater.timeout)
      for required in self.required:
        template[required.column] = perm.pop(0)
      rows.extend(self._SelectTable(table, self.updater, template))
    return rows


class ResourceCache(PERSISTENT_CACHE_IMPLEMENTATION.Cache):
  """A resource cache object.

  Attributes:
    cache: The persistent cache object.
  """

  def __init__(self, name=None, create=True):
    """ResourceCache constructor.

    Args:
      name: The persistent cache object name. If None then a default name
        conditioned on the account name is used.
          <GLOBAL_CONFIG_DIR>/cache/<ACCOUNT>/resource.cache
      create: Create the cache if it doesn't exist if True.
    """
    if not name:
      path = [config.Paths().cache_dir]
      account = properties.VALUES.core.account.Get(required=False)
      if account:
        path.append(account)
      files.MakeDir(os.path.join(*path))
      path.append('resource.cache')
      name = os.path.join(*path)
    super(ResourceCache, self).__init__(
        name=name, create=create, version='googlecloudsdk.resource-1.0')

  def Collection(self, updater_class, create=True):
    """Returns a collection object for updater_class.

    Args:
      updater_class: The collection Updater class.
      create: Create the persistent object if True.

    Returns:
      A collection object for updater.
    """
    # Updater object instantiation is on demand so they don't have to be
    # instantiated at import time in the static CLI tree. It also makes it
    # easiter to serialize in the static CLI tree JSON object.
    return Collection(self, updater_class(self), create=create)
