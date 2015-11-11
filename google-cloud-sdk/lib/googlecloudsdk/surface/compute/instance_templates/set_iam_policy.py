# Copyright 2015 Google Inc. All Rights Reserved.
"""Command to set IAM policy for a resource."""

from googlecloudsdk.api_lib.compute import iam_base_classes

# pylint: disable=invalid-name
SetIamPolicy = iam_base_classes.GenerateSetIamPolicy(
    iam_base_classes.GlobalSetIamPolicy, 'instanceTemplates',
    'instance template')
