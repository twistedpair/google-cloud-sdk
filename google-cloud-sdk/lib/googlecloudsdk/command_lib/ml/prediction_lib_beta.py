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
"""Bundled copy of_predict_lib.

Includes (from the Cloud ML SDK):
- _predict_lib
- session_bundle

Important changes:
- Replace shutil.rmtree with core.util.files.RmTree.
- _file utilities have been inlined. We use tensorflow's file_io instead of
  Apache Beam's. We use a more primitive version of globbing (using fnmatch)
  instead of the Apache Beam Cloud Storage globbing (which file_io doesn't
  support).
- Remove interfaces for DefaultModel (they don't change behavior).
- Set from_client(skip_preprocessing=True) and remove the pre-processing code.
"""
import base64
import collections
from contextlib import contextmanager
import fnmatch
import json
import logging
import os
import tempfile
import timeit
from googlecloudsdk.core.util import files

import numpy as np
import tensorflow as tf
from tensorflow.core.protobuf import meta_graph_pb2
from tensorflow.python.framework import dtypes
from tensorflow.python.lib.io import file_io


def _import_tensorflow_contrib():
  """Import tf.contrib.

  Otherwise Tensorflow won't load those operations, and imported graphs may need
  them.

  Silence logging messages, since there are many.
  """
  old_level = logging.getLogger().getEffectiveLevel()
  logging.getLogger().setLevel(logging.ERROR)
  import tensorflow.contrib  # pylint: disable=unused-variable,g-import-not-at-top
  logging.getLogger().setLevel(old_level)


_import_tensorflow_contrib()


# -------------------------
# session_bundle._constants
# -------------------------


VERSION_FORMAT_SPECIFIER = "%08d"
ASSETS_DIRECTORY = "assets"
META_GRAPH_DEF_FILENAME = "export.meta"
VARIABLES_FILENAME = "export"
VARIABLES_FILENAME_V2 = "export.data"
VARIABLES_FILENAME_PATTERN = "export-?????-of-?????"
VARIABLES_FILENAME_PATTERN_V2 = "export.data-?????-of-?????"
VARIABLES_INDEX_FILENAME_V2 = "export.index"
INIT_OP_KEY = "serving_init_op"
SIGNATURES_KEY = "serving_signatures"
ASSETS_KEY = "serving_assets"
GRAPH_KEY = "serving_graph"
INPUTS_KEY = "inputs"
OUTPUTS_KEY = "outputs"
KEYS_KEY = "keys"


def keys_used_for_serving():
  """Return a list of all keys used for predictions."""
  return [
      INIT_OP_KEY,
      SIGNATURES_KEY,
      ASSETS_KEY,
      GRAPH_KEY,
      INPUTS_KEY,
      OUTPUTS_KEY,
      KEYS_KEY,
  ]


# ------------------------------
# session_bundle._session_bundle
# ------------------------------


