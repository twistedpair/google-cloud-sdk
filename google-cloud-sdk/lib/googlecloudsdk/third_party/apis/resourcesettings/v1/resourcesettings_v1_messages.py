"""Generated message classes for resourcesettings version v1.

The Resource Settings API allows users to control and modify the behavior of
their GCP resources (e.g., VM, firewall, Project, etc.) across the Cloud
Resource Hierarchy.
"""
# NOTE: This file is autogenerated and should not be edited by hand.

from __future__ import absolute_import

from apitools.base.protorpclite import messages as _messages
from apitools.base.py import encoding


package = 'resourcesettings'


class GoogleCloudResourcesettingsV1ListSettingsResponse(_messages.Message):
  r"""The response from ListSettings.

  Fields:
    nextPageToken: Unused. A page token used to retrieve the next page.
    settings: A list of settings that are available at the specified Cloud
      resource.
  """

  nextPageToken = _messages.StringField(1)
  settings = _messages.MessageField('GoogleCloudResourcesettingsV1Setting', 2, repeated=True)


class GoogleCloudResourcesettingsV1SearchSettingValuesResponse(_messages.Message):
  r"""The response from SearchSettingValues.

  Fields:
    nextPageToken: Unused. A page token used to retrieve the next page.
    settingValues: All setting values that exist on the specified Cloud
      resource.
  """

  nextPageToken = _messages.StringField(1)
  settingValues = _messages.MessageField('GoogleCloudResourcesettingsV1SettingValue', 2, repeated=True)


class GoogleCloudResourcesettingsV1Setting(_messages.Message):
  r"""The schema for settings.

  Enums:
    DataTypeValueValuesEnum: Output only. The data type for this setting.

  Fields:
    dataType: Output only. The data type for this setting.
    defaultValue: Output only. The value provided by Setting.effective_value
      if no setting value is explicitly set. Note: not all settings have a
      default value.
    description: Output only. A detailed description of what this setting
      does.
    displayName: Output only. The human readable name for this setting.
    effectiveValue: Output only. The computed effective value of the setting
      at the given parent resource (based on the resource hierarchy). The
      effective value evaluates to one of the following options in the given
      order (the next option is used if the previous one does not exist): 1.
      the local setting value on the given resource: Setting.local_value 2. if
      one of the given resource's ancestors have a local setting value, the
      local value at the nearest such ancestor 3. the setting's default value:
      SettingMetadata.default_value 4. an empty value (defined as a `Value`
      with all fields unset) The data type of Value must always be consistent
      with the data type defined in Setting.metadata.
    etag: A fingerprint used for optimistic concurrency. See UpdateSetting for
      more details.
    localValue: The configured value of the setting at the given parent
      resource (ignoring the resource hierarchy). The data type of Value must
      always be consistent with the data type defined in Setting.metadata.
    metadata: Output only. Metadata about a setting which is not editable by
      the end user.
    name: The resource name of the setting. Must be in one of the following
      forms: * `projects/{project_number}/settings/{setting_name}` *
      `folders/{folder_id}/settings/{setting_name}` *
      `organizations/{organization_id}/settings/{setting_name}` For example,
      "/projects/123/settings/gcp-enableMyFeature"
    readOnly: Output only. A flag indicating that values of this setting
      cannot be modified (see documentation of the specific setting for
      updates and reasons).
  """

  class DataTypeValueValuesEnum(_messages.Enum):
    r"""Output only. The data type for this setting.

    Values:
      DATA_TYPE_UNSPECIFIED: Unspecified data type.
      BOOLEAN: A boolean setting.
      STRING: A string setting.
      STRING_SET: A string set setting.
      ENUM_VALUE: A Enum setting
    """
    DATA_TYPE_UNSPECIFIED = 0
    BOOLEAN = 1
    STRING = 2
    STRING_SET = 3
    ENUM_VALUE = 4

  dataType = _messages.EnumField('DataTypeValueValuesEnum', 1)
  defaultValue = _messages.MessageField('GoogleCloudResourcesettingsV1Value', 2)
  description = _messages.StringField(3)
  displayName = _messages.StringField(4)
  effectiveValue = _messages.MessageField('GoogleCloudResourcesettingsV1Value', 5)
  etag = _messages.StringField(6)
  localValue = _messages.MessageField('GoogleCloudResourcesettingsV1Value', 7)
  metadata = _messages.MessageField('GoogleCloudResourcesettingsV1SettingMetadata', 8)
  name = _messages.StringField(9)
  readOnly = _messages.BooleanField(10)


