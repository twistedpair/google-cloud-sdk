# Copyright 2015 Google Inc. All Rights Reserved.
"""Useful commands for interacting with the Cloud Resource Management API."""


from googlecloudsdk.api_lib.projects import util
from googlecloudsdk.third_party.apitools.base.py import list_pager


def List(client=None, messages=None, http=None, limit=None):
  if not client:
    if not http:
      raise ValueError('At least one of {client, http} must be provided.')
    client = util.GetClient(http)
  messages = messages or util.GetMessages()
  return list_pager.YieldFromList(
      client.projects,
      messages.CloudresourcemanagerProjectsListRequest(),
      limit=limit,
      field='projects',
      predicate=util.IsActive,
      batch_size_attribute='pageSize')
