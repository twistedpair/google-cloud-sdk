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

"""Command Utilities for ml products commands."""

ALPHA_LIST_NOTE = ('Note: For alpha, only catalogs with associated '
                   'ReferenceImages will be displayed by the list command. '
                   'Please be sure to note the catalog name at creation time '
                   'so that it can be used by `ml products catalogs '
                   'reference-image` commands.')

DELETE_IMAGE_NOTE = ('Note: ReferenceImages are only marked for deletion. The '
                     'ReferenceImages will remain in the catalog until the '
                     'next time the catalog is indexed (currently daily). The '
                     'actual image files are not deleted from '
                     'Google Cloud Storage.')

CATALOG_LIST_FORMAT = """
table(
  name,
  name.basename():label=CATALOG_ID
  )
"""

REF_IMAGE_LIST_FORMAT = """
table(
  name.basename(),
  name.segment(index=2):label=CATALOG_ID,
  productId,
  imageUri,
  category
  )
"""
