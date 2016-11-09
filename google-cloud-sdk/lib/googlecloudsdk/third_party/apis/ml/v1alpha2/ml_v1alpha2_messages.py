"""Generated message classes for ml version v1alpha2.

An API to enable creating and using machine learning models.
"""
# NOTE: This file is autogenerated and should not be edited by hand.

from googlecloudsdk.third_party.apitools.base.protorpclite import messages as _messages
from googlecloudsdk.third_party.apitools.base.py import encoding


package = 'ml'


class Analysis(_messages.Message):
  """Represents analysis of a trained model.

  Fields:
    classification: The analysis of a classification model.
    regression: The analysis of a regression model.
  """

  classification = _messages.MessageField('ClassificationAnalysis', 1)
  regression = _messages.MessageField('RegressionAnalysis', 2)


class ClassificationAnalysis(_messages.Message):
  """Represents the analysis of a trained classification model.

  Fields:
    error: The error rate of a classification model.
  """

  error = _messages.FloatField(1)


class ClassificationConfig(_messages.Message):
  """Represents the definition of a classification model.

  Fields:
    tensorflowGraph: Options for classification using a custom TensorFlow
      graph.
  """

  tensorflowGraph = _messages.MessageField('TensorFlowGraph', 1)


class ClassificationPrediction(_messages.Message):
  """Represents the classification output or prediction generated from a a
  classification model. A classification by default produces a single label,
  the one with highest confidence score. Additional labels are produced when
  requested in the prediction request.

  Fields:
    additionalLabels: Optional additional labels produced by the model.
    label: The top label produced by the model.
  """

  additionalLabels = _messages.MessageField('ClassificationPredictionLabel', 1, repeated=True)
  label = _messages.MessageField('ClassificationPredictionLabel', 2)


class ClassificationPredictionLabel(_messages.Message):
  """Represents a label produced by the model, along with its associated
  confidence score.

  Fields:
    name: The name of the label.
    score: The associated confidence score.
  """

  name = _messages.StringField(1)
  score = _messages.FloatField(2)


class DataSet(_messages.Message):
  """Represents data to be used within training and prediction.

  Fields:
    files: A dataset comprised of a set of individual files or objects within
      Cloud Storage.
    inline: A dataset comprised of a set of individual instances inlined. The
      number of instances is limited based on constraints of individual
      methods.
  """

  files = _messages.MessageField('StorageData', 1)
  inline = _messages.MessageField('InlineData', 2)


class DeleteVersionRequest(_messages.Message):
  """Request message for the DeleteVersion API on ModelService.

  Fields:
    version: The version to delete.
  """

  version = _messages.StringField(1)


class Empty(_messages.Message):
  """A generic empty message that you can re-use to avoid defining duplicated
  empty messages in your APIs. A typical example is to use it as the request
  or the response type of an API method. For instance:      service Foo {
  rpc Bar(google.protobuf.Empty) returns (google.protobuf.Empty);     }  The
  JSON representation for `Empty` is empty JSON object `{}`.
  """



class EvaluationJob(_messages.Message):
  """Represents a specification for an evaluation job.

  Fields:
    evalData: The data to evaluate over.
    outputUri: The storage location of a folder to write out the evaluation
      outputs.
  """

  evalData = _messages.MessageField('DataSet', 1)
  outputUri = _messages.StringField(2)


class GetVersionRequest(_messages.Message):
  """Request message for the GetVersion API on ModelService

  Fields:
    version: The version of the model to describe.
  """

  version = _messages.StringField(1)


class GetVersionResponse(_messages.Message):
  """Request message for the GetVersion API on ModelService.

  Fields:
    evalData: The data that was used for evaluating the model during training.
    model: The specification used to train the model.
    ready: Whether the training job has completed and the version is ready to
      use.
    trainData: The data that was used for training the model.
    trainingAnalysis: The analysis generated during training.
    trainingOperationName: The name of the associated training operation.
  """

  evalData = _messages.MessageField('DataSet', 1)
  model = _messages.MessageField('ModelSpec', 2)
  ready = _messages.BooleanField(3)
  trainData = _messages.MessageField('DataSet', 4)
  trainingAnalysis = _messages.MessageField('Analysis', 5)
  trainingOperationName = _messages.StringField(6)


