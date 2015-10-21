# Copyright 2015 Google Inc. All Rights Reserved.
"""managed-instance-groups list-instances command.

It's an alias for the instance-groups list-instances command.
"""
from googlecloudsdk.shared.compute import instance_groups_utils
from googlecloudsdk.shared.compute import path_simplifier
from googlecloudsdk.shared.compute import property_selector
from googlecloudsdk.shared.compute import request_helper


def LastAttemptErrorToMessage(last_attempt):
  if 'errors' not in last_attempt:
    return None
  if 'errors' not in last_attempt['errors']:
    return None
  return ', '.join(['Error ' + e['code'] + ': ' + e['message']
                    for e in last_attempt['errors']['errors']])


class ListInstances(instance_groups_utils.InstanceGroupListInstancesBase):
  """List Google Compute Engine instances present in managed instance group."""

  _LIST_TABS = [
      ('NAME', property_selector.PropertyGetter('instance')),
      ('STATUS', property_selector.PropertyGetter('instanceStatus')),
      ('ACTION', property_selector.PropertyGetter('currentAction')),
      ('LAST_ERROR', property_selector.PropertyGetter('lastAttempt'))]

  _FIELD_TRANSFORMS = [
      ('instance', path_simplifier.Name),
      ('lastAttempt', LastAttemptErrorToMessage)]

  @property
  def service(self):
    return self.compute.instanceGroupManagers

  @property
  def resource_type(self):
    return 'instanceGroups'

  @property
  def method(self):
    return 'ListManagedInstances'

  @property
  def list_field(self):
    return 'managedInstances'

  def GetResources(self, args):
    """Retrieves response with instance in the instance group."""
    group_ref = self.CreateZonalReference(args.name, args.zone)

    request = self.service.GetRequestType(self.method)(
        instanceGroupManager=group_ref.Name(),
        zone=group_ref.zone,
        project=self.context['project'])

    errors = []
    results = list(request_helper.MakeRequests(
        requests=[(self.service, self.method, request)],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors,
        custom_get_requests=None))

    return results, errors

  detailed_help = {
      'brief': 'List instances present in the managed instance group',
      'DESCRIPTION': """\
          *{command}* list instances in a managed instance group.
          """,
  }
