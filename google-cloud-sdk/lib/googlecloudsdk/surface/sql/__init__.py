# Copyright 2013 Google Inc. All Rights Reserved.

"""The super-group for the sql CLI.

The fact that this is a directory with
an __init__.py in it makes it a command group. The methods written below will
all be called by calliope (though they are all optional).
"""
import argparse
import os
import re

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import config
from googlecloudsdk.core import properties
from googlecloudsdk.core import resolvers
from googlecloudsdk.core import resources as cloud_resources
from googlecloudsdk.core.credentials import store as c_store
from googlecloudsdk.third_party.apis.sqladmin import v1beta3 as sql_v1beta3
from googlecloudsdk.third_party.apis.sqladmin import v1beta4 as sql_v1beta4


_ACTIVE_VERSIONS = [
    'v1beta3',
    'v1beta4',
]


def _Args(parser):
  parser.add_argument(
      '--api-version',
      help=argparse.SUPPRESS,
      choices=_ACTIVE_VERSIONS)


def _DoFilter(context, http, api_version_default, api_version_arg):
  """Set up and return the context to be used by all SQL release tracks."""

  api_version = api_version_default
  if properties.VALUES.api_client_overrides.sql.Get():
    api_version = properties.VALUES.api_client_overrides.sql.Get()
  if api_version_arg:
    api_version = api_version_arg

  cloud_resources.SetParamDefault(
      api='sql', collection=None, param='project',
      resolver=resolvers.FromProperty(properties.VALUES.core.project))

  url = properties.VALUES.api_endpoint_overrides.sql.Get()

  context['sql_client-v1beta3'] = sql_v1beta3.SqladminV1beta3(
      get_credentials=False, url=url, http=http)
  context['sql_messages-v1beta3'] = sql_v1beta3
  context['registry-v1beta3'] = cloud_resources.REGISTRY.CloneAndSwitchAPIs(
      context['sql_client-v1beta3'])

  context['sql_client-v1beta4'] = sql_v1beta4.SqladminV1beta4(
      get_credentials=False, url=url, http=http)
  context['sql_messages-v1beta4'] = sql_v1beta4
  context['registry-v1beta4'] = cloud_resources.REGISTRY.CloneAndSwitchAPIs(
      context['sql_client-v1beta4'])

  context['sql_client'] = context['sql_client-' + api_version]
  context['sql_messages'] = context['sql_messages-' + api_version]
  context['registry'] = context['registry-' + api_version]

  return context


@base.ReleaseTracks(base.ReleaseTrack.GA)
class SQL(base.Group):
  """Manage Cloud SQL databases."""

  @staticmethod
  def Args(parser):
    _Args(parser)

  @exceptions.RaiseToolExceptionInsteadOf(c_store.Error)
  def Filter(self, context, args):
    _DoFilter(context, self.Http(), 'v1beta3', args.api_version)


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class SQLBeta(base.Group):
  """Manage Cloud SQL databases."""

  @staticmethod
  def Args(parser):
    _Args(parser)

  @exceptions.RaiseToolExceptionInsteadOf(c_store.Error)
  def Filter(self, context, args):
    _DoFilter(context, self.Http(), 'v1beta4', args.api_version)