class InlineData(_messages.Message):
  """Represents inlined data.

  Fields:
    instances: The list of data instances.
  """

  instances = _messages.StringField(1, repeated=True)


class JobResult(_messages.Message):
  """Represents the results of a training, prediction or evaluation job.

  Fields:
    analysis: The analysis of a trained model for training or evaluation jobs.
    outputFiles: The list of generated output files.
  """

  analysis = _messages.MessageField('Analysis', 1)
  outputFiles = _messages.StringField(2, repeated=True)


class ListModelsResponse(_messages.Message):
  """Response message for the ListModels API on ModelService.

  Fields:
    models: The set of models within the project.
    nextPageToken: Optional pagination token to use for retrieving the next
      page of results.
  """

  models = _messages.MessageField('Model', 1, repeated=True)
  nextPageToken = _messages.StringField(2)


class ListOperationsResponse(_messages.Message):
  """The response message for Operations.ListOperations.

  Fields:
    nextPageToken: The standard List next-page token.
    operations: A list of operations that matches the specified filter in the
      request.
  """

  nextPageToken = _messages.StringField(1)
  operations = _messages.MessageField('Operation', 2, repeated=True)


class MlProjectsModelsCreateRequest(_messages.Message):
  """A MlProjectsModelsCreateRequest object.

  Fields:
    model: A Model resource to be passed as the request body.
    name: The name of the project that will own this model.
  """

  model = _messages.MessageField('Model', 1)
  name = _messages.StringField(2, required=True)


class MlProjectsModelsDeleteRequest(_messages.Message):
  """A MlProjectsModelsDeleteRequest object.

  Fields:
    name: The name of the model to delete.
  """

  name = _messages.StringField(1, required=True)


class MlProjectsModelsDeleteVersionRequest(_messages.Message):
  """A MlProjectsModelsDeleteVersionRequest object.

  Fields:
    deleteVersionRequest: A DeleteVersionRequest resource to be passed as the
      request body.
    name: The name of the model to update.
  """

  deleteVersionRequest = _messages.MessageField('DeleteVersionRequest', 1)
  name = _messages.StringField(2, required=True)


class MlProjectsModelsGetRequest(_messages.Message):
  """A MlProjectsModelsGetRequest object.

  Fields:
    name: The name of the model to retrieve.
  """

  name = _messages.StringField(1, required=True)


class MlProjectsModelsGetVersionRequest(_messages.Message):
  """A MlProjectsModelsGetVersionRequest object.

  Fields:
    getVersionRequest: A GetVersionRequest resource to be passed as the
      request body.
    name: The name of the model to use for prediction.
  """

  getVersionRequest = _messages.MessageField('GetVersionRequest', 1)
  name = _messages.StringField(2, required=True)


class MlProjectsModelsListRequest(_messages.Message):
  """A MlProjectsModelsListRequest object.

  Fields:
    filter: Specifies the subset of models to retrieve.
    name: The name of the project whose models are to be listed.
    orderBy: Specifies the ordering of the models.
    pageSize: Optional page size. The default is 100.
    pageToken: An optional pagination token, if available, for continuing the
      enumeration.
  """

  filter = _messages.StringField(1)
  name = _messages.StringField(2, required=True)
  orderBy = _messages.StringField(3)
  pageSize = _messages.IntegerField(4, variant=_messages.Variant.INT32)
  pageToken = _messages.StringField(5)


class MlProjectsModelsPredictRequest(_messages.Message):
  """A MlProjectsModelsPredictRequest object.

  Fields:
    name: The name of the model to use for prediction.
    predictRequest: A PredictRequest resource to be passed as the request
      body.
  """

  name = _messages.StringField(1, required=True)
  predictRequest = _messages.MessageField('PredictRequest', 2)


