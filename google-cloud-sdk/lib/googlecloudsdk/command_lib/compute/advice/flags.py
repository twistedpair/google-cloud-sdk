# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Advice group command flags."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.compute.reservations import flags as reservation_flags
from googlecloudsdk.command_lib.util.apis import arg_utils


def AddRegionFlag(parser):
  """Add the --region flag."""
  compute_flags.AddRegionFlag(
      parser=parser,
      resource_type="resources",
      operation_type="get advice on")


def AddLocationPolicyFlag(parser):
  """Add the --location_policy flag."""
  parser.add_argument(
      "--location-policy",
      metavar="ZONE=POLICY",
      type=arg_parsers.ArgDict(),
      help="""
        Policy for which zones to include or exclude when looking for the optimal
        time window and zone for Future Reservations within a region. Policy is
        defined as a list of key-value pairs, with the key being the zone name,
        and value being the applied policy. Available policies are `allow` and
        `deny`. Default for zones if left unspecified is `allow`.

        Example:

          gcloud compute advice calendar-mode --location-policy=us-central1-a=allow,us-central1-b=deny
      """,
  )


def AddStartTimeRangeFlag(parser):
  """Add the --start-time-range flag."""
  parser.add_argument(
      "--start-time-range",
      type=arg_parsers.ArgDict(
          spec={
              "from": arg_parsers.Datetime.Parse,
              "to": arg_parsers.Datetime.Parse,
          },
          max_length=2,
      ),
      help="""
        A time range for the start time of the Future Reservation. Defined as
        a list of key-value pairs.

        The key is either "from" or "to", and the value is a datetime.
        See $ gcloud topic datetimes for information on time formats.

        *from*:: The earliest possible start time for the reservation.
        *to*:: The latest possible start time for the reservation.

        Example:

          gcloud compute advice calendar-mode --start-time-range=from=2024-08-01T00:00:00Z,to=2024-08-02T00:00:00Z
      """,
  )


def AddEndTimeRangeFlag(parser):
  """Add the --end-time-range flag."""
  parser.add_argument(
      "--end-time-range",
      type=arg_parsers.ArgDict(
          spec={
              "from": arg_parsers.Datetime.Parse,
              "to": arg_parsers.Datetime.Parse,
          },
          max_length=2,
      ),
      help="""
        A time range for the end time of the Future Reservation. Defined as
        a list of key-value pairs.

        The key is either "from" or "to", and the value is a datetime.
        See $ gcloud topic datetimes for information on time formats.

        *from*:: The earliest possible end time for the reservation.
        *to*:: The latest possible end time for the reservation.

        Example:

          gcloud compute advice calendar-mode --end-time-range=from=2024-08-01T00:00:00Z,to=2024-08-02T00:00:00Z
      """,
  )


def AddDurationRangeFlag(parser):
  """Add the --duration-range flag."""
  parser.add_argument(
      "--duration-range",
      type=arg_parsers.ArgDict(
          spec={
              "min": arg_parsers.Duration(),
              "max": arg_parsers.Duration(),
          },
          max_length=2,
      ),
      help="""
        A duration range for the duration of the Future Reservation. Defined as
        a list of key-value pairs.

        The key is either "min" or "max", and the value is a duration in seconds.
        For example, specify `30m` for a duration of 30 minutes or specify
        `1d2h3m4s` for a duration of 1 day, 2 hours, 3 minutes, and 4 seconds.

        See $ gcloud topic datetimes for information on duration formats.

        *min*:: The minimum duration of the Future Reservation.
        *max*:: The maximum duration of the Future Reservation.

        Example:

          gcloud compute advice calendar-mode --duration-range=min=24h,max=72h
      """,
  )


def AddSkuPropertiesFlags(accelerator_properties_group):
  """Add the SKU properties flags."""

  instance_properties_group = accelerator_properties_group.add_group(help="""
        Define individual instance properties for the specific SKU reservation.
      """)

  # add --machine-type
  reservation_flags.GetMachineType(True).AddToParser(instance_properties_group)

  # add --vm-count
  vm_count_flag = reservation_flags.GetVmCountFlag(True)
  vm_count_flag.kwargs["help"] = (
      """The number of instances to check for availability."""
  )
  vm_count_flag.AddToParser(instance_properties_group)

  # add --local-ssd
  local_ssd_flag = reservation_flags.GetLocalSsdFlag()
  local_ssd_flag.kwargs["help"] = """\
  Manage the size and the interface of local SSD to use. See
  https://cloud.google.com/compute/docs/disks/local-ssd for more information.
  *interface*::: The kind of disk interface exposed to the VM for this SSD.
  The only valid value is `nvme`.
  *size*::: The size of the local SSD in base-2 GB."""
  local_ssd_flag.AddToParser(instance_properties_group)


