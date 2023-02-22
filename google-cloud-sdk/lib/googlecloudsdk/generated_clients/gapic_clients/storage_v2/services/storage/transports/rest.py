# -*- coding: utf-8 -*-
# Copyright 2022 Google LLC
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

from google.auth.transport.requests import AuthorizedSession  # type: ignore
import json  # type: ignore
import grpc  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.api_core import exceptions as core_exceptions
from google.api_core import retry as retries
from google.api_core import rest_helpers
from google.api_core import rest_streaming
from google.api_core import path_template
from google.api_core import gapic_v1

from cloudsdk.google.protobuf import json_format
from requests import __version__ as requests_version
import dataclasses
import re
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union
import warnings

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object]  # type: ignore


from google.iam.v1 import iam_policy_pb2  # type: ignore
from google.iam.v1 import policy_pb2  # type: ignore
from cloudsdk.google.protobuf import empty_pb2  # type: ignore
from googlecloudsdk.generated_clients.gapic_clients.storage_v2.types import storage

from .base import StorageTransport, DEFAULT_CLIENT_INFO as BASE_DEFAULT_CLIENT_INFO


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=BASE_DEFAULT_CLIENT_INFO.gapic_version,
    grpc_version=None,
    rest_version=requests_version,
)


class StorageRestInterceptor:
    """Interceptor for Storage.

    Interceptors are used to manipulate requests, request metadata, and responses
    in arbitrary ways.
    Example use cases include:
    * Logging
    * Verifying requests according to service or custom semantics
    * Stripping extraneous information from responses

    These use cases and more can be enabled by injecting an
    instance of a custom subclass when constructing the StorageRestTransport.

    .. code-block:: python
        class MyCustomStorageInterceptor(StorageRestInterceptor):
            def pre_cancel_resumable_write(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_cancel_resumable_write(response):
                logging.log(f"Received response: {response}")

            def pre_compose_object(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_compose_object(response):
                logging.log(f"Received response: {response}")

            def pre_create_bucket(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_create_bucket(response):
                logging.log(f"Received response: {response}")

            def pre_create_hmac_key(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_create_hmac_key(response):
                logging.log(f"Received response: {response}")

            def pre_create_notification_config(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_create_notification_config(response):
                logging.log(f"Received response: {response}")

            def pre_delete_bucket(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def pre_delete_hmac_key(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def pre_delete_notification_config(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def pre_delete_object(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def pre_get_bucket(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_get_bucket(response):
                logging.log(f"Received response: {response}")

            def pre_get_hmac_key(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_get_hmac_key(response):
                logging.log(f"Received response: {response}")

            def pre_get_iam_policy(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_get_iam_policy(response):
                logging.log(f"Received response: {response}")

            def pre_get_notification_config(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_get_notification_config(response):
                logging.log(f"Received response: {response}")

            def pre_get_object(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_get_object(response):
                logging.log(f"Received response: {response}")

            def pre_get_service_account(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_get_service_account(response):
                logging.log(f"Received response: {response}")

            def pre_list_buckets(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_list_buckets(response):
                logging.log(f"Received response: {response}")

            def pre_list_hmac_keys(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_list_hmac_keys(response):
                logging.log(f"Received response: {response}")

            def pre_list_notification_configs(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_list_notification_configs(response):
                logging.log(f"Received response: {response}")

            def pre_list_objects(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_list_objects(response):
                logging.log(f"Received response: {response}")

            def pre_lock_bucket_retention_policy(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_lock_bucket_retention_policy(response):
                logging.log(f"Received response: {response}")

            def pre_query_write_status(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_query_write_status(response):
                logging.log(f"Received response: {response}")

            def pre_read_object(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_read_object(response):
                logging.log(f"Received response: {response}")

            def pre_rewrite_object(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_rewrite_object(response):
                logging.log(f"Received response: {response}")

            def pre_set_iam_policy(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_set_iam_policy(response):
                logging.log(f"Received response: {response}")

            def pre_start_resumable_write(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_start_resumable_write(response):
                logging.log(f"Received response: {response}")

            def pre_test_iam_permissions(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_test_iam_permissions(response):
                logging.log(f"Received response: {response}")

            def pre_update_bucket(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_update_bucket(response):
                logging.log(f"Received response: {response}")

            def pre_update_hmac_key(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_update_hmac_key(response):
                logging.log(f"Received response: {response}")

            def pre_update_object(request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_update_object(response):
                logging.log(f"Received response: {response}")

        transport = StorageRestTransport(interceptor=MyCustomStorageInterceptor())
        client = StorageClient(transport=transport)


    """