def load_session_bundle_from_path(export_dir, target="", config=None):
  """Load session bundle from the given path.

  The function reads input from the export_dir, constructs the graph data to the
  default graph and restores the parameters for the session created.

  Args:
    export_dir: the directory that contains files exported by exporter.
    target: The execution engine to connect to. See target in tf.Session()
    config: A ConfigProto proto with configuration options. See config in
    tf.Session()

  Returns:
    session: a tensorflow session created from the variable files.
    meta_graph: a meta graph proto saved in the exporter directory.

  Raises:
    RuntimeError: if the required files are missing or contain unrecognizable
    fields, i.e. the exported model is invalid.
  """
  if hasattr(tf, "GIT_VERSION"):
    logging.info("tf.GIT_VERSION=%s", tf.GIT_VERSION)
  else:
    logging.info("tf.GIT_VERSION=unknown")

  meta_graph_filename = os.path.join(export_dir,
                                     META_GRAPH_DEF_FILENAME)
  if not file_io.file_exists(meta_graph_filename):
    raise RuntimeError("Expected meta graph file missing %s" %
                       meta_graph_filename)

  variables_filename = ""
  variables_filename_list = []
  additional_files_to_copy = []
  checkpoint_sharded = False

  variables_index_filename = os.path.join(
      export_dir, VARIABLES_INDEX_FILENAME_V2)
  checkpoint_v2 = file_io.file_exists(variables_index_filename)

  if checkpoint_v2:
    # The checkpoint is in v2 format.
    variables_filename = os.path.join(export_dir,
                                      VARIABLES_FILENAME_V2)
    # Check to see if the file "export" exists or not.
    if file_io.file_exists(variables_filename):
      variables_filename_list = [variables_filename]
    else:
      # Check to see if the sharded file named "export-?????-of-?????" exists.
      variables_filename_list = fnmatch.filter(
          file_io.list_directory(export_dir),
          VARIABLES_FILENAME_PATTERN_V2)
      checkpoint_sharded = True
    # If the checkpoint is not local, we need to copy export.index locally too.
    additional_files_to_copy = [variables_index_filename]
  else:
    variables_filename = os.path.join(export_dir,
                                      VARIABLES_FILENAME)
    if file_io.file_exists(variables_filename):
      variables_filename_list = [variables_filename]
    else:
      variables_filename_list = fnmatch.filter(
          file_io.list_directory(export_dir),
          VARIABLES_FILENAME_PATTERN)
      checkpoint_sharded = True

  if not variables_filename_list or not variables_filename:
    raise RuntimeError("No or bad checkpoint files found in %s" % export_dir)

  # Prepare the files to restore a session.
  restore_files = ""
  if checkpoint_v2 or not checkpoint_sharded:
    # For checkpoint v2 or v1 with non-sharded files, use "export" to restore
    # the session.
    restore_files = VARIABLES_FILENAME
  else:
    restore_files = VARIABLES_FILENAME_PATTERN

  # Reads meta graph file.
  meta_graph_def = meta_graph_pb2.MetaGraphDef()
  with file_io.FileIO(meta_graph_filename, "r") as f:
    logging.info("Reading metagraph from %s", meta_graph_filename)
    meta_graph_def.ParseFromString(f.read())

  collection_def = meta_graph_def.collection_def
  graph_def = tf.GraphDef()
  if GRAPH_KEY in collection_def:
    logging.info("Using value of collection %s for the graph.",
                 GRAPH_KEY)
    # Use serving graph_def in MetaGraphDef collection_def if exists
    graph_def_any = collection_def[GRAPH_KEY].any_list.value
    if len(graph_def_any) != 1:
      raise RuntimeError(
          "Expected exactly one serving GraphDef in : %s" % meta_graph_def)
    else:
      graph_def_any[0].Unpack(graph_def)
      # Replace the graph def in meta graph proto.
      meta_graph_def.graph_def.CopyFrom(graph_def)

      # TODO(user): If we don't clear the collections then import_meta_graph
      # fails.
      #
      # We can't delete all the collections because some of them are used
      # by prediction to get the names of the input/output tensors.
      keys_to_delete = (set(meta_graph_def.collection_def.keys()) -
                        set(keys_used_for_serving()))
      for k in keys_to_delete:
        del meta_graph_def.collection_def[k]
  else:
    logging.info("No %s found in metagraph. Using metagraph as serving graph",
                 GRAPH_KEY)

  tf.reset_default_graph()
  sess = tf.Session(target, graph=None, config=config)
  # Import the graph.
  saver = tf.train.import_meta_graph(meta_graph_def)
  # Restore the session.
  if variables_filename_list[0].startswith("gs://"):
    # Make copy from GCS files.
    # TODO(user): Retire this once tensorflow can access GCS.
    try:
      temp_dir_path = tempfile.mkdtemp("local_variable_files")
      for f in variables_filename_list + additional_files_to_copy:
        file_io.copy(f, os.path.join(temp_dir_path, os.path.basename(f)))

      saver.restore(sess, os.path.join(temp_dir_path, restore_files))
    finally:
      try:
        files.RmTree(temp_dir_path)
      except OSError as e:
        if e.message == "Cannot call rmtree on a symbolic link":
          # Interesting synthetic exception made up by shutil.rmtree.
          # Means we received a symlink from mkdtemp.
          # Also means must clean up the symlink instead.
          os.unlink(temp_dir_path)
        else:
          raise
  else:
    saver.restore(sess, os.path.join(export_dir, restore_files))

  init_op_tensor = None
  if INIT_OP_KEY in collection_def:
    init_ops = collection_def[INIT_OP_KEY].node_list.value
    if len(init_ops) != 1:
      raise RuntimeError(
          "Expected exactly one serving init op in : %s" % meta_graph_def)
    init_op_tensor = tf.get_collection(INIT_OP_KEY)[0]

  if init_op_tensor:
    # Run the init op.
    sess.run(fetches=[init_op_tensor])

  return sess, meta_graph_def


