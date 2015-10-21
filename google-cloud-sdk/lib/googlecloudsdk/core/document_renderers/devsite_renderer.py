# Copyright 2015 Google Inc. All Rights Reserved.

"""Cloud SDK markdown document HTML renderer."""

from googlecloudsdk.core.document_renderers import devsite_scripts
from googlecloudsdk.core.document_renderers import html_renderer


class DevSiteRenderer(html_renderer.HTMLRenderer):
  """Renders markdown to DevSiteHTML."""

  def __init__(self, *args, **kwargs):
    super(DevSiteRenderer, self).__init__(*args, **kwargs)

  def _Title(self):
    """Renders an HTML document title."""
    self._out.write(
        '<html devsite="">\n'
        '<head>\n')
    if self._title:
      self._out.write(
          '<title>' + self._title + '</title>\n')
    self._out.write(
        '<meta http-equiv="Content-Type" content="text/html; '
        'charset=UTF-8">\n'
        '<meta name="project_path" value="/sdk/_project.yaml">\n'
        '<meta name="book_path" value="/sdk/_book.yaml">\n')
    for comment, script in devsite_scripts.SCRIPTS:
      self._out.write('<!-- {comment} -->\n{script}\n'.format(comment=comment,
                                                              script=script))

  def _Heading(self, unused_level, heading):
    """Renders a DevSite heading.

    Args:
      unused_level: The heading level counting from 1.
      heading: The heading text.
    """
    self._heading = '</dd>\n</section>\n'
    self._out.write('\n<section id="{heading}">\n'
                    '<dt>{heading}</dt>\n<dd class="sectionbody">\n'.format(
                        heading=heading))
