# Copyright 2015 Google Inc. All Rights Reserved.

"""Module used by appengine_client to perform deployment tasks."""
# TODO(user): Convert usage of old % string formatting to new style.

from __future__ import with_statement

import copy
import hashlib
import mimetypes
import os
import random
import re
import urllib

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
import yaml

from googlecloudsdk.appengine.lib.external.api import appinfo
from googlecloudsdk.appengine.lib.external.api import yaml_object
from googlecloudsdk.appengine.lib import util


# App readable static file path prefix.
STATIC_FILE_PREFIX = '__static__'

LIST_DELIMITER = '\n'
TUPLE_DELIMITER = '|'

# Batching parameters.
MAX_BATCH_SIZE = 3200000  # Max batch size in bytes, including overhead.
MAX_BATCH_COUNT = 100  # Max number of files per batch.
MAX_BATCH_FILE_SIZE = 200000  # Max size of individual batched files.
BATCH_OVERHEAD = 500  # Approximate number of overhead bytes per file.


class Error(exceptions.Error):
  """Error encountered while using the appengine_deployments module."""
  pass


class CannotStartServingError(Error):
  """We could not start serving the version being uploaded."""
  pass


def _FormatHash(h):
  """Return a string representation of a hash.

  The hash is a sha1 hash. It is computed both for files that need to be
  pushed to App Engine and for data payloads of requests made to App Engine.

  Args:
    h: The hash

  Returns:
    The string representation of the hash.
  """
  return '{0}_{1}_{2}_{3}_{4}'.format(
      h[0: 8], h[8: 16], h[16: 24], h[24: 32], h[32: 40])


def _Hash(content):
  """Compute the sha1 hash of the content.

  Args:
    content: The data to hash as a string.

  Returns:
    The string representation of the hash.
  """
  h = hashlib.sha1(content).hexdigest()
  return _FormatHash(h)


def _HashFromFileHandle(file_handle):
  """Compute the hash of the content of the file pointed to by file_handle.

  Args:
    file_handle: File-like object which provides seek, read and tell.

  Returns:
    The string representation of the hash.
  """
  # Hash the content of the file and then reset the file_handle.
  # TODO(user): A future optimization could make appcfg.py store a
  # manifest and only re-hash those files that haven't been changed
  # since the last upload.  Probably need to store both mtime and size
  # with the path and hash.  Note that we must issue a cloneblobs or
  # clonefiles for every file in the app even if they have not
  # changed.
  pos = file_handle.tell()
  content_hash = _Hash(file_handle.read())
  file_handle.seek(pos, 0)
  return content_hash


def GetFileLength(fh):
  """Returns the length of the file represented by fh.

  This function is capable of finding the length of any seekable stream,
  unlike os.fstat, which only works on file streams.

  Args:
    fh: The stream to get the length of.

  Returns:
    The length of the stream.
  """
  pos = fh.tell()
  # Seek to the end of the file.
  fh.seek(0, 2)
  length = fh.tell()
  fh.seek(pos, 0)
  return length


def BuildClonePostBody(file_tuples):
  """Build the post body for the /api/clone{files,blobs,errorblobs} urls.

  Args:
    file_tuples: A list of tuples.  Each tuple should contain the entries
      appropriate for the endpoint in question.

  Returns:
    A string containing the properly delimited tuples.
  """
  file_list = []
  for tup in file_tuples:
    path = tup[1]
    tup = tup[2:]
    file_list.append(TUPLE_DELIMITER.join([path] + list(tup)))
  return LIST_DELIMITER.join(file_list)


class EndpointsState(object):
  SERVING = 'serving'
  PENDING = 'pending'
  FAILED = 'failed'
  _STATES = frozenset((SERVING, PENDING, FAILED))

  @classmethod
  def Parse(cls, value):
    state = value.lower()
    if state not in cls._STATES:
      lst = sorted(cls._STATES)
      pretty_states = ', '.join(lst[:-1]) + ', or ' + lst[-1]
      raise Error('Unexpected Endpoints state [{0}]; should be {1}.'.format(
          value,
          pretty_states))
    return state


