# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Library that handles importing files for Deployment Manager."""


import os
import posixpath
import re
import urlparse
from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.deployment_manager import exceptions
from googlecloudsdk.api_lib.util import exceptions as api_exceptions
from googlecloudsdk.core import yaml
import requests

IMPORTS = 'imports'
PATH = 'path'
NAME = 'name'
OUTPUTS = 'outputs'


class _BaseImport(object):
  """An imported DM config object."""

  def __init__(self, full_path, name):
    self.full_path = full_path
    self.name = name
    self.content = None
    self.base_name = None

  def GetFullPath(self):
    return self.full_path

  def GetName(self):
    return self.name

  def SetContent(self, content):
    self.content = content
    return self

  def IsTemplate(self):
    return self.full_path.endswith(('.jinja', '.py'))


class _ImportSyntheticCompositeTypeFile(_BaseImport):
  """Performs common operations on an imported composite type."""

  def __init__(self, full_path, properties=None):
    name = full_path.split(':')[1]
    super(_ImportSyntheticCompositeTypeFile, self).__init__(full_path, name)
    self.properties = properties

  def GetBaseName(self):
    if self.base_name is None:
      self.base_name = self.name
    return self.base_name

  def Exists(self):
    return True

  def GetContent(self):
    """Returns the content of the synthetic file as a string."""
    if self.content is None:
      resources = {'resources': [{'type': self.full_path, 'name': self.name}]}
      if self.properties:
        resources['resources'][0]['properties'] = self.properties
      self.content = yaml.dump(resources)
    return self.content

  def BuildChildPath(self, unused_child_path):
    raise NotImplementedError


class _ImportFile(_BaseImport):
  """Performs common operations on an imported file."""

  def __init__(self, full_path, name=None):
    name = name if name else full_path
    super(_ImportFile, self).__init__(full_path, name)

  def GetBaseName(self):
    if self.base_name is None:
      self.base_name = os.path.basename(self.full_path)
    return self.base_name

  def Exists(self):
    return os.path.isfile(self.full_path)

  def GetContent(self):
    if self.content is None:
      try:
        with open(self.full_path, 'r') as resource:
          self.content = resource.read()
      except IOError as e:
        raise exceptions.ConfigError(
            "Unable to read file '%s'. %s" % (self.full_path, e.message))
    return self.content

  def BuildChildPath(self, child_path):
    if _IsUrl(child_path):
      return child_path
    return os.path.normpath(
        os.path.join(os.path.dirname(self.full_path), child_path))


class _ImportUrl(_BaseImport):
  """Class to perform operations on a URL import."""

  def __init__(self, full_path, name=None):
    full_path = self._ValidateUrl(full_path)
    name = name if name else full_path
    super(_ImportUrl, self).__init__(full_path, name)

  def GetBaseName(self):
    if self.base_name is None:
      # We must use posixpath explicitly so this will work on Windows.
      self.base_name = posixpath.basename(
          urlparse.urlparse(self.full_path).path)
    return self.base_name

  def Exists(self):
    if self.content:
      return True
    return self._RetrieveContent(raise_exceptions=False)

  def GetContent(self):
    if self.content is None:
      self._RetrieveContent()
    return self.content

  def _RetrieveContent(self, raise_exceptions=True):
    """Helper function for both Exists and GetContent.

    Args:
      raise_exceptions: Set to false if you just want to know if the file
          actually exists.

    Returns:
      True if we successfully got the content of the URL. Returns False is
      raise_exceptions is False.

    Raises:
      HTTPError: If raise_exceptions is True, will raise exceptions for 4xx or
          5xx response codes instead of returning False.
    """
    r = requests.get(self.full_path)

    try:
      r.raise_for_status()
    except requests.exceptions.HTTPError as e:
      if raise_exceptions:
        raise e
      return False

    self.content = r.text
    return True

  def BuildChildPath(self, child_path):
    if _IsUrl(child_path):
      return child_path
    return urlparse.urljoin(self.full_path, child_path)

  @staticmethod
  def _ValidateUrl(url):
    """Make sure the url fits the format we expect."""
    parsed_url = urlparse.urlparse(url)

    if parsed_url.scheme not in ('http', 'https'):
      raise exceptions.ConfigError(
          "URL '%s' scheme was '%s'; it must be either 'https' or 'http'."
          % (url, parsed_url.scheme))

    if not parsed_url.path or parsed_url.path == '/':
      raise exceptions.ConfigError("URL '%s' doesn't have a path." % url)

    if parsed_url.params or parsed_url.query or parsed_url.fragment:
      raise exceptions.ConfigError(
          "URL '%s' should only have a path, no params, queries, or fragments."
          % url)

    return url


