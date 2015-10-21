# Copyright 2013 Google Inc. All Rights Reserved.

"""The gcloud app group."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


# TODO(b/24169312): remove
CHANGE_WARNING = """\
The `gcloud preview app` surface is rapidly improving. Look out for
changing flags and new commands before the transition out of the `preview`
component. These changes will be documented in the Cloud SDK release notes
<https://goo.gl/X8apDJ> and via deprecation notices for changing commands.

If you would like to avoid changing behavior, please pin to a fixed version of
the Google Cloud SDK as described under the "Alternative Methods" section of the
Cloud SDK web site: <https://cloud.google.com/sdk/#alternative>.
"""


@base.Beta
class Appengine(base.Group):
  """Manage your App Engine app.

  This set of commands allows you to deploy your app, manage your existing
  deployments, and also run your app locally.  These commands replace their
  equivalents in the appcfg tool.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To run your app locally in the development application server, run:

            $ {command} run DEPLOYABLES

          To create a new deployment of one or more modules, run:

            $ {command} deploy DEPLOYABLES

          To list your existing deployments, run:

            $ {command} modules list

          To generate config files for your source directory:

            $ {command} gen-config
          """,
  }

  def Filter(self, unused_context, unused_args):
    # TODO(b/24169312): remove
    if not properties.VALUES.app.suppress_change_warning.GetBool():
      log.warn(CHANGE_WARNING)
    properties.PersistProperty(properties.VALUES.app.suppress_change_warning,
                               'true')