@dataclasses.dataclass
class StorageRestStub:
    _session: AuthorizedSession
    _host: str
    _interceptor: StorageRestInterceptor


class StorageRestTransport(StorageTransport):
    """REST backend transport for Storage.

    API Overview and Naming Syntax
    ------------------------------

    The Cloud Storage gRPC API allows applications to read and write
    data through the abstractions of buckets and objects. For a
    description of these abstractions please see
    https://cloud.google.com/storage/docs.

    Resources are named as follows:

    -  Projects are referred to as they are defined by the Resource
       Manager API, using strings like ``projects/123456`` or
       ``projects/my-string-id``.

    -  Buckets are named using string names of the form:
       ``projects/{project}/buckets/{bucket}`` For globally unique
       buckets, ``_`` may be substituted for the project.

    -  Objects are uniquely identified by their name along with the name
       of the bucket they belong to, as separate strings in this API.
       For example:

       ReadObjectRequest { bucket: 'projects/_/buckets/my-bucket'
       object: 'my-object' } Note that object names can contain ``/``
       characters, which are treated as any other character (no special
       directory semantics).

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends JSON representations of protocol buffers over HTTP/1.1

    NOTE: This REST transport functionality is currently in a beta
    state (preview). We welcome your feedback via an issue in this
    library's source repository. Thank you!
    """

    def __init__(self, *,
            host: str = 'storage.googleapis.com',
            credentials: ga_credentials.Credentials=None,
            credentials_file: str=None,
            scopes: Sequence[str]=None,
            client_cert_source_for_mtls: Callable[[
                ], Tuple[bytes, bytes]]=None,
            quota_project_id: Optional[str]=None,
            client_info: gapic_v1.client_info.ClientInfo=DEFAULT_CLIENT_INFO,
            always_use_jwt_access: Optional[bool]=False,
            url_scheme: str='https',
            interceptor: Optional[StorageRestInterceptor] = None,
            api_audience: Optional[str] = None,
            ) -> None:
        """Instantiate the transport.

       NOTE: This REST transport functionality is currently in a beta
       state (preview). We welcome your feedback via a GitHub issue in
       this library's repository. Thank you!

        Args:
            host (Optional[str]):
                 The hostname to connect to.
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.

            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if ``channel`` is provided.
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if ``channel`` is provided.
            client_cert_source_for_mtls (Callable[[], Tuple[bytes, bytes]]): Client
                certificate to configure mutual TLS HTTP channel. It is ignored
                if ``channel`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you are developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
            url_scheme: the protocol scheme for the API endpoint.  Normally
                "https", but for testing or local servers,
                "http" can be specified.
        """
        # Run the base constructor
        # TODO(yon-mg): resolve other ctor params i.e. scopes, quota, etc.
        # TODO: When custom host (api_endpoint) is set, `scopes` must *also* be set on the
        # credentials object
        maybe_url_match = re.match("^(?P<scheme>http(?:s)?://)?(?P<host>.*)$", host)
        if maybe_url_match is None:
            raise ValueError(f"Unexpected hostname structure: {host}")  # pragma: NO COVER

        url_match_items = maybe_url_match.groupdict()

        host = f"{url_scheme}://{host}" if not url_match_items["scheme"] else host

        super().__init__(
            host=host,
            credentials=credentials,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience
        )
        self._session = AuthorizedSession(
            self._credentials, default_host=self.DEFAULT_HOST)
        if client_cert_source_for_mtls:
            self._session.configure_mtls_channel(client_cert_source_for_mtls)
        self._interceptor = interceptor or StorageRestInterceptor()
        self._prep_wrapped_messages(client_info)

    class _CancelResumableWrite(StorageRestStub):
        def __hash__(self):
            return hash("CancelResumableWrite")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.CancelResumableWriteRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.CancelResumableWriteResponse:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _ComposeObject(StorageRestStub):
        def __hash__(self):
            return hash("ComposeObject")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.ComposeObjectRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.Object:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _CreateBucket(StorageRestStub):
        def __hash__(self):
            return hash("CreateBucket")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.CreateBucketRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.Bucket:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _CreateHmacKey(StorageRestStub):
        def __hash__(self):
            return hash("CreateHmacKey")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.CreateHmacKeyRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.CreateHmacKeyResponse:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _CreateNotificationConfig(StorageRestStub):
        def __hash__(self):
            return hash("CreateNotificationConfig")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.CreateNotificationConfigRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.NotificationConfig:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _DeleteBucket(StorageRestStub):
        def __hash__(self):
            return hash("DeleteBucket")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.DeleteBucketRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ):
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _DeleteHmacKey(StorageRestStub):
        def __hash__(self):
            return hash("DeleteHmacKey")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.DeleteHmacKeyRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ):
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _DeleteNotificationConfig(StorageRestStub):
        def __hash__(self):
            return hash("DeleteNotificationConfig")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.DeleteNotificationConfigRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ):
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _DeleteObject(StorageRestStub):
        def __hash__(self):
            return hash("DeleteObject")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.DeleteObjectRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ):
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _GetBucket(StorageRestStub):
        def __hash__(self):
            return hash("GetBucket")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.GetBucketRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.Bucket:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _GetHmacKey(StorageRestStub):
        def __hash__(self):
            return hash("GetHmacKey")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.GetHmacKeyRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.HmacKeyMetadata:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _GetIamPolicy(StorageRestStub):
        def __hash__(self):
            return hash("GetIamPolicy")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: iam_policy_pb2.GetIamPolicyRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> policy_pb2.Policy:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _GetNotificationConfig(StorageRestStub):
        def __hash__(self):
            return hash("GetNotificationConfig")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.GetNotificationConfigRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.NotificationConfig:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _GetObject(StorageRestStub):
        def __hash__(self):
            return hash("GetObject")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.GetObjectRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.Object:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _GetServiceAccount(StorageRestStub):
        def __hash__(self):
            return hash("GetServiceAccount")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.GetServiceAccountRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.ServiceAccount:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _ListBuckets(StorageRestStub):
        def __hash__(self):
            return hash("ListBuckets")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.ListBucketsRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.ListBucketsResponse:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _ListHmacKeys(StorageRestStub):
        def __hash__(self):
            return hash("ListHmacKeys")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.ListHmacKeysRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.ListHmacKeysResponse:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _ListNotificationConfigs(StorageRestStub):
        def __hash__(self):
            return hash("ListNotificationConfigs")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.ListNotificationConfigsRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.ListNotificationConfigsResponse:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _ListObjects(StorageRestStub):
        def __hash__(self):
            return hash("ListObjects")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.ListObjectsRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.ListObjectsResponse:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _LockBucketRetentionPolicy(StorageRestStub):
        def __hash__(self):
            return hash("LockBucketRetentionPolicy")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.LockBucketRetentionPolicyRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.Bucket:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _QueryWriteStatus(StorageRestStub):
        def __hash__(self):
            return hash("QueryWriteStatus")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.QueryWriteStatusRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.QueryWriteStatusResponse:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _ReadObject(StorageRestStub):
        def __hash__(self):
            return hash("ReadObject")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.ReadObjectRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> rest_streaming.ResponseIterator:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _RewriteObject(StorageRestStub):
        def __hash__(self):
            return hash("RewriteObject")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.RewriteObjectRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.RewriteResponse:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _SetIamPolicy(StorageRestStub):
        def __hash__(self):
            return hash("SetIamPolicy")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: iam_policy_pb2.SetIamPolicyRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> policy_pb2.Policy:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _StartResumableWrite(StorageRestStub):
        def __hash__(self):
            return hash("StartResumableWrite")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.StartResumableWriteRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.StartResumableWriteResponse:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _TestIamPermissions(StorageRestStub):
        def __hash__(self):
            return hash("TestIamPermissions")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: iam_policy_pb2.TestIamPermissionsRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> iam_policy_pb2.TestIamPermissionsResponse:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _UpdateBucket(StorageRestStub):
        def __hash__(self):
            return hash("UpdateBucket")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.UpdateBucketRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.Bucket:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _UpdateHmacKey(StorageRestStub):
        def __hash__(self):
            return hash("UpdateHmacKey")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.UpdateHmacKeyRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.HmacKeyMetadata:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _UpdateObject(StorageRestStub):
        def __hash__(self):
            return hash("UpdateObject")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, str] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: storage.UpdateObjectRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.Object:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    class _WriteObject(StorageRestStub):
        def __hash__(self):
            return hash("WriteObject")

        def __call__(self,
                request: storage.WriteObjectRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: float=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> storage.WriteObjectResponse:
            raise RuntimeError(
                "Cannot define a method without a valid 'google.api.http' annotation.")

    @property
    def cancel_resumable_write(self) -> Callable[
            [storage.CancelResumableWriteRequest],
            storage.CancelResumableWriteResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._CancelResumableWrite(self._session, self._host, self._interceptor) # type: ignore

    @property
    def compose_object(self) -> Callable[
            [storage.ComposeObjectRequest],
            storage.Object]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._ComposeObject(self._session, self._host, self._interceptor) # type: ignore

    @property
    def create_bucket(self) -> Callable[
            [storage.CreateBucketRequest],
            storage.Bucket]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._CreateBucket(self._session, self._host, self._interceptor) # type: ignore

    @property
    def create_hmac_key(self) -> Callable[
            [storage.CreateHmacKeyRequest],
            storage.CreateHmacKeyResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._CreateHmacKey(self._session, self._host, self._interceptor) # type: ignore

    @property
    def create_notification_config(self) -> Callable[
            [storage.CreateNotificationConfigRequest],
            storage.NotificationConfig]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._CreateNotificationConfig(self._session, self._host, self._interceptor) # type: ignore

    @property
    def delete_bucket(self) -> Callable[
            [storage.DeleteBucketRequest],
            empty_pb2.Empty]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._DeleteBucket(self._session, self._host, self._interceptor) # type: ignore

    @property
    def delete_hmac_key(self) -> Callable[
            [storage.DeleteHmacKeyRequest],
            empty_pb2.Empty]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._DeleteHmacKey(self._session, self._host, self._interceptor) # type: ignore

    @property
    def delete_notification_config(self) -> Callable[
            [storage.DeleteNotificationConfigRequest],
            empty_pb2.Empty]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._DeleteNotificationConfig(self._session, self._host, self._interceptor) # type: ignore

    @property
    def delete_object(self) -> Callable[
            [storage.DeleteObjectRequest],
            empty_pb2.Empty]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._DeleteObject(self._session, self._host, self._interceptor) # type: ignore

    @property
    def get_bucket(self) -> Callable[
            [storage.GetBucketRequest],
            storage.Bucket]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GetBucket(self._session, self._host, self._interceptor) # type: ignore

    @property
    def get_hmac_key(self) -> Callable[
            [storage.GetHmacKeyRequest],
            storage.HmacKeyMetadata]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GetHmacKey(self._session, self._host, self._interceptor) # type: ignore

    @property
    def get_iam_policy(self) -> Callable[
            [iam_policy_pb2.GetIamPolicyRequest],
            policy_pb2.Policy]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GetIamPolicy(self._session, self._host, self._interceptor) # type: ignore

    @property
    def get_notification_config(self) -> Callable[
            [storage.GetNotificationConfigRequest],
            storage.NotificationConfig]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GetNotificationConfig(self._session, self._host, self._interceptor) # type: ignore

    @property
    def get_object(self) -> Callable[
            [storage.GetObjectRequest],
            storage.Object]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GetObject(self._session, self._host, self._interceptor) # type: ignore

    @property
    def get_service_account(self) -> Callable[
            [storage.GetServiceAccountRequest],
            storage.ServiceAccount]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GetServiceAccount(self._session, self._host, self._interceptor) # type: ignore

    @property
    def list_buckets(self) -> Callable[
            [storage.ListBucketsRequest],
            storage.ListBucketsResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._ListBuckets(self._session, self._host, self._interceptor) # type: ignore

    @property
    def list_hmac_keys(self) -> Callable[
            [storage.ListHmacKeysRequest],
            storage.ListHmacKeysResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._ListHmacKeys(self._session, self._host, self._interceptor) # type: ignore

    @property
    def list_notification_configs(self) -> Callable[
            [storage.ListNotificationConfigsRequest],
            storage.ListNotificationConfigsResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._ListNotificationConfigs(self._session, self._host, self._interceptor) # type: ignore

    @property
    def list_objects(self) -> Callable[
            [storage.ListObjectsRequest],
            storage.ListObjectsResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._ListObjects(self._session, self._host, self._interceptor) # type: ignore

    @property
    def lock_bucket_retention_policy(self) -> Callable[
            [storage.LockBucketRetentionPolicyRequest],
            storage.Bucket]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._LockBucketRetentionPolicy(self._session, self._host, self._interceptor) # type: ignore

    @property
    def query_write_status(self) -> Callable[
            [storage.QueryWriteStatusRequest],
            storage.QueryWriteStatusResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._QueryWriteStatus(self._session, self._host, self._interceptor) # type: ignore

    @property
    def read_object(self) -> Callable[
            [storage.ReadObjectRequest],
            storage.ReadObjectResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._ReadObject(self._session, self._host, self._interceptor) # type: ignore

    @property
    def rewrite_object(self) -> Callable[
            [storage.RewriteObjectRequest],
            storage.RewriteResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._RewriteObject(self._session, self._host, self._interceptor) # type: ignore

    @property
    def set_iam_policy(self) -> Callable[
            [iam_policy_pb2.SetIamPolicyRequest],
            policy_pb2.Policy]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._SetIamPolicy(self._session, self._host, self._interceptor) # type: ignore

    @property
    def start_resumable_write(self) -> Callable[
            [storage.StartResumableWriteRequest],
            storage.StartResumableWriteResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._StartResumableWrite(self._session, self._host, self._interceptor) # type: ignore

    @property
    def test_iam_permissions(self) -> Callable[
            [iam_policy_pb2.TestIamPermissionsRequest],
            iam_policy_pb2.TestIamPermissionsResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._TestIamPermissions(self._session, self._host, self._interceptor) # type: ignore

    @property
    def update_bucket(self) -> Callable[
            [storage.UpdateBucketRequest],
            storage.Bucket]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._UpdateBucket(self._session, self._host, self._interceptor) # type: ignore

    @property
    def update_hmac_key(self) -> Callable[
            [storage.UpdateHmacKeyRequest],
            storage.HmacKeyMetadata]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._UpdateHmacKey(self._session, self._host, self._interceptor) # type: ignore

    @property
    def update_object(self) -> Callable[
            [storage.UpdateObjectRequest],
            storage.Object]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._UpdateObject(self._session, self._host, self._interceptor) # type: ignore

    @property
    def write_object(self) -> Callable[
            [storage.WriteObjectRequest],
            storage.WriteObjectResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._WriteObject(self._session, self._host, self._interceptor) # type: ignore

    @property
    def kind(self) -> str:
        return "rest"

    def close(self):
        self._session.close()


__all__=(
    'StorageRestTransport',
)
