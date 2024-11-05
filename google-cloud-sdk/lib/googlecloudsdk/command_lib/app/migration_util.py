# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Utilities for app migrate gen1-to-gen2."""

import json
import os
from os import path
import pathlib
import shutil
import time

from googlecloudsdk.command_lib.app import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import files


class Gen1toGen2Migration:
  """Utility class for migrating Gen 1 App Engine applications to Gen 2."""

  DEFAULT_APPYAML = 'app.yaml'
  MIGRATION_PROGRESS_FILE = 'migration_progress.json'
  DEFAULT_SERVICE_NAME = 'default'
  SUPPORTED_GEN1_RUNTIMES = ('python27',)
  SERVICE_FIELD = 'service'
  PYTHON_GEN1_RUNTIME = 'python27'
  APP_YAML_FIELD = 'app_yaml'
  PROCESSED_FILES_FIELD = 'processed_files'

  def __init__(self, api_client, args):
    """Initializes the Gen1toGen2Migration utility class.

    Args:
      api_client: The AppEngine API client.
      args: The argparse arguments.
    """
    log.debug(args)
    self.api_client = api_client
    self.input_dir = os.getcwd()

    # if app.yaml is not provided, use app.yaml in current directory
    if args.appyaml:
      self.appyaml_path = os.path.relpath(args.appyaml)
    else:
      log.info('appyaml not provided. Using app.yaml in current directory.')
      self.appyaml_path = os.path.join(self.input_dir, self.DEFAULT_APPYAML)
    self.output_dir = os.path.abspath(args.output_dir)
    self.project = properties.VALUES.core.project.Get()

  def StartMigration(self):
    """Starts the migration process.

    Raises:
      MissingGen1ApplicationError: If the provided project does not contain an
      AppEngine version with a Gen1 runtime.
    """

    app_yaml_content = self.ValidateAppyamlAndGetContents()
    # If service is not present in app.yaml, use default service
    if app_yaml_content.get(self.SERVICE_FIELD):
      service_name = app_yaml_content.get(self.SERVICE_FIELD)
    else:
      service_name = self.DEFAULT_SERVICE_NAME
      log.status.Print(
          'Service name not found in app.yaml. Using default service.'
      )
    log.info('service_name: {0}'.format(service_name))

    # Check if the project has a Gen 1 version deployed.
    if not self.api_client.CheckGen1AppId(service_name, self.project):
      raise exceptions.MissingGen1ApplicationError(self.project)

    # Check status of the migration i.e. new migration or resumed migration.
    is_new_migration = self.CheckOutputDirectoryAndGetMigrationStatus()
    if is_new_migration:
      self.StartNewMigration(service_name)
    else:
      self.ResumeMigration(service_name)

  def ValidateAppyamlAndGetContents(self):
    """Validates the app.yaml file and returns its contents.

    Returns:
      The contents of the app.yaml file.

    Raises:
      FileNotFoundError: If the app.yaml file is not found.
      UnsupportedRuntimeError: If the runtime in app.yaml is not a valid Gen 1
      runtime.
    """
    if not path.exists(self.appyaml_path):
      raise exceptions.FileNotFoundError(self.appyaml_path)

    # If the runtime is app.yaml is not a supported Gen 1 runtime or is not
    # present, raise an error.
    appyaml_content = yaml.load_path(self.appyaml_path)
    if appyaml_content.get('runtime') not in self.SUPPORTED_GEN1_RUNTIMES:
      raise exceptions.UnsupportedRuntimeError(
          self.appyaml_path, self.SUPPORTED_GEN1_RUNTIMES
      )

    return appyaml_content

  def CheckOutputDirectoryAndGetMigrationStatus(self):
    """Check if output directory exists and decide the migration status.

    If an output directory does not exist, we create one and decide that it is a
    new migration.

    Returns:
      Boolean: True for new migration, False for resuming migration.

    Raises:
      InvalidOutputDirectoryError: If the output directory is not empty and does
      not contain a migration_progress.json file.
    """
    if not os.path.exists(self.output_dir):
      os.makedirs(self.output_dir)
      log.info('Creating directory: {0}'.format(self.output_dir))
      return True

    # Check if the directory is empty
    if not os.listdir(self.output_dir):
      log.info('Output directory {0} is empty.'.format(self.output_dir))
      return True

    # Check if migration_progress.json exists
    if self.MIGRATION_PROGRESS_FILE in os.listdir(self.output_dir):
      log.warning(
          'Output directory {0} is not empty. Resuming migration...'.format(
              self.output_dir
          )
      )
      return False
    # Raise error if output directory is not empty and does not contain a
    # migration_progress.json file.
    raise exceptions.InvalidOutputDirectoryError(self.output_dir)

  def StartNewMigration(self, service_name):
    """Flow for starting a new migration.

    Args:
      service_name: The service name.
    """

    log.info('input_dir: {0}'.format(self.input_dir))
    appyaml_filename = os.path.basename(self.appyaml_path)

    # Copy all files from input directory to output directory except app.yaml,
    # files with .py extension and the output directory itself.
    shutil.copytree(
        self.input_dir,
        self.output_dir,
        ignore=shutil.ignore_patterns(
            '*.py', appyaml_filename, pathlib.PurePath(self.output_dir).name
        ),
        dirs_exist_ok=True,
    )
    log.status.Print('Copying files to output directory')

    # Create a migration progress file.
    progress_file = os.path.join(self.output_dir, self.MIGRATION_PROGRESS_FILE)
    migration_progress = {}

    # Write the migrated app.yaml to the output directory.
    self.WriteMigratedYaml(
        service_name,
        os.path.join(self.output_dir, appyaml_filename),
        migration_progress,
        progress_file,
    )

    requirements_file = os.path.join(self.output_dir, 'requirements.txt')
    # Write the migrated code to the output directory.
    self.WriteMigratedCode(
        service_name, migration_progress, progress_file, requirements_file
    )
    log.status.Print('Migration completed.')

  def ResumeMigration(self, service_name):
    """Flow for a resumed migration.

    Args:
      service_name: The service name.

    Raises:
      InvalidOutputDirectoryError: If the output directory is not empty and does
      not contain a migration_progress.json file.
    """

    log.info('input_dir: {0}'.format(self.input_dir))

    # Load the migration progress file.
    progress_file = os.path.join(self.output_dir, self.MIGRATION_PROGRESS_FILE)
    with files.FileReader(progress_file) as pf:
      migration_progress = json.load(pf)

    # If app.yaml is not present in migration_progress, migrate it.
    if self.appyaml_path not in migration_progress.get('app_yaml', ''):
      log.info(
          '{0} not present in migration_progress. Will be migrated.'.format(
              self.appyaml_path
          )
      )
      self.WriteMigratedYaml(
          service_name,
          os.path.join(self.output_dir, os.path.basename(self.appyaml_path)),
          migration_progress,
          progress_file,
      )

    requirements_file = os.path.join(self.output_dir, 'requirements.txt')
    # Write the migrated code to the output directory.
    self.WriteMigratedCode(
        service_name, migration_progress, progress_file, requirements_file
    )
    log.status.Print('Migration completed.')

  def WriteMigratedYaml(
      self, service_name, output_path, migration_progress, progress_file
  ):
    """Writes the migrated app.yaml to the output directory.

    Args:
      service_name: The service name.
      output_path: The path to the output directory.
      migration_progress: The migration progress dictionary.
      progress_file: The path to the migration progress file.
    """
    appyaml_content = files.ReadFileContents(self.appyaml_path)
    appyaml_filename = os.path.basename(self.appyaml_path)
    response = self.api_client.MigrateConfigYaml(
        self.project, appyaml_content, self.PYTHON_GEN1_RUNTIME, service_name
    )
    migrated_yaml_contents = yaml.load(response.configAsString)
    with files.FileWriter(output_path) as f:
      yaml.dump(migrated_yaml_contents, f)

    # Update the migration progress file.
    migration_progress[self.APP_YAML_FIELD] = self.appyaml_path
    with files.FileWriter(progress_file, 'w') as pf:
      json.dump(migration_progress, pf, indent=4)
    log.status.Print(
        'Config modifications applied to {0}.'.format(appyaml_filename)
    )

  def WriteMigratedCode(
      self, service_name, migration_progress, progress_file, requirements_file
  ):
    """Writes the migrated code to the output directory.

    Args:
      service_name: The service name.
      migration_progress: The migration progress dictionary.
      progress_file: The path to the migration progress file.
      requirements_file: The path to the requirements file.
    """
    # Recursively walk through the input directory.
    for dirpath, dirname, filenames in os.walk(self.input_dir):
      dirname[:] = [
          d
          for d in dirname
          if d != pathlib.PurePath(self.output_dir).name
      ]
      for filename in filenames:
        file_path = os.path.join(dirpath, filename)
        if pathlib.Path(file_path).suffix == '.py':
          # If the file is already present in the migration_progress, skip it.
          if (
              self.PROCESSED_FILES_FIELD in migration_progress
              and file_path in migration_progress[self.PROCESSED_FILES_FIELD]
          ):
            log.info(
                'File {0} already exists. Will be skipped.'.format(file_path)
            )
            continue

          log.status.Print('Currently on file: {0}'.format(file_path))
          file_content = files.ReadFileContents(file_path)
          transformed_code, requirements_list = self.GetMigratedCode(
              file_content, service_name
          )
          output_path = os.path.join(
              self.output_dir, os.path.relpath(file_path, self.input_dir)
          )
          # Get the existing requirements from the requirements file.
          existing_requirements = []
          if os.path.exists(requirements_file):
            requirements_file_contents = files.ReadFileContents(
                requirements_file
            )
            if requirements_file_contents:
              existing_requirements = requirements_file_contents.split('\n')

          # Add the new requirements to the existing requirements.
          for requirement in requirements_list:
            if requirement not in existing_requirements:
              existing_requirements.append(requirement)
          files.WriteFileContents(
              requirements_file, '\n'.join(existing_requirements)
          )

          # If the file already exists in the output_dir and not in
          # migration_progress, do not overwrite it.
          if os.path.exists(output_path):
            new_output_path = (
                os.path.splitext(output_path)[0]
                + '_'
                + str(time.time()).split('.')[0]
                + '.py'
            )
            log.warning(
                'File {0} already exists. Will be renamed to {1}.'.format(
                    file_path, new_output_path
                )
            )
            output_path = new_output_path
          files.WriteFileContents(
              output_path, transformed_code, overwrite=False
          )

          # Update the migration progress file.
          if self.PROCESSED_FILES_FIELD not in migration_progress:
            migration_progress[self.PROCESSED_FILES_FIELD] = []
          migration_progress[self.PROCESSED_FILES_FIELD].append(file_path)
          with files.FileWriter(progress_file, 'w') as pf:
            json.dump(migration_progress, pf, indent=4)

  def GetMigratedCode(
      self, file_content, service_name
  ):
    """Calls MigrateCodeFile and gets the migrated code for a python file.

    Args:
      file_content: The contents of the python file.
      service_name: The service name.

    Returns:
      transformed_code: The migrated code for the python file.
      requirements_list: The list of requirements for the python file.
    """
    operation = self.api_client.MigrateCodeFile(
        self.project, file_content, self.PYTHON_GEN1_RUNTIME, service_name
    )
    transformed_code = ''
    requirements_list = []
    operation_response = operation.response.additionalProperties
    for prop in operation_response:
      if prop.key == 'codeAsString':
        transformed_code = prop.value.string_value
      if prop.key == 'python3Requirements':
        requirements = prop.value.array_value.entries
        for entry in requirements:
          requirements_list.append(entry.string_value.strip())
    return transformed_code, requirements_list