def _IsUrl(resource_handle):
  """Returns true if the passed resource_handle is a url."""
  parsed = urlparse.urlparse(resource_handle)
  return parsed.scheme and parsed.netloc


def _IsValidCompositeTypeSyntax(composite_type_name):
  """Returns true if the resource_handle matches composite type syntax.

  Args:
    composite_type_name: a string of the name of the composite type.

  Catches most syntax errors by checking that the string contains the substring
  '/composite:' preceded and followed by at least one character, none of which
  are colons, periods, slashes, or whitespace.
  """
  return re.match(r'^[^/:.\s]+/composite:[^/:.\s]+$', composite_type_name)


def _BuildFileImportObject(full_path, name=None):
  if _IsUrl(full_path):
    return _ImportUrl(full_path, name)
  else:
    return _ImportFile(full_path, name)


def _BuildImportObject(config=None, template=None,
                       composite_type=None, properties=None):
  """Build an import object from the given config name."""
  if composite_type:
    if not _IsValidCompositeTypeSyntax(composite_type):
      raise exceptions.ConfigError('Invalid composite type syntax.')
    return _ImportSyntheticCompositeTypeFile(composite_type, properties)
  if config:
    return _BuildFileImportObject(config)
  if template:
    return _BuildFileImportObject(template)
  raise exceptions.ConfigError('No path or name for a config, template, or '
                               'composite type was specified.')


def _GetYamlImports(import_object):
  """Extract the import section of a file.

  Args:
    import_object: The object in which to look for imports.

  Returns:
    A list of dictionary objects, containing the keys 'path' and 'name' for each
    file to import. If no name was found, we populate it with the value of path.

  Raises:
   ConfigError: If we cannont read the file, the yaml is malformed, or
       the import object does not contain a 'path' field.
  """
  content = import_object.GetContent()
  yaml_content = yaml.load(content)
  imports = []
  if yaml_content and IMPORTS in yaml_content:
    imports = yaml_content[IMPORTS]
    # Validate the yaml imports, and make sure the optional name is set.
    for i in imports:
      if PATH not in i:
        raise exceptions.ConfigError(
            'Missing required field %s in import in file %s.'
            % (PATH, import_object.full_path))
      # Populate the name field.
      if NAME not in i:
        i[NAME] = i[PATH]
  return imports


def _GetImportObjects(parent_object):
  """Given a file object, gets all child objects it imports.

  Args:
    parent_object: The object in which to look for imports.

  Returns:
    A list of import objects representing the files imported by the parent.

  Raises:
    ConfigError: If we cannont read the file, the yaml is malformed, or
       the import object does not contain a 'path' field.
  """
  yaml_imports = _GetYamlImports(parent_object)

  child_objects = []

  for yaml_import in yaml_imports:
    child_path = parent_object.BuildChildPath(yaml_import[PATH])
    child_objects.append(_BuildFileImportObject(child_path, yaml_import[NAME]))

  return child_objects