class FileClassification(object):
  """A class to hold a file's classification.

  This class both abstracts away the details of how we determine
  whether a file is a regular, static or error file as well as acting
  as a container for various metadata about the file.
  """

  def __init__(self, config_yaml, filename):
    """Initializes a FileClassification instance.

    Args:
      config_yaml: The app.yaml object to check the filename against.
      filename: The name of the file.
    """
    self._config_yaml = config_yaml
    self._filename = filename
    self._static_mime_type = self._GetMimeTypeIfStaticFile()
    self._static_app_readable = self._GetAppReadableIfStaticFile()
    self._error_mime_type, self._error_code = self._LookupErrorBlob()

  def _GetMimeTypeIfStaticFile(self):
    """Looks up the mime type.

    Uses the handlers to determine if the file should be treated as a static
    file.

    Returns:
      The mime type string.  For example, 'text/plain' or 'image/gif'.
      None if this is not a static file.
    """
    if self._FileNameImpliesStaticFile():
      return self._MimeType()
    for handler in self._config_yaml.handlers:
      handler_type = handler.GetHandlerType()
      if handler_type in ('static_dir', 'static_files'):
        if handler_type == 'static_dir':
          regex = os.path.join(re.escape(handler.GetHandler()), '.*')
        else:
          regex = handler.upload
        if re.match(regex, self._filename):
          return handler.mime_type or self._MimeType()
    return None

  def _FileNameImpliesStaticFile(self):
    """True if the name of a file implies that it is a static resource.

    For Java applications specified with web.xml and appengine-web.xml, we
    create a staging directory that includes a __static__ hierarchy containing
    links to all files that are implied static by the contents of those XML
    files. So if a file has been copied into that directory then we can assume
    it is static.

    Returns:
      True if the file should be considered a static resource based on its name.
    """
    static = '__static__' + os.sep
    return static in self._filename

  def _GetAppReadableIfStaticFile(self):
    """Looks up whether a static file is readable by the application.

    Uses the handlers in 'config_yaml' to determine if the file should
    be treated as a static file and if so, if the file should be readable by the
    application.

    Returns:
      True if the file is static and marked as app readable, False otherwise.
    """
    for handler in self._config_yaml.handlers:
      handler_type = handler.GetHandlerType()
      if handler_type in ('static_dir', 'static_files'):
        if handler_type == 'static_dir':
          regex = os.path.join(re.escape(handler.GetHandler()), '.*')
        else:
          regex = handler.upload
        if re.match(regex, self._filename):
          return handler.application_readable
    return False

  def _LookupErrorBlob(self):
    """Looks up the mime type and error_code for 'filename'.

    Uses the error handlers in 'config_yaml' to determine if the file should
    be treated as an error blob.

    Returns:

      A tuple of (mime_type, error_code), or (None, None) if this is not an
      error blob.  For example, ('text/plain', default) or ('image/gif',
      timeout) or (None, None).
    """
    if not self._config_yaml.error_handlers:
      return (None, None)
    for error_handler in self._config_yaml.error_handlers:
      if error_handler.file == self._filename:
        error_code = error_handler.error_code
        error_code = error_code or 'default'
        if error_handler.mime_type:
          return (error_handler.mime_type, error_code)
        else:
          return (self._MimeType(self._filename), error_code)
    return (None, None)

  def _MimeType(self, default='application/octet-stream'):
    guess = mimetypes.guess_type(self._filename)[0]
    if guess is None:
      log.debug('Could not guess mimetype for {0}. Using {1}.'.format(
          self._filename,
          default))
      return default
    return guess

  def IsApplicationFile(self):
    # Don't upload any application files for vm: true
    return bool((not self.IsStaticFile() or self._static_app_readable) and
                not self.IsErrorFile() and not self._config_yaml.vm)

  def IsStaticFile(self):
    return bool(self._static_mime_type)

  def StaticMimeType(self):
    return self._static_mime_type

  def IsErrorFile(self):
    return bool(self._error_mime_type)

  def ErrorMimeType(self):
    return self._error_mime_type

  def ErrorCode(self):
    return self._error_code