class GoogleCloudResourcesettingsV1SettingMetadata(_messages.Message):
  r"""Metadata about a setting which is not editable by the end user.

  Enums:
    DataTypeValueValuesEnum: The data type for this setting.

  Fields:
    dataType: The data type for this setting.
    defaultValue: The value provided by Setting.effective_value if no setting
      value is explicitly set. Note: not all settings have a default value.
    description: A detailed description of what this setting does.
    displayName: The human readable name for this setting.
    readOnly: A flag indicating that values of this setting cannot be modified
      (see documentation of the specific setting for updates and reasons).
  """

  class DataTypeValueValuesEnum(_messages.Enum):
    r"""The data type for this setting.

    Values:
      DATA_TYPE_UNSPECIFIED: Unspecified data type.
      BOOLEAN: A boolean setting.
      STRING: A string setting.
      STRING_SET: A string set setting.
      ENUM_VALUE: A Enum setting
    """
    DATA_TYPE_UNSPECIFIED = 0
    BOOLEAN = 1
    STRING = 2
    STRING_SET = 3
    ENUM_VALUE = 4

  dataType = _messages.EnumField('DataTypeValueValuesEnum', 1)
  defaultValue = _messages.MessageField('GoogleCloudResourcesettingsV1Value', 2)
  description = _messages.StringField(3)
  displayName = _messages.StringField(4)
  readOnly = _messages.BooleanField(5)


class GoogleCloudResourcesettingsV1SettingValue(_messages.Message):
  r"""The instantiation of a setting. Every setting value is parented by its
  corresponding setting.

  Fields:
    etag: A fingerprint used for optimistic concurrency. See
      UpdateSettingValue for more details.
    name: The resource name of the setting value. Must be in one of the
      following forms: *
      `projects/{project_number}/settings/{setting_name}/value` *
      `folders/{folder_id}/settings/{setting_name}/value` *
      `organizations/{organization_id}/settings/{setting_name}/value` For
      example, "/projects/123/settings/gcp-enableMyFeature/value"
    readOnly: Output only. A flag indicating that this setting value cannot be
      modified. This flag is inherited from its parent setting and is for
      convenience purposes. See Setting.read_only for more details.
    updateTime: Output only. The timestamp indicating when the setting value
      was last updated.
    value: The value of the setting. The data type of Value must always be
      consistent with the data type defined by the parent setting.
  """

  etag = _messages.StringField(1)
  name = _messages.StringField(2)
  readOnly = _messages.BooleanField(3)
  updateTime = _messages.StringField(4)
  value = _messages.MessageField('GoogleCloudResourcesettingsV1Value', 5)


class GoogleCloudResourcesettingsV1Value(_messages.Message):
  r"""The data in a setting value.

  Fields:
    booleanValue: Defines this value as being a boolean value.
    enumValue: Defines this value as being a Enum.
    stringSetValue: Defines this value as being a StringSet.
    stringValue: Defines this value as being a string value.
  """

  booleanValue = _messages.BooleanField(1)
  enumValue = _messages.MessageField('GoogleCloudResourcesettingsV1ValueEnumValue', 2)
  stringSetValue = _messages.MessageField('GoogleCloudResourcesettingsV1ValueStringSet', 3)
  stringValue = _messages.StringField(4)


class GoogleCloudResourcesettingsV1ValueEnumValue(_messages.Message):
  r"""A enum value that can hold any enum type setting values. Each enum type
  is represented by a number, this representation is stored in the
  definitions.

  Fields:
    value: The value of this enum
  """

  value = _messages.StringField(1)


class GoogleCloudResourcesettingsV1ValueStringSet(_messages.Message):
  r"""A string set value that can hold a set of strings. The maximum length of
  each string is 200 characters and there can be a maximum of 50 strings in
  the string set.

  Fields:
    values: The strings in the set
  """

  values = _messages.StringField(1, repeated=True)


