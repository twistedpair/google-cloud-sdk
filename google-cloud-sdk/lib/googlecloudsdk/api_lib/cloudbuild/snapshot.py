# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Move local source snapshots to GCP.

"""

import os
import os.path
import tarfile

from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files


class FileMetadata(object):
  """FileMetadata contains information about a file destined for GCP upload.

  Attributes:
      root: str, The root directory for considering file metadata.
      path: str, The path of this file, relative to the root.
      size: int, The size of this file, in bytes.
  """

  def __init__(self, root, path):
    """Collect file metadata.

    Args:
      root: str, The root directory for considering file metadata.
      path: str, The path of this file, relative to the root.
    """
    self.root = root
    self.path = path
    self.size = os.path.getsize(os.path.join(root, path))


class Snapshot(object):
  """Snapshot is a manifest of the source in a directory.

  Attributes:
    src_dir: str, The root of the snapshot source on the local disk.
    files: {str: FileMetadata}, A mapping from file path (relative to the
        snapshot root) to file metadata.
    dir: [str], The list of dirs (possibly empty) in the snapshot.
    uncompressed_size: int, The number of bytes needed to store all of the
        files in this snapshot, uncompressed.
  """

  def __init__(self, src_dir):
    self.src_dir = src_dir
    self.files = {}
    self.dirs = []
    self.uncompressed_size = 0
    self._client = core_apis.GetClientInstance('storage', 'v1')
    self._messages = core_apis.GetMessagesModule('storage', 'v1')
    for (dirpath, dirnames, filenames) in os.walk(self.src_dir):
      for fname in filenames:
        fpath = os.path.relpath(os.path.join(dirpath, fname), self.src_dir)
        fm = FileMetadata(self.src_dir, fpath)
        self.files[fpath] = fm
        self.uncompressed_size += fm.size
      for dname in dirnames:
        dpath = os.path.relpath(os.path.join(dirpath, dname), self.src_dir)
        self.dirs.append(dpath)

  def _MakeTarball(self, archive_path):
    """Constructs a tarball of snapshot contents.

    Args:
      archive_path: Path to place tar file.

    Returns:
      tarfile.TarFile, The constructed tar file.
    """
    tf = tarfile.open(archive_path, mode='w:gz')
    for dpath in self.dirs:
      t = tarfile.TarInfo(dpath)
      t.type = tarfile.DIRTYPE
      t.mode = os.stat(dpath).st_mode
      tf.addfile(t)
      log.debug('Added dir [%s]', dpath)
    for path in self.files:
      tf.add(path)
      log.debug('Added [%s]', path)
    return tf

  def CopyTarballToGCS(self, storage_client, gcs_object):
    """Copy a tarball of the snapshot to GCS.

    Args:
      storage_client: storage_api.StorageClient, The storage client to use for
                      uploading.
      gcs_object: storage.objects Resource, The GCS object to write.

    Returns:
      storage_v1_messages.Object, The written GCS object.
    """
    with files.ChDir(self.src_dir):
      with files.TemporaryDirectory() as tmp:
        archive_path = os.path.join(tmp, 'file.tgz')
        tf = self._MakeTarball(archive_path)
        tf.close()
        log.status.write(
            'Uploading tarball of [{src_dir}] to '
            '[gs://{bucket}/{object}]\n'.format(
                src_dir=self.src_dir,
                bucket=gcs_object.bucket,
                object=gcs_object.object,
            ),
        )
        return storage_client.CopyFileToGCS(
            storage_util.BucketReference.FromBucketUrl(gcs_object.bucket),
            archive_path,
            gcs_object.object)
