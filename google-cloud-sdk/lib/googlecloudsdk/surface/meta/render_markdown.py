# Copyright 2015 Google Inc. All Rights Reserved.

"""A command that generates all DevSite and manpage documents."""

import sys

from googlecloudsdk.calliope import base
from googlecloudsdk.core.document_renderers import render_document


class GenerateHelpDocs(base.Command):
  """Uses gcloud's markdown renderer to render the given markdown file."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'md_file', help='The path to a file containing markdown to render.')
    parser.add_argument(
        '--style', default='text', help='The output format of the renderer.')

  def Run(self, args):
    with open(args.md_file, 'r') as f:
      render_document.RenderDocument(args.style, f, sys.stdout)
