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

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.compute.reservations import flags as reservation_flags


def AddRegionFlag(parser):
  """Add the --region flag."""
  compute_flags.AddRegionFlag(
      parser=parser, resource_type=None, operation_type=None
  )


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
        See <a href="https://cloud.google.com/sdk/gcloud/reference/topic/datetimes">
        $ gcloud topic datetimes</a> for information on time formats.

        *from*::: The earliest possible start time for the reservation.
        *to*::: The latest possible start time for the reservation.

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
        See <a href="https://cloud.google.com/sdk/gcloud/reference/topic/datetimes">
        $ gcloud topic datetimes</a> for information on time formats.

        *from*::: The earliest possible end time for the reservation.
        *to*::: The latest possible end time for the reservation.

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

        See <a href="https://cloud.google.com/sdk/gcloud/reference/topic/datetimes">
        $ gcloud topic datetimes</a> for information on duration format.

        *min*::: The minimum duration of the Future Reservation.
        *max*::: The maximum duration of the Future Reservation.

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

  # future_reservation_flags.GetDeploymentTypeFlag().AddToParser(parser)

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