def _HandleTemplateImport(import_object):
  """Takes a template and looks for its schema to process.

  Args:
    import_object: Template object whose schema to check for and process

  Returns:
    List of import_objects that the schema is importing.

  Raises:
    ConfigError: If any of the schema's imported items are missing the
        'path' field.
  """
  schema_path = import_object.GetFullPath() + '.schema'
  schema_name = import_object.GetName() + '.schema'

  schema_object = _BuildFileImportObject(schema_path, schema_name)

  if not schema_object.Exists():
    # There is no schema file, so we have nothing to process
    return []

  # Add all files imported by the schema to the list of files to process
  import_objects = _GetImportObjects(schema_object)

  # Add the schema itself to the list of files to process
  import_objects.append(schema_object)

  return import_objects


def CreateImports(messages, config_object):
  """Constructs a list of ImportFiles from the provided import file names.

  Args:
    messages: Object with v2 API messages.
    config_object: Parent file that contains files to import.

  Returns:
    List of ImportFiles containing the name and content of the imports.

  Raises:
    ConfigError: if the import files cannot be read from the specified
        location, the import does not have a 'path' attribute, or the filename
        has already been imported.
  """
  # Make a stack of Import objects. We use a stack because we want to make sure
  # errors are grouped by template.
  import_objects = []

  # Seed the stack with imports from the user's config.
  import_objects.extend(_GetImportObjects(config_object))

  # Map of imported resource names to their full path, used to check for
  # duplicate imports.
  import_resource_map = {}

  # List of import resources to return.
  import_resources = []

  while import_objects:
    import_object = import_objects.pop()

    process_object = True

    # Check to see if the same name is being used to refer to multiple imports.
    if import_object.GetName() in import_resource_map:
      if (import_object.GetFullPath() ==
          import_resource_map[import_object.GetName()]):
        # If the full path for these two objects is the same, we don't need to
        # process it again
        process_object = False
      else:
        # If the full path is different, fail.
        raise exceptions.ConfigError(
            'Files %s and %s both being imported as %s.' %
            (import_object.GetFullPath(),
             import_resource_map[import_object.GetName()],
             import_object.GetName()))

    if process_object:
      # If this file is a template, see if there is a corresponding schema
      # and then add all of it's imports to be processed.
      if import_object.IsTemplate():
        import_objects.extend(_HandleTemplateImport(import_object))

      import_resource = messages.ImportFile(
          name=import_object.GetName(),
          content=import_object.GetContent())

      import_resource_map[import_object.GetName()] = import_object.GetFullPath()
      import_resources.append(import_resource)

  return import_resources


def _SanitizeBaseName(base_name):
  """Make sure the base_name will be a valid resource name.

  Args:
    base_name: Name of a template file, and therefore not empty.

  Returns:
    base_name with periods and underscores removed,
        and the first letter lowercased.
  """
  # Remove periods and underscores.
  sanitized = base_name.replace('.', '-').replace('_', '-')

  # Lower case the first character.
  return sanitized[0].lower() + sanitized[1:]


def BuildConfig(config=None, template=None,
                composite_type=None, properties=None):
  """Takes the path to a config and returns a processed config.

  Args:
    config: Path to the yaml config file.
    template: Path to the template config file.
    composite_type: name of the composite type config.
    properties: Dictionary of properties, only used if
                the file is a template or composite type.

  Returns:
    A tuple of base_path, config_contents, and a list of import objects.

  Raises:
    ArgumentError: If using the properties flag for a config file
        instead of a template or composite type.
  """
  config_obj = _BuildImportObject(config=config,
                                  template=template,
                                  composite_type=composite_type,
                                  properties=properties)

  if composite_type:
    return config_obj

  if config:
    if config_obj.IsTemplate():
      raise exceptions.ArgumentError(
          'Creating deployments from templates with the --config '
          'flag is not supported. Please use the --template flag.')
    elif properties:
      raise exceptions.ArgumentError(
          'The properties flag should only be used '
          'when using a template (--template) or composite type '
          '(--composite-type) as your config file.')
    else:
      return config_obj

  if template:
    if not config_obj.IsTemplate():
      raise exceptions.ArgumentError(
          'The --template flag should only be used '
          'when using a template as your config file.')

  # Otherwise we should build the config from scratch.
  base_name = config_obj.GetBaseName()

  # Build the single template resource.
  custom_resource = {'type': base_name,
                     'name': _SanitizeBaseName(base_name)}

  # Attach properties if we were given any.
  if properties:
    custom_resource['properties'] = properties

  # Add the import and single resource together into a config file.
  custom_dict = {'imports': [{'path': base_name},],
                 'resources': [custom_resource,]}

  custom_outputs = []

  # Import the schema file and attach the outputs to config if there is any
  schema_path = config_obj.GetFullPath() + '.schema'
  schema_name = config_obj.GetName() + '.schema'

  schema_object = _BuildFileImportObject(schema_path, schema_name)

  if schema_object.Exists():
    schema_content = schema_object.GetContent()
    config_name = custom_resource['name']
    yaml_schema = yaml.load(schema_content, file_hint=schema_path)
    if yaml_schema and OUTPUTS in yaml_schema:
      for output_name in yaml_schema[OUTPUTS].keys():
        custom_outputs.append(
            {'name': output_name,
             'value': '$(ref.' + config_name + '.' + output_name + ')'})

  if custom_outputs:
    custom_dict['outputs'] = custom_outputs

  custom_content = yaml.dump(custom_dict)

  # Override the template_object with it's new config_content
  return config_obj.SetContent(custom_content)


