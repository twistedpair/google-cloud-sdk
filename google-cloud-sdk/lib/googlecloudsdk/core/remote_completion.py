# Copyright 2014 Google Inc. All Rights Reserved.
"""Remote resource completion and caching."""
import logging
import os
from os import listdir
import tempfile
import threading
import time

from googlecloudsdk.core import config
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import platforms


_GETINSTANCEFUN = None

_RESOURCE_FLAGS = {
    'compute.projects': ' --project ',
    'compute.regions': ' --region ',
    'compute.zones': ' --zone ',
    'sql.projects': ' --project '
}

_OPTIONAL_PARMS = {
    'compute': [
        {'project': lambda parsed_args: parsed_args.project},
        {'region': lambda parsed_args: parsed_args.region},
        {'zone': lambda parsed_args: parsed_args.zone},
    ],
    'sql': [
        {'instance': lambda parsed_args: parsed_args.instance},
        {'project': lambda parsed_args: parsed_args.project},
    ],
}


def SetGetInstanceFun(fun):
  """Sets function to use to convert list items to instance_ref selfref.

  Args:
    fun: The function to call with the list item

  Returns:
    instance_ref: The selflink corresponding to the reference.
  """
  global _GETINSTANCEFUN
  _GETINSTANCEFUN = fun


class CompletionProgressTracker(object):
  """A context manager for telling the user about long-running completions."""

  SPIN_MARKS = [
      '|',
      '/',
      '-',
      '\\',
  ]

  def __init__(self, ofile, timeout=3.0, autotick=True):
    self._ticks = 0
    self._autotick = autotick
    self._done = False
    self._lock = threading.Lock()
    self.ofile = ofile
    self.timeout = timeout
    self.has_forked = False  # set when a child process is created

  def __enter__(self):

    if self._autotick:
      def Ticker():
        time.sleep(.2)
        self.timeout -= .2
        while True:
          if self.timeout < 0:
            self.ofile.write('?\b')
            self.ofile.flush()
            os.fork()
            # the next line indicates that the tracker has forked() the process
            self.has_forked = True
            return
          time.sleep(.1)
          self.timeout -= .1
          if self.Tick():
            return
      threading.Thread(target=Ticker).start()

    return self

  def Tick(self):
    """Give a visual indication to the user that some progress has been made."""
    with self._lock:
      if not self._done:
        self._ticks += 1
        self.ofile.write(
            CompletionProgressTracker.SPIN_MARKS[
                self._ticks % len(CompletionProgressTracker.SPIN_MARKS)] + '\b')
        self.ofile.flush()
      return self._done

  def __exit__(self, unused_type=None, unused_value=True,
               unused_traceback=None):
    with self._lock:
      self.ofile.write(' \b')
      self._done = True


def Iterate(obj, resource_refs, fun):
  if platforms.OperatingSystem.Current() == platforms.OperatingSystem.WINDOWS:
    return obj
  return Iter(iter(obj), resource_refs, fun)


class Iter(object):
  """Create an iterator that extracts the names of objects.

  Args:
    items: List of items to iterate
    resource_refs: List of resource_refs created by iterator.
  """

  def __init__(self, items, resource_refs, fun):
    self.items = items
    self.resource_refs = resource_refs
    self.fun = fun

  def next(self):
    """Returns next item in list.

    Returns:
      Next Item in the list.
    """
    item = self.items.next()
    ref = self.fun(item)
    self.resource_refs.append(ref)
    return item

  def __iter__(self):
    return self