class MlProjectsModelsSetDefaultVersionRequest(_messages.Message):
  """A MlProjectsModelsSetDefaultVersionRequest object.

  Fields:
    name: The name of the model to update.
    setDefaultVersionRequest: A SetDefaultVersionRequest resource to be passed
      as the request body.
  """

  name = _messages.StringField(1, required=True)
  setDefaultVersionRequest = _messages.MessageField('SetDefaultVersionRequest', 2)


class MlProjectsModelsSubmitEvaluationJobRequest(_messages.Message):
  """A MlProjectsModelsSubmitEvaluationJobRequest object.

  Fields:
    name: The name of the associated project.
    submitEvaluationJobRequest: A SubmitEvaluationJobRequest resource to be
      passed as the request body.
  """

  name = _messages.StringField(1, required=True)
  submitEvaluationJobRequest = _messages.MessageField('SubmitEvaluationJobRequest', 2)


class MlProjectsModelsSubmitPredictionJobRequest(_messages.Message):
  """A MlProjectsModelsSubmitPredictionJobRequest object.

  Fields:
    name: The name of the associated model.
    submitPredictionJobRequest: A SubmitPredictionJobRequest resource to be
      passed as the request body.
  """

  name = _messages.StringField(1, required=True)
  submitPredictionJobRequest = _messages.MessageField('SubmitPredictionJobRequest', 2)


class MlProjectsModelsSubmitTrainingJobRequest(_messages.Message):
  """A MlProjectsModelsSubmitTrainingJobRequest object.

  Fields:
    name: The name of the associated model.
    submitTrainingJobRequest: A SubmitTrainingJobRequest resource to be passed
      as the request body.
  """

  name = _messages.StringField(1, required=True)
  submitTrainingJobRequest = _messages.MessageField('SubmitTrainingJobRequest', 2)


class MlProjectsOperationsCancelRequest(_messages.Message):
  """A MlProjectsOperationsCancelRequest object.

  Fields:
    name: The name of the operation resource to be cancelled.
  """

  name = _messages.StringField(1, required=True)


class MlProjectsOperationsDeleteRequest(_messages.Message):
  """A MlProjectsOperationsDeleteRequest object.

  Fields:
    name: The name of the operation resource to be deleted.
  """

  name = _messages.StringField(1, required=True)


class MlProjectsOperationsGetRequest(_messages.Message):
  """A MlProjectsOperationsGetRequest object.

  Fields:
    name: The name of the operation resource.
  """

  name = _messages.StringField(1, required=True)


class MlProjectsOperationsListRequest(_messages.Message):
  """A MlProjectsOperationsListRequest object.

  Fields:
    filter: The standard list filter.
    name: The name of the operation collection.
    pageSize: The standard list page size.
    pageToken: The standard list page token.
  """

  filter = _messages.StringField(1)
  name = _messages.StringField(2, required=True)
  pageSize = _messages.IntegerField(3, variant=_messages.Variant.INT32)
  pageToken = _messages.StringField(4)


class Model(_messages.Message):
  """Represents a machine learning model resource that can be used to perform
  training and prediction. In order to be usable, a model must have at least
  one version trained. A model might have multiple versions, with one of them
  marked as the default. The default version cannot be deleted.

  Enums:
    ScenarioValueValuesEnum: The machine learning scenario that this model
      implements.

  Fields:
    defaultVersion: The version marked as the default. This is used when
      version is not explicitly specified in various requests.
    description: The optional, user-supplied description of the model.
    name: The user-specified name of the model. This must be unique within the
      project.
    scenario: The machine learning scenario that this model implements.
    versions: The set of versions that have been defined on this model. A
      model can have a small and finite number of versions active at any
      point.
  """

  class ScenarioValueValuesEnum(_messages.Enum):
    """The machine learning scenario that this model implements.

    Values:
      SCENARIO_UNSPECIFIED: Default model scenario, representing an invalid
        value.
      CLASSIFICATION: Classification model
      REGRESSION: Regression model
    """
    SCENARIO_UNSPECIFIED = 0
    CLASSIFICATION = 1
    REGRESSION = 2

  defaultVersion = _messages.StringField(1)
  description = _messages.StringField(2)
  name = _messages.StringField(3)
  scenario = _messages.EnumField('ScenarioValueValuesEnum', 4)
  versions = _messages.MessageField('ModelVersion', 5, repeated=True)