class GoogleProtobufEmpty(_messages.Message):
  r"""A generic empty message that you can re-use to avoid defining duplicated
  empty messages in your APIs. A typical example is to use it as the request
  or the response type of an API method. For instance: service Foo { rpc
  Bar(google.protobuf.Empty) returns (google.protobuf.Empty); } The JSON
  representation for `Empty` is empty JSON object `{}`.
  """



class ResourcesettingsFoldersSettingsDeleteValueRequest(_messages.Message):
  r"""A ResourcesettingsFoldersSettingsDeleteValueRequest object.

  Fields:
    name: Required. The name of the setting value to delete. See SettingValue
      for naming requirements.
  """

  name = _messages.StringField(1, required=True)


class ResourcesettingsFoldersSettingsGetRequest(_messages.Message):
  r"""A ResourcesettingsFoldersSettingsGetRequest object.

  Enums:
    ViewValueValuesEnum: The SettingView for this request.

  Fields:
    name: Required. The name of the setting to get. See Setting for naming
      requirements.
    view: The SettingView for this request.
  """

  class ViewValueValuesEnum(_messages.Enum):
    r"""The SettingView for this request.

    Values:
      SETTING_VIEW_UNSPECIFIED: The default / unset value. The API will
        default to the SETTING_VIEW_BASIC view.
      SETTING_VIEW_BASIC: Include Setting.metadata, but nothing else. This is
        the default value (for both ListSettings and GetSetting).
      SETTING_VIEW_EFFECTIVE_VALUE: Include Setting.effective_value, but
        nothing else.
      SETTING_VIEW_LOCAL_VALUE: Include Setting.local_value, but nothing else.
    """
    SETTING_VIEW_UNSPECIFIED = 0
    SETTING_VIEW_BASIC = 1
    SETTING_VIEW_EFFECTIVE_VALUE = 2
    SETTING_VIEW_LOCAL_VALUE = 3

  name = _messages.StringField(1, required=True)
  view = _messages.EnumField('ViewValueValuesEnum', 2)


class ResourcesettingsFoldersSettingsGetValueRequest(_messages.Message):
  r"""A ResourcesettingsFoldersSettingsGetValueRequest object.

  Fields:
    name: Required. The name of the setting value to get. See SettingValue for
      naming requirements.
  """

  name = _messages.StringField(1, required=True)


class ResourcesettingsFoldersSettingsListRequest(_messages.Message):
  r"""A ResourcesettingsFoldersSettingsListRequest object.

  Enums:
    ViewValueValuesEnum: The SettingView for this request.

  Fields:
    pageSize: Unused. The size of the page to be returned.
    pageToken: Unused. A page token used to retrieve the next page.
    parent: Required. The Cloud resource that parents the setting. Must be in
      one of the following forms: * `projects/{project_number}` *
      `projects/{project_id}` * `folders/{folder_id}` *
      `organizations/{organization_id}`
    view: The SettingView for this request.
  """

  class ViewValueValuesEnum(_messages.Enum):
    r"""The SettingView for this request.

    Values:
      SETTING_VIEW_UNSPECIFIED: The default / unset value. The API will
        default to the SETTING_VIEW_BASIC view.
      SETTING_VIEW_BASIC: Include Setting.metadata, but nothing else. This is
        the default value (for both ListSettings and GetSetting).
      SETTING_VIEW_EFFECTIVE_VALUE: Include Setting.effective_value, but
        nothing else.
      SETTING_VIEW_LOCAL_VALUE: Include Setting.local_value, but nothing else.
    """
    SETTING_VIEW_UNSPECIFIED = 0
    SETTING_VIEW_BASIC = 1
    SETTING_VIEW_EFFECTIVE_VALUE = 2
    SETTING_VIEW_LOCAL_VALUE = 3

  pageSize = _messages.IntegerField(1, variant=_messages.Variant.INT32)
  pageToken = _messages.StringField(2)
  parent = _messages.StringField(3, required=True)
  view = _messages.EnumField('ViewValueValuesEnum', 4)