# --------------------------
# prediction._prediction_lib
# --------------------------


ENGINE = "Prediction-Engine"
PREPROCESSING_TIME = "Prediction-Preprocessing-Time"
COLUMNARIZE_TIME = "Prediction-Columnarize-Time"
UNALIAS_TIME = "Prediction-Unalias-Time"
ENGINE_RUN_TIME = "Prediction-Engine-Run-Time"
SESSION_RUN_TIME = "Prediction-Session-Run-Time"
ALIAS_TIME = "Prediction-Alias-Time"
ROWIFY_TIME = "Prediction-Rowify-Time"
INPUT_PROCESSING_TIME = "Prediction-Input-Processing-Time"

SESSION_RUN_ENGINE_NAME = "TF_SESSION_RUN"


class PredictionError(Exception):
  """Customer exception for known prediction exception."""

  # The error code for prediction.
  # TODO(b/34686732) Use strings instead of ints for these errors.
  FAILED_TO_LOAD_MODEL = 0
  FAILED_TO_PREPROCESS_INPUTS = 1
  FAILED_TO_PARSE_INPUTS = 2
  FAILED_TO_HANDLE_BAD_INPUTS = 3
  FAILED_TO_RUN_GRAPH = 4
  FAILED_TO_GET_INPUT_TENSOR_ALIAS_MAP = 5
  FAILED_TO_GET_OUTPUT_TENSOR_ALIAS_MAP = 6
  FAILED_TO_RUN_GRAPH_BAD_OUTPUTS = 7
  FAILED_TO_GET_DEFAULT_SIGNATURE = 8

  def __init__(self, error_code, error_message, *args):
    super(PredictionError, self).__init__(error_code, error_message, *args)

  @property
  def error_code(self):
    return self.args[0]

  @property
  def error_message(self):
    return self.args[1]


METADATA_FILENAMES = {"metadata.yaml", "metadata.json"}

MICRO = 1000000
MILLI = 1000


class Timer(object):
  """Context manager for timing code blocks.

  The object is intended to be used solely as a context manager and not
  as a general purpose object.

  The timer starts when __enter__ is invoked on the context manager
  and stopped when __exit__ is invoked. After __exit__ is called,
  the duration properties report the amount of time between
  __enter__ and __exit__ and thus do not change. However, if any of the
  duration properties are called between the call to __enter__ and __exit__,
  then they will return the "live" value of the timer.

  If the same Timer object is re-used in multiple with statements, the values
  reported will reflect the latest call. Do not use the same Timer object in
  nested with blocks with the same Timer context manager.

  Example usage:

    with Timer() as timer:
      foo()
    print(timer.duration_secs)
  """

  def __init__(self):
    self.start = None
    self.end = None

  def __enter__(self):
    self.end = None
    self.start = timeit.default_timer()
    return self

  def __exit__(self, exc_type, value, traceback):
    self.end = timeit.default_timer()
    return False

  @property
  def seconds(self):
    now = timeit.default_timer()
    return (self.end or now) - (self.start or now)

  @property
  def microseconds(self):
    return int(MICRO * self.seconds)

  @property
  def milliseconds(self):
    return int(MILLI * self.seconds)


