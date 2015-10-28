# Copyright 2015 Google Inc. All Rights Reserved.

"""Methods for formatting and printing Python objects.

Each printer has three main attributes, all accessible as strings in the
--format='NAME[ATTRIBUTES](PROJECTION)' option:

  NAME: str, The printer name.

  [ATTRIBUTES]: str, An optional [no-]name[=value] list of attributes. Unknown
    attributes are silently ignored. Attributes are added to a printer local
    dict indexed by name.

  (PROJECTION): str, List of resource names to be included in the output
    resource. Unknown names are silently ignored. Resource names are
    '.'-separated key identifiers with an implicit top level resource name.

Example:

  gcloud compute instances list \
      --format='table[box](name, networkInterfaces[0].networkIP)'
"""

from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core.resource import csv_printer
from googlecloudsdk.core.resource import flattened_printer
from googlecloudsdk.core.resource import json_printer
from googlecloudsdk.core.resource import list_printer
from googlecloudsdk.core.resource import resource_printer_base
from googlecloudsdk.core.resource import resource_projector
from googlecloudsdk.core.resource import resource_property
from googlecloudsdk.core.resource import resource_transform
from googlecloudsdk.core.resource import table_printer
from googlecloudsdk.core.resource import yaml_printer


class Error(core_exceptions.Error):
  """Exceptions for this module."""


class UnknownFormatError(Error):
  """UnknownFormatError for unknown format names."""


class ProjectionRequiredError(Error):
  """ProjectionRequiredError for format with no projection that needs one."""


class DefaultPrinter(yaml_printer.YamlPrinter):
  """An alias for YamlPrinter.

  An alias for the *yaml* format.
  """


class NonePrinter(resource_printer_base.ResourcePrinter):
  """Disables formatted output and consumes the resources.

  Disables formatted output and consumes the resources.
  """


class TextPrinter(flattened_printer.FlattenedPrinter):
  """An alias for FlattenedPrinter.

  An alias for the *flattened* format.
  """


class PrinterAttributes(resource_printer_base.ResourcePrinter):
  """Attributes for all printers. This docstring is used to generate topic docs.

  All formats have these attributes.

  Printer attributes:
    disable: Disables formatted output and does not consume the resources.
    private: Disables log file output. Use this for sensitive resource data
      that should not be displayed in log files. Explicit command line IO
      redirection overrides this attribute.
  """


_FORMATTERS = {
    'csv': csv_printer.CsvPrinter,
    'default': DefaultPrinter,
    'flattened': flattened_printer.FlattenedPrinter,
    'json': json_printer.JsonPrinter,
    'list': list_printer.ListPrinter,
    'none': NonePrinter,
    'table': table_printer.TablePrinter,
    'text': TextPrinter,  # TODO(gsfowler): Drop this in the cleanup.
    'value': csv_printer.ValuePrinter,
    'yaml': yaml_printer.YamlPrinter,
}


def GetFormatRegistry():
  """Returns the (format-name => Printer) format registry dictionary.

  Returns:
    The (format-name => Printer) format registry dictionary.
  """
  return _FORMATTERS


def SupportedFormats():
  """Returns a sorted list of supported format names."""
  return sorted(_FORMATTERS)


def Printer(print_format, out=None, defaults=None):
  """Returns a resource printer given a format string.

  Args:
    print_format: The _FORMATTERS name with optional attributes and projection.
    out: Output stream, log.out if None.
    defaults: Optional resource_projection_spec.ProjectionSpec defaults.

  Raises:
    UnknownFormatError: The print_format is invalid.

  Returns:
    An initialized ResourcePrinter class or None if printing is disabled.
  """

  projector = resource_projector.Compile(
      expression=print_format, defaults=defaults,
      symbols=resource_transform.GetTransforms())
  projection = projector.Projection()
  printer_name = projection.Name()
  try:
    printer_class = _FORMATTERS[printer_name]
  except KeyError:
    raise UnknownFormatError(
        'Format must be one of {0}; received [{1}]'.format(
            ', '.join(SupportedFormats()), printer_name))
  printer = printer_class(out=out,
                          name=printer_name,
                          attributes=projection.Attributes(),
                          column_attributes=projection,
                          process_record=projector.Evaluate)
  projector.SetByColumns(printer.ByColumns())
  return printer


def Print(resources, print_format, out=None, defaults=None, single=False):
  """Prints the given resources.

  Args:
    resources: A singleton or list of JSON-serializable Python objects.
    print_format: The _FORMATTER name with optional projection expression.
    out: Output stream, log.out if None.
    defaults: Optional resource_projection_spec.ProjectionSpec defaults.
    single: If True then resources is a single item and not a list.
      For example, use this to print a single object as JSON.

  Raises:
    ProjectionRequiredError: If a format requires a projection and one is not
      provided.
  """
  printer = Printer(print_format, out=out, defaults=defaults)
  if 'disable' in printer.attributes:
    # Disables formatted output and does not consume the resources.
    return
  if printer.ByColumns() and not printer.column_attributes.Columns():
    raise ProjectionRequiredError(
        'Format [{0}] requires a non-empty projection.'.format(
            printer.column_attributes.Name()))

  # Resources may be a generator and since generators can raise exceptions, we
  # have to call Finish() in the finally block to make sure that the resources
  # we've been able to pull out of the generator are printed before control is
  # given to the exception-handling code.
  try:
    if resources:
      if single or not resource_property.IsListLike(resources):
        printer.AddRecord(resources, delimit=False)
      else:
        for resource in resources:
          printer.AddRecord(resource)
  finally:
    printer.Finish()
