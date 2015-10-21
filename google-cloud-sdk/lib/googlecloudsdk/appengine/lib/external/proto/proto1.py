# Copyright 2015 Google Inc. All Rights Reserved.
# Error definition (moved here from ProtocolBuffer.py)
# are now common for native and shim (in ./python) proto1 API implementations.
class ProtocolBufferDecodeError(Exception): pass
class ProtocolBufferEncodeError(Exception): pass
class ProtocolBufferReturnError(Exception): pass
