# Copyright 2015 Google Inc. All Rights Reserved.

"""Utilities for dealing with service resources."""


class Service(object):
  """Value class representing a service resource."""

  _RESOURCE_PATH_PARTS = 2  # project/service

  def __init__(self, project, id_, versions=None):
    self.project = project
    self.id = id_
    self.versions = versions or []

  def __eq__(self, other):
    return (type(other) is Service and
            self.project == other.project and self.id == other.id)

  def __ne__(self, other):
    return not self == other

  # TODO(b/25662075): convert to use functools.total_ordering
  def __lt__(self, other):
    return (self.project, self.id) < (other.project, other.id)

  def __le__(self, other):
    return (self.project, self.id) <= (other.project, other.id)

  def __gt__(self, other):
    return (self.project, self.id) > (other.project, other.id)

  def __ge__(self, other):
    return (self.project, self.id) >= (other.project, other.id)

  def __repr__(self):
    return '{0}/{1}'.format(self.project, self.id)
