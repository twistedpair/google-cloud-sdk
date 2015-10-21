# Copyright 2015 Google Inc. All Rights Reserved.

"""A collection of CLI walkers."""

import cStringIO
import os

from googlecloudsdk.calliope import cli_tree
from googlecloudsdk.calliope import markdown
from googlecloudsdk.calliope import walker
from googlecloudsdk.core.document_renderers import render_document
from googlecloudsdk.core.util import files


class DevSiteGenerator(walker.Walker):
  """Generates DevSite reference HTML in a directory hierarchy.

  This implements gcloud meta generate-help-docs --manpage-dir=DIRECTORY.

  Attributes:
    _directory: The DevSite reference output directory.
    _need_section_tag[]: _need_section_tag[i] is True if there are section
      subitems at depth i. This prevents the creation of empty 'section:' tags
      in the '_toc' files.
    _toc_root: The root TOC output stream.
    _toc_main: The current main (just under root) TOC output stream.
  """

  _REFERENCE = '/sdk/gcloud/reference'  # TOC reference directory offset.
  _TOC = '_toc.yaml'

  def __init__(self, cli, directory):
    """Constructor.

    Args:
      cli: The Cloud SDK CLI object.
      directory: The DevSite output directory path name.
    """
    super(DevSiteGenerator, self).__init__(cli)
    self._directory = directory
    files.MakeDir(self._directory)
    self._need_section_tag = []
    toc_path = os.path.join(self._directory, self._TOC)
    self._toc_root = open(toc_path, 'w')
    self._toc_root.write('toc:\n')
    self._toc_root.write('- title: "Reference"\n')
    self._toc_root.write('  path: %s\n' % self._REFERENCE)
    self._toc_root.write('  section:\n')
    self._toc_main = None

  def Visit(self, node, parent, is_group):
    """Updates the TOC and Renders a DevSite doc for each node in the CLI tree.

    Args:
      node: group/command CommandCommon info.
      parent: The parent Visit() return value, None at the top level.
      is_group: True if node is a group, otherwise its is a command.

    Returns:
      The parent value, ignored here.
    """
    def _UpdateTOC():
      """Updates the DevSIte TOC."""
      depth = len(command) - 1
      if not depth:
        return
      while depth >= len(self._need_section_tag):
        self._need_section_tag.append(False)
      if depth == 1:
        if self._toc_main:
          # Close the current main group toc if needed.
          self._toc_main.close()
        # Create a new main group toc.
        toc_path = os.path.join(directory, self._TOC)
        toc = open(toc_path, 'w')
        self._toc_main = toc
        title = ' '.join(command)
        toc.write('toc:\n')
        toc.write('- title: "%s"\n' % title)
        toc.write('  path: %s\n' % '/'.join([self._REFERENCE] + command[1:]))
        self._need_section_tag[depth] = True

        toc = self._toc_root
        indent = '  '
        if is_group:
          toc.write('%s- include: %s\n' % (
              indent, '/'.join([self._REFERENCE] + command[1:] + [self._TOC])))
          return
      else:
        toc = self._toc_main
        indent = '  ' * (depth - 1)
        if self._need_section_tag[depth - 1]:
          self._need_section_tag[depth - 1] = False
          toc.write('%ssection:\n' % indent)
        title = command[-1]
      toc.write('%s- title: "%s"\n' % (indent, title))
      toc.write('%s  path: %s\n' % (indent,
                                    '/'.join([self._REFERENCE] + command[1:])))
      self._need_section_tag[depth] = is_group

    # Set up the destination dir for this level.
    command = node.GetPath()
    if is_group:
      directory = os.path.join(self._directory, *command[1:])
      files.MakeDir(directory, mode=0755)
    else:
      directory = os.path.join(self._directory, *command[1:-1])

    # Render the DevSite document.
    path = os.path.join(
        directory, 'index' if is_group else command[-1]) + '.html'
    with open(path, 'w') as f:
      md = markdown.Markdown(node)
      render_document.RenderDocument(style='devsite',
                                     title=' '.join(command),
                                     fin=cStringIO.StringIO(md),
                                     out=f)
    _UpdateTOC()
    return parent

  def Done(self):
    """Closes the TOC files after the CLI tree walk is done."""
    self._toc_root.close()
    if self._toc_main:
      self._toc_main.close()