class ModelSpec(_messages.Message):
  """Represents the specification of a model.

  Fields:
    classification: The configuration for classification models.
    regression: The configuration for regression models.
  """

  classification = _messages.MessageField('ClassificationConfig', 1)
  regression = _messages.MessageField('RegressionConfig', 2)


class ModelVersion(_messages.Message):
  """Represents information about a version.

  Fields:
    createTime: The timestamp representing when the version was created.
      Specifically, this is the time stamp of when the training job was
      submitted.
    name: The user-specified name of the version.
    ready: Whether the training job has completed and the version is ready to
      use.
    trainingAnalysis: The analysis generated during training.
  """

  createTime = _messages.StringField(1)
  name = _messages.StringField(2)
  ready = _messages.BooleanField(3)
  trainingAnalysis = _messages.MessageField('Analysis', 4)


class Operation(_messages.Message):
  """This resource represents a long-running operation that is the result of a
  network API call.

  Messages:
    MetadataValue: Service-specific metadata associated with the operation.
      It typically contains progress information and common metadata such as
      create time. Some services might not provide such metadata.  Any method
      that returns a long-running operation should document the metadata type,
      if any.
    ResponseValue: The normal response of the operation in case of success.
      If the original method returns no data on success, such as `Delete`, the
      response is `google.protobuf.Empty`.  If the original method is standard
      `Get`/`Create`/`Update`, the response should be the resource.  For other
      methods, the response should have the type `XxxResponse`, where `Xxx` is
      the original method name.  For example, if the original method name is
      `TakeSnapshot()`, the inferred response type is `TakeSnapshotResponse`.

  Fields:
    done: If the value is `false`, it means the operation is still in
      progress. If true, the operation is completed, and either `error` or
      `response` is available.
    error: The error result of the operation in case of failure.
    metadata: Service-specific metadata associated with the operation.  It
      typically contains progress information and common metadata such as
      create time. Some services might not provide such metadata.  Any method
      that returns a long-running operation should document the metadata type,
      if any.
    name: The server-assigned name, which is only unique within the same
      service that originally returns it. If you use the default HTTP mapping,
      the `name` should have the format of `operations/some/unique/name`.
    response: The normal response of the operation in case of success.  If the
      original method returns no data on success, such as `Delete`, the
      response is `google.protobuf.Empty`.  If the original method is standard
      `Get`/`Create`/`Update`, the response should be the resource.  For other
      methods, the response should have the type `XxxResponse`, where `Xxx` is
      the original method name.  For example, if the original method name is
      `TakeSnapshot()`, the inferred response type is `TakeSnapshotResponse`.
  """

  @encoding.MapUnrecognizedFields('additionalProperties')
  class MetadataValue(_messages.Message):
    """Service-specific metadata associated with the operation.  It typically
    contains progress information and common metadata such as create time.
    Some services might not provide such metadata.  Any method that returns a
    long-running operation should document the metadata type, if any.

    Messages:
      AdditionalProperty: An additional property for a MetadataValue object.

    Fields:
      additionalProperties: Properties of the object. Contains field @ype with
        type URL.
    """

    class AdditionalProperty(_messages.Message):
      """An additional property for a MetadataValue object.

      Fields:
        key: Name of the additional property.
        value: A extra_types.JsonValue attribute.
      """

      key = _messages.StringField(1)
      value = _messages.MessageField('extra_types.JsonValue', 2)

    additionalProperties = _messages.MessageField('AdditionalProperty', 1, repeated=True)

  @encoding.MapUnrecognizedFields('additionalProperties')
  class ResponseValue(_messages.Message):
    """The normal response of the operation in case of success.  If the
    original method returns no data on success, such as `Delete`, the response
    is `google.protobuf.Empty`.  If the original method is standard
    `Get`/`Create`/`Update`, the response should be the resource.  For other
    methods, the response should have the type `XxxResponse`, where `Xxx` is
    the original method name.  For example, if the original method name is
    `TakeSnapshot()`, the inferred response type is `TakeSnapshotResponse`.

    Messages:
      AdditionalProperty: An additional property for a ResponseValue object.

    Fields:
      additionalProperties: Properties of the object. Contains field @ype with
        type URL.
    """

    class AdditionalProperty(_messages.Message):
      """An additional property for a ResponseValue object.

      Fields:
        key: Name of the additional property.
        value: A extra_types.JsonValue attribute.
      """

      key = _messages.StringField(1)
      value = _messages.MessageField('extra_types.JsonValue', 2)

    additionalProperties = _messages.MessageField('AdditionalProperty', 1, repeated=True)

  done = _messages.BooleanField(1)
  error = _messages.MessageField('Status', 2)
  metadata = _messages.MessageField('MetadataValue', 3)
  name = _messages.StringField(4)
  response = _messages.MessageField('ResponseValue', 5)


