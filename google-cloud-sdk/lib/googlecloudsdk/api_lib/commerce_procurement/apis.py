# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Helpers for interacting with the Procurement API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import exceptions
from googlecloudsdk.core import properties

COMMERCE_PROCUREMENT_CONSUMER_API_NAME = 'cloudcommerceconsumerprocurement'
COMMERCE_PROCUREMENT_CONSUMER_API_VERSION = 'v1alpha1'


def GetMessagesModule():
  return apis.GetMessagesModule(COMMERCE_PROCUREMENT_CONSUMER_API_NAME,
                                COMMERCE_PROCUREMENT_CONSUMER_API_VERSION)


def GetClientInstance():
  return apis.GetClientInstance(COMMERCE_PROCUREMENT_CONSUMER_API_NAME,
                                COMMERCE_PROCUREMENT_CONSUMER_API_VERSION)


class Accounts(object):
  """The Accounts set of Commerce Procurement Consumer API functions."""

  GET_REQUEST = GetMessagesModule(
  ).CloudcommerceconsumerprocurementBillingAccountsAccountsGetRequest
  LIST_REQUEST = GetMessagesModule(
  ).CloudcommerceconsumerprocurementBillingAccountsAccountsListRequest

  @staticmethod
  def GetService():
    return GetClientInstance().billingAccounts_accounts

  @staticmethod
  def Get(account_name):
    """Calls the Procurement Consumer Accounts.Get method.

    Args:
      account_name: Name of an account.

    Returns:
      (Account)
    """
    request = GetMessagesModule(
    ).CloudcommerceconsumerprocurementBillingAccountsAccountsGetRequest(
        name=account_name)
    try:
      return Accounts.GetService().Get(request)
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(error)

  @staticmethod
  def List(billing_account_name, page_size, page_token):
    """Calls the Procurement Consumer Accounts.List method.

    Args:
      billing_account_name: Name of a billing account.
      page_size: Max size of records to be retrieved in page.
      page_token: Token to specify page in list.

    Returns:
      List of Accounts and next page token if applicable.
    """
    request = GetMessagesModule(
    ).CloudcommerceconsumerprocurementBillingAccountsAccountsListRequest(
        parent=billing_account_name, pageSize=page_size, pageToken=page_token)
    try:
      return Accounts.GetService().List(request)
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(error)


class Entitlements(object):
  """The Entitlements set of Commerce Procurement Consumer API functions."""

  GET_REQUEST = GetMessagesModule(
  ).CloudcommerceconsumerprocurementProjectsEntitlementsGetRequest
  LIST_REQUEST = GetMessagesModule(
  ).CloudcommerceconsumerprocurementProjectsEntitlementsListRequest

  @staticmethod
  def GetService():
    return GetClientInstance().projects_entitlements

  @staticmethod
  def Get(entitlement_name):
    """Calls the Procurement Consumer Entitlements.Get method.

    Args:
      entitlement_name: Name of an entitlement.

    Returns:
      (Entitlement)
    """
    request = GetMessagesModule(
    ).CloudcommerceconsumerprocurementProjectsEntitlementsGetRequest(
        name=entitlement_name)
    try:
      return Entitlements.GetService().Get(request)
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(error)

  @staticmethod
  def List(page_size, page_token):
    """Calls the Procurement Consumer Entitlements.List method.

    Args:
      page_size: Max size of records to be retrieved in page.
      page_token: Token to specify page in list.

    Returns:
      List of Entitlements and next page token if applicable.
    """
    project_name = 'projects/%s' % properties.VALUES.core.project.GetOrFail()
    request = GetMessagesModule(
    ).CloudcommerceconsumerprocurementProjectsEntitlementsListRequest(
        parent=project_name, pageSize=page_size, pageToken=page_token)
    try:
      return Entitlements.GetService().List(request)
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(error)


class FreeTrials(object):
  """The Free Trials set of Commerce Procurement Consumer API functions."""

  CREATE_REQUEST = GetMessagesModule(
  ).CloudcommerceconsumerprocurementProjectsFreeTrialsCreateRequest
  LIST_REQUEST = GetMessagesModule(
  ).CloudcommerceconsumerprocurementProjectsFreeTrialsListRequest

  @staticmethod
  def GetService():
    return GetClientInstance().projects_freeTrials

  @staticmethod
  def Create(provider_id, product_external_name):
    """Calls the Procurement Consumer FreeTrials.Create method.

    Args:
      provider_id: Id of the provider.
      product_external_name: Name of the product.

    Returns:
      (Operation)
    """
    project_name = 'projects/%s' % properties.VALUES.core.project.GetOrFail()
    provider_name = 'providers/%s' % provider_id
    free_trial = GetMessagesModule(
    ).GoogleCloudCommerceConsumerProcurementV1alpha1FreeTrial(
        provider=provider_name, productExternalName=product_external_name)
    request = GetMessagesModule(
    ).CloudcommerceconsumerprocurementProjectsFreeTrialsCreateRequest(
        parent=project_name,
        googleCloudCommerceConsumerProcurementV1alpha1FreeTrial=free_trial)
    try:
      return FreeTrials.GetService().Create(request)
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(error)

  @staticmethod
  def List(page_size, page_token, filter_rule):
    """Calls the Procurement Consumer FreeTrials.List method.

    Args:
      page_size: Max size of records to be retrieved in page.
      page_token: Token to specify page in list.
      filter_rule: The filter that can be used to limit the the result.

    Returns:
      List of Free Trials and next page token if applicable.
    """
    project_name = 'projects/%s' % properties.VALUES.core.project.GetOrFail()
    request = GetMessagesModule(
    ).CloudcommerceconsumerprocurementProjectsFreeTrialsListRequest(
        parent=project_name,
        pageSize=page_size,
        pageToken=page_token,
        filter=filter_rule)
    try:
      return FreeTrials.GetService().List(request)
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(error)
