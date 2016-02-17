# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Iterable peek utilities."""


class Peeker(object):
  """Peeks the first element from an iterable.

  The returned object is another iterable that is equivalent to the original.
  If the object is not iterable then the first item is the object itself.

  Example:
    iterable = Peeker(iterable)
    first_item = iterable.Peek()
    assert list(iterable)[0] == first_item

  Attributes:
    _iterable: The original iterable.
    _peek: The first item in the iterable, or the iterable itself if its not
      iterable.
    _peek_seen: _peek was already seen by the first next() call.
  """

  def __init__(self, iterable):
    self._iterable = iterable
    self._peek = self._Peek()
    self._peek_seen = False

  def __iter__(self):
    return self

  def _Peek(self):
    """Peeks the first item from the iterable."""
    try:
      # Object is a generator or iterator.
      return self._iterable.next()
    except AttributeError:
      pass
    except StopIteration:
      self._peek_seen = True
      return None
    try:
      # Object is a list.
      return self._iterable.pop(0)
    except (AttributeError, IndexError, KeyError, TypeError):
      pass
    # Object is not iterable -- treat it as the only item.
    return self._iterable

  def next(self):
    """Returns the next item in the iterable."""
    if not self._peek_seen:
      self._peek_seen = True
      return self._peek
    try:
      # Object is a generator or iterator.
      return self._iterable.next()
    except AttributeError:
      pass
    try:
      # Object is a list.
      return self._iterable.pop(0)
    except AttributeError:
      pass
    except (AttributeError, IndexError, KeyError, TypeError):
      raise StopIteration
    # Object is not iterable -- treat it as the only item.
    raise StopIteration

  def Peek(self):
    """Returns the first item in the iterable."""
    return self._peek


class Tapper(object):
  """Taps an iterable by calling a method on each item and another when done.

  The returned object is another iterable that is equivalent to the original.
  If the object is not iterable then the first item is the object itself.

  Example:
    iterable = Tapper(iterable, call_on_each, call_after_last)
    # The next statement calls call_on_each(item) for each item and
    # call_after_last() after the last item.
    list(iterable)

  Attributes:
    _iterable: The original iterable.
    _call_on_each: If not None a method called on each item as it is fetched.
      If _call_on_each returns True then the item is returned to the caller,
      if it returns False or None then it is consumed by the tapper and not
      returned to the caller, otherwise the return value is an item that is
      injected into iterable list and returned to the caller.
    _call_after_last: If not None a method called after the last item.
    _stop: If True then the object is not iterable and it has already been
      returned.
    _injected: The previous call_on_each injected a new item and this is the
      next item to return.
  """

  def __init__(self, iterable, call_on_each=None, call_after_last=None):
    self._iterable = iterable
    self._call_on_each = call_on_each
    self._call_after_last = call_after_last
    self._stop = False
    self._injected = None

  def __iter__(self):
    return self

  def _NextItem(self):
    """Returns the next item in self._iterable."""
    if self._injected:
      item = self._injected
      self._injected = None
      return item
    try:
      # Object is a generator or iterator.
      return self._iterable.next()
    except AttributeError:
      pass
    except StopIteration:
      if self._call_after_last:
        self._call_after_last()
      raise
    try:
      # Object is a list.
      return self._iterable.pop(0)
    except (AttributeError, KeyError, TypeError):
      pass
    except IndexError:
      if self._call_after_last:
        self._call_after_last()
      raise StopIteration
    # Object is not iterable -- treat it as the only item.
    if self._iterable is None or self._stop:
      if self._call_after_last:
        self._call_after_last()
      raise StopIteration
    self._stop = True
    return self._iterable

  def next(self):
    """Gets the next item, calls _call_on_each on it, and returns it."""
    while True:
      item = self._NextItem()
      if not self._call_on_each:
        return item
      inject_or_keep = self._call_on_each(item)
      if inject_or_keep not in (True, False, None):
        self._injected = item
        return inject_or_keep
      if inject_or_keep:
        return item