class PredictRequest(_messages.Message):
  """Request message for the Predict API on ModelService.

  Fields:
    data: The data instances to perform prediction over. Only datasets with
      with inline data are supported. Additionally, inline data is limited to
      128 instances.
    labelsPerInstance: The number of labels to predict per instance. This
      applies only to classification models, and defaults to 1, i.e., produce
      only the label with highest confidence score.
    version: The version of the model to be used for prediction.
  """

  data = _messages.MessageField('DataSet', 1)
  labelsPerInstance = _messages.IntegerField(2, variant=_messages.Variant.INT32)
  version = _messages.StringField(3)


class PredictResponse(_messages.Message):
  """Response message for the Predict API on ModelService.

  Fields:
    predictions: The list of prediction results.
  """

  predictions = _messages.MessageField('Prediction', 1, repeated=True)


class Prediction(_messages.Message):
  """Represents a prediction output.

  Fields:
    classification: The prediction produced by a classification model.
    regression: The prediction produced by a regression model.
  """

  classification = _messages.MessageField('ClassificationPrediction', 1)
  regression = _messages.MessageField('RegressionPrediction', 2)


class PredictionJob(_messages.Message):
  """Represents a specification for a prediction job.

  Fields:
    labelsPerInstance: The number of labels to predict per instance. This
      applies only to classification models, and defaults to 1, i.e., produce
      only the label with highest confidence score. If this is set to -1, all
      labels are included in the output.
    outputUri: The storage location of a folder to write out the predictions.
    predictData: The dataset to predict over.
  """

  labelsPerInstance = _messages.IntegerField(1, variant=_messages.Variant.INT32)
  outputUri = _messages.StringField(2)
  predictData = _messages.MessageField('DataSet', 3)


class RegressionAnalysis(_messages.Message):
  """Represents the analysis of a trained regression model.

  Fields:
    error: The root mean squared error of a regression model.
  """

  error = _messages.FloatField(1)


class RegressionConfig(_messages.Message):
  """Represents the definition of a regression model.

  Fields:
    tensorflowGraph: Options for regression using a custom TensorFlow graph.
  """

  tensorflowGraph = _messages.MessageField('TensorFlowGraph', 1)


class RegressionPrediction(_messages.Message):
  """Represents the regression output or prediction generated from a a
  regression model.

  Fields:
    value: The regression value produced by the model.
  """

  value = _messages.FloatField(1)


class SetDefaultVersionRequest(_messages.Message):
  """Request message for the SetDefaultVersion API on ModelService.

  Fields:
    version: The version of the model that should be promoted to be the new
      default. If this is empty, then the default version on the model is
      cleared.
  """

  version = _messages.StringField(1)