class Stats(dict):
  """An object for tracking stats.

  This class is dict-like, so stats are accessed/stored like so:

    stats = Stats()
    stats["count"] = 1
    stats["foo"] = "bar"

  This class also facilitates collecting timing information via the
  context manager obtained using the "time" method. Reported timings
  are in microseconds.

  Example usage:

    with stats.time("foo_time"):
      foo()
    print(stats["foo_time"])
  """

  @contextmanager
  def time(self, name):
    with Timer() as timer:
      yield timer
    self[name] = timer.microseconds


def batch(instances):
  """Batch up the inputs.

  Each line in the input is a dictionary of input tensor names to the value
  for that input, for a single instance. For each input tensor, we add each of
  the input values to a list, i.e., batch them up.
  The result is a map from input tensor name to a batch
  of input data. This can be directly used as the feed dict during
  prediction.

  For example,

    instances = [{"a": [1.0, 2.0], "b": "a"},
                 {"a": [3.0, 4.0], "b": "c"},
                 {"a": [5.0, 6.0], "b": "e"},]
    batch = prediction_server_lib.batch(instances)
    assert batch == {"a": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
                     "b": ["a", "c", "e"]}

  Arguments:
    instances: (list of dict) where the dictionaries map tensor aliases
      to the values for those tensors.

  Returns:
    A dictionary mapping tensor names to values, as described above.
  """
  batched = collections.defaultdict(list)
  for instance in instances:
    for k, v in instance.iteritems():
      batched[k].append(v)
  return batched


def unbatch(batched):
  """Unbatches input.

  Consider the following code:

    batched = {"prediction": np.array([1,             # 1st instance
                                       0,             # 2nd
                                       1]),           # 3rd
               "scores": np.array([[0.1, 0.9],        # 1st instance
                                   [0.7, 0.3],        # 2nd
                                   [0.4, 0.6]])}      # 3rd

  Then the following will return the equivalent of:

    [{"prediction": 1, "scores": [0.1, 0.9]},
     {"prediction": 0, "scores": [0.7, 0.3]},
     {"prediction": 1, "scores": [0.4, 0.6]}]

  (each row is yielded; no list is actually created).

  Arguments:
    batched: (dict) mapping names to numpy arrays, where the arrays
      contain a batch of data.

  Raises:
    PredictionError: if the input doesn't have identical batch dimensions for
    each of element.

  Yields:
    A map with a single instance, as described above. NB: instances
    is not a numpy array.
  """
  sizes_set = {e.shape[0] for e in batched.itervalues()}

  # All the elements in the length array should be identical. Otherwise,
  # raise an exception.
  if len(sizes_set) != 1:
    sizes_dict = {name: e.shape[0] for name, e in batched.iteritems()}
    raise PredictionError(
        PredictionError.FAILED_TO_RUN_GRAPH_BAD_OUTPUTS,
        "Bad output from running tensorflow session: outputs had differing "
        "sizes in the batch (outer) dimension. See the outputs and their "
        "size: %s. Check your model for bugs that effect the size of the "
        "outputs." % sizes_dict)
  # Pick an arbitrary value in the map to get it's size.
  num_instances = len(next(batched.itervalues()))
  for row in xrange(num_instances):
    yield {name: output[row, ...].tolist()
           for name, output in batched.iteritems()}


def _build_signature(graph, input_map, output_map):
  """Return a Signature def using maps from alias to inputs/outputs."""
  # Function for creating TensorInfo structures from tensor names.
  def get_tensor_info(tensor_name):
    tensor = graph.get_tensor_by_name(tensor_name)
    return meta_graph_pb2.TensorInfo(
        name=tensor_name,
        dtype=tensor.dtype.as_datatype_enum,
        tensor_shape=tensor.get_shape().as_proto(),)

  inputs = {alias: get_tensor_info(tensor_name)
            for alias, tensor_name in input_map.iteritems()}
  outputs = {alias: get_tensor_info(tensor_name)
             for alias, tensor_name in output_map.iteritems()}
  return meta_graph_pb2.SignatureDef(inputs=inputs, outputs=outputs)