class RemoteCompletion(object):
  """Class to cache the names of remote resources."""

  CACHE_HITS = 0
  CACHE_TRIES = 0
  _TIMEOUTS = {  # Timeouts for resources in seconds
      'sql.instances': 600,
      'compute.instances': 600,
      'compute.regions': 3600*10,
      'compute.zones': 3600*10
  }
  ITEM_NAME_FUN = {
      'compute': lambda item: item['name'],
      'sql': lambda item: item.instance
  }

  @staticmethod
  def CacheHits():
    return RemoteCompletion.CACHE_HITS

  @staticmethod
  def CacheTries():
    return RemoteCompletion.CACHE_TRIES

  def __init__(self):
    """Set the cache directory."""
    try:
      self.project = properties.VALUES.core.project.Get(required=True)
    except Exception:  # pylint:disable=broad-except
      self.project = 0
    self.cache_dir = config.Paths().completion_cache_dir
    self.flags = ''
    self.index_offset = 0
    self.account = properties.VALUES.core.account.Get(required=False)
    if self.account:
      self.index_offset = 1
      self.cache_dir = os.path.join(self.cache_dir, self.account)

  @staticmethod
  def CachePath(self_link):
    """Returns cache path corresponding to self_link.

    Args:
      self_link: A resource selflink.

    Returns:
      A file path for storing resource names.
    """
    ref = self_link.replace('https://', '')
    lst = ref.split('/')
    name = lst[-1]
    lst[-1] = '_names_'
    return [os.path.join(*lst), name]

  def ResourceIsCached(self, resource):
    """Returns True for resources that can be cached.

    Args:
      resource: The resource as subcommand.resource.

    Returns:
      True when resource is cacheable.
    """
    if resource == 'sql.instances':
      return True
    if resource.startswith('compute.'):
      return True
    return False

  def GetFromCache(self, self_link, prefix, increment_counters=True):
    """Return a list of names for the specified self_link.

    Args:
      self_link: A selflink for the desired resource.
      prefix: completion word prefix
      increment_counters: If True and found in cache, CACHE_TRIES is
      incremented.

    Returns:
      Returns a list of names if in the cache.
    """
    options = None
    if increment_counters:
      RemoteCompletion.CACHE_TRIES += 1
    path = RemoteCompletion.CachePath(self_link)[0]
    fpath = os.path.join(self.cache_dir, path)
    return self._GetAllMatchesFromCache(prefix, fpath, options,
                                        increment_counters)

  def _GetAllMatchesFromCache(self, prefix, fpath, options, increment_counters):
    """Return a list of names matching fpath.

    Args:
      prefix: completion word prefix
      fpath: A selflink for the desired resource.
      options: list of names in the cache.
      increment_counters: If True and found in cache, CACHE_HITS is incremented.

    Returns:
      Returns a list of names if in the cache.
    """
    lst = fpath.split('*')
    items = lst[0].split('/')
    if len(lst) > 1:
      # A resource flag such as --zone or --region is not specified so
      #   look at all resources with that type
      if not os.path.isdir(lst[0]):
        return None
      index = items.index('completion_cache') + self.index_offset
      if index < 0 or index >= len(items):
        return options
      flagname = _RESOURCE_FLAGS[items[index+2] + '.' + items[-2]]
      for name in listdir(lst[0]):
        self.flags = flagname + name
        fpath = lst[0] + name + lst[1]
        # make sure that the data in this path is still valid
        if os.path.isfile(fpath) and os.path.getmtime(fpath) > time.time():
          options = self._GetAllMatchesFromCache(prefix, fpath, options,
                                                 increment_counters)
        else:
          # if not valid than the cache can't be used so return no matches
          size = 0
          if os.path.isdir(os.path.dirname(fpath)):
            size = os.path.getsize(fpath)
          if size > 0:
            return None
      # for regional resources also check for global resources
      lst0 = lst[0]
      if lst0.endswith('regions/'):
        fpath = lst0[:-len('regions/')] + 'global' + lst[1]
        if os.path.isfile(fpath) and os.path.getmtime(fpath) > time.time():
          self.flags = ' --global'
          options = self. GetAllMatchesFromCache(prefix, fpath, options,
                                                 increment_counters)
      return options
    if not fpath:
      return None
    try:
      # The zone or region is specified so use it if it hasn't timed out
      if not os.path.isfile(fpath) or os.path.getmtime(fpath) <= time.time():
        return None
      with open(fpath, 'r') as f:
        data = f.read()
        if not options:
          options = []
        for item in data.split('\n'):
          if not prefix or item.startswith(prefix):
            options.append(item + self.flags)
      self.flags = ''
      if increment_counters:
        RemoteCompletion.CACHE_HITS += 1
      return options
    except IOError:
      return None

  def StoreInCache(self, self_links):
    """Store names of resources listed in  cache.

    Args:
      self_links: A list of resource instance references

    Returns:
      None
    """
    if platforms.OperatingSystem.Current() == platforms.OperatingSystem.WINDOWS:
      return None
    paths = {}
    collection = None
    for ref in self_links:
      if not collection:
        try:
          instance_ref = resources.Parse(ref)
          collection = instance_ref.Collection()
        except resources.InvalidResourceException:
          #  construct collection from self link
          lst = ref.split('/')
          collection = lst[3] + '.' + lst[-2]
      lst = RemoteCompletion.CachePath(ref)
      path = lst[0]
      name = lst[1]
      if path in paths:
        paths[path].append(name)
      else:
        paths[path] = [name]
    if not collection:
      return
    for path in paths:
      abs_path = os.path.join(self.cache_dir, path)
      dirname = os.path.dirname(abs_path)
      try:
        if not os.path.isdir(dirname):
          files.MakeDir(dirname)
        tempname = tempfile.NamedTemporaryFile(dir=dirname).name
        with open(tempname, 'w') as f:
          f.write('\n'.join(paths[path]))
        # note that atomic rename does't work on windows
        os.rename(tempname, abs_path)
        now = time.time()
        timeout = RemoteCompletion._TIMEOUTS.get(collection, 300)
        os.utime(abs_path, (now, now+timeout))
      except Exception:  # pylint: disable=broad-except
        return

  def AddToCache(self, self_link, delete=False):
    """Add the specified instance to the cache.

    Args:
      self_link: A resource selflink.
      delete: Delete the resource from the cache

    Returns:
      None
    """
    lst = RemoteCompletion.CachePath(self_link)
    path = lst[0]
    name = lst[1]
    abs_path = os.path.join(self.cache_dir, path)
    try:
      # save the current modification time on the cache file
      mtime = os.path.getmtime(abs_path)
      with open(abs_path, 'r') as f:
        data = f.read()
      options = data.split('\n')
      if delete:
        options.remove(name)
        if not options:
          os.remove(abs_path)
          return
      else:
        options.append(name)
      with open(abs_path, 'w') as f:
        f.write('\n'.join(options))
      os.utime(abs_path, (time.time(), mtime))
      # restore the current modification time on the cache file
    except OSError:
      if delete:
        return
      self.StoreInCache([self_link])
    except ValueError:
      if delete:
        return

  def DeleteFromCache(self, self_link):
    """Delete the specified instance from the cache.

    Args:
      self_link: A resource selflink.

    Returns:
      None
    """
    self.AddToCache(self_link, delete=True)

  @staticmethod
  def GetTickerStream():
    return os.fdopen(9, 'w')

  @staticmethod
  def RunListCommand(cli, command):
    return list(cli().Execute(command, call_arg_complete=False))

  @staticmethod
  def GetCompleterForResource(ro_resource, cli, ro_command_line=None):
    """Returns a completer function for the given ro_resource.

    Args:
      ro_resource: The resource as subcommand.resource.
      cli: The calliope instance.
      ro_command_line: The gcloud list command to run.

    Returns:
      A completer function for the specified resource.
    """
    if platforms.OperatingSystem.Current() == platforms.OperatingSystem.WINDOWS:
      return None
    if not ro_command_line:
      ro_command_line = ro_resource

    def RemoteCompleter(parsed_args, **unused_kwargs):
      """Run list command on resource to generates completion options."""
      resource = ro_resource
      command_line = ro_command_line
      options = []
      try:
        if hasattr(parsed_args, 'property'):
          if parsed_args.property == 'compute/region':
            resource = 'compute.regions'
            command_line = resource
          elif parsed_args.property == 'compute/zone':
            resource = 'compute.zones'
            command_line = resource
          elif parsed_args.property != 'project':
            return options
        line = os.getenv('COMP_LINE')
        prefix = ''
        if line:
          for i in range(len(line)-1, -1, -1):
            c = line[i]
            if c == ' ' or c == '\t':
              break
            prefix = c + prefix
        command = command_line.split('.') + ['list']
        project = properties.VALUES.core.project.Get(required=True)
        parms = {}
        if command[0] in _OPTIONAL_PARMS:
          for arg in _OPTIONAL_PARMS[command[0]]:
            for attrib in dict(arg):
              if hasattr(parsed_args, attrib):
                fun = arg[attrib]
                value = fun(parsed_args)
                if value:
                  parms[attrib] = value
                  command.append('--' + attrib)
                  command.append(value)
        parms['project'] = project
        resource_link = resources.Parse('+', parms, resource, resolve=False)
        resource_link = resource_link.WeakSelfLink()
        lst = resource_link.split('*')
        resource_missing = len(lst) > 1
        ccache = RemoteCompletion()
        options = ccache.GetFromCache(resource_link, prefix)
        pid = os.getpid()
        if options is None:
          properties.VALUES.core.user_output_enabled.Set(False)
          ofile = RemoteCompletion.GetTickerStream()
          tracker = CompletionProgressTracker(ofile)
          with tracker:
            items = RemoteCompletion.RunListCommand(cli, command)
          options = []
          # the following is true if tracker forked and this is the parent
          if tracker.has_forked and os.getpid() == pid:
            return options
          self_links = []
          for item in items:
            # Get a selflink for the item
            if command[0] == 'compute':
              if 'selfLink' in item:
                instance_ref = resources.Parse(item['selfLink'])
                selflink = instance_ref.SelfLink()
              elif resource_link:
                selflink = resource_link.rstrip('+') + item['name']
            elif _GETINSTANCEFUN:
              # List command provides a function to get the selflink
              selflink = _GETINSTANCEFUN(item)
            else:
              instance_ref = resources.Create(resource, project=item.project,
                                              instance=item.instance)
              selflink = instance_ref.SelfLink()
            self_links.append(selflink)
            lst = selflink.split('/')
            name = lst[-1]
            if not prefix or name.startswith(prefix):
              options.append(name)
          if self_links:
            ccache.StoreInCache(self_links)
            if tracker.has_forked:
              # the parent already exited, so exit the child
              os.exit(0)
            if resource_missing:
              options = ccache.GetFromCache(resource_link, prefix,
                                            increment_counters=False) or []
      except Exception:  # pylint:disable=broad-except
        logging.error(resource + 'completion command failed', exc_info=True)
        return []
      return options
    return RemoteCompleter