class StandardQueryParameters(_messages.Message):
  """Query parameters accepted by all methods.

  Enums:
    FXgafvValueValuesEnum: V1 error format.
    AltValueValuesEnum: Data format for response.

  Fields:
    f__xgafv: V1 error format.
    access_token: OAuth access token.
    alt: Data format for response.
    bearer_token: OAuth bearer token.
    callback: JSONP
    fields: Selector specifying which fields to include in a partial response.
    key: API key. Your API key identifies your project and provides you with
      API access, quota, and reports. Required unless you provide an OAuth 2.0
      token.
    oauth_token: OAuth 2.0 token for the current user.
    pp: Pretty-print response.
    prettyPrint: Returns response with indentations and line breaks.
    quotaUser: Available to use for quota purposes for server-side
      applications. Can be any arbitrary string assigned to a user, but should
      not exceed 40 characters.
    trace: A tracing token of the form "token:<tokenid>" to include in api
      requests.
    uploadType: Legacy upload protocol for media (e.g. "media", "multipart").
    upload_protocol: Upload protocol for media (e.g. "raw", "multipart").
  """

  class AltValueValuesEnum(_messages.Enum):
    """Data format for response.

    Values:
      json: Responses with Content-Type of application/json
      media: Media download with context-dependent Content-Type
      proto: Responses with Content-Type of application/x-protobuf
    """
    json = 0
    media = 1
    proto = 2

  class FXgafvValueValuesEnum(_messages.Enum):
    """V1 error format.

    Values:
      _1: v1 error format
      _2: v2 error format
    """
    _1 = 0
    _2 = 1

  f__xgafv = _messages.EnumField('FXgafvValueValuesEnum', 1)
  access_token = _messages.StringField(2)
  alt = _messages.EnumField('AltValueValuesEnum', 3, default=u'json')
  bearer_token = _messages.StringField(4)
  callback = _messages.StringField(5)
  fields = _messages.StringField(6)
  key = _messages.StringField(7)
  oauth_token = _messages.StringField(8)
  pp = _messages.BooleanField(9, default=True)
  prettyPrint = _messages.BooleanField(10, default=True)
  quotaUser = _messages.StringField(11)
  trace = _messages.StringField(12)
  uploadType = _messages.StringField(13)
  upload_protocol = _messages.StringField(14)


class Status(_messages.Message):
  """The `Status` type defines a logical error model that is suitable for
  different programming environments, including REST APIs and RPC APIs. It is
  used by [gRPC](https://github.com/grpc). The error model is designed to be:
  - Simple to use and understand for most users - Flexible enough to meet
  unexpected needs  # Overview  The `Status` message contains three pieces of
  data: error code, error message, and error details. The error code should be
  an enum value of google.rpc.Code, but it may accept additional error codes
  if needed.  The error message should be a developer-facing English message
  that helps developers *understand* and *resolve* the error. If a localized
  user-facing error message is needed, put the localized message in the error
  details or localize it in the client. The optional error details may contain
  arbitrary information about the error. There is a predefined set of error
  detail types in the package `google.rpc` which can be used for common error
  conditions.  # Language mapping  The `Status` message is the logical
  representation of the error model, but it is not necessarily the actual wire
  format. When the `Status` message is exposed in different client libraries
  and different wire protocols, it can be mapped differently. For example, it
  will likely be mapped to some exceptions in Java, but more likely mapped to
  some error codes in C.  # Other uses  The error model and the `Status`
  message can be used in a variety of environments, either with or without
  APIs, to provide a consistent developer experience across different
  environments.  Example uses of this error model include:  - Partial errors.
  If a service needs to return partial errors to the client,     it may embed
  the `Status` in the normal response to indicate the partial     errors.  -
  Workflow errors. A typical workflow has multiple steps. Each step may
  have a `Status` message for error reporting purpose.  - Batch operations. If
  a client uses batch request and batch response, the     `Status` message
  should be used directly inside batch response, one for     each error sub-
  response.  - Asynchronous operations. If an API call embeds asynchronous
  operation     results in its response, the status of those operations should
  be     represented directly using the `Status` message.  - Logging. If some
  API errors are stored in logs, the message `Status` could     be used
  directly after any stripping needed for security/privacy reasons.

  Messages:
    DetailsValueListEntry: A DetailsValueListEntry object.

  Fields:
    code: The status code, which should be an enum value of google.rpc.Code.
    details: A list of messages that carry the error details.  There will be a
      common set of message types for APIs to use.
    message: A developer-facing error message, which should be in English. Any
      user-facing error message should be localized and sent in the
      google.rpc.Status.details field, or localized by the client.
  """

  @encoding.MapUnrecognizedFields('additionalProperties')
  class DetailsValueListEntry(_messages.Message):
    """A DetailsValueListEntry object.

    Messages:
      AdditionalProperty: An additional property for a DetailsValueListEntry
        object.

    Fields:
      additionalProperties: Properties of the object. Contains field @ype with
        type URL.
    """

    class AdditionalProperty(_messages.Message):
      """An additional property for a DetailsValueListEntry object.

      Fields:
        key: Name of the additional property.
        value: A extra_types.JsonValue attribute.
      """

      key = _messages.StringField(1)
      value = _messages.MessageField('extra_types.JsonValue', 2)

    additionalProperties = _messages.MessageField('AdditionalProperty', 1, repeated=True)

  code = _messages.IntegerField(1, variant=_messages.Variant.INT32)
  details = _messages.MessageField('DetailsValueListEntry', 2, repeated=True)
  message = _messages.StringField(3)