def AddAggregatePropertiesFlags(accelerator_properties_group):
  """Add the aggregate properties flags."""

  aggregate_properties_group = accelerator_properties_group.add_group(help="""
          You must define the version and number of TPUs to reserve.
        """)

  # add --tpu-version
  reservation_flags.GetTpuVersion(True).AddToParser(aggregate_properties_group)

  # add --chip-count
  chip_count_flag = reservation_flags.GetChipCount(True)
  chip_count_flag.kwargs["help"] = (
      """The number of chips to check for availability."""
  )
  chip_count_flag.AddToParser(aggregate_properties_group)

  # add --workload-type
  workload_type_flag = reservation_flags.GetWorkloadType(False)
  workload_type_flag.kwargs["help"] = (
      """Type of the workload that will be running on the reserved TPUs."""
  )
  workload_type_flag.kwargs["choices"]["SERVING"] = (
      "Reserved resources will be optimized for SERVING workloads that"
      " handle concurrent requests and require minimal network latency,"
      " such as ML inference."
  )
  workload_type_flag.kwargs["choices"]["BATCH"] = (
      "Reserved resources will be optimized for BATCH workloads that"
      " handle large amounts of data in single or multiple operations,"
      " such as ML training workloads."
  )
  workload_type_flag.AddToParser(aggregate_properties_group)


def AddAcceleratorPropertiesFlags(parser):
  """Add the accelerator properties flags."""
  accelerator_properties_group = parser.add_group(
      help="""
        Specify the properties of the resources that you want to view the availability of.
      """,
      mutex=True,
      required=True,
  )

  AddSkuPropertiesFlags(accelerator_properties_group)
  AddAggregatePropertiesFlags(accelerator_properties_group)


def AddDeploymentTypeFlag(parser):
  """Add the --deployment-type flag."""

  # Calendar Mode currently only supports Dense deployment as a MVP; this will
  # be the default. Once the Flexible deployment is supported we will use the
  # deployment-type flag from the Future Reservations.

  help_text = """\
  The deployment type for the reserved capacity.
  """
  parser.add_argument(
      "--deployment-type",
      choices={
          "DENSE": "DENSE mode is for densely deployed reservation blocks.",
      },
      default="DENSE",
      help=help_text,
      hidden=True,
  )


def AddProvisioningModelFlag(parser):
  """Add the --provisioning-model flag."""
  provisioning_model_choices = {
      "SPOT": (
          "Compute Engine may preempt a Spot VM whenever it needs capacity. "
          "Because Spot VMs don't have a guaranteed runtime, they come at a "
          "discounted price."
      ),
  }
  parser.add_argument(
      "--provisioning-model",
      choices=provisioning_model_choices,
      type=arg_utils.ChoiceToEnumName,
      required=True,
      help="""
Specifies the provisioning model.
""",
  )


def AddTargetDistributionShapeFlag(parser):
  """Add the --target-distribution-shape flag."""
  help_text = """\
Defines the distribution requirement for the requested VMs.
  """
  choices = {
      "ANY": (
          "When you specify ANY for VM instance creation across multiple"
          " zones, you specify that you want to create your VM instances in one"
          " or more zones based on resource availability, and to use any"
          " unused, matching reservation in your project. Use ANY for batch"
          " workloads that don't require high availability."
      ),
      "ANY_SINGLE_ZONE": (
          "When you specify ANY_SINGLE_ZONE for VM instance creation, you"
          " specify that you want to create all VM instances in a single"
          " available zone. Compute Engine selects this zone based on resource"
          " availability and on any unused, matching reservation in your"
          " project. However, zonal resource availability constraints might"
          " prevent Compute Engine from creating all your requested VM"
          " instances. Use ANY_SINGLE_ZONE when the VM instances in your"
          " workloads need to frequently communicate among each other."
      ),
  }
  parser.add_argument(
      "--target-distribution-shape",
      choices=choices,
      type=arg_utils.ChoiceToEnumName,
      required=True,
      help=help_text)


def ValidateZonesAndRegionFlags(args, resources):
  """Validate --zones and --region flags."""
  if not args.zones:
    return

  ignored_required_params = {"project": "fake"}
  zone_names = []
  for zone in args.zones:
    zone_ref = resources.Parse(
        zone, collection="compute.zones", params=ignored_required_params
    )
    zone_names.append(zone_ref.Name())

  zone_regions = set([utils.ZoneNameToRegionName(z) for z in zone_names])
  if len(zone_regions) > 1:
    raise exceptions.InvalidArgumentException(
        "--zones", "All zones must be in the same region."
    )
  elif len(zone_regions) == 1 and args.region:
    zone_region = zone_regions.pop()
    region_ref = resources.Parse(
        args.region,
        collection="compute.regions",
        params=ignored_required_params,
    )
    region = region_ref.Name()
    if zone_region != region:
      raise exceptions.InvalidArgumentException(
          "--zones",
          "Specified zones are not in specified region [{0}].".format(region),
      )