class ResourcesettingsFoldersSettingsPatchRequest(_messages.Message):
  r"""A ResourcesettingsFoldersSettingsPatchRequest object.

  Fields:
    googleCloudResourcesettingsV1Setting: A
      GoogleCloudResourcesettingsV1Setting resource to be passed as the
      request body.
    name: The resource name of the setting. Must be in one of the following
      forms: * `projects/{project_number}/settings/{setting_name}` *
      `folders/{folder_id}/settings/{setting_name}` *
      `organizations/{organization_id}/settings/{setting_name}` For example,
      "/projects/123/settings/gcp-enableMyFeature"
  """

  googleCloudResourcesettingsV1Setting = _messages.MessageField('GoogleCloudResourcesettingsV1Setting', 1)
  name = _messages.StringField(2, required=True)


class ResourcesettingsFoldersSettingsSearchRequest(_messages.Message):
  r"""A ResourcesettingsFoldersSettingsSearchRequest object.

  Fields:
    pageSize: Unused. The size of the page to be returned.
    pageToken: Unused. A page token used to retrieve the next page.
    parent: Required. The Cloud resource that parents the setting. Must be in
      one of the following forms: * `projects/{project_number}` *
      `projects/{project_id}` * `folders/{folder_id}` *
      `organizations/{organization_id}`
  """

  pageSize = _messages.IntegerField(1, variant=_messages.Variant.INT32)
  pageToken = _messages.StringField(2)
  parent = _messages.StringField(3, required=True)


class ResourcesettingsFoldersSettingsValueCreateRequest(_messages.Message):
  r"""A ResourcesettingsFoldersSettingsValueCreateRequest object.

  Fields:
    googleCloudResourcesettingsV1SettingValue: A
      GoogleCloudResourcesettingsV1SettingValue resource to be passed as the
      request body.
    parent: Required. The name of the setting for which a value should be
      created. See Setting for naming requirements.
    settingsId: A string attribute.
  """

  googleCloudResourcesettingsV1SettingValue = _messages.MessageField('GoogleCloudResourcesettingsV1SettingValue', 1)
  parent = _messages.StringField(2, required=True)
  settingsId = _messages.StringField(3, required=True)


class ResourcesettingsFoldersSettingsValueLookupEffectiveValueRequest(_messages.Message):
  r"""A ResourcesettingsFoldersSettingsValueLookupEffectiveValueRequest
  object.

  Fields:
    name: Required. The setting value for which an effective value will be
      evaluated. See SettingValue for naming requirements.
  """

  name = _messages.StringField(1, required=True)


class ResourcesettingsOrganizationsSettingsDeleteValueRequest(_messages.Message):
  r"""A ResourcesettingsOrganizationsSettingsDeleteValueRequest object.

  Fields:
    name: Required. The name of the setting value to delete. See SettingValue
      for naming requirements.
  """

  name = _messages.StringField(1, required=True)


class ResourcesettingsOrganizationsSettingsGetRequest(_messages.Message):
  r"""A ResourcesettingsOrganizationsSettingsGetRequest object.

  Enums:
    ViewValueValuesEnum: The SettingView for this request.

  Fields:
    name: Required. The name of the setting to get. See Setting for naming
      requirements.
    view: The SettingView for this request.
  """

  class ViewValueValuesEnum(_messages.Enum):
    r"""The SettingView for this request.

    Values:
      SETTING_VIEW_UNSPECIFIED: The default / unset value. The API will
        default to the SETTING_VIEW_BASIC view.
      SETTING_VIEW_BASIC: Include Setting.metadata, but nothing else. This is
        the default value (for both ListSettings and GetSetting).
      SETTING_VIEW_EFFECTIVE_VALUE: Include Setting.effective_value, but
        nothing else.
      SETTING_VIEW_LOCAL_VALUE: Include Setting.local_value, but nothing else.
    """
    SETTING_VIEW_UNSPECIFIED = 0
    SETTING_VIEW_BASIC = 1
    SETTING_VIEW_EFFECTIVE_VALUE = 2
    SETTING_VIEW_LOCAL_VALUE = 3

  name = _messages.StringField(1, required=True)
  view = _messages.EnumField('ViewValueValuesEnum', 2)


class ResourcesettingsOrganizationsSettingsGetValueRequest(_messages.Message):
  r"""A ResourcesettingsOrganizationsSettingsGetValueRequest object.

  Fields:
    name: Required. The name of the setting value to get. See SettingValue for
      naming requirements.
  """

  name = _messages.StringField(1, required=True)