class UploadBatcher(object):
  """Helper to batch file uploads."""

  def __init__(self, what, logging_context):
    """Constructor.

    Args:
      what: Either 'file' or 'blob' or 'errorblob' indicating what kind of
        objects this batcher uploads.  Used in messages and URLs.
      logging_context: The _ClientDeployLoggingContext for this upload.
    """
    assert what in ('file', 'blob', 'errorblob'), repr(what)
    self.what = what
    self.logging_context = logging_context
    self.single_url = '/api/appversion/add' + what  # /addfile or /addblob.
    self.batch_url = self.single_url + 's'  # /addfiles or /addblobs.
    self.batching = True  # Whether we assume the server supports batching.
    self.batch = []  # List of (path, payload, mime_type) tuples.
    self.batch_size = 0  # Approximate number of bytes represented by batch.

  def SendBatch(self):
    """Send the current batch on its way.

    If successful, resets self.batch and self.batch_size.

    Raises:
      HTTPError with code=404 if the server doesn't support batching.
    """
    boundary = 'boundary'
    parts = []
    for path, payload, mime_type in self.batch:
      while boundary in payload:  # The boundary mustn't occur in contents.
        boundary += '%04x' % random.randint(0, 0xffff)
        assert len(boundary) < 80, 'Unexpected error, please try again.'
      part = '\n'.join(['',
                        'X-Appcfg-File: %s' % urllib.quote(path),
                        'X-Appcfg-Hash: %s' % _Hash(payload),
                        'Content-Type: %s' % mime_type,
                        'Content-Length: %d' % len(payload),
                        'Content-Transfer-Encoding: 8bit',
                        '',
                        payload])
      parts.append(part)
    parts.insert(0,
                 'MIME-Version: 1.0\n'
                 'Content-Type: multipart/mixed; boundary="%s"\n'
                 '\n'
                 'This is a message with multiple parts in MIME format.' %
                 boundary)
    parts.append('--\n')
    delimiter = '\n--%s' % boundary
    payload = delimiter.join(parts)
    log.info('Uploading batch of %d %ss to %s with boundary="%s".',
             len(self.batch), self.what, self.batch_url, boundary)
    self.logging_context.Send(self.batch_url,
                              payload=payload,
                              content_type='message/rfc822')
    self.batch = []
    self.batch_size = 0

  def SendSingleFile(self, path, payload, mime_type):
    """Send a single file on its way."""
    log.info('Uploading %s %s (%s bytes, type=%s) to %s.',
             self.what, path, len(payload), mime_type, self.single_url)
    self.logging_context.Send(self.single_url,
                              payload=payload,
                              content_type=mime_type,
                              path=path)

  def Flush(self):
    """Flush the current batch.

    This first attempts to send the batch as a single request; if that
    fails because the server doesn't support batching, the files are
    sent one by one, and self.batching is reset to False.

    At the end, self.batch and self.batch_size are reset.
    """
    if not self.batch:
      return
    try:
      self.SendBatch()
    except util.RPCError as err:
      if err.url_error.code != 404:
        raise

      # Assume it's an old server.  Disable batching.
      log.info('Old server detected; turning off %s batching.', self.what)
      self.batching = False

      # Send the files individually now.
      for path, payload, mime_type in self.batch:
        self.SendSingleFile(path, payload, mime_type)

      # And reset the batch info.
      self.batch = []
      self.batch_size = 0

  def AddToBatch(self, path, payload, mime_type):
    """Batch a file, possibly flushing first, or perhaps upload it directly.

    Args:
      path: The name of the file.
      payload: The contents of the file.
      mime_type: The MIME Content-type of the file, or None.

    If mime_type is None, application/octet-stream is substituted.
    """
    if not mime_type:
      mime_type = 'application/octet-stream'
    size = len(payload)
    if size <= MAX_BATCH_FILE_SIZE:
      if (len(self.batch) >= MAX_BATCH_COUNT or
          self.batch_size + size > MAX_BATCH_SIZE):
        self.Flush()
      if self.batching:
        log.info('Adding %s %s (%s bytes, type=%s) to batch.',
                 self.what, path, size, mime_type)
        self.batch.append((path, payload, mime_type))
        self.batch_size += size + BATCH_OVERHEAD
        return
    self.SendSingleFile(path, payload, mime_type)