class HelpTextGenerator(walker.Walker):
  """Generates help text files in a directory hierarchy.

  Attributes:
    _directory: The help text output directory.
  """

  def __init__(self, cli, directory):
    """Constructor.

    Args:
      cli: The Cloud SDK CLI object.
      directory: The help text output directory path name.
    """
    super(HelpTextGenerator, self).__init__(cli)
    self._directory = directory
    files.MakeDir(self._directory)

  def Visit(self, node, parent, is_group):
    """Renders a help text doc for each node in the CLI tree.

    Args:
      node: group/command CommandCommon info.
      parent: The parent Visit() return value, None at the top level.
      is_group: True if node is a group, otherwise its is a command.

    Returns:
      The parent value, ignored here.
    """
    # Set up the destination dir for this level.
    command = node.GetPath()
    if is_group:
      directory = os.path.join(self._directory, *command[1:])
      files.MakeDir(directory, mode=0755)
    else:
      directory = os.path.join(self._directory, *command[1:-1])

    # Render the help text document.
    path = os.path.join(directory, 'GROUP' if is_group else command[-1])
    with open(path, 'w') as f:
      md = markdown.Markdown(node)
      render_document.RenderDocument(style='text', fin=cStringIO.StringIO(md),
                                     out=f)
    return parent


class ManPageGenerator(walker.Walker):
  """Generates manpage man(1) files in an output directory.

  This implements gcloud meta generate-help-docs --manpage-dir=DIRECTORY.

  The output directory will contain a manN subdirectory for each section N
  required by markdown.

  Attributes:
    _directory: The manpage output directory.
  """

  _SECTION_FORMAT = 'man{section}'

  def __init__(self, cli, directory):
    """Constructor.

    Args:
      cli: The Cloud SDK CLI object.
      directory: The manpage output directory path name.
    """
    super(ManPageGenerator, self).__init__(cli)
    # Currently all gcloud manpages are in section 1.
    section_1 = self._SECTION_FORMAT.format(section=1)
    self._directory = os.path.join(directory, section_1)
    files.MakeDir(self._directory)

  def Visit(self, node, parent, is_group):
    """Renders a manpage doc for each node in the CLI tree.

    Args:
      node: group/command CommandCommon info.
      parent: The parent Visit() return value, None at the top level.
      is_group: True if node is a group, otherwise its is a command.

    Returns:
      The parent value, ignored here.
    """
    command = node.GetPath()
    path = os.path.join(self._directory, '_'.join(command)) + '.1'
    with open(path, 'w') as f:
      md = markdown.Markdown(node)
      render_document.RenderDocument(style='man',
                                     title=' '.join(command),
                                     fin=cStringIO.StringIO(md),
                                     out=f)
    return parent


class CommandTreeGenerator(walker.Walker):
  """Constructs a CLI command dict tree.

  This implements the resource generator for gcloud meta list-commands.
  """

  def __init__(self, cli):
    """Constructor.

    Args:
      cli: The Cloud SDK CLI object.
    """
    super(CommandTreeGenerator, self).__init__(cli)

  def Visit(self, node, parent, is_group):
    """Visits each node in the CLI command tree to construct the dict tree.

    Args:
      node: group/command CommandCommon info.
      parent: The parent Visit() return value, None at the top level.
      is_group: True if node is a group, otherwise its is a command.

    Returns:
      The subtree parent value, used here to construct a dict tree.
    """
    name = node.name.replace('_', '-')
    if is_group:
      info = {}
      info['_name_'] = name
      if parent:
        if 'groups' not in parent:
          parent['groups'] = []
        parent['groups'].append(info)
      return info
    if 'commands' not in parent:
      parent['commands'] = []
    parent['commands'].append(name)
    return None


class GCloudTreeGenerator(walker.Walker):
  """Generates an external representation of the gcloud CLI tree.

  This implements the resource generator for gcloud meta list-gcloud.
  """

  def __init__(self, cli):
    """Constructor.

    Args:
      cli: The Cloud SDK CLI object.
    """
    super(GCloudTreeGenerator, self).__init__(cli)

  def Visit(self, node, parent, is_group):
    """Visits each node in the CLI command tree to construct the external rep.

    Args:
      node: group/command CommandCommon info.
      parent: The parent Visit() return value, None at the top level.
      is_group: True if node is a group, otherwise its is a command.

    Returns:
      The subtree parent value, used here to construct an external rep node.
    """
    return cli_tree.Command(node, parent)
