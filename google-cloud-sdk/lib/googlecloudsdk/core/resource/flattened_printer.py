# Copyright 2014 Google Inc. All Rights Reserved.

"""Flattened tree resource printer."""

from googlecloudsdk.core.resource import resource_printer_base


def _Flatten(obj):
  """Flattens a JSON-serializable object into a list of tuples.

  The first element of each tuple will be a key and the second element
  will be a simple value.

  For example, _Flatten({'a': ['hello', 'world'], 'b': {'x': 'bye'}})
  will produce:

    [
        ('a[0]', 'hello'),
        ('a[1]', 'world'),
        ('b.x', 'bye'),
    ]

  Args:
    obj: A JSON-serializable object.

  Returns:
    A list of tuples.
  """

  def Flatten(obj, name, res):
    """Recursively appends keys in path from obj into res.

    Args:
      obj: The object to flatten.
      name: The key name of the current obj.
      res: The ordered result value list.
    """
    if isinstance(obj, list):
      if obj:
        for i, item in enumerate(obj):
          Flatten(item, '{name}[{index}]'.format(name=name, index=i), res)
      else:
        res.append((name, []))
    elif isinstance(obj, dict):
      if obj:
        for k, v in sorted(obj.iteritems()):
          Flatten(v, '{name}{dot}{key}'.format(
              name=name, dot='.' if name else '', key=k), res)
      else:
        res.append((name, {}))
    else:
      res.append((name, obj))

  res = []
  Flatten(obj, '', res)
  return res


class FlattenedPrinter(resource_printer_base.ResourcePrinter):
  """Prints a flattened tree representation of JSON-serializable objects.

  A flattened tree. Each output line contains one *key*:*value* pair.

  Printer attributes:
    no-pad: bool, Print only one space after ':'. The default adjusts the space
      to align the values into the same output column. Use *no-pad* for
      comparing resource outputs.

  For example:

    printer = resource_printer.Printer('flattened', out=sys.stdout)
    printer.AddRecord({'a': ['hello', 'world'], 'b': {'x': 'bye'}})

  produces:

    ---
    a[0]: hello
    a[1]: world
    b.x:  bye
  """

  def __init__(self, *args, **kwargs):
    super(FlattenedPrinter, self).__init__(*args, **kwargs)

  def _AddRecord(self, record, delimit=True):
    """Immediately prints the record as flattened a flattened tree.

    Args:
      record: A JSON-serializable object.
      delimit: Prints resource delimiters if True.
    """
    if delimit:
      self._out.write('---\n')
    flattened_record = _Flatten(record)
    if flattened_record:
      pad = 'no-pad' not in self.attributes
      if pad:
        max_key_len = max(len(key) for key, _ in flattened_record)
      for key, value in flattened_record:
        self._out.write(key + ': ')
        if pad:
          self._out.write(' ' * (max_key_len - len(key)))
        val = str(value)
        # Value must be one text line with leading/trailing space quoted.
        if '\n' in val or val[0:1].isspace() or val[-1:].isspace():
          val = "'" + val.encode('string-escape') + "'"
        self._out.write(val + '\n')