class AppVersionUploader(object):
  """Provides facilities to upload a new appversion to the hosting service.

  Attributes:
    rpcserver: The AbstractRpcServer to use for the upload.
    module_yaml: The AppInfoExternal object derived from the app.yaml file.
    app_id: The application string from 'module_yaml'.
    version: The version string from 'module_yaml'.
    files: A dictionary of files to upload to the rpcserver, mapping path to
      hash of the file contents.
    in_transaction: True iff a transaction with the server has started.
      An AppVersionUploader can do only one transaction at a time.
    deployed: True iff the Deploy method has been called.
    started: True iff the StartServing method has been called.
    logging_context: The _ClientDeployLoggingContext for this upload.
    ignore_endpoints_failures: True to finish deployment even if there are
      errors updating the Google Cloud Endpoints configuration (if there is
      one). False if these errors should cause a failure/rollback.
    resource_limits: Current resource limits.
  """

  def __init__(self, rpcserver, project, module, version, module_yaml,
               module_yaml_path, resource_limits, usage_reporting=False,
               ignore_endpoints_failures=True):
    """Creates a new AppVersionUploader.

    Args:
      rpcserver: The RPC server to use. Should be an instance of HttpRpcServer
        or TestRpcServer.
      project: str, The project being used.
      module: str, The module to upload.
      version: str, The version of the module to upload.
      module_yaml: An AppInfoExternal object that specifies the configuration
        for this application.
      module_yaml_path: The full path to the file corresponding to module_yaml
      resource_limits: Current resource limits.
      usage_reporting: Whether or not to report usage.
      ignore_endpoints_failures: True to finish deployment even if there are
        errors updating the Google Cloud Endpoints configuration (if there is
        one). False if these errors should cause a failure/rollback.
    """
    self.rpcserver = rpcserver
    self.module_yaml = module_yaml
    self.module_yaml_path = module_yaml_path
    self.app_id = project
    self.module = module
    self.version = version
    self.resource_limits = resource_limits

    self.params = {
        'app_id': self.app_id,
        'module': self.module,
        'version': self.version
    }

    # A map from file name to the sha1 hash of the file contents. This map is
    # used to track all files that remain to be cloned or uploaded (either as
    # code files or static blobs).
    self.files = {}

    # The set of all file names for the app; not modified after it is populated.
    self.all_files = set()

    self.in_transaction = False
    self.deployed = False
    self.started = False
    self.batching = True
    self.logging_context = util.ClientDeployLoggingContext(rpcserver,
                                                           self.params,
                                                           usage_reporting)
    self.file_batcher = UploadBatcher('file', self.logging_context)
    self.blob_batcher = UploadBatcher('blob', self.logging_context)
    self.errorblob_batcher = UploadBatcher('errorblob', self.logging_context)
    # Init some VM-specific state for this AppVersionUploader.
    if not self.module_yaml.vm_settings:
      self.module_yaml.vm_settings = appinfo.VmSettings()
    self.module_yaml.vm_settings['module_yaml_path'] = (
        os.path.basename(module_yaml_path))
    # Set auto_id_policy to the default for this sdk version, if unspecified.
    if not self.module_yaml.auto_id_policy:
      self.module_yaml.auto_id_policy = appinfo.DATASTORE_ID_POLICY_DEFAULT
    self.ignore_endpoints_failures = ignore_endpoints_failures

  def AddFile(self, path, file_handle):
    """Adds the provided file to the list to be pushed to the server.

    Args:
      path: The path the file should be uploaded as.
      file_handle: A stream containing data to upload.
    """
    assert not self.in_transaction, 'Already in a transaction.'
    assert file_handle is not None

    reason = appinfo.ValidFilename(path)
    if reason:
      log.error(reason)
      return

    content_hash = _HashFromFileHandle(file_handle)

    self.files[path] = content_hash
    self.all_files.add(path)

  def Describe(self):
    """Returns a string describing the object being updated."""
    result = 'app: %s' % self.app_id
    if self.module is not None and self.module != appinfo.DEFAULT_MODULE:
      result += ', module: %s' % self.module
    if self.version:
      result += ', version: %s' % self.version
    return result

  @staticmethod
  def _ValidateBeginYaml(resp):
    """Validates the given /api/appversion/create response string."""
    response_dict = yaml.safe_load(resp)
    if not response_dict or 'warnings' not in response_dict:
      return False
    return response_dict

  def Begin(self):
    """Begins the transaction, returning a list of files that need uploading.

    All calls to AddFile must be made before calling Begin().

    Returns:
      A list of pathnames for files that should be uploaded using UploadFile()
      before Commit() can be called.
    """
    assert not self.in_transaction, 'Already in a transaction.'

    # Make a one-off copy of the given config, and send this tweaked config to
    # the "create" request without modifying the actual config belonging to this
    # AppVersionUploader object.
    config_copy = copy.deepcopy(self.module_yaml)
    for url in config_copy.handlers:
      handler_type = url.GetHandlerType()
      if url.application_readable:
        # Forward slashes are the only valid path separator regardless of
        # platform.
        if handler_type == 'static_dir':
          url.static_dir = '%s/%s' % (STATIC_FILE_PREFIX, url.static_dir)
        elif handler_type == 'static_files':
          url.static_files = '%s/%s' % (STATIC_FILE_PREFIX, url.static_files)
          url.upload = '%s/%s' % (STATIC_FILE_PREFIX, url.upload)

    response = self.logging_context.Send(
        '/api/appversion/create',
        payload=config_copy.ToYAML())

    result = self._ValidateBeginYaml(response)
    if result:
      warnings = result.get('warnings')
      for warning in warnings:
        log.warn(warning)

    self.in_transaction = True

    files_to_clone = []
    blobs_to_clone = []
    errorblobs = {}
    for path, content_hash in self.files.iteritems():
      file_classification = FileClassification(self.module_yaml, path)

      if file_classification.IsStaticFile():
        upload_path = path
        if file_classification.IsApplicationFile():
          upload_path = '%s/%s' % (STATIC_FILE_PREFIX, path)
        blobs_to_clone.append((path, upload_path, content_hash,
                               file_classification.StaticMimeType()))

      # Additionally check if this is an error blob. A file may be both a normal
      # blob and an error blob.
      if file_classification.IsErrorFile():
        # TODO(user): Clone error blobs instead of re-uploading them each and
        # every time. Punting for now because the savings here are incredibly
        # small but the code complexity is high.
        errorblobs[path] = content_hash

      if file_classification.IsApplicationFile():
        files_to_clone.append((path, path, content_hash))

    files_to_upload = {}

    def CloneFiles(url, files, file_type):
      """Sends files to the given url.

      Args:
        url: the server URL to use.
        files: a list of files
        file_type: the type of the files
      """
      if not files:
        return

      log.debug('Cloning %d %s file%s.' %
                (len(files), file_type, len(files) != 1 and 's' or ''))
      # Do only N files at a time to avoid huge requests and responses.
      max_files = self.resource_limits['max_files_to_clone']
      for i in xrange(0, len(files), max_files):
        if i > 0 and i % max_files == 0:
          log.debug('Cloned %d files.' % i)

        chunk = files[i:min(len(files), i + max_files)]
        result = self.logging_context.Send(url,
                                           payload=BuildClonePostBody(chunk))
        if result:
          to_upload = {}
          for f in result.split(LIST_DELIMITER):
            for entry in files:
              real_path, upload_path = entry[:2]
              if f == upload_path:
                to_upload[real_path] = self.files[real_path]
                break
          files_to_upload.update(to_upload)

    CloneFiles('/api/appversion/cloneblobs', blobs_to_clone, 'static')
    CloneFiles('/api/appversion/clonefiles', files_to_clone, 'application')

    log.debug('Files to upload: %s', files_to_upload)

    for (path, content_hash) in errorblobs.iteritems():
      files_to_upload[path] = content_hash
    self.files = files_to_upload
    return sorted(files_to_upload.iterkeys())

  def UploadFile(self, path, file_handle):
    """Uploads a file to the hosting service.

    Must only be called after Begin().
    The path provided must be one of those that were returned by Begin().

    Args:
      path: The path the file is being uploaded as.
      file_handle: A file-like object containing the data to upload.

    Raises:
      Error: The provided file is not amongst those to be uploaded.
    """
    assert self.in_transaction, 'Begin() must be called before UploadFile().'
    if path not in self.files:
      raise Error('File [%s] is not in the list of files to be uploaded.'
                  % path)

    del self.files[path]

    file_classification = FileClassification(self.module_yaml, path)
    payload = file_handle.read()
    if file_classification.IsStaticFile():
      upload_path = path
      if file_classification.IsApplicationFile():
        upload_path = '%s/%s' % (STATIC_FILE_PREFIX, path)
      self.blob_batcher.AddToBatch(upload_path, payload,
                                   file_classification.StaticMimeType())

    # Additionally check if this is an error blob. A file may be both a normal
    # blob and an error blob.
    if file_classification.IsErrorFile():
      # NOTE: Using error_code as the path here, so that we can reuse
      # UploadBatcher without modification.
      self.errorblob_batcher.AddToBatch(file_classification.ErrorCode(),
                                        payload,
                                        file_classification.ErrorMimeType())

    if file_classification.IsApplicationFile():
      # NOTE: The mime_type field is ignored by /api/appversion/addfiles.
      self.file_batcher.AddToBatch(path, payload, None)

  def Precompile(self):
    """Handle precompilation."""
    log.debug('Compilation starting.')
    files = []
    while True:
      if files:
        log.debug('Compilation: %d files left.' % len(files))
      files = self.PrecompileBatch(files)
      if not files:
        break
    log.debug('Compilation completed.')

  def PrecompileBatch(self, files):
    """Precompile a batch of files.

    Args:
      files: Either an empty list (for the initial request) or a list
        of files to be precompiled.

    Returns:
      Either an empty list (if no more files need to be precompiled)
      or a list of files to be precompiled subsequently.
    """
    payload = LIST_DELIMITER.join(files)
    response = self.logging_context.Send('/api/appversion/precompile',
                                         payload=payload)
    if not response:
      return []
    return response.split(LIST_DELIMITER)

  def Commit(self):
    """Commits the transaction, making the new app version available.

    All the files returned by Begin() must have been uploaded with UploadFile()
    before Commit() can be called.

    This tries the new 'deploy' method; if that fails it uses the old 'commit'.

    Returns:
      An appinfo.AppInfoSummary if one was returned from the Deploy, None
      otherwise.

    Raises:
      Error: Some required files were not uploaded.
      CannotStartServingError: Another operation is in progress on this version.
    """
    assert self.in_transaction, 'Begin() must be called before Commit().'
    if self.files:
      raise Error('Not all required files have been uploaded.')

    def PrintRetryMessage(_, delay):
      log.debug('Will check again in %s seconds.' % delay)

    app_summary = self.Deploy()

    # These backoff numbers seem reasonable and allow up to 15 minutes.
    success, unused_contents = util.RetryWithBackoff(
        lambda: (self.IsReady(), None), PrintRetryMessage, 1, 2, 60, 20)
    if not success:
      # TODO(user): Nicer exception, and handle printing it below.
      log.warn('Version still not ready to serve, aborting.')
      raise Error('Version not ready.')

    result = self.StartServing()
    if not result:
      # This is an old version of the admin console (i.e. 1.5.0 or
      # earlier). The update is now complete.
      self.in_transaction = False
    else:
      if result == '0':
        raise CannotStartServingError(
            'Another operation on this version is in progress.')
      success, response = util.RetryNoBackoff(self.IsServing, PrintRetryMessage)
      if not success:
        # TODO(user): Nicer exception, and handle printing it below.
        log.warn('Version still not serving, aborting.')
        raise Error('Version not ready.')

      # If the server indicates that the Google Cloud Endpoints configuration
      # is going to be updated, wait until that configuration is updated.
      check_config_updated = response.get('check_endpoints_config')
      if check_config_updated:
        unused_done, (last_state, user_error) = util.RetryWithBackoff(
            self.IsEndpointsConfigUpdated,
            PrintRetryMessage, 1, 2, 60, 20)
        if last_state != EndpointsState.SERVING:
          self.HandleEndpointsError(user_error)
      self.in_transaction = False

    return app_summary

  def Deploy(self):
    """Deploys the new app version but does not make it default.

    All the files returned by Begin() must have been uploaded with UploadFile()
    before Deploy() can be called.

    Returns:
      An appinfo.AppInfoSummary if one was returned from the Deploy, None
      otherwise.

    Raises:
      Error: Some required files were not uploaded.
    """
    assert self.in_transaction, 'Begin() must be called before Deploy().'
    if self.files:
      raise Error('Not all required files have been uploaded.')

    log.debug('Starting deployment.')
    result = self.logging_context.Send('/api/appversion/deploy')
    self.deployed = True

    if result:
      return yaml_object.BuildSingleObject(appinfo.AppInfoSummary, result)
    else:
      return None

  def IsReady(self):
    """Check if the new app version is ready to serve traffic.

    Raises:
      RuntimeError: Deploy has not yet been called.

    Returns:
      True if the server returned the app is ready to serve.
    """
    assert self.deployed, 'Deploy() must be called before IsReady().'

    log.debug('Checking if deployment succeeded.')
    result = self.logging_context.Send('/api/appversion/isready')
    return result == '1'

  def StartServing(self):
    """Start serving with the newly created version.

    Raises:
      RuntimeError: Deploy has not yet been called.

    Returns:
      The response body, as a string.
    """
    assert self.deployed, 'Deploy() must be called before StartServing().'

    log.debug('Deployment successful.')
    self.params['willcheckserving'] = '1'
    result = self.logging_context.Send('/api/appversion/startserving')
    del self.params['willcheckserving']
    self.started = True
    return result

  @staticmethod
  def _ValidateIsServingYaml(resp):
    """Validates the given /isserving YAML string.

    Args:
      resp: the response from an RPC to a URL such as /api/appversion/isserving.

    Returns:
      The resulting dictionary if the response is valid, or None otherwise.
    """
    response_dict = yaml.safe_load(resp)
    if 'serving' not in response_dict:
      return None
    return response_dict

  def IsServing(self):
    """Check if the new app version is serving.

    Raises:
      RuntimeError: Deploy has not yet been called.
      CannotStartServingError: A bad response was received from the isserving
        API call.

    Returns:
      (serving, response) Where serving is True if the deployed app version is
        serving, False otherwise.  response is a dict containing the parsed
        response from the server, or an empty dict if the server's response was
        an old style 0/1 response.
    """
    assert self.started, 'StartServing() must be called before IsServing().'

    log.debug('Checking if updated app version is serving.')
    # TODO(user): Remove this backwards compatibility hack when possible.
    self.params['new_serving_resp'] = '1'
    result = self.logging_context.Send('/api/appversion/isserving')
    del self.params['new_serving_resp']
    if result in ['0', '1']:
      return result == '1', {}
    result = AppVersionUploader._ValidateIsServingYaml(result)
    if not result:
      raise CannotStartServingError(
          'Internal error: Could not parse IsServing response.')
    message = result.get('message')
    fatal = result.get('fatal')
    if message:
      log.debug(message)
    if fatal:
      message = message or 'Unknown error.'
      if message.startswith('Not enough VMs ready'):
        message += (
            '\n\nThis can happen when your application does not start '
            'successfully.\n'
            'Please check your project logs at:\n'
            'https://console.developers.google.com'
            '/project/{project}/appengine/logs'
            '?versionId={version}&moduleId={module}\n\n'
            '(You may have to select a log name to see the logs.)').format(
                project=self.app_id, version=self.version, module=self.module)
      raise CannotStartServingError(message)
    return result['serving'], result

  @staticmethod
  def _ValidateIsEndpointsConfigUpdatedYaml(resp):
    """Validates the YAML string response from an isconfigupdated request.

    Args:
      resp: A string containing the response from the server.

    Returns:
      The dictionary with the parsed response if the response is valid.
      Otherwise returns False.
    """
    response_dict = yaml.safe_load(resp)
    # As long as either of these two fields is present, we're fine:
    if 'updated' not in response_dict and 'updatedDetail2' not in response_dict:
      return None
    return response_dict

  def GetLogUrl(self):
    """Get the URL for the app's logs."""
    module = '%s:' % self.module if self.module else ''
    return ('https://appengine.google.com/logs?' +
            urllib.urlencode((('app_id', self.app_id),
                              ('version_id', module + self.version))))

  def IsEndpointsConfigUpdated(self):
    """Check if the Endpoints configuration for this app has been updated.

    This should only be called if the app has a Google Cloud Endpoints
    handler, or if it's removing one.  The server performs the check to see
    if Endpoints support is added/updated/removed, and the response to the
    isserving call indicates whether IsEndpointsConfigUpdated should be called.

    Raises:
      AssertionError: Deploy has not yet been called.
      CannotStartServingError: There was an unexpected error with the server
        response.

    Returns:
      (done, updated_state), where done is False if this function should
      be called again to retry, True if not.  updated_state is an
      EndpointsState value indicating whether the Endpoints configuration has
      been updated on the server.
    """

    assert self.started, ('StartServing() must be called before '
                          'IsEndpointsConfigUpdated().')

    log.debug('Checking if Endpoints configuration has been updated.')

    result = self.logging_context.Send('/api/isconfigupdated')
    result = AppVersionUploader._ValidateIsEndpointsConfigUpdatedYaml(result)
    if result is None:
      raise CannotStartServingError(
          'Internal error: Could not parse IsEndpointsConfigUpdated response.')
    if 'updatedDetail2' in result:
      updated_state = EndpointsState.Parse(result['updatedDetail2'])
      user_error = result.get('errorMessage')
    else:
      # For backwards compatibility, we still handle boolean values in the
      # "updated" field.  Old versions of the GAE server will return this to
      # indicate Serving or Pending.  There is no equivalent status for Failed.
      # prod. (b/15333622)
      updated_state = (EndpointsState.SERVING if result['updated']
                       else EndpointsState.PENDING)
      user_error = None
    return updated_state != EndpointsState.PENDING, (updated_state, user_error)

  def HandleEndpointsError(self, user_error):
    """Handle an error state returned by IsEndpointsConfigUpdated.

    Args:
      user_error: Either None or a string with a message from the server
        that indicates what the error was and how the user should resolve it.

    Raises:
      Error: The update state is fatal and the user hasn't chosen
        to ignore Endpoints errors.
    """
    detailed_error = user_error or (
        "Check the app's AppEngine logs for errors: %s" % self.GetLogUrl())
    error_message = ('Failed to update Endpoints configuration.  %s' %
                     detailed_error)
    log.error(error_message)

    # Also display a link to the Python troubleshooting documentation.
    doc_link = ('https://developers.google.com/appengine/docs/python/'
                'endpoints/test_deploy#troubleshooting_a_deployment_failure')
    log.error('See the deployment troubleshooting documentation for more '
              'information: %s' % doc_link)

    if self.ignore_endpoints_failures:
      log.debug('Ignoring Endpoints failure and proceeding with update.')
    else:
      raise Error(error_message)

  def Rollback(self, force_rollback=False):
    """Rolls back the transaction if one is in progress."""
    if not self.in_transaction:
      return
    msg = 'Rolling back the update.'
    if self.module_yaml.vm and not force_rollback:
      msg += ('  This can sometimes take a while since a VM version is being '
              'rolled back.')
    log.debug(msg)
    self.logging_context.Send('/api/appversion/rollback',
                              force_rollback='1' if force_rollback else '0')
    self.in_transaction = False
    self.files = {}

  def DoUpload(self):
    """Uploads a new appversion with the given config and files to the server.

    Returns:
      An appinfo.AppInfoSummary if one was returned from the server, None
      otherwise.
    """
    start_time_usec = self.logging_context.GetCurrentTimeUsec()
    log.info('Reading app configuration.')

    log.debug('\nStarting update of %s' % self.Describe())

    # Add all the files in the directory tree.
    try:
      self._AddFilesThatAreSmallEnough()
    except KeyboardInterrupt:
      log.info('User interrupted. Aborting.')
      raise
    except EnvironmentError as e:
      if self._IsExceptionClientDeployLoggable(e):
        self.logging_context.LogClientDeploy(self.module_yaml.runtime,
                                             start_time_usec, False)
      log.error('An error occurred while processing files: %s. Aborting.', e)
      raise

    try:
      missing_files = self.Begin()
      self._UploadMissingFiles(missing_files)

      # Precompile app.
      if (self.module_yaml.derived_file_type and
          appinfo.PYTHON_PRECOMPILED in self.module_yaml.derived_file_type):
        try:
          self.Precompile()
        except util.RPCError as e:
          log.error('Error %d: --- begin server output ---\n'
                    '%s\n--- end server output ---' %
                    (e.url_error.code, e.url_error.read().rstrip('\n')))
          if e.url_error.code == 422:
            # This should really be a 400 and transient, retryable
            # failures should be 5xx.  However, to avoid breaking
            # backwards compatibility with existing SDKs we will use
            # 422 to represent a fatal, non-retryable failure.  422 is
            # Unprocessable Entity (i.e. a semantic error) in the post
            # body.
            raise
          log.error(
              'Precompilation failed. Your app can still serve but may '
              'have reduced startup performance. You can retry the update '
              'later to retry the precompilation step.')

      # Commit the app version.
      app_summary = self.Commit()
      log.debug('Completed update of %s' % self.Describe())
      self.logging_context.LogClientDeploy(self.module_yaml.runtime,
                                           start_time_usec, True)
    except BaseException, e:
      try:
        self.Rollback()
      finally:
        if self._IsExceptionClientDeployLoggable(e):
          self.logging_context.LogClientDeploy(self.module_yaml.runtime,
                                               start_time_usec, False)

      raise

    if self.module_yaml.pagespeed:
      log.warn('This application contains PageSpeed related configurations, '
               'which is deprecated! Those configurations will stop working '
               'after December 1, 2015. Read '
               'https://cloud.google.com/appengine/docs/adminconsole/pagespeed#disabling-pagespeed'
               ' to learn how to disable PageSpeed.')

    log.info('Done!')
    return app_summary

  def _IsExceptionClientDeployLoggable(self, exception):
    """Determines if an exception qualifes for client deploy log reistration.

    Args:
      exception: The exception to check.

    Returns:
      True iff exception qualifies for client deploy logging - basically a
      system error rather than a user or error or cancellation.
    """

    if isinstance(exception, KeyboardInterrupt):
      return False

    if (isinstance(exception, util.RPCError)
        and 400 <= exception.url_error.code <= 499):
      return False

    return True

  def _AddFilesThatAreSmallEnough(self):
    """Calls self.AddFile on files that are small enough.

    By small enough, we mean that their size is within
    self.resource_limits['max_file_size'] for application files, and
    'max_blob_size' otherwise. Files that are too large are logged as errors,
    and dropped (not sure why this isn't handled by raising an exception...).
    """
    log.debug('Scanning files on local disk.')

    module_yaml_dirname = os.path.dirname(self.module_yaml_path)
    paths = util.FileIterator(module_yaml_dirname,
                              self.module_yaml.skip_files,
                              self.module_yaml.runtime)
    num_files = 0
    for path in paths:
      with open(os.path.join(module_yaml_dirname, path), 'rb') as file_handle:
        file_length = GetFileLength(file_handle)

        # Get maximum length that the file may be.
        file_classification = FileClassification(self.module_yaml, path)
        if file_classification.IsApplicationFile():
          max_size = self.resource_limits['max_file_size']
        else:
          max_size = self.resource_limits['max_blob_size']

        # Handle whether the file is too big.
        if file_length > max_size:
          log.error('Ignoring file [{0}]: Too long '
                    '(max {1} bytes, file is {2} bytes).'.format(
                        path, max_size, file_length))
        else:
          log.info('Processing file [{0}]'.format(path))
          self.AddFile(path, file_handle)

      # Occassionally, indicate that progress is being made.
      num_files += 1
      if num_files % 500 == 0:
        log.debug('Scanned {0} files.'.format(num_files))

  def _UploadMissingFiles(self, missing_files):
    """DoUpload helper to upload files that need to be uploaded.

    Args:
      missing_files: List of files that need to be uploaded. Begin returns such
        a list. Design note: we don't call Begin here, because we want DoUpload
        to call it directly so that Begin/Commit are more clearly paired.
    """
    if not missing_files:
      return

    log.debug('Uploading %d files and blobs.' % len(missing_files))
    dirname = os.path.dirname(self.module_yaml_path)
    num_files = 0
    for missing_file in missing_files:
      with open(os.path.join(dirname, missing_file), 'rb') as file_handle:
        self.UploadFile(missing_file, file_handle)

      # Occassionally, indicate that progress is being made.
      num_files += 1
      if num_files % 500 == 0:
        log.debug('Processed %d out of %s.' %
                  (num_files, len(missing_files)))

    # Flush the final batches.
    self.file_batcher.Flush()
    self.blob_batcher.Flush()
    self.errorblob_batcher.Flush()
    log.debug('Uploaded %d files and blobs.' % num_files)