def BuildTargetConfig(messages, config=None, template=None,
                      composite_type=None, properties=None):
  """Construct a TargetConfig from the provided config file with imports.

  Args:
    messages: Object with v2 API messages.
    config: Path to the yaml config file.
    template: Path to the template config file.
    composite_type: name of the composite type config.
    properties: Dictionary of properties, only used if the full_path is a
        template or composite type.

  Returns:
    TargetConfig containing the contents of the config file and the names and
    contents of any imports.

  Raises:
    ConfigError: if the config file or import files cannot be read from
        the specified locations, or if they are malformed.
  """
  config_object = BuildConfig(config=config,
                              template=template,
                              composite_type=composite_type,
                              properties=properties)

  return messages.TargetConfiguration(
      config=messages.ConfigFile(content=config_object.GetContent()),
      imports=CreateImports(messages, config_object))


def BuildTargetConfigFromManifest(client, messages, project_id, deployment_id,
                                  manifest_id, properties=None):
  """Construct a TargetConfig from a manifest of a previous deployment.

  Args:
    client: Deployment Manager v2 API client.
    messages: Object with v2 API messages.
    project_id: Project for this deployment. This is used when pulling the
        the existing manifest.
    deployment_id: Deployment used to pull retrieve the manifest.
    manifest_id: The manifest to pull down for constructing the target.
    properties: Dictionary of properties, only used if the manifest has a
        single resource. Properties will override only. If the manifest
        has properties which do not exist in the properties hash will remain
        unchanged.

  Returns:
    TargetConfig containing the contents of the config file and the names and
    contents of any imports.

  Raises:
    HttpException: in the event that there is a failure to pull the manifest
        from deployment manager
    ManifestError: When the manifest being revived has more than one
        resource
  """
  try:
    manifest = client.manifests.Get(
        messages.DeploymentmanagerManifestsGetRequest(
            project=project_id,
            deployment=deployment_id,
            manifest=manifest_id,
        )
    )
    config_file = manifest.config
    imports = manifest.imports
  except apitools_exceptions.HttpError as error:
    raise api_exceptions.HttpException(error)

  # If properties were specified, then we need to ensure that the
  # configuration in the manifest retrieved has only a single resource.
  if properties:
    config_yaml = yaml.load(config_file.content)
    if len(config_yaml['resources']) != 1:
      raise exceptions.ManifestError(
          'Manifest reuse with properties requires '
          'there only be a single resource.')
    single_resource = config_yaml['resources'][0]
    if not single_resource.has_key('properties'):
      single_resource['properties'] = {}
    existing_properties = single_resource['properties']
    for key, value in properties.iteritems():
      existing_properties[key] = value
    config_file.content = yaml.dump(config_yaml)

  return messages.TargetConfiguration(config=config_file, imports=imports)
