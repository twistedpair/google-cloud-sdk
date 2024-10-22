# -*- coding: utf-8 -*-
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from googlecloudsdk.generated_clients.gapic_clients.storage_v2 import gapic_version as package_version

__version__ = package_version.__version__


from .services.storage import StorageClient
from .services.storage import StorageAsyncClient

from .types.storage import BidiWriteObjectRequest
from .types.storage import BidiWriteObjectResponse
from .types.storage import Bucket
from .types.storage import BucketAccessControl
from .types.storage import CancelResumableWriteRequest
from .types.storage import CancelResumableWriteResponse
from .types.storage import ChecksummedData
from .types.storage import CommonObjectRequestParams
from .types.storage import ComposeObjectRequest
from .types.storage import ContentRange
from .types.storage import CreateBucketRequest
from .types.storage import CustomerEncryption
from .types.storage import DeleteBucketRequest
from .types.storage import DeleteObjectRequest
from .types.storage import GetBucketRequest
from .types.storage import GetObjectRequest
from .types.storage import ListBucketsRequest
from .types.storage import ListBucketsResponse
from .types.storage import ListObjectsRequest
from .types.storage import ListObjectsResponse
from .types.storage import LockBucketRetentionPolicyRequest
from .types.storage import Object
from .types.storage import ObjectAccessControl
from .types.storage import ObjectChecksums
from .types.storage import Owner
from .types.storage import ProjectTeam
from .types.storage import QueryWriteStatusRequest
from .types.storage import QueryWriteStatusResponse
from .types.storage import ReadObjectRequest
from .types.storage import ReadObjectResponse
from .types.storage import RestoreObjectRequest
from .types.storage import RewriteObjectRequest
from .types.storage import RewriteResponse
from .types.storage import ServiceConstants
from .types.storage import StartResumableWriteRequest
from .types.storage import StartResumableWriteResponse
from .types.storage import UpdateBucketRequest
from .types.storage import UpdateObjectRequest
from .types.storage import WriteObjectRequest
from .types.storage import WriteObjectResponse
from .types.storage import WriteObjectSpec

__all__ = (
    'StorageAsyncClient',
'BidiWriteObjectRequest',
'BidiWriteObjectResponse',
'Bucket',
'BucketAccessControl',
'CancelResumableWriteRequest',
'CancelResumableWriteResponse',
'ChecksummedData',
'CommonObjectRequestParams',
'ComposeObjectRequest',
'ContentRange',
'CreateBucketRequest',
'CustomerEncryption',
'DeleteBucketRequest',
'DeleteObjectRequest',
'GetBucketRequest',
'GetObjectRequest',
'ListBucketsRequest',
'ListBucketsResponse',
'ListObjectsRequest',
'ListObjectsResponse',
'LockBucketRetentionPolicyRequest',
'Object',
'ObjectAccessControl',
'ObjectChecksums',
'Owner',
'ProjectTeam',
'QueryWriteStatusRequest',
'QueryWriteStatusResponse',
'ReadObjectRequest',
'ReadObjectResponse',
'RestoreObjectRequest',
'RewriteObjectRequest',
'RewriteResponse',
'ServiceConstants',
'StartResumableWriteRequest',
'StartResumableWriteResponse',
'StorageClient',
'UpdateBucketRequest',
'UpdateObjectRequest',
'WriteObjectRequest',
'WriteObjectResponse',
'WriteObjectSpec',
)
