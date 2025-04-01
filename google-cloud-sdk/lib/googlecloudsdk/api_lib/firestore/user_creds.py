# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Useful commands for interacting with the Cloud Firestore User Creds API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.firestore import api_utils


def _GetUserCredsService():
  """Returns the service to interact with the Firestore User Creds."""
  return api_utils.GetClient().projects_databases_userCreds


def CreateUserCreds(
    project, database, user_creds
):
  """Creates a user creds.

  Args:
    project: the project of the database of the user creds, a string.
    database: the database id of the user creds, a string.
    user_creds: The user-provided id for the user creds.

  Returns:
    a user creds.

  Raises:
    InvalidArgumentException: if user_creds is invalid.
  """
  messages = api_utils.GetMessages()
  return _GetUserCredsService().Create(
      messages.FirestoreProjectsDatabasesUserCredsCreateRequest(
          parent='projects/{}/databases/{}'.format(
              project,
              database,
          ),
          userCredsId=user_creds,
      )
  )


def GetUserCreds(project, database, user_creds):
  """Gets a user creds.

  Args:
    project: the project of the database of the user creds, a string.
    database: the database id of the user creds, a string.
    user_creds: the user creds to read, a string.

  Returns:
    a user creds.
  """
  messages = api_utils.GetMessages()
  return _GetUserCredsService().Get(
      messages.FirestoreProjectsDatabasesUserCredsGetRequest(
          name='projects/{}/databases/{}/userCreds/{}'.format(
              project,
              database,
              user_creds,
          ),
      )
  )


def ListUserCreds(project, database):
  """Lists user Creds under a database.

  Args:
    project: the project of the database of the user creds, a string.
    database: the database id of the user creds, a string.

  Returns:
    a list of user Creds.
  """
  messages = api_utils.GetMessages()
  return list(
      _GetUserCredsService()
      .List(
          messages.FirestoreProjectsDatabasesUserCredsListRequest(
              parent='projects/{}/databases/{}'.format(
                  project,
                  database,
              ),
          )
      )
      .userCreds
  )


def EnableUserCreds(project, database, user_creds):
  """Enables a user creds.

  Args:
    project: the project of the database of the user creds, a string.
    database: the database id of the user creds, a string.
    user_creds: the user creds to enable, a string.

  Returns:
    a user creds.
  """
  messages = api_utils.GetMessages()
  return _GetUserCredsService().Enable(
      messages.FirestoreProjectsDatabasesUserCredsEnableRequest(
          name='projects/{}/databases/{}/userCreds/{}'.format(
              project,
              database,
              user_creds,
          ),
      )
  )


def DisableUserCreds(project, database, user_creds):
  """Disables a user creds.

  Args:
    project: the project of the database of the user creds, a string.
    database: the database id of the user creds, a string.
    user_creds: the user creds to disable, a string.

  Returns:
    a user creds.
  """
  messages = api_utils.GetMessages()
  return _GetUserCredsService().Disable(
      messages.FirestoreProjectsDatabasesUserCredsDisableRequest(
          name='projects/{}/databases/{}/userCreds/{}'.format(
              project,
              database,
              user_creds,
          ),
      )
  )


def ResetUserCreds(project, database, user_creds):
  """Resets a user creds.

  Args:
    project: the project of the database of the user creds, a string.
    database: the database id of the user creds, a string.
    user_creds: the user creds to reset, a string.

  Returns:
    a user creds.
  """
  messages = api_utils.GetMessages()
  return _GetUserCredsService().ResetPassword(
      messages.FirestoreProjectsDatabasesUserCredsResetPasswordRequest(
          name='projects/{}/databases/{}/userCreds/{}'.format(
              project,
              database,
              user_creds,
          ),
      )
  )


def DeleteUserCreds(project, database, user_creds):
  """Deletes a user creds.

  Args:
    project: the project of the database of the user creds, a string.
    database: the database id of the user creds, a string.
    user_creds: the user creds to delete, a string.

  Returns:
    Empty response message.
  """
  messages = api_utils.GetMessages()
  return _GetUserCredsService().Delete(
      messages.FirestoreProjectsDatabasesUserCredsDeleteRequest(
          name='projects/{}/databases/{}/userCreds/{}'.format(
              project,
              database,
              user_creds,
          ),
      )
  )
