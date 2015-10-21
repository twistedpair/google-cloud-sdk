# Copyright 2014 Google Inc. All Rights Reserved.
"""Facilities for user prompting for request context."""

import abc

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.credentials import gce as c_gce
from googlecloudsdk.shared.compute import lister
from googlecloudsdk.shared.compute import utils


def _GetGCERegion():
  if properties.VALUES.core.check_gce_metadata.GetBool():
    return c_gce.Metadata().Region()
  return None


def _GetGCEZone():
  if properties.VALUES.core.check_gce_metadata.GetBool():
    return c_gce.Metadata().Zone()
  return None


GCE_SUGGESTION_SOURCES = {
    'zone': _GetGCEZone,
    'region': _GetGCERegion
}


class ScopePrompter(object):
  """A mixin class prompting in the case of ambiguous resource context."""

  __metaclass__ = abc.ABCMeta

  def GetCollection(self, resource_type):
    """Coverts a resource type to a collection."""
    resource_type = resource_type or self.resource_type
    if resource_type == 'zoneViews':
      return 'resourceviews.' + resource_type
    elif (resource_type == 'users' or
          resource_type == 'groups' or
          resource_type == 'globalAccountsOperations'):
      return 'clouduseraccounts.' + resource_type
    else:
      return 'compute.' + resource_type

  def HasDefaultValue(self, resource_type, scope_name):
    """Returns whether the scope has a default value."""
    collection = self.GetCollection(resource_type)
    api = utils.CollectionToApi(collection)
    try:
      self.resources.GetParamDefault(
          api=api,
          collection=resource_type,
          param=scope_name)
      return True
    except properties.RequiredPropertyError:
      return False

  def FetchChoiceResources(self, attribute, service, flag_names,
                           prefix_filter=None):
    """Returns a list of choices used to prompt with."""
    if prefix_filter:
      filter_expr = 'name eq {0}.*'.format(prefix_filter)
    else:
      filter_expr = None

    errors = []
    global_resources = lister.GetGlobalResources(
        service=service,
        project=self.project,
        filter_expr=filter_expr,
        http=self.http,
        batch_url=self.batch_url,
        errors=errors)

    choices = [resource for resource in global_resources]
    if errors or not choices:
      punctuation = ':' if errors else '.'
      utils.RaiseToolException(
          errors,
          'Unable to fetch a list of {0}s. Specifying [{1}] may fix this '
          'issue{2}'.format(attribute, ', or '.join(flag_names), punctuation))

    return choices

  def PromptForScope(self, ambiguous_refs, attribute, service, resource_type,
                     flag_names, prefix_filter):
    """Prompts user to specify a scope for ambiguous resources."""

    def RaiseOnPromptFailure():
      """Call this to raise an exn when prompt cannot read from input stream."""
      phrases = ('one of ', 'flags') if len(flag_names) > 1 else ('', 'flag')
      raise exceptions.ToolException(
          'Unable to prompt. Specify {0}the [{1}] {2}.'.format(
              phrases[0], ', '.join(flag_names), phrases[1]))

    # Update selected_resource_name in response to user prompts
    selected_resource_name = None

    # Try first to give a precise suggestion based on current VM zone/region.
    gce_suggestor = GCE_SUGGESTION_SOURCES.get(attribute) or (lambda: None)
    gce_suggested_resource = gce_suggestor()
    if gce_suggested_resource:
      selected_resource_name = self._PromptDidYouMeanScope(
          ambiguous_refs, attribute, resource_type, gce_suggested_resource,
          RaiseOnPromptFailure)

    # If the user said "no" fall back to a generic prompt.
    if selected_resource_name is None:
      choice_resources = self.FetchChoiceResources(attribute, service,
                                                   flag_names, prefix_filter)
      selected_resource_name = self._PromptForScopeList(
          ambiguous_refs, attribute, resource_type, choice_resources,
          RaiseOnPromptFailure)

    # _PromptForScopeList ensures this.
    assert selected_resource_name is not None

    for _, resource_ref in ambiguous_refs:
      setattr(resource_ref, attribute, selected_resource_name)

  def _PromptDidYouMeanScope(self, ambiguous_refs, attribute, resource_type,
                             suggested_resource, raise_on_prompt_failure):
    """Prompts "did you mean <scope>".  Returns str or None, or raises."""

    # targetInstances -> target instances
    resource_name = utils.CamelCaseToOutputFriendly(resource_type)
    names = ['[{0}]'.format(name) for name, _ in ambiguous_refs]
    message = 'Did you mean {0} [{1}] for {2}: [{3}]?'.format(
        attribute, suggested_resource, resource_name, names)

    try:
      if console_io.PromptContinue(message=message, default=True,
                                   throw_if_unattended=True):
        return suggested_resource
      else:
        return None
    except console_io.UnattendedPromptError:
      raise_on_prompt_failure()

  def _PromptForScopeList(self, ambiguous_refs, attribute,
                          resource_type, choice_resources,
                          raise_on_prompt_failure):
    """Prompt to resolve abiguous resources.  Either returns str or throws."""

    # targetInstances -> target instances
    resource_name = utils.CamelCaseToOutputFriendly(resource_type)
    # Resource names should be surrounded by brackets while choices should not
    names = ['[{0}]'.format(name) for name, _ in ambiguous_refs]
    # Print deprecation state for choices.
    choice_names = []
    for choice_resource in choice_resources:
      deprecated = choice_resource.deprecated
      if deprecated:
        choice_name = '{0} ({1})'.format(
            choice_resource.name, deprecated.state)
      else:
        choice_name = choice_resource.name
      choice_names.append(choice_name)

    title = utils.ConstructList(
        'For the following {0}:'.format(resource_name), names)
    idx = console_io.PromptChoice(
        options=choice_names,
        message='{0}choose a {1}:'.format(title, attribute))
    if idx is None:
      raise_on_prompt_failure()
    else:
      return choice_resources[idx].name

  def CreateScopedReferences(self, resource_names, scope_name, scope_arg,
                             scope_service, resource_type, flag_names,
                             prefix_filter=None):
    """Returns a list of resolved resource references for scoped resources."""
    resource_refs = []
    ambiguous_refs = []
    for resource_name in resource_names:
      resource_ref = self.resources.Parse(
          resource_name,
          collection=self.GetCollection(resource_type),
          params={scope_name: scope_arg},
          resolve=False)
      resource_refs.append(resource_ref)
      if not getattr(resource_ref, scope_name):
        ambiguous_refs.append((resource_name, resource_ref))

    has_default = self.HasDefaultValue(resource_type, scope_name)
    if ambiguous_refs and not scope_arg and not has_default:
      # We need to prompt.
      self.PromptForScope(
          ambiguous_refs=ambiguous_refs,
          attribute=scope_name,
          service=scope_service,
          resource_type=resource_type or self.resource_type,
          flag_names=flag_names,
          prefix_filter=prefix_filter)

    for resource_ref in resource_refs:
      resource_ref.Resolve()

    return resource_refs

  def CreateZonalReferences(self, resource_names, zone_arg, resource_type=None,
                            flag_names=None, region_filter=None):
    """Returns a list of resolved zonal resource references."""
    if flag_names is None:
      flag_names = ['--zone']

    if zone_arg:
      zone_ref = self.resources.Parse(zone_arg, collection='compute.zones')
      zone_name = zone_ref.Name()
    else:
      zone_name = None

    return self.CreateScopedReferences(
        resource_names,
        scope_name='zone',
        scope_arg=zone_name,
        scope_service=self.compute.zones,
        resource_type=resource_type,
        flag_names=flag_names,
        prefix_filter=region_filter)

  def CreateZonalReference(self, resource_name, zone_arg, resource_type=None,
                           flag_names=None, region_filter=None):
    return self.CreateZonalReferences(
        [resource_name], zone_arg, resource_type, flag_names, region_filter)[0]

  def CreateRegionalReferences(self, resource_names, region_arg,
                               flag_names=None, resource_type=None):
    """Returns a list of resolved regional resource references."""
    if flag_names is None:
      flag_names = ['--region']

    if region_arg:
      region_ref = self.resources.Parse(
          region_arg, collection='compute.regions')
      region_name = region_ref.Name()
    else:
      region_name = None

    return self.CreateScopedReferences(
        resource_names,
        scope_name='region',
        scope_arg=region_name,
        scope_service=self.compute.regions,
        flag_names=flag_names,
        resource_type=resource_type)

  def CreateRegionalReference(self, resource_name, region_arg,
                              flag_names=None, resource_type=None):
    return self.CreateRegionalReferences(
        [resource_name], region_arg, flag_names, resource_type)[0]

  def CreateGlobalReferences(self, resource_names, resource_type=None):
    """Returns a list of resolved global resource references."""
    resource_refs = []
    for resource_name in resource_names:
      resource_refs.append(self.resources.Parse(
          resource_name,
          collection=self.GetCollection(resource_type)))
    return resource_refs

  def CreateGlobalReference(self, resource_name, resource_type=None):
    return self.CreateGlobalReferences([resource_name], resource_type)[0]

  def CreateAccountsReferences(self, resource_names, resource_type=None):
    """Returns a list of resolved compute account resource references."""
    resource_refs = []
    for resource_name in resource_names:
      resource_refs.append(self.clouduseraccounts_resources.Parse(
          resource_name,
          collection=self.GetCollection(resource_type)))
    return resource_refs

  def CreateAccountsReference(self, resource_name, resource_type=None):
    return self.CreateAccountsReferences([resource_name], resource_type)[0]
