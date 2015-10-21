# Copyright 2015 Google Inc. All Rights Reserved.
#!/usr/bin/python2.4
#
# Copyright 2013 Google Inc. All Rights Reserved.
# All Rights Reserved.

"""The Python datastore protocol buffer definition (old name)."""



# The proto2 compiler generates datastore_v3_pb.py, but all our code refers
# to datastore_pb.py, so import all the symbols from there. Also import the
# names that were imported to datastore_pb by the old proto1 specification,
# as some tests and possibly some user code may be referring to them.

from googlecloudsdk.appengine.lib.external.googlestorage.onestore.v3.action_pb import Action
from googlecloudsdk.appengine.lib.external.googlestorage.onestore.v3.entity_pb import CompositeIndex
from googlecloudsdk.appengine.lib.external.googlestorage.onestore.v3.entity_pb import EntityProto
from googlecloudsdk.appengine.lib.external.googlestorage.onestore.v3.entity_pb import Index
from googlecloudsdk.appengine.lib.external.googlestorage.onestore.v3.entity_pb import Path
from googlecloudsdk.appengine.lib.external.googlestorage.onestore.v3.entity_pb import Property
from googlecloudsdk.appengine.lib.external.googlestorage.onestore.v3.entity_pb import PropertyValue
from googlecloudsdk.appengine.lib.external.googlestorage.onestore.v3.entity_pb import Reference
from googlecloudsdk.appengine.lib.external.googlestorage.onestore.v3.snapshot_pb import Snapshot

from googlecloudsdk.appengine.lib.external.api.api_base_pb import Integer64Proto
from googlecloudsdk.appengine.lib.external.api.api_base_pb import StringProto
from googlecloudsdk.appengine.lib.external.api.api_base_pb import VoidProto
from googlecloudsdk.appengine.lib.external.datastore import datastore_v3_pb
from googlecloudsdk.appengine.lib.external.datastore.datastore_v3_pb import *

# Some python2.5 tests depend on this
if hasattr(datastore_v3_pb, '_DatastoreService_ClientStub'):
  _DatastoreService_ClientStub = datastore_v3_pb._DatastoreService_ClientStub
