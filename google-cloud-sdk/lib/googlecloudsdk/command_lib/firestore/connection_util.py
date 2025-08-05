# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Utility for validating Firestore Mongo connection strings."""

import dataclasses
import re
from typing import List

from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_attr


@dataclasses.dataclass(frozen=True)
class ValidationResults:
  """Container class for results of validating a connection string."""

  headers: List[str]
  info: List[str]
  warnings: List[str]
  errors: List[str]
  footers: List[str]

  def __str__(self):
    return '\n'.join(
        self.headers + self.info + self.warnings + self.errors + self.footers
    )


def ValidateConnectionString(
    connection_string,
    db_uid=None,
    db_location_id=None,
    database_id=None,
):
  """Validate the specified connection_string for the specified database."""

  headers = [
      '-' * 80,
      f'Evaluating connection string: {connection_string}',
      '-' * 80,
  ]
  info = []
  warnings = []
  errors = []
  footers = ['-' * 80]
  user = None
  password = None

  # Helper method for checking k=v params
  def CheckParam(param_name, expected_value, error_description=''):
    if param_name not in extra_params:
      errors.append(
          f'{error_description}The connection string must specify'
          f' {param_name}={expected_value}.'
      )
    else:
      actual_value = extra_params[param_name]
      del extra_params[param_name]
      if actual_value != expected_value:
        errors.append(
            f'{error_description}The parameter {param_name} is set to '
            f'{actual_value}. The connection string must specify '
            f'{param_name}={expected_value}.'
        )
      else:
        info.append(f'{param_name}={expected_value}.')

  # Scan the connection string left-to-right and emit recommendations.
  while True:
    # Check that the connection string starts with the appropriate prefix
    if not connection_string.startswith('mongodb://'):
      errors.append('The connection string must start with mongodb://')
      break
    # Strip off mongodb:// and continue evaluation
    connection_string = connection_string[len('mongodb://') :]

    # Check for the presense of a user/password (optional)
    match = re.match(r'^([^:]*):([^@]*)@', connection_string)
    if match:
      user = match.group(1)
      password = '*' * len(match.group(2))
      info.append(
          f'The connection string specifies user: {user} '
          f'and password: {password}'
      )
      # Strip off the user+password and continue evaluation
      connection_string = connection_string[len(user) + len(password) + 2 :]

    # Check that the database address begins with a valid UUID
    match = re.match(
        r'^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.',
        connection_string,
    )
    if not match:
      errors.append((
          'The database address must start with a valid UUID. '
          f'For database {database_id}, use the value {db_uid}'
      ))
      errors.append(
          'NOTE: for password based authentication, the connection string '
          'can also start with mongodb://username:password@UUID.'
      )
      break
    if match.group(1) != db_uid:
      errors.append(
          f'the UUID {match.group(1)} in the connection string does not '
          f'match the UUID {db_uid} for the current database {database_id}.'
      )
    else:
      info.append(f'The UUID {db_uid} is correct.')
    # Strip off the 36 characters of the UUID + . and continue evaluation
    connection_string = connection_string[37:]

    # Check that the UUID is followed by a valid database location
    match = re.match(
        r'^([^\.]+)\.',
        connection_string,
    )
    if not match:
      errors.append(
          'The database address must have the form: '
          'UUID.location.firestore.goog:443'
      )
      break
    if match.group(1) != db_location_id:
      errors.append(
          f'The location {match.group(1)} in the connection string does '
          f'not match the location {db_location_id} for the '
          f'current database {database_id}.'
      )
    else:
      info.append(f'The location {db_location_id} is correct.')
    # Strip off the location + . and continue evaluation
    connection_string = connection_string[len(match.group(1)) + 1 :]

    # Check that the location is followed by the valid domain and port number
    if not connection_string.startswith('firestore.goog:443/'):
      errors.append(
          'The database address must end with firestore.goog:443 as '
          'the domain name and port.'
      )
      break
    # Strip off the rest of the address and continue evaluation
    connection_string = connection_string[len('firestore.goog:443/') :]

    # Check that the string contains a valid database name.
    match = re.match(r'^([^\?]*)\?', connection_string)
    if not match:
      errors.append(
          'The connection string must specify the database id. '
          f'For the current database {database_id} it should have the form '
          f'UUID.location.firestore.goog:443/{database_id}?'
      )
      break
    if match.group(1) != database_id:
      if match.group(1):
        errors.append(
            f'The database name {match.group(1)} in the connection'
            f' string does not match the current database {database_id}.'
        )
      else:
        errors.append(
            'The database name in the connection string is empty. '
            'It is recommended to explicitly specify the database name '
            f'{database_id}, e.g. firestore.goog:443/{database_id}?'
        )
    else:
      info.append(f'The database name {database_id} is correct.')
    # Stip off the rest of database id + '?' and continue evaluation
    connection_string = connection_string[len(match.group(1)) + 1 :]

    # Validate additional parameters, which should come in as k=v pairs.
    extra_params = {}
    entries = connection_string.split('&')
    for entry in entries:
      if not entry:
        continue
      parts = entry.split('=')
      if len(parts) != 2:
        errors.append(
            f'The parameter {entry} appears malformed. Expected'
            ' something in the form key=value.'
        )
      else:
        extra_params[parts[0]] = parts[1]

    # Check for always-required params
    CheckParam('loadBalanced', 'true')
    CheckParam('tls', 'true')
    CheckParam('retryWrites', 'false')

    # Check for params that require extra validation
    if 'authMechanism' in extra_params:
      auth_mechanism = extra_params['authMechanism']
      del extra_params['authMechanism']
      if auth_mechanism == 'PLAIN':
        CheckParam(
            'authSource',
            '$external',
            error_description='Using PLAIN authentication. ',
        )
        if not user:
          errors.append(
              'The username and an access token should be specified in '
              'the connection string when PLAIN authentication is enabled.'
          )
        else:
          info.append(
              'username and access token specified for PLAIN authentication.'
          )
      elif auth_mechanism == 'SCRAM-SHA-256':
        if not user:
          errors.append(
              'The username and password should be specified in the '
              'connection string when SCRAM-SHA-256 is enabled.'
          )
        else:
          info.append('username and password specified for SCRAM-SHA-256.')
      elif auth_mechanism == 'MONGODB-OIDC':
        if user:
          errors.append(
              'The username should not be specified when using the '
              'MONGODB-OIDC authentication mechanism.'
          )
        CheckParam(
            'authMechanismProperties',
            'ENVIRONMENT:gcp,TOKEN_RESOURCE:FIRESTORE',
            error_description='Using MONGODB-OIDC authentication. ',
        )
      else:
        errors.append(f'Unsupported authentication mechanism {auth_mechanism}.')
    else:
      if user:
        errors.append(
            f'Since the connection string specified user: {user} and'
            f' password: {password}, the connection must also be configured'
            ' with an appropriate authentication mechanism, e.g.'
            ' authMechanism=SCRAM-SHA-256'
        )
      else:
        errors.append(
            'No authMechanism specified. The connection string must '
            'specify one of the supported authentication mechanisms.'
        )

    # Check for any unconsumed parameters
    for k, v in extra_params.items():
      # Emit these was warnings. We don't know how they'll affect the client.
      warnings.append(f'Unknown parameter {k}={v}.')

    break

  if not errors:
    footers.append('Did not detect any errors in this connection string.')
  else:
    footers.append(
        "TIP: You can use 'gcloud firestore databases connection-string "
        f"--database={database_id}' to construct valid connection strings."
    )
  return ValidationResults(
      headers=headers,
      info=info,
      warnings=warnings,
      errors=errors,
      footers=footers,
  )


def PrettyPrintValidationResults(validation_results: ValidationResults):
  """Renders the connection string validation results to the console."""

  con = console_attr.GetConsoleAttr()
  for header in validation_results.headers:
    log.status.Print(header)
  for info in validation_results.info:
    log.status.Print(f"{con.Colorize('INFO:', 'green')} {info}")
  for warning in validation_results.warnings:
    log.status.Print(f"{con.Colorize('WARNING:', 'yellow')} {warning}")
  for error in validation_results.errors:
    log.status.Print(f"{con.Colorize('ERROR:', 'red')} {error}")
  for footer in validation_results.footers:
    log.status.Print(footer)
