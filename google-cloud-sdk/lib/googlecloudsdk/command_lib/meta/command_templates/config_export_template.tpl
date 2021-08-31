# -*- coding: utf-8 -*- #
## Copyright 2021 Google LLC. All Rights Reserved.
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##    http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.
release_tracks: ${release_tracks}
command_type: CONFIG_EXPORT
help_text:
  brief: Export the configuration for ${api_a_or_an} ${capitalized_api_name} ${singular_name_with_spaces}.
  description: |
    *{command}* exports the configuration for ${api_a_or_an} ${capitalized_api_name} ${singular_name_with_spaces}.

    ${singular_capitalized_name} configurations can be exported in
    Kubernetes Resource Model (krm) or Terraform HCL formats. The
    default format is `krm`.

    Specifying `--all` allows you to export the configurations for all
    ${plural_resource_name_with_spaces} within the project.

    Specifying `--path` allows you to export the configuration(s) to
    a local directory.
  examples: |
    To export the configuration for ${resource_a_or_an} ${singular_name_with_spaces}, run:

      $ {command} ${resource_argument_name}

    To export the configuration for ${resource_a_or_an} ${singular_name_with_spaces} to a file, run:

      $ {command} ${resource_argument_name} --path=/path/to/dir/

    To export the configuration for ${resource_a_or_an} ${singular_name_with_spaces} in Terraform
    HCL format, run:

      $ {command} ${resource_argument_name} --resource-format=terraform

    To export the configurations for all ${plural_resource_name_with_spaces} within a
    project, run:

      $ {command} --all
arguments:
  resource:
    help_text: ${singular_capitalized_name} to export the configuration for.
    spec: !REF googlecloudsdk.command_lib.${api_name}.resources:${resource_file_name}