class StorageData(_messages.Message):
  """Represents reference to data stored in Cloud Storage. Each object is
  interpreted as a file.

  Fields:
    uris: The list of Cloud Storage URIs formatted as a complete URI such as
      Format: gs://bucket/path/to/data/file.
  """

  uris = _messages.StringField(1, repeated=True)


class SubmitEvaluationJobMetadata(_messages.Message):
  """Represents the metadata on the operation resulting from
  SubmitEvaluationJob.

  Fields:
    createTime: When the job was submitted.
    endTime: When the job processing completed.
    isCancellationRequested: Whether the cancellation of the job has been
      requested.
    job: The specification of the job.
    model: The name of the model.
    operationType: The type of this operation: 'evaluation'.
    startTime: When the job processing started.
    version: The name of the model version.
  """

  createTime = _messages.StringField(1)
  endTime = _messages.StringField(2)
  isCancellationRequested = _messages.BooleanField(3)
  job = _messages.MessageField('EvaluationJob', 4)
  model = _messages.StringField(5)
  operationType = _messages.StringField(6)
  startTime = _messages.StringField(7)
  version = _messages.StringField(8)


class SubmitEvaluationJobRequest(_messages.Message):
  """Request message for the SubmitEvaluationJob API on JobService.

  Fields:
    job: The evaluation specification.
    version: The version of the model to use.
  """

  job = _messages.MessageField('EvaluationJob', 1)
  version = _messages.StringField(2)


class SubmitPredictionJobMetadata(_messages.Message):
  """Represents the metadata on the operation resulting from
  SubmitPredictionJob.

  Fields:
    createTime: When the job was submitted.
    endTime: When the job processing completed.
    isCancellationRequested: Whether the cancellation of the job has been
      requested.
    job: The specification of the job.
    model: The name of the model.
    operationType: The type of this operation: 'prediction'.
    startTime: When the job processing started.
    version: The name of the model version.
  """

  createTime = _messages.StringField(1)
  endTime = _messages.StringField(2)
  isCancellationRequested = _messages.BooleanField(3)
  job = _messages.MessageField('PredictionJob', 4)
  model = _messages.StringField(5)
  operationType = _messages.StringField(6)
  startTime = _messages.StringField(7)
  version = _messages.StringField(8)


class SubmitPredictionJobRequest(_messages.Message):
  """Request message for the SubmitPredictionJob API on JobService.

  Fields:
    job: The prediction specification.
    version: The version of the model to use.
  """

  job = _messages.MessageField('PredictionJob', 1)
  version = _messages.StringField(2)


class SubmitTrainingJobMetadata(_messages.Message):
  """Represents the metadata on the operation resulting from
  SubmitTrainingJob.

  Fields:
    createTime: When the job was submitted.
    endTime: When the job processing completed.
    isCancellationRequested: Whether the cancellation of the job has been
      requested.
    job: The specification of the job.
    model: The name of the model.
    operationType: The type of this operation: 'training'.
    startTime: When the job processing started.
    version: The name of the model version.
  """

  createTime = _messages.StringField(1)
  endTime = _messages.StringField(2)
  isCancellationRequested = _messages.BooleanField(3)
  job = _messages.MessageField('TrainingJob', 4)
  model = _messages.StringField(5)
  operationType = _messages.StringField(6)
  startTime = _messages.StringField(7)
  version = _messages.StringField(8)


