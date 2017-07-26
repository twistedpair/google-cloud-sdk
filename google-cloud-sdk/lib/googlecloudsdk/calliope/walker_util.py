# Copyright 2015 Google Inc. All Rights Reserved.
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

"""A collection of CLI walkers."""

import cStringIO
import os

from googlecloudsdk.calliope import arg_parsers
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
    self._toc_root.write('- title: "gcloud Reference"\n')
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
      title = ' '.join(command)
      while depth >= len(self._need_section_tag):
        self._need_section_tag.append(False)
      if depth == 1:
        if is_group:
          if self._toc_main:
            # Close the current main group toc if needed.
            self._toc_main.close()
          # Create a new main group toc.
          toc_path = os.path.join(directory, self._TOC)
          toc = open(toc_path, 'w')
          self._toc_main = toc
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

  def __init__(self, cli, directory, progress_callback=None):
    """Constructor.

    Args:
      cli: The Cloud SDK CLI object.
      directory: The help text output directory path name.
      progress_callback: f(float), The function to call to update the progress
        bar or None for no progress bar.
    """
    super(HelpTextGenerator, self).__init__(
        cli, progress_callback=progress_callback)
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


class DocumentGenerator(walker.Walker):
  """Generates style manpage files with suffix in an output directory.

  All files will be generated in one directory.

  Attributes:
    _directory: The document output directory.
    _style: The document style.
    _suffix: The output file suffix.
  """

  def __init__(self, cli, directory, style, suffix):
    """Constructor.

    Args:
      cli: The Cloud SDK CLI object.
      directory: The manpage output directory path name.
      style: The document style.
      suffix: The generate document file suffix. None for .<SECTION>.
    """
    super(DocumentGenerator, self).__init__(cli)
    self._directory = directory
    self._style = style
    self._suffix = suffix
    files.MakeDir(self._directory)

  def Visit(self, node, parent, is_group):
    """Renders document file for each node in the CLI tree.

    Args:
      node: group/command CommandCommon info.
      parent: The parent Visit() return value, None at the top level.
      is_group: True if node is a group, otherwise its is a command.

    Returns:
      The parent value, ignored here.
    """
    command = node.GetPath()
    path = os.path.join(self._directory, '_'.join(command)) + self._suffix
    with open(path, 'w') as f:
      md = markdown.Markdown(node)
      render_document.RenderDocument(style=self._style,
                                     title=' '.join(command),
                                     fin=cStringIO.StringIO(md),
                                     out=f)
    return parent


class HtmlGenerator(DocumentGenerator):
  """Generates HTML manpage files with suffix .html in an output directory.

  The output directory will contain a man1 subdirectory containing all of the
  HTML manpage files.
  """

  def __init__(self, cli, directory):
    """Constructor.

    Args:
      cli: The Cloud SDK CLI object.
      directory: The HTML output directory path name.
    """
    super(HtmlGenerator, self).__init__(
        cli, directory=directory, style='html', suffix='.html')


class ManPageGenerator(DocumentGenerator):
  """Generates manpage files with suffix .1 in an output directory.

  The output directory will contain a man1 subdirectory containing all of the
  manpage files.
  """

  _SECTION_FORMAT = 'man{section}'

  def __init__(self, cli, directory):
    """Constructor.

    Args:
      cli: The Cloud SDK CLI object.
      directory: The manpage output directory path name.
    """
    # Currently all gcloud manpages are in section 1.
    section_subdir = self._SECTION_FORMAT.format(section=1)
    section_dir = os.path.join(directory, section_subdir)
    super(ManPageGenerator, self).__init__(
        cli, directory=section_dir, style='man', suffix='.1')


class CommandTreeGenerator(walker.Walker):
  """Constructs a CLI command dict tree.

  This implements the resource generator for gcloud meta list-commands.

  Attributes:
    _with_flags: Include the non-global flags for each command/group if True.
    _with_flag_values: Include flag value choices or :type: if True.
    _global_flags: The set of global flags, only listed for the root command.
  """

  def __init__(self, cli, with_flags=False, with_flag_values=False):
    """Constructor.

    Args:
      cli: The Cloud SDK CLI object.
      with_flags: Include the non-global flags for each command/group if True.
      with_flag_values: Include flags and flag value choices or :type: if True.
    """
    super(CommandTreeGenerator, self).__init__(cli)
    self._with_flags = with_flags or with_flag_values
    self._with_flag_values = with_flag_values
    self._global_flags = set()

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
    info = {'_name_': name}
    if self._with_flags:
      all_flags = []
      for arg in node.GetAllAvailableFlags():
        value = None
        if self._with_flag_values:
          if arg.choices:
            choices = sorted(arg.choices)
            if choices != ['false', 'true']:
              value = ','.join([str(choice) for choice in choices])
          elif isinstance(arg.type, int):
            value = ':int:'
          elif isinstance(arg.type, float):
            value = ':float:'
          elif isinstance(arg.type, arg_parsers.ArgDict):
            value = ':dict:'
          elif isinstance(arg.type, arg_parsers.ArgList):
            value = ':list:'
          elif arg.nargs != 0:
            metavar = arg.metavar or arg.dest.upper()
            value = ':' + metavar + ':'
        for f in arg.option_strings:
          if value:
            f += '=' + value
          all_flags.append(f)
      no_prefix = '--no-'
      flags = []
      for flag in all_flags:
        if flag in self._global_flags:
          continue
        if flag.startswith(no_prefix):
          positive = '--' + flag[len(no_prefix):]
          if positive in all_flags:
            continue
        flags.append(flag)
      if flags:
        info['_flags_'] = sorted(flags)
        if not self._global_flags:
          # Most command flags are global (defined by the root command) or
          # command-specific. Group-specific flags are rare. Separating out
          # the global flags streamlines command descriptions and prevents
          # global flag changes (we already have too many!) from making it
          # look like every command has changed.
          self._global_flags.update(flags)
    if is_group:
      if parent:
        if 'groups' not in parent:
          parent['groups'] = []
        parent['groups'].append(info)
      return info
    if 'commands' not in parent:
      parent['commands'] = []
    parent['commands'].append(info)
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
