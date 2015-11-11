# Copyright 2015 Google Inc. All Rights Reserved.
"""Command to get IAM policy for a resource."""

from googlecloudsdk.api_lib.compute import iam_base_classes

# pylint: disable=invalid-name
GetIamPolicy = iam_base_classes.GenerateGetIamPolicy(
    iam_base_classes.ZonalGetIamPolicy, 'instances', 'instance',
    'compute.instances')