class ResourcesettingsOrganizationsSettingsListRequest(_messages.Message):
  r"""A ResourcesettingsOrganizationsSettingsListRequest object.

  Enums:
    ViewValueValuesEnum: The SettingView for this request.

  Fields:
    pageSize: Unused. The size of the page to be returned.
    pageToken: Unused. A page token used to retrieve the next page.
    parent: Required. The Cloud resource that parents the setting. Must be in
      one of the following forms: * `projects/{project_number}` *
      `projects/{project_id}` * `folders/{folder_id}` *
      `organizations/{organization_id}`
    view: The SettingView for this request.
  """

  class ViewValueValuesEnum(_messages.Enum):
    r"""The SettingView for this request.

    Values:
      SETTING_VIEW_UNSPECIFIED: The default / unset value. The API will
        default to the SETTING_VIEW_BASIC view.
      SETTING_VIEW_BASIC: Include Setting.metadata, but nothing else. This is
        the default value (for both ListSettings and GetSetting).
      SETTING_VIEW_EFFECTIVE_VALUE: Include Setting.effective_value, but
        nothing else.
      SETTING_VIEW_LOCAL_VALUE: Include Setting.local_value, but nothing else.
    """
    SETTING_VIEW_UNSPECIFIED = 0
    SETTING_VIEW_BASIC = 1
    SETTING_VIEW_EFFECTIVE_VALUE = 2
    SETTING_VIEW_LOCAL_VALUE = 3

  pageSize = _messages.IntegerField(1, variant=_messages.Variant.INT32)
  pageToken = _messages.StringField(2)
  parent = _messages.StringField(3, required=True)
  view = _messages.EnumField('ViewValueValuesEnum', 4)


class ResourcesettingsOrganizationsSettingsPatchRequest(_messages.Message):
  r"""A ResourcesettingsOrganizationsSettingsPatchRequest object.

  Fields:
    googleCloudResourcesettingsV1Setting: A
      GoogleCloudResourcesettingsV1Setting resource to be passed as the
      request body.
    name: The resource name of the setting. Must be in one of the following
      forms: * `projects/{project_number}/settings/{setting_name}` *
      `folders/{folder_id}/settings/{setting_name}` *
      `organizations/{organization_id}/settings/{setting_name}` For example,
      "/projects/123/settings/gcp-enableMyFeature"
  """

  googleCloudResourcesettingsV1Setting = _messages.MessageField('GoogleCloudResourcesettingsV1Setting', 1)
  name = _messages.StringField(2, required=True)


class ResourcesettingsOrganizationsSettingsSearchRequest(_messages.Message):
  r"""A ResourcesettingsOrganizationsSettingsSearchRequest object.

  Fields:
    pageSize: Unused. The size of the page to be returned.
    pageToken: Unused. A page token used to retrieve the next page.
    parent: Required. The Cloud resource that parents the setting. Must be in
      one of the following forms: * `projects/{project_number}` *
      `projects/{project_id}` * `folders/{folder_id}` *
      `organizations/{organization_id}`
  """

  pageSize = _messages.IntegerField(1, variant=_messages.Variant.INT32)
  pageToken = _messages.StringField(2)
  parent = _messages.StringField(3, required=True)


class ResourcesettingsOrganizationsSettingsValueCreateRequest(_messages.Message):
  r"""A ResourcesettingsOrganizationsSettingsValueCreateRequest object.

  Fields:
    googleCloudResourcesettingsV1SettingValue: A
      GoogleCloudResourcesettingsV1SettingValue resource to be passed as the
      request body.
    parent: Required. The name of the setting for which a value should be
      created. See Setting for naming requirements.
    settingsId: A string attribute.
  """

  googleCloudResourcesettingsV1SettingValue = _messages.MessageField('GoogleCloudResourcesettingsV1SettingValue', 1)
  parent = _messages.StringField(2, required=True)
  settingsId = _messages.StringField(3, required=True)