def _get_interfaces(graph):
  """Returns maps from aliases to inputs and outputs of the graph."""
  try:
    inputs = json.loads(graph.get_collection(INPUTS_KEY)[0])

  except Exception as e:
    logging.error(str(e))
    raise PredictionError(
        PredictionError.FAILED_TO_GET_INPUT_TENSOR_ALIAS_MAP,
        ("Invalid value for collection: {0}. Should be a tensor alias "
         "map.".format(INPUTS_KEY)))
  try:
    outputs = json.loads(graph.get_collection(OUTPUTS_KEY)[0])
  except Exception as e:
    logging.error(str(e))
    raise PredictionError(
        PredictionError.FAILED_TO_GET_OUTPUT_TENSOR_ALIAS_MAP,
        ("Invalid value for collection: {0}. "
         "Should be a tensor alias map.".format(OUTPUTS_KEY)))

  return inputs, outputs


# TODO(b/34686738): when we no longer load the model to get the signature
# consider making this a named constructor on SessionClient.
def load_model(model_path):
  """Loads the model at the specified path.

  Args:
    model_path: the path to either session_bundle or SavedModel

  Returns:
    A pair of (Session, SignatureDef) objects.

  Raises:
    PredictionError: if the model could not be loaded.
  """
  # Ideally, we could just always use bundle_shim to load legacy and
  # regular graphs. However, bundle_shim and supporting functions are
  # only available on recent versions of TF (~0.12). It's not even
  # really possible to detect whether or not we're going to be able
  # to use these functions, so in true Python function, it's better
  # to ask forgiveness than permission...we try to import bundle_shim,
  # which may fail, then we try to use bundle_shim, which may also fail
  # for legacy graphs. In other failure case, we back off to our older
  # custom session_bundle implementation.
  try:
    from tensorflow.contrib.session_bundle import bundle_shim  # pylint: disable=g-import-not-at-top
    from tensorflow.python.saved_model import tag_constants  # pylint: disable=g-import-not-at-top
    # We expect that the customer will export saved model and use
    # tag_constants.SERVING for serving graph. This assumption also extends to
    # model server.
    session, meta_graph = (
        bundle_shim.load_session_bundle_or_saved_model_bundle_from_path(
            model_path, tags=[tag_constants.SERVING]))
  except Exception:  # pylint: disable=broad-except
    session, meta_graph = load_session_bundle_from_path(
        model_path)

  if session is None:
    raise PredictionError(PredictionError.FAILED_TO_LOAD_MODEL,
                          "Could not load model from %s" % model_path)

  # Before the SavedModel spec came into existence the inputs and outputs
  # of a model were specified using TensorFlow collections. Check if this model
  # uses that spec.
  graph = session.graph
  collection_keys = graph.get_all_collection_keys()
  if INPUTS_KEY in collection_keys and OUTPUTS_KEY in collection_keys:
    signature = _get_legacy_signature(graph)
  else:
    # Otherwise, use (possibly upgraded from session_bundle) SavedModel.
    signature = _get_signature_from_meta_graph(graph, meta_graph)

  return session, signature


def _get_legacy_signature(graph):
  # Get maps from alias to inputs/outputs.
  input_map, output_map = _get_interfaces(graph)
  # Create a SignatureDef from those maps.
  return _build_signature(graph, input_map, output_map)


