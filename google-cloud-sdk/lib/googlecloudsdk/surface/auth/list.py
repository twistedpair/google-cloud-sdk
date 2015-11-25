# Copyright 2013 Google Inc. All Rights Reserved.

"""Command to list the available accounts."""

import textwrap

from googlecloudsdk.calliope import base
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.credentials import store as c_store
from googlecloudsdk.third_party.py27 import py27_collections as collections


class List(base.Command):
  """List the accounts for known credentials."""

  @staticmethod
  def Args(parser):
    parser.add_argument('--filter-account',
                        help='List only credentials for one account.')

  def Run(self, args):
    """List the account for known credentials."""
    accounts = c_store.AvailableAccounts()

    active_account = properties.VALUES.core.account.Get()

    if args.account:
      # TODO(jeffvaughan) Remove error after Sept. 13, 2015.
      raise exceptions.Error(
          'The behavior of ``gcloud auth list --account has changed. '
          'Please use ``--filter-account'' to filter the output of '
          '``auth list''.  Elsewhere in gcloud ``--account'' sets the '
          'currently active account and this behavior will become available '
          'to ``auth list'' in a future gcloud release.')

    if args.filter_account:
      if args.filter_account in accounts:
        accounts = [args.filter_account]
      else:
        accounts = []

    auth_info = collections.namedtuple(
        'auth_info',
        ['active_account', 'accounts'])
    return auth_info(active_account, accounts)

  def Display(self, unused_args, result):
    if result.accounts:
      lp = console_io.ListPrinter('Credentialed accounts:')
      lp.Print([account +
                (' (active)' if account == result.active_account else '')
                for account in result.accounts])
      log.err.Print(textwrap.dedent("""
          To set the active account, run:
            $ gcloud config set account ``ACCOUNT''
          """))
    else:
      log.err.Print(textwrap.dedent("""\
          No credentialed accounts.

          To login, run:
            $ gcloud auth login ``ACCOUNT''
          """))
