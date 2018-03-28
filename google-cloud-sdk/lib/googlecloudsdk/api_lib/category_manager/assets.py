# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Helpers for assets related operations in Cloud Category Manager."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from googlecloudsdk.api_lib.category_manager import utils

DELETE_TAG_NAME_PATTERN = '{}/annotationTag'


def ListAssetAnnotationTags(asset_ref):
  """Gets all annotation tags associated with an asset.

  Args:
    asset_ref: An asset reference object.

  Returns:
    A ListAnnotationTagsResponse message.
  """
  messages = utils.GetMessagesModule()
  # Set url_escape=True because the resource name of the asset must be escaped.
  req = messages.CategorymanagerAssetsAnnotationTagsListRequest(
      name=asset_ref.RelativeName(url_escape=True))
  return utils.GetClientInstance().assets_annotationTags.List(request=req)


def ApplyAnnotationTag(asset_ref, annotation_ref, sub_asset=None):
  """Applies an annotation tag to an asset.

  Args:
    asset_ref: An asset reference object.
    annotation_ref: An annotation reference object.
    sub_asset: A string representing the asset's sub-asset, if any.

  Returns:
    AnnotationTag response message.
  """
  messages = utils.GetMessagesModule()
  # Set url_escape=True because the resource name of the asset must be escaped.
  req = messages.CategorymanagerAssetsApplyAnnotationTagRequest(
      name=asset_ref.RelativeName(url_escape=True),
      applyAnnotationTagRequest=messages.ApplyAnnotationTagRequest(
          annotation=annotation_ref.RelativeName(), subAsset=sub_asset))
  return utils.GetClientInstance().assets.ApplyAnnotationTag(request=req)


def DeleteAnnotationTag(asset_ref, annotation_ref, sub_asset=None):
  """Delete an annotation tag on an asset.

  Args:
    asset_ref: An asset reference object.
    annotation_ref: An annotation reference object.
    sub_asset: A string representing the asset's sub-asset, if any.

  Returns:
    DeleteAnnotationTag response message.
  """
  messages = utils.GetMessagesModule()
  # Set url_escape=True because the resource name of the asset must be escaped.
  req = messages.CategorymanagerAssetsDeleteAnnotationTagRequest(
      name=DELETE_TAG_NAME_PATTERN.format(
          asset_ref.RelativeName(url_escape=True)),
      annotation=annotation_ref.RelativeName(),
      subAsset=sub_asset)
  return utils.GetClientInstance().assets.DeleteAnnotationTag(request=req)