def _get_signature_from_meta_graph(graph, meta_graph):
  """Returns the SignatureDef in meta_graph update dtypes using graph."""
  if not meta_graph.signature_def:
    raise Exception("MetaGraph must have at least one signature_def.")
  named_key = "serving_default_from_named"
  if len(meta_graph.signature_def) > 1:
    logging.warning("MetaGraph has multiple signatures %d. Support for "
                    "multiple signatures is limited. By default we select "
                    "named signatures.", len(meta_graph.signature_def))
  if named_key in meta_graph.signature_def:
    return meta_graph.signature_def[named_key]

  # TODO(b/34690042): document these and point to a public, canonical constant.
  signature = meta_graph.signature_def["serving_default"]

  # Signatures often omit the dtype and shape information. Looks those up if
  # necessary.
  _update_dtypes(graph, signature.inputs)
  _update_dtypes(graph, signature.outputs)

  return signature


def _update_dtypes(graph, interface):
  """Adds dtype to TensorInfos in interface if necessary.

  If already present, validates TensorInfo matches values in the graph.
  TensorInfo is updated in place.

  Args:
    graph: the TensorFlow graph; used to lookup datatypes of tensors.
    interface: map from alias to TensorInfo object.

  Raises:
    ValueError: if the data type in the TensorInfo does not match the type
      found in graph.
  """
  for alias, info in interface.iteritems():
    # Postpone conversion to enum for better error messages.
    dtype = graph.get_tensor_by_name(info.name).dtype
    if not info.dtype:
      info.dtype = dtype.as_datatype_enum
    elif info.dtype != dtype.as_datatype_enum:
      raise ValueError("Specified data types do not match for alias %s. "
                       "Graph has %d while TensorInfo reports %d." %
                       (alias, dtype, info.dtype))


class SessionClient(object):
  """A client for Prediction that uses Session.run."""

  def __init__(self, session, signature):
    self._session = session
    self._signature = signature

    # TensorFlow requires a bonefide list for the fetches. To regenerating the
    # list every prediction, we cache the list of output tensor names.
    self._output_tensors = [v.name for v in self._signature.outputs.values()]

  @property
  def signature(self):
    return self._signature

  def predict(self, inputs, stats):
    """Produces predictions for the given inputs.

    Args:
      inputs: a dict mapping input names to values
      stats: Stats object for recording timing information.

    Returns:
      A dict mapping output names to output values, similar to the input
      dict.
    """
    stats[ENGINE] = "SessionRun"

    with stats.time(UNALIAS_TIME):
      try:
        unaliased = {self.signature.inputs[key].name: val
                     for key, val in inputs.iteritems()}
      except Exception as e:
        raise PredictionError(PredictionError.FAILED_TO_HANDLE_BAD_INPUTS,
                              "Input mismatch: " + str(e))

    with stats.time(SESSION_RUN_TIME):
      try:
        # TODO(b/33849399): measure the actual session.run() time, even in the
        # case of ModelServer.
        outputs = self._session.run(fetches=self._output_tensors,
                                    feed_dict=unaliased)
      except Exception as e:
        logging.error("Exception during running the graph: " + str(e))
        raise PredictionError(PredictionError.FAILED_TO_RUN_GRAPH,
                              "Exception during running the graph: " + str(e))

    with stats.time(ALIAS_TIME):
      return dict(zip(self._signature.outputs.iterkeys(), outputs))