class ResourcesettingsOrganizationsSettingsValueLookupEffectiveValueRequest(_messages.Message):
  r"""A ResourcesettingsOrganizationsSettingsValueLookupEffectiveValueRequest
  object.

  Fields:
    name: Required. The setting value for which an effective value will be
      evaluated. See SettingValue for naming requirements.
  """

  name = _messages.StringField(1, required=True)


class ResourcesettingsProjectsSettingsDeleteValueRequest(_messages.Message):
  r"""A ResourcesettingsProjectsSettingsDeleteValueRequest object.

  Fields:
    name: Required. The name of the setting value to delete. See SettingValue
      for naming requirements.
  """

  name = _messages.StringField(1, required=True)


class ResourcesettingsProjectsSettingsGetRequest(_messages.Message):
  r"""A ResourcesettingsProjectsSettingsGetRequest object.

  Enums:
    ViewValueValuesEnum: The SettingView for this request.

  Fields:
    name: Required. The name of the setting to get. See Setting for naming
      requirements.
    view: The SettingView for this request.
  """

  class ViewValueValuesEnum(_messages.Enum):
    r"""The SettingView for this request.

    Values:
      SETTING_VIEW_UNSPECIFIED: The default / unset value. The API will
        default to the SETTING_VIEW_BASIC view.
      SETTING_VIEW_BASIC: Include Setting.metadata, but nothing else. This is
        the default value (for both ListSettings and GetSetting).
      SETTING_VIEW_EFFECTIVE_VALUE: Include Setting.effective_value, but
        nothing else.
      SETTING_VIEW_LOCAL_VALUE: Include Setting.local_value, but nothing else.
    """
    SETTING_VIEW_UNSPECIFIED = 0
    SETTING_VIEW_BASIC = 1
    SETTING_VIEW_EFFECTIVE_VALUE = 2
    SETTING_VIEW_LOCAL_VALUE = 3

  name = _messages.StringField(1, required=True)
  view = _messages.EnumField('ViewValueValuesEnum', 2)


class ResourcesettingsProjectsSettingsGetValueRequest(_messages.Message):
  r"""A ResourcesettingsProjectsSettingsGetValueRequest object.

  Fields:
    name: Required. The name of the setting value to get. See SettingValue for
      naming requirements.
  """

  name = _messages.StringField(1, required=True)


class ResourcesettingsProjectsSettingsListRequest(_messages.Message):
  r"""A ResourcesettingsProjectsSettingsListRequest object.

  Enums:
    ViewValueValuesEnum: The SettingView for this request.

  Fields:
    pageSize: Unused. The size of the page to be returned.
    pageToken: Unused. A page token used to retrieve the next page.
    parent: Required. The Cloud resource that parents the setting. Must be in
      one of the following forms: * `projects/{project_number}` *
      `projects/{project_id}` * `folders/{folder_id}` *
      `organizations/{organization_id}`
    view: The SettingView for this request.
  """

  class ViewValueValuesEnum(_messages.Enum):
    r"""The SettingView for this request.

    Values:
      SETTING_VIEW_UNSPECIFIED: The default / unset value. The API will
        default to the SETTING_VIEW_BASIC view.
      SETTING_VIEW_BASIC: Include Setting.metadata, but nothing else. This is
        the default value (for both ListSettings and GetSetting).
      SETTING_VIEW_EFFECTIVE_VALUE: Include Setting.effective_value, but
        nothing else.
      SETTING_VIEW_LOCAL_VALUE: Include Setting.local_value, but nothing else.
    """
    SETTING_VIEW_UNSPECIFIED = 0
    SETTING_VIEW_BASIC = 1
    SETTING_VIEW_EFFECTIVE_VALUE = 2
    SETTING_VIEW_LOCAL_VALUE = 3

  pageSize = _messages.IntegerField(1, variant=_messages.Variant.INT32)
  pageToken = _messages.StringField(2)
  parent = _messages.StringField(3, required=True)
  view = _messages.EnumField('ViewValueValuesEnum', 4)


