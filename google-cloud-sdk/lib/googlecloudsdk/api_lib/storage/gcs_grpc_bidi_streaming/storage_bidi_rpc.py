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
"""Base class for gRPC bidi streaming RPCs in gcloud storage."""

from __future__ import annotations

import queue
import threading
from typing import Any, Callable

from googlecloudsdk.api_lib.storage import errors as api_errors
from googlecloudsdk.core import gapic_util
from googlecloudsdk.core import log


# Default timeout for bidi RPC operations in seconds.
_DEFAULT_TIMEOUT = 300  # 5 minutes
_STORAGE_BIDI_RPC_WORKER_NAME = 'StorageBidiRpcWorker'


def _execute_with_timeout(
    target_func: Callable[..., Any],
    timeout: float,
    *,
    source_resource: Any | None = None,
    destination_resource: Any | None = None,
    args=None,
    kwargs=None,
) -> Any:
  """Executes target_func with args and kwargs with a timeout."""
  if args is None:
    args = []
  if kwargs is None:
    kwargs = {}

  def storage_bidi_rpc_executor(
      func: Callable[..., Any],
      result_queue,
      *,
      args,
      kwargs,
  ):
    """Worker function for execution in a separate thread."""
    try:
      result = func(*args, **kwargs)
      result_queue.put({'result': result})
    except Exception as e:  # pylint: disable=broad-except
      result_queue.put({'exception': e})

  result_queue = queue.Queue()
  thread = threading.Thread(
      target=storage_bidi_rpc_executor,
      args=(
          target_func,
          result_queue,
      ),
      kwargs={
          'args': args,
          'kwargs': kwargs,
      },
      daemon=True,
      name=_STORAGE_BIDI_RPC_WORKER_NAME,
  )
  thread.start()

  try:
    result_dict = result_queue.get(timeout=timeout)
  except queue.Empty as e:
    log.debug(
        'Operation %s for data transfer from source %s to destination %s,'
        ' timed out after %s seconds.',
        getattr(target_func, '__name__', repr(target_func)),
        source_resource,
        destination_resource,
        timeout,
    )
    raise api_errors.RetryableApiError(
        f'Operation {getattr(target_func, "__name__", repr(target_func))} for'
        f' data transfer from source {source_resource} to destination'
        f' {destination_resource} timed'
        f' out after {timeout} seconds.'
    ) from e
  else:
    if result_dict.get('exception'):
      exception = result_dict['exception']
      log.debug(
          'Operation %s for data transfer from source %s to destination %s,'
          ' failed with exception: %r',
          getattr(target_func, '__name__', repr(target_func)),
          source_resource,
          destination_resource,
          exception,
      )
      raise exception
    return result_dict.get('result')


class StorageBidiRpc:
  """Base class for gRPC bidi streaming RPCs in gcloud storage.

  This class uses gapic_util.MakeBidiRpc with storage specific overrides.
  """

  def __init__(
      self,
      client,
      start_rpc,
      *,
      initial_request=None,
      metadata: list[tuple[str, str]] | None = None,
      source_resource: Any | None = None,
      destination_resource: Any | None = None,
  ):
    """Initializes a StorageBidiRpc instance.

    Args:
      client: The gRPC client to use for the RPC. This is typically a GAPIC
        client.
      start_rpc: The start_rpc method of the gRPC client.
      initial_request: The initial request to send to the RPC.
      metadata: The metadata to use for the RPC. This is typically a list of
        tuples. The first string in the tuple is the header name and the second
        is the header value.
      source_resource: The source resource of the RPC.
      destination_resource: The destination resource of the RPC.
    """
    self._client = client
    self._start_rpc = start_rpc
    self._initial_request = initial_request
    self._metadata = metadata
    self._source_resource = source_resource
    self._destination_resource = destination_resource
    self._bidi_rpc = gapic_util.MakeBidiRpc(
        client,
        start_rpc,
        initial_request=initial_request,
        metadata=metadata,
    )

  def open(self, timeout_seconds: float | None = None) -> None:
    """Opens the bidi RPC.

    Args:
      timeout_seconds: The timeout in seconds for the open operation. If None,
        defaults to _DEFAULT_TIMEOUT(60s).
    """
    effective_timeout = (
        _DEFAULT_TIMEOUT if timeout_seconds is None else timeout_seconds
    )
    log.debug(
        'Opening bidi RPC with timeout: %s, for data transfer from source %s to'
        ' destination %s.',
        effective_timeout,
        self._source_resource,
        self._destination_resource,
    )
    # Open is a blocking call due to default pre-fetching, If we are unlucky and
    # some other thread or proxy closes the connection while the open call is in
    # progress, it can get stuck in the open call forever. Hence, we need to
    # timeout the open call.
    # The bidi rpc currently does not provide a way to provide per method
    # timeout(see  https://github.com/grpc/grpc/issues/20562) so this custom
    # timeout implemetation is needed.
    _execute_with_timeout(
        self._bidi_rpc.open,
        timeout=effective_timeout,
        source_resource=self._source_resource,
        destination_resource=self._destination_resource,
    )

  def close(self) -> None:
    """Closes the bidi RPC."""
    log.debug(
        'Closing bidi RPC, for data transfer from source %s to destination %s.',
        self._source_resource,
        self._destination_resource,
    )
    self._bidi_rpc.close()

  @property
  def is_active(self) -> bool:
    return self._bidi_rpc.is_active

  def recv(self, timeout_seconds: float | None = None) -> Any:
    """Receives a response from the bidi RPC."""
    effective_timeout = (
        _DEFAULT_TIMEOUT if timeout_seconds is None else timeout_seconds
    )
    log.debug(
        'Receiving response from bidi RPC with timeout: %s, for data transfer'
        ' from source %s to destination %s.',
        effective_timeout,
        self._source_resource,
        self._destination_resource,
    )
    # Recv is a blocking call. If we are unlucky and some other thread or proxy
    # closes the connection while the recv call is in progress, it can get stuck
    # in the recv call forever. Hence, we need to timeout the recv call.
    # The bidi rpc currently does not provide a way to provide per method
    # timeout(see  https://github.com/grpc/grpc/issues/20562) so this custom
    # timeout implemetation is needed.
    return _execute_with_timeout(
        self._bidi_rpc.recv,
        timeout=effective_timeout,
        source_resource=self._source_resource,
        destination_resource=self._destination_resource,
    )

  def send(self, request: Any) -> None:
    """Sends a request to the bidi RPC."""
    log.debug(
        'Sending request to bidi RPC, for data transfer from source %s to'
        ' destination %s.',
        self._source_resource,
        self._destination_resource,
    )
    self._bidi_rpc.send(request)

  def requests_done(self) -> None:
    """Signals that client is done sending requests (half-close)."""
    log.debug(
        'Half-closing bidi RPC, for data transfer from source %s to'
        ' destination %s.',
        self._source_resource,
        self._destination_resource,
    )
    self._bidi_rpc.send(None)