class DefaultModel(object):
  """The default implementation of the Model interface.

  This implementation optionally performs preprocessing and postprocessing
  using the provided functions. These functions accept a single instance
  as input and produce a corresponding output to send to the prediction
  client.
  """

  def __init__(self, client, preprocess_fn=None, postprocess_fn=None):
    """Constructs a DefaultModel.

    Args:
      client: An instance of ModelServerClient for performing prediction.
      preprocess_fn: a function to run on each instance before calling predict,
          if this parameter is not None. See class docstring.
      postprocess_fn: a function to run on each instance after calling predict,
          if this parameter is not None. See class docstring.
    """
    self._client = client
    self._preprocess_fn = preprocess_fn
    self._postprocess_fn = postprocess_fn

  def _get_batched_instance(self, instances):
    """Columnarize the batch, appending input_name, if necessary.

    Instances are the same instances passed to the predict() method. Since
    models with a single input can accept the raw input without the name,
    we create a dict here with that name.

    This list of instances is then converted into a column-oriented format:
    The result is a dictionary mapping input name to a list of values for just
    that input (one entry per row in the original instances list).

    Args:
      instances: the list of instances as provided to the predict() method.

    Returns:
      A dictionary mapping input names to their values.
    """
    if len(self._client.signature.inputs) == 1:
      input_name = self._client.signature.inputs.keys()[0]
      return {input_name: instances}
    return batch(instances)

  def _preprocess(self, instances):
    """Runs the preprocessing function on the instances.

    Args:
      instances: list of instances as provided to the predict() method.

    Returns:
      A new list of preprocessed instances. Each instance is as described
      in the predict() method.
    """
    if not self._preprocess_fn:
      return instances

    try:
      return [self._preprocess_fn(i).SerializeToString() for i in instances]
    except Exception as e:
      logging.error("Exception during preprocessing: " + str(e))
      raise PredictionError(PredictionError.FAILED_TO_PREPROCESS_INPUTS,
                            "Exception during preprocessing: " + str(e))

  # TODO(b/34686738): can this be removed?
  def need_preprocess(self):
    """Returns True if preprocessing is needed."""
    return bool(self._preprocess_fn)

  # TODO(b/34686738): can this be removed?
  def is_single_input(self):
    """Returns True if the graph only has one input tensor."""
    return len(self._client.signature.inputs) == 1

  # TODO(b/34686738): can this be removed?
  def is_single_string_input(self):
    """Returns True if the graph only has one string input tensor."""
    if self.is_single_input():
      dtype = self._client.signature.inputs.values()[0].dtype
      return dtype == dtypes.string.as_datatype_enum
    return False

  def maybe_preprocess(self, instances):
    """Preprocess the instances if necessary."""
    # The instances should be already (b64-) decoded here.
    if not self.is_single_input():
      return instances

    # Input is a single string tensor, the tensor name might or might not
    # be given.
    # There are 3 cases (assuming the tensor name is "t", tensor = "abc"):
    # 1) {"t": "abc"}
    # 2) "abc"
    # 3) {"y": ...} --> wrong tensor name is given.

    tensor_name = self._client.signature.inputs.keys()[0]

    def parse_single_tensor(x, tensor_name):
      if not isinstance(x, dict):
        # case (2)
        return x
      elif len(x) == 1 and tensor_name == x.keys()[0]:
        # case (1)
        return x.values()[0]
      else:
        raise PredictionError(
            PredictionError.FAILED_TO_PARSE_INPUTS,
            "Expected tensor name: %s, got tensor name: %s." %
            (tensor_name, x.keys()))

    if not isinstance(instances, list):
      instances = [instances]
    instances = [parse_single_tensor(x, tensor_name) for x in instances]
    preprocessed = self._preprocess(instances)
    result = list(preprocessed)
    return result

  def predict(self, instances, stats=None):
    """Returns predictions for the provided instances.

    Instances are the decoded values from the request.

    Args:
      instances: list of instances, as described in the API.
      stats: Stats object for recording timing information.

    Returns:
      A two-element tuple (inputs, outputs). Both inputs and outputs are
      lists. Each input/output is a dict mapping input/output alias to the
      value for that input/output.

    Raises:
      PredictionError: if an error occurs during prediction.
    """
    stats = stats or Stats()
    with stats.time(PREPROCESSING_TIME):
      preprocessed = self.maybe_preprocess(instances)

    with stats.time(COLUMNARIZE_TIME):
      batched = self._get_batched_instance(preprocessed)
      for k, v in batched.iteritems():
        # Detect whether or not the user omits an input in one or more inputs.
        # TODO(b/34686738): check in batch?
        if isinstance(v, list) and len(v) != len(preprocessed):
          raise PredictionError(
              PredictionError.FAILED_TO_HANDLE_BAD_INPUTS,
              "Input %s was missing in at least one input instance." % k)

    with stats.time(ENGINE_RUN_TIME):
      outputs = self._client.predict(batched, stats)

    with stats.time(ROWIFY_TIME):
      # When returned element only contains one result (batch size == 1),
      # tensorflow's session.run() will return a scalar directly instead of a
      # a list. So we need to listify that scalar.
      # TODO(b/34686738): verify this behavior is correct.
      def listify(value):
        if not hasattr(value, "shape"):
          return np.asarray([value], dtype=np.object)
        elif not value.shape:
          # TODO(b/34686738): pretty sure this is a bug that only exists because
          # samples like iris have a bug where they use tf.squeeze which removes
          # the batch dimension. The samples should be fixed.
          return np.expand_dims(value, axis=0)
        else:
          return value
      outputs = {alias: listify(val) for alias, val in outputs.iteritems()}
      outputs = unbatch(outputs)

    # TODO(b/34686738): this should probably be taken care of directly
    # in batch_prediction.py, or at least a helper method. That would
    # allow us to avoid processing the inputs when not necessary.
    with stats.time(INPUT_PROCESSING_TIME):
      inputs = instances
      if self.is_single_input:
        input_name = self._client.signature.inputs.keys()[0]
        inputs = [{input_name: i} for i in inputs]

    return inputs, outputs

  # TODO(b/34686738): use signatures instead; remove this method.
  def outputs_type_map(self):
    """Returns a map from tensor alias to tensor type."""
    return {alias: dtypes.DType(info.dtype)
            for alias, info in self._client.signature.outputs.iteritems()}

  # TODO(b/34686738). Seems like this should be split into helper methods:
  #   default_preprocess_fn(model_path, skip_preprocessing) and
  #   default_model_and_preprocessor.
  @classmethod
  def from_client(cls, client, model_path, skip_preprocessing=False):
    """Creates a DefaultModel from a SessionClient and model data files."""
    del model_path  # Unused in from_client
    preprocess_fn = None
    if not skip_preprocessing:
      raise NotImplementedError("Preprocessing depends on features library, "
                                "which is not bundled.")
    return cls(client, preprocess_fn)


