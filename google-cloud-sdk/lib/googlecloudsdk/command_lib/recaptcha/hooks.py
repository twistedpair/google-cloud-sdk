# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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

"""Declarative hooks for reCAPTCHA Enterprise Keys CLI."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from googlecloudsdk.generated_clients.apis.recaptchaenterprise.v1 import recaptchaenterprise_v1_messages as messages


def SanitizePlatformSettings(unused_ref, args, request):
  """Make sure that at most one platform setting is set at the same time."""
  if args.android:
    request.googleCloudRecaptchaenterpriseV1Key.iosSettings = None
    request.googleCloudRecaptchaenterpriseV1Key.webSettings = None
    request.googleCloudRecaptchaenterpriseV1Key.expressSettings = None
  elif args.ios:
    request.googleCloudRecaptchaenterpriseV1Key.androidSettings = None
    request.googleCloudRecaptchaenterpriseV1Key.webSettings = None
    request.googleCloudRecaptchaenterpriseV1Key.expressSettings = None
  elif args.web:
    request.googleCloudRecaptchaenterpriseV1Key.androidSettings = None
    request.googleCloudRecaptchaenterpriseV1Key.iosSettings = None
    request.googleCloudRecaptchaenterpriseV1Key.expressSettings = None
  elif args.express:
    request.googleCloudRecaptchaenterpriseV1Key.expressSettings = (
        messages.GoogleCloudRecaptchaenterpriseV1ExpressKeySettings()
    )
    request.googleCloudRecaptchaenterpriseV1Key.androidSettings = None
    request.googleCloudRecaptchaenterpriseV1Key.iosSettings = None
    request.googleCloudRecaptchaenterpriseV1Key.webSettings = None
  else:
    request.googleCloudRecaptchaenterpriseV1Key.androidSettings = None
    request.googleCloudRecaptchaenterpriseV1Key.iosSettings = None
    request.googleCloudRecaptchaenterpriseV1Key.webSettings = None
    request.googleCloudRecaptchaenterpriseV1Key.expressSettings = None

  return request
