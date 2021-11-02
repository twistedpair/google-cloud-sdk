# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Reducer functions to generate user props from prior state and flags."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


def ParsePasswordPolicy(sql_messages,
                        password_policy_allowed_failed_attempts=None,
                        password_policy_password_expiration_duration=None,
                        password_policy_enable_failed_attempts_check=None,
                        clear_password_policy=None):
  """Generates password policy for the user.

  Args:
    sql_messages: module, The messages module that should be used.
    password_policy_allowed_failed_attempts: int, Number of failed login
      attempts allowed before the user get locked.
    password_policy_password_expiration_duration: duration, Expiration duration
      after password is updated.
    password_policy_enable_failed_attempts_check: boolean, True if failed login
      attempts check enabled.
    clear_password_policy: boolean, True if clear existing password policy.

  Returns:
    sql_messages.UserPasswordValidationPolicy or None

  """
  should_generate_policy = any([
      password_policy_allowed_failed_attempts is not None,
      password_policy_password_expiration_duration is not None,
      password_policy_enable_failed_attempts_check is not None,
      clear_password_policy is not None,
  ])
  if not should_generate_policy:
    return None

  # Config exists, generate password policy.
  password_policy = sql_messages.UserPasswordValidationPolicy()

  # Directly return empty policy to clear the existing password policy.
  if clear_password_policy:
    return password_policy

  if password_policy_allowed_failed_attempts is not None:
    password_policy.allowedFailedAttempts = password_policy_allowed_failed_attempts
  if password_policy_password_expiration_duration is not None:
    password_policy.passwordExpirationDuration = str(
        password_policy_password_expiration_duration) + 's'
  if password_policy_enable_failed_attempts_check is not None:
    password_policy.enableFailedAttemptsCheck = password_policy_enable_failed_attempts_check

  return password_policy