class SubmitTrainingJobRequest(_messages.Message):
  """Request message for the SubmitTrainingJob API on JobService.

  Fields:
    job: The training specification.
    overwrite: Whether the version with this name can be overwritten if it
      already exists.
    version: The version of the model to produce.
  """

  job = _messages.MessageField('TrainingJob', 1)
  overwrite = _messages.BooleanField(2)
  version = _messages.StringField(3)


class TensorFlowGraph(_messages.Message):
  """Represents options for using TensorFlow graph-based classification or
  regression.

  Fields:
    graphUri: The Cloud Storage location of the serialized graph definition.
      The file must represent TensorFlowGraphDefinition message in JSON
      format.
    session: The training session to use.
  """

  graphUri = _messages.StringField(1)
  session = _messages.MessageField('TensorFlowSession', 2)


class TensorFlowSession(_messages.Message):
  """Represents the settings used to run a TensorFlow session.

  Enums:
    ModelToKeepValueValuesEnum: Specifies which model should be kept at the
      end of the training: the model from the latest training step or the
      model with the minimum evaluation error observed during training.
      Defaults to the model from the latest step.

  Fields:
    batchSize: The number of data instances to read or process in each
      iteration step. This parameter is used to balance how quickly the model
      can be trained. Altering this parameter often requires altering learning
      rate. Decreasing batch size may require a decrease in learning rate, and
      vice-versa. Powers of two are recommended, because they can yield in
      optimizations. Typical values are between 32 and 256. This defaults to
      64.
    enableAcceleration: Whether the session should attempt to use additional
      hardware capabilities to accelerate the execution of the graph.
    modelToKeep: Specifies which model should be kept at the end of the
      training: the model from the latest training step or the model with the
      minimum evaluation error observed during training. Defaults to the model
      from the latest step.
    replicas: The number of replicas of the graph that should run in parallel
      over the data.
    steps: The number of steps to iterate over during the execution of the
      graph.
  """

  class ModelToKeepValueValuesEnum(_messages.Enum):
    """Specifies which model should be kept at the end of the training: the
    model from the latest training step or the model with the minimum
    evaluation error observed during training. Defaults to the model from the
    latest step.

    Values:
      LATEST: The latest model.
      MIN_ERROR: The model with the minimum evaluation error.
    """
    LATEST = 0
    MIN_ERROR = 1

  batchSize = _messages.IntegerField(1, variant=_messages.Variant.INT32)
  enableAcceleration = _messages.BooleanField(2)
  modelToKeep = _messages.EnumField('ModelToKeepValueValuesEnum', 3)
  replicas = _messages.IntegerField(4, variant=_messages.Variant.INT32)
  steps = _messages.IntegerField(5, variant=_messages.Variant.INT32)


class TrainingJob(_messages.Message):
  """Represents a specification for a training job.

  Fields:
    evalData: The data to use for evaluating the model during training.
    model: The specification of the model to train.
    outputUri: The storage location of a folder to write out the training
      outputs, such as a model analysis, a training event log, predictions on
      the eval dataset and others.
    trainData: The data to use for training the model.
  """

  evalData = _messages.MessageField('DataSet', 1)
  model = _messages.MessageField('ModelSpec', 2)
  outputUri = _messages.StringField(3)
  trainData = _messages.MessageField('DataSet', 4)


encoding.AddCustomJsonFieldMapping(
    StandardQueryParameters, 'f__xgafv', '$.xgafv',
    package=u'ml')
encoding.AddCustomJsonEnumMapping(
    StandardQueryParameters.FXgafvValueValuesEnum, '_1', '1',
    package=u'ml')
encoding.AddCustomJsonEnumMapping(
    StandardQueryParameters.FXgafvValueValuesEnum, '_2', '2',
    package=u'ml')