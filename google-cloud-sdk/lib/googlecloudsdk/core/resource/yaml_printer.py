# -*- coding: utf-8 -*-
# Copyright 2014 Google Inc. All Rights Reserved.

"""YAML format printer."""

from googlecloudsdk.core.resource import resource_printer_base

import yaml


class YamlPrinter(resource_printer_base.ResourcePrinter):
  """Prints the YAML representations of JSON-serializable objects.

  link:www.yaml.org[YAML], YAML ain't markup language.

  For example:

    printer = YamlPrinter(log.out)
    printer.AddRecord({'a': ['hello', 'world'], 'b': {'x': 'bye'}})

  produces:

    ---
    a:
      - hello
      - world
    b:
      - x: bye
  """

  def __init__(self, *args, **kwargs):
    super(YamlPrinter, self).__init__(*args, **kwargs)

    def LiteralPresenter(dumper, data):
      return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')

    yaml.add_representer(YamlPrinter._LiteralString, LiteralPresenter,
                         Dumper=yaml.dumper.SafeDumper)

  class _LiteralString(str):
    """A type used to inform the yaml printer about how it should look."""

  def _UpdateTypesForOutput(self, val):
    """Dig through a dict of list of primitives to help yaml output.

    Args:
      val: A dict, list, or primitive object.

    Returns:
      An updated version of val.
    """
    if isinstance(val, basestring) and '\n' in val:
      return YamlPrinter._LiteralString(val)
    if isinstance(val, list):
      for i in range(len(val)):
        val[i] = self._UpdateTypesForOutput(val[i])
      return val
    if isinstance(val, dict):
      for key in val:
        val[key] = self._UpdateTypesForOutput(val[key])
      return val
    return val

  def _AddRecord(self, record, delimit=True):
    """Immediately prints the given record as YAML.

    Args:
      record: A YAML-serializable Python object.
      delimit: Prints resource delimiters if True.
    """
    record = self._UpdateTypesForOutput(record)
    yaml.safe_dump(
        record,
        stream=self._out,
        default_flow_style=False,
        indent=resource_printer_base.STRUCTURED_INDENTATION,
        explicit_start=delimit)