def decode_base64(data):
  if isinstance(data, list):
    return [decode_base64(val) for val in data]
  elif isinstance(data, dict):
    if data.viewkeys() == {"b64"}:
      return base64.b64decode(data["b64"])
    else:
      return {k: decode_base64(v) for k, v in data.iteritems()}
  else:
    return data


def encode_base64(instances, type_map):
  """Encodes binary data in a JSON-friendly way."""
  if not isinstance(instances, list):
    raise ValueError("only lists allowed in output; got %s" %
                     (type(instances),))

  if not instances:
    return instances

  first_value = instances[0]
  if not isinstance(first_value, dict):
    if len(type_map) != 1:
      return ValueError("The first instance was a string, but there are "
                        "more than one output tensor, so dict expected.")
    # Only string tensors whose name ends in _bytes needs encoding.
    tensor_name, tensor_type = type_map.items()[0]
    if tensor_type == dtypes.string and tensor_name.endswith("_bytes"):
      instances = _encode_str_tensor(instances)
    return instances

  encoded_data = []
  for instance in instances:
    encoded_instance = {}
    for tensor_name, tensor_type in type_map.iteritems():
      tensor_data = instance[tensor_name]
      if tensor_type == dtypes.string and tensor_name.endswith("_bytes"):
        tensor_data = _encode_str_tensor(tensor_data)
      encoded_instance[tensor_name] = tensor_data
    encoded_data.append(encoded_instance)
  return encoded_data


def _encode_str_tensor(data):
  if isinstance(data, list):
    return [_encode_str_tensor(val) for val in data]
  return {"b64": base64.b64encode(data)}


def local_predict(model_dir=None, instances=None):
  instances = decode_base64(instances)

  client = SessionClient(*load_model(model_dir))
  model = DefaultModel.from_client(client, model_dir, skip_preprocessing=True)
  _, predictions = model.predict(instances)
  predictions = list(predictions)
  predictions = encode_base64(predictions, model.outputs_type_map())
  return {"predictions": predictions}