class ResourcesettingsProjectsSettingsPatchRequest(_messages.Message):
  r"""A ResourcesettingsProjectsSettingsPatchRequest object.

  Fields:
    googleCloudResourcesettingsV1Setting: A
      GoogleCloudResourcesettingsV1Setting resource to be passed as the
      request body.
    name: The resource name of the setting. Must be in one of the following
      forms: * `projects/{project_number}/settings/{setting_name}` *
      `folders/{folder_id}/settings/{setting_name}` *
      `organizations/{organization_id}/settings/{setting_name}` For example,
      "/projects/123/settings/gcp-enableMyFeature"
  """

  googleCloudResourcesettingsV1Setting = _messages.MessageField('GoogleCloudResourcesettingsV1Setting', 1)
  name = _messages.StringField(2, required=True)


class ResourcesettingsProjectsSettingsSearchRequest(_messages.Message):
  r"""A ResourcesettingsProjectsSettingsSearchRequest object.

  Fields:
    pageSize: Unused. The size of the page to be returned.
    pageToken: Unused. A page token used to retrieve the next page.
    parent: Required. The Cloud resource that parents the setting. Must be in
      one of the following forms: * `projects/{project_number}` *
      `projects/{project_id}` * `folders/{folder_id}` *
      `organizations/{organization_id}`
  """

  pageSize = _messages.IntegerField(1, variant=_messages.Variant.INT32)
  pageToken = _messages.StringField(2)
  parent = _messages.StringField(3, required=True)


class ResourcesettingsProjectsSettingsValueCreateRequest(_messages.Message):
  r"""A ResourcesettingsProjectsSettingsValueCreateRequest object.

  Fields:
    googleCloudResourcesettingsV1SettingValue: A
      GoogleCloudResourcesettingsV1SettingValue resource to be passed as the
      request body.
    parent: Required. The name of the setting for which a value should be
      created. See Setting for naming requirements.
    settingsId: A string attribute.
  """

  googleCloudResourcesettingsV1SettingValue = _messages.MessageField('GoogleCloudResourcesettingsV1SettingValue', 1)
  parent = _messages.StringField(2, required=True)
  settingsId = _messages.StringField(3, required=True)


class ResourcesettingsProjectsSettingsValueLookupEffectiveValueRequest(_messages.Message):
  r"""A ResourcesettingsProjectsSettingsValueLookupEffectiveValueRequest
  object.

  Fields:
    name: Required. The setting value for which an effective value will be
      evaluated. See SettingValue for naming requirements.
  """

  name = _messages.StringField(1, required=True)


class StandardQueryParameters(_messages.Message):
  r"""Query parameters accepted by all methods.

  Enums:
    FXgafvValueValuesEnum: V1 error format.
    AltValueValuesEnum: Data format for response.

  Fields:
    f__xgafv: V1 error format.
    access_token: OAuth access token.
    alt: Data format for response.
    callback: JSONP
    fields: Selector specifying which fields to include in a partial response.
    key: API key. Your API key identifies your project and provides you with
      API access, quota, and reports. Required unless you provide an OAuth 2.0
      token.
    oauth_token: OAuth 2.0 token for the current user.
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
    r"""Data format for response.

    Values:
      json: Responses with Content-Type of application/json
      media: Media download with context-dependent Content-Type
      proto: Responses with Content-Type of application/x-protobuf
    """
    json = 0
    media = 1
    proto = 2

  class FXgafvValueValuesEnum(_messages.Enum):
    r"""V1 error format.

    Values:
      _1: v1 error format
      _2: v2 error format
    """
    _1 = 0
    _2 = 1

  f__xgafv = _messages.EnumField('FXgafvValueValuesEnum', 1)
  access_token = _messages.StringField(2)
  alt = _messages.EnumField('AltValueValuesEnum', 3, default='json')
  callback = _messages.StringField(4)
  fields = _messages.StringField(5)
  key = _messages.StringField(6)
  oauth_token = _messages.StringField(7)
  prettyPrint = _messages.BooleanField(8, default=True)
  quotaUser = _messages.StringField(9)
  trace = _messages.StringField(10)
  uploadType = _messages.StringField(11)
  upload_protocol = _messages.StringField(12)


encoding.AddCustomJsonFieldMapping(
    StandardQueryParameters, 'f__xgafv', '$.xgafv')
encoding.AddCustomJsonEnumMapping(
    StandardQueryParameters.FXgafvValueValuesEnum, '_1', '1')
encoding.AddCustomJsonEnumMapping(
    StandardQueryParameters.FXgafvValueValuesEnum, '_2', '2')
