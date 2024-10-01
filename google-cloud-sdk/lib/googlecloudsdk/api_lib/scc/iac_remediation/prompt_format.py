# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Prompt Format Lookup."""

from __future__ import annotations


class PromptFormatLookup:
  """Prompt lookup."""

  def get_policy_prompt_template(self) -> str:
    """Get policy prompt template."""
    self._policy_prompt_format = """
# SYSTEM INSTRUCTIONS:
- You are an expert in creating terraform resources for GCP.
- You have access to a complete and up-to-date knowledge base of all GCP resource types terraform documentation.
- Identify the most relevant GCP terraform resource used to grant the permission from the given IAM BINDINGS .
- You have to update the relevant terraform files for the given IAM binding as per the roles and permissions required.

#TASK
- Analyze the INPUT_TF_FILES and identify the resource types that are most likely to contain the information needed.
- ** Identify the resource types in INPUT_TF_FILES that are most likely to contain the IAM_BINDINGS information.**
- ** Prioritize resource types which are most likely to create or remove the permissions given in IAM binding for the given RESOURCE_NAME.**
- ** DO NOT update the permission for any member which is not present in the IAM_BINDINGS.**
- ** Verify the output to check no other permissions are updated for the member which is not present in the IAM_BINDINGS.**
- The output should contain the complete INPUT_TF_FILES which were updated as per given IAM bindings .
- The resource "google_project_iam_member_remove" should be created only if the role needs to be removed.
- Refer to the summary of TERRAFORM_DOCUMENTATION given below for updating the files.
- Refer to TFSTATE_INFORMATION to identify the terraform files from INPUT_TF_FILES which needs to be updated.
- The output must be a valid json file with the following OUTPUT_FORMAT.
- The output must contains only those files which were updated.
- The output should be in the OUTPUT_FORMAT given below.

# OUTPUT_FORMAT is as follows
FilePath= "file_path1"
```
The complete terraform file(s) which were updated as per given IAM bindings .
The output must be valid .tf files.
```
FilePath= "file_path2"
```
The complete terraform file(s) which were updated as per given IAM bindings .
The output must be valid .tf files.
```

# IAM_BINDINGS
{{iam_bindings}}

# RESOURCE_NAME
{{resource_name}}

# INPUT_TF_FILES
{{input_tf_files}}

# TFSTATE_INFORMATION
{{tfstate_information}}

# EXAMPLE1 is as follows

## INPUT_TF_FILES
FilePath= "file_path1"
```
resource "google_project_iam_policy" "project" {
  project     = "project_name_test"
  policy_data = "${data.google_iam_policy.admin.policy_data}"
}

data "google_iam_policy" "admin" {
  binding {
    role = "roles/compute.admin"

    members = [
      "user:jane@example.com",
      "user:user1@google.com",
      "user:user2@google.com",
    ]

    condition {
      title       = "expires_after_2019_12_31"
      description = "Expiring at midnight of 2019-12-31"
      expression  = "request.time < timestamp(\"2020-01-01T00:00:00Z\")"
    }
  }
  binding {
    role = "roles/compute.viewer"

    members = [
      "user:jane@example.com",
    ]

    condition {
      title       = "expires_after_2019_12_31"
      description = "Expiring at midnight of 2019-12-31"
      expression  = "request.time < timestamp(\"2020-01-01T00:00:00Z\")"
    }
  }
}
```
FilePath= "file_path2"
```
resource "google_project_iam_policy" "project" {
  project     = "your-project-id"
  policy_data = "${data.google_iam_policy.admin.policy_data}"
}

data "google_iam_policy" "admin" {
  binding {
    role = "roles/compute.admin"

    members = [
      "user:jane@example.com",
    ]

    condition {
      title       = "expires_after_2019_12_31"
      description = "Expiring at midnight of 2019-12-31"
      expression  = "request.time < timestamp(\"2020-01-01T00:00:00Z\")"
    }
  }
}
```

## IAM_BINDINGS
Member : "user:user1@google.com"

Action: "ADD"
Role : "roles/compute.viewer"
Role: "roles/storage.objectViewer"


Action: "REMOVE"
Role: "roles/compute.admin"
Role: "roles/storage.objectAdmin"

## RESOURCE_NAME
project_name_test

## TFSTATE_INFORMATION


** ANSWER **
FilePath= "file_path1"
```
resource "google_project_iam_policy" "project" {
  project     = "project_name_test"
  policy_data = "${data.google_iam_policy.admin.policy_data}"
}

data "google_iam_policy" "admin" {
  binding {
    role = "roles/compute.admin"

    members = [
      "user:jane@example.com",
      "user:user2@google.com",
    ]

    condition {
      title       = "expires_after_2019_12_31"
      description = "Expiring at midnight of 2019-12-31"
      expression  = "request.time < timestamp(\"2020-01-01T00:00:00Z\")"
    }
  }
  binding {
    role = "roles/compute.viewer"

    members = [
      "user:jane@example.com",
      "user:user1@google.com",
    ]

    condition {
      title       = "expires_after_2019_12_31"
      description = "Expiring at midnight of 2019-12-31"
      expression  = "request.time < timestamp(\"2020-01-01T00:00:00Z\")"
    }
  }
  binding {
    role = "roles/storage.objectViewer"
    members = [
      "user:user1@google.com",
    ]
  }
}

# Remove the permission for user1 for storage.objectAdmin
resource "google_project_iam_member_remove" "remove_permission_for_user1" {
  role     = "roles/storage.objectAdmin"
  project  = "project_name_test"
  member  = "user:user1@google.com"
}
```

** Steps **
1. **Identify the file**: Identify the file(s) that contains the resources that need to be updated as per information in IAM Binding.
2. **Identify the resource**: Identify the resource(s) that need to be updated as per information in IAM Binding.
3. ** If the binding for a role is not present in the policy data**, then add the binding to the policy data.
4. **If the binding for a role is present in the policy data for removing the permission**, Create a resource to remove the permission for the user.
5. **If the binding for a role is present in the policy data for adding the permission**, Add the permission for the user.
6. **If the binding for a role is not present in the policy data for adding the permission**, Add the binding for the role and assign permission to the user.
7. **If the binding for a role is not present in the policy data for removing the permission**, Create a resource to remove the permission for the user.

# TERRAFORM_DOCUMENTATION

## Documentation for google_project_iam_member_remove
data "google_project" "target_project" {}

resource "google_project_iam_member_remove" "foo" {
  # (Required) The target role that should be removed.
  role     = "roles/editor"

  # (Required) The project id of the target project.
  project  = google_project.target_project.project_id

  # (Required) The IAM principal that should not have the target role. Each entry can have one of the following values:
  # user:{emailid}: An email address that represents a specific Google account. For example, alice@gmail.com or joe@example.com.
  # serviceAccount:{emailid}: An email address that represents a service account. For example, my-other-app@appspot.gserviceaccount.com.
  # group:{emailid}: An email address that represents a Google group. For example, admins@example.com.
  # domain:{domain}: A G Suite domain (primary, instead of alias) name that represents all the users of that domain. For example, google.com or example.com.
  member  = "serviceAccount:${google_project.target_project.number}-compute@developer.gserviceaccount.com"
}

## Documentation for google_project_iam_policy
resource "google_project_iam_policy" "project" {
  # (Required) The project id of the target project. This is not inferred from the provider.
  project     = "your-project-id"

  # (Required) The google_iam_policy data source that represents the IAM policy that will be applied to the project. The policy will be merged with any existing policy applied to the project.
  # Changing this updates the policy.
  # Deleting this removes all policies from the project, locking out users without organization-level access.
  policy_data = "${data.google_iam_policy.admin.policy_data}"
}

data "google_iam_policy" "admin" {
  binding {
    # (Required) The role that should be applied. Only one google_project_iam_binding can be used per role. Note that custom roles must be of the format [projects|organizations]/{parent-name}/roles/{role-name}
    role = "roles/compute.admin"

    # (Required) Identities that will be granted the privilege in role. google_project_iam_binding expects members field while google_project_iam_member expects member field. Each entry can have one of the following values:
    # user:{emailid}: An email address that represents a specific Google account. For example, alice@gmail.com or joe@example.com.
    # serviceAccount:{emailid}: An email address that represents a service account. For example, my-other-app@appspot.gserviceaccount.com.
    # group:{emailid}: An email address that represents a Google group. For example, admins@example.com.
    # domain:{domain}: A G Suite domain (primary, instead of alias) name that represents all the users of that domain. For example, google.com or example.com.
    members = [
      "user:jane@example.com",
    ]

    # (Optional) An IAM Condition for a given binding.
    condition {
      # (Required) A title for the expression, i.e. a short string describing its purpose.
      title       = "expires_after_2019_12_31"

      # (Optional) An optional description of the expression. This is a longer text which describes the expression, e.g. when hovered over it in a UI.
      description = "Expiring at midnight of 2019-12-31"

      # (Required) Textual representation of an expression in Common Expression Language syntax.
      expression  = "request.time < timestamp(\"2020-01-01T00:00:00Z\")"
    }
  }
}

    """
    return self._policy_prompt_format

  def get_binding_prompt_template(self) -> str:
    """Get binding prompt template."""
    self._binding_prompt_format = """
# SYSTEM INSTRUCTIONS:
- You are an expert in creating terraform resources for GCP.
- You have access to a complete and up-to-date knowledge base of all GCP resource types terraform documentation.
- Identify the most relevant GCP terraform resource used to grant the permission from the given IAM BINDING .
- You have to update the relevant terraform file for the given IAM binding as per the roles and permissions required.
- When a resource that grants an IAM role is deleted, do not create a google_project_iam_member_remove resource for that role and member. The deletion of the resource implicitly removes the permission.
- Ensure that the generated Terraform code is idempotent. Avoid creating unnecessary resources, especially if the desired state is already achieved by deleting an existing resource.

#TASK
- Analyze the INPUT_TF_FILES and identify the files that needs to be updated by referring to TFSTATE_INFORMATION.
- Assume that the complete system information is provided in INPUT_TF_FILES.
- **Identify the resource types in INPUT_TF_FILES that are most likely to contain the IAM_BINDING information.**
- ** Give meaningful names to the resources which are being created. A name must start with a letter or underscore and may contain only letters, digits, underscores, and dashes.**
- **Prioritize resource types which are most likely to create or remove the permissions given in IAM binding for the given RESOURCE_NAME.**
- The output should contain the complete INPUT_TF_FILES which were updated as per given IAM bindings .
- **Pay close attention to resources that use `for_each` loops or dynamic blocks and handle changes within those constructs to ensure idempotency.**
- google_project_iam_binding resources can be used in conjunction with google_project_iam_member resources only if they do not grant privilege to the same role.
- Refer to the summary of TERRAFORM_DOCUMENTATION given below for updating the files.
- **Validate that the generated Terraform code does not create unnecessary google_project_iam_member_remove resources when the corresponding resource granting the role is already deleted.**
- The output must be list of valid .tf files.
- The output must contains only those files which were updated.
- The output should start with: ```
- The output must end with: ```
- The output should be in the FORMAT given below.

# TERRAFORM DOCUMENTATION

Purpose: The google_project_iam resource empowers you to define who (users, groups, service accounts) has what permissions (roles) on your Google Cloud projects. This is crucial for controlling access to your cloud resources and ensuring security.
Functionality:
Granting Permissions: You can use this resource to assign specific roles to different entities (users, groups, service accounts) on your Google Cloud project. This allows you to give them the exact permissions they need to perform their tasks.
Revoking Permissions: Similarly, you can use this resource to remove existing roles from entities, effectively revoking their permissions on the project.
Managing Complex Policies: The resource supports intricate scenarios, allowing you to define conditional bindings based on attributes like resource tags or request conditions.
Key Attributes:
project: The ID of the Google Cloud project where you want to manage IAM.
role: The specific role you want to grant or revoke (e.g., "roles/editor", "roles/viewer").
members: A list of entities (in the format "user:example@example.com", "group:group-name@example.com", "serviceAccount:serviceaccount-id@project.iam.gserviceaccount.com") that should be granted or revoked the specified role.
condition: (Optional) Allows you to define conditions under which the role binding should be active.
Usage Examples: The documentation provides comprehensive examples of how to use the google_project_iam resource in various scenarios, including:
Granting a user the "Editor" role on a project.
Allowing a service account to access resources in a project.
Setting up conditional access based on specific attributes.
In essence, the google_project_iam resource is a fundamental tool for managing access control and security for your Google Cloud projects within your Terraform infrastructure code.

## Documentation for google_project_iam_binding
resource "google_project_iam_binding" "project" {
  # (Required) The project id of the target project. This is not inferred from the provider.
  project = "your-project-id"

  # (Required) The role that should be applied. Only one google_project_iam_binding can be used per role. Note that custom roles must be of the format [projects|organizations]/{parent-name}/roles/{role-name}
  role    = "roles/container.admin"

  # (Required) Identities that will be granted the privilege in role. google_project_iam_binding expects members field while google_project_iam_member expects member field. Each entry can have one of the following values:
  # user:{emailid}: An email address that represents a specific Google account. For example, alice@gmail.com or joe@example.com.
  # serviceAccount:{emailid}: An email address that represents a service account. For example, my-other-app@appspot.gserviceaccount.com.
  # group:{emailid}: An email address that represents a Google group. For example, admins@example.com.
  # domain:{domain}: A G Suite domain (primary, instead of alias) name that represents all the users of that domain. For example, google.com or example.com.
  members = [
    "user:jane@example.com",
  ]

  # (Optional) An IAM Condition for a given binding.
  condition {
    # (Required) A title for the expression, i.e. a short string describing its purpose.
    title       = "expires_after_2019_12_31"

    # (Optional) An optional description of the expression. This is a longer text which describes the expression, e.g. when hovered over it in a UI.
    description = "Expiring at midnight of 2019-12-31"

    # (Required) Textual representation of an expression in Common Expression Language syntax.
    expression  = "request.time < timestamp("2020-01-01T00:00:00Z")"
  }
}

#DOCUMENTATION for "google_project_iam_member_remove"
data "google_project" "target_project" {}

resource "google_project_iam_member_remove" "foo" {
  # (Required) The target role that should be removed.
  role     = "roles/editor"

  # (Required) The project id of the target project.
  project  = google_project.target_project.project_id

  # (Required) The IAM principal that should not have the target role. Each entry can have one of the following values:
  # user:{emailid}: An email address that represents a specific Google account. For example, alice@gmail.com or joe@example.com.
  # serviceAccount:{emailid}: An email address that represents a service account. For example, my-other-app@appspot.gserviceaccount.com.
  # group:{emailid}: An email address that represents a Google group. For example, admins@example.com.
  # domain:{domain}: A G Suite domain (primary, instead of alias) name that represents all the users of that domain. For example, google.com or example.com.
  member  = "serviceAccount:${google_project.target_project.number}-compute@developer.gserviceaccount.com"
}

## Documentation for google_project_iam_member
resource "google_project_iam_member" "project" {
  # (Required) The project id of the target project. This is not inferred from the provider.
  project = "your-project-id"

  # (Required) The role that should be applied. Only one google_project_iam_binding can be used per role. Note that custom roles must be of the format [projects|organizations]/{parent-name}/roles/{role-name}
  role    = "roles/firebase.admin"

  # (Required) Identities that will be granted the privilege in role. google_project_iam_binding expects members field while google_project_iam_member expects member field. Each entry can have one of the following values:
  # user:{emailid}: An email address that represents a specific Google account. For example, alice@gmail.com or joe@example.com.
  # serviceAccount:{emailid}: An email address that represents a service account. For example, my-other-app@appspot.gserviceaccount.com.
  # group:{emailid}: An email address that represents a Google group. For example, admins@example.com.
  # domain:{domain}: A G Suite domain (primary, instead of alias) name that represents all the users of that domain. For example, google.com or example.com.
  member  = "user:jane@example.com"

  # (Optional) An IAM Condition for a given binding.
  condition {
    # (Required) A title for the expression, i.e. a short string describing its purpose.
    title       = "expires_after_2019_12_31"

    # (Optional) An optional description of the expression. This is a longer text which describes the expression, e.g. when hovered over it in a UI.
    description = "Expiring at midnight of 2019-12-31"

    # (Required) Textual representation of an expression in Common Expression Language syntax.
    expression  = "request.time < timestamp("2020-01-01T00:00:00Z")"
  }
}

# FORMAT is as follows
FilePath= "file_path1"
```
The complete terraform file(s) which were updated as per given IAM bindings .
The output must be valid .tf files.
```
FilePath= "file_path2"
```
The complete terraform file(s) which were updated as per given IAM bindings .
The output must be valid .tf files.

## IAM_BINDINGS
{{iam_bindings}}

## RESOURCE_NAME
{{resource_name}}

## INPUT_TF_FILES
{{input_tf_files}}

## TFSTATE_INFORMATION
{{tfstate_information}}

# EXAMPLE1 is as follows

## INPUT_TF_FILES
FilePath1= "file_path1"
```
resource "google_project_iam_binding" "iam_binding_for_admin_project" {
  project = project_name_test
  role    = "roles/compute.admin"
  members = [
    "user:user1@google.com",
    "user:user2@google.com",
    "user:user3@google.com",
  ]
}

resource "google_project_iam_binding" "iam_binding_for_bigquery" {
  project = project_name_test
  role    = "roles/bigquery.dataViewer"
  members = [
    "user:user2@google.com",
    "user:user3@google.com",
  ]
}
```
FilePath2= "file_path2"
```
resource "google_project_iam_binding" "iam_binding_for_admin_project2" {
  project = var.project_id2
  role =  "roles/compute.admin"
  members = [
    "user:user1@google.com",
    "user:user2@google.com",
  ]
}
```

## IAM_BINDINGS

Member: "user:user1@google.com"

Action: "ADD"
Role: "roles/compute.viewer"
Role: "roles/bigquery.dataViewer"

Action: "REMOVE"
Role: "roles/compute.admin"
Role: "roles/bigquery.dataEditor"


## RESOURCE_NAME
project_name_test

** ANSWER **
FilePath= "file_path1"
```
resource "google_project_iam_binding" "iam_binding_for_admin_project" {
  project = project_name_test
  role    = "roles/compute.admin"
  members = [
    "user:user2@google.com",
    "user:user3@google.com",
  ]
}

resource "google_project_iam_member" "iam_member_for_bigquery" {
  project = project_name_test
  role    = "roles/compute.viewer"
  member = "user:user1@google.com"
}

resource "google_project_iam_binding" "iam_binding_for_bigquery" {
  project = project_name_test
  role    = "roles/bigquery.dataViewer"
  members = [
    "user:user2@google.com",
    "user:user3@google.com",
    "user:user1@google.com",
  ]
}

resource "google_project_iam_member_remove" "iam_member_remove_for_bigquery" {
  project = project_name_test
  role    = "roles/bigquery.dataEditor"
  member = "user:user1@google.com"
}
```

# EXAMPLE2 is as follows

## INPUT_TF_FILES
FilePath= "file_path1"
```
resource "google_project_iam_binding" "iam_binding_for_admin_project" {
  for_each = toset([
    "roles/billing.projectManager",            # assign billing account to project
    "roles/billing.user",                      # view and associate billing accounts
    "roles/compute.admin",
    "roles/iam.organizationRoleAdmin",         # create custom org roles
    "roles/iam.serviceAccountAdmin",           # create service accounts and setIamPolicy
    "roles/iam.workloadIdentityPoolAdmin",     # create workload identity pool and providers
    "roles/orgpolicy.policyAdmin",             # create org policies
    "roles/resourcemanager.organizationAdmin", # setIamPolicy on organization
    "roles/resourcemanager.folderAdmin",       # create folders
    "roles/resourcemanager.projectCreator",    # create projects
    "roles/resourcemanager.tagAdmin",          # create tag keys and values
    "roles/resourcemanager.tagUser",           # create tag bindings on resources
    "roles/serviceusage.serviceUsageAdmin",    # enable services
  ])
  project = project_name_test
  role    = each.value
  members = [
    "user:user1@google.com",
    "user:user2@google.com",
    "user:user3@google.com",
  ]
}
```
FilePath= "file_path2"
```
resource "google_project_iam_binding" "iam_binding" {
  project = var.project_id2
  role =  "roles/compute.admin"
  members = [
    "user:user1@google.com",
    "user:user2@google.com",
  ]
}
```

## IAM_BINDINGS
Member: "user:user1@google.com"

Action: "ADD"
Role: "roles/compute.viewer"
Role: "roles/bigquery.dataViewer"

Action: "REMOVE"
Role: "roles/compute.admin"
Role: "roles/bigquery.dataEditor"

## RESOURCE_NAME
project_name_test


** ANSWER **
FilePath= "file_path1"
```
resource "google_project_iam_binding" "iam_binding_for_admin_project" {
  for_each = toset([
    "roles/billing.projectManager",            # assign billing account to project
    "roles/billing.user",                      # view and associate billing accounts
    "roles/iam.organizationRoleAdmin",         # create custom org roles
    "roles/iam.serviceAccountAdmin",           # create service accounts and setIamPolicy
    "roles/iam.workloadIdentityPoolAdmin",     # create workload identity pool and providers
    "roles/orgpolicy.policyAdmin",             # create org policies
    "roles/resourcemanager.organizationAdmin", # setIamPolicy on organization
    "roles/resourcemanager.folderAdmin",       # create folders
    "roles/resourcemanager.projectCreator",    # create projects
    "roles/resourcemanager.tagAdmin",          # create tag keys and values
    "roles/resourcemanager.tagUser",           # create tag bindings on resources
    "roles/serviceusage.serviceUsageAdmin",    # enable services
  ])
  project = project_name_test
  role    = each.value
  members = [
    "user:user1@google.com",
    "user:user2@google.com",
    "user:user3@google.com",
  ]
}

resource "google_project_iam_binding" "iam_binding_for_admin_project" {
  project = project_name_test
  role    = "roles/compute.admin"
  members = [
    "user:user2@google.com",
    "user:user3@google.com",
  ]
}

resource "google_project_iam_member" "iam_member_for_compute_viewer" {
  project = project_name_test
  role    = "roles/compute.viewer"
  member = "user:user1@google.com"
}

resource "google_project_iam_member_remove" "iam_member_remove_for_bigquery" {
  project = project_name_test
  role    = "roles/bigquery.dataEditor"
  member = "user:user1@google.com"
}

resource "google_project_iam_member" "iam_member_for_bigquery" {
  project = project_name_test
  role    = "roles/bigquery.dataViewer"
  member = "user:user1@google.com"
}
```


** Steps **
1. **Identify the file**: Identify the file(s) that contains the resources that need to be updated as per information in IAM Binding and TFSTATE_INFORMATION.
2. **Identify the actions**: Identify the ADD and REMOVE actions for the MEMBER in IAM Bindings.
3. **Identify the resource**: Identify the resource(s) that need to be updated as per information in IAM Binding.
4. **Identify the role**: Identify the role that needs to be assigned to the user(s) as per information in IAM Binding.
5. **Identify the permissions**: Identify the permissions that need to be granted to the user(s) as per information in IAM Binding.
6. **Identify the action**: Identify the action that needs to be taken as per information in IAM Binding.
7. **For action "ADD"**:
   7a. If the role is present in google_project_iam_binding, Add the user(s) to the role(s) with the permissions.
   7b. If the role is not present in google_project_iam_binding, use "google_project_iam_member" to add the user(s) to the role(s) with the permissions.
   7c. If the role is present in google_project_iam_binding but have multiple roles in a for construct, use "google_project_iam_member" to add the user(s) to the role(s) with the permissions.
8. **For action "REMOVE"**:
  8a.Identify the Resources: Determine which resources in your Terraform code (e.g., google_project_iam_binding, google_project_iam_member) might be granting the roles you want to remove to member specified.
  8b. Remove the Member:
      1. If the roles are managed within a google_project_iam_binding resource using the members attribute, remove member from that list for each role.
      2. **If you find individual google_project_iam_member resources granting those specific roles to member, you can either delete those resources entirely or comment them out**.
      3.  If the role is not present in the INPUT_TF_FILES, use "google_project_iam_member_remove" to remove the user(s) from the role(s).
      4. If a "google_project_iam_binding" exist for the role and member list in IAM_BINDING is not part of it, Nothing needs to be done for that role.

9. If the role is present in for loop in a "google_project_iam_binding" and any action has to be performed, create a new binding for the role and perform action while preserving the existing permissions.
10. If the role is present in for loop in a "google_project_iam_member" and any action has to be performed, create a new binding for the role and perform action while preserving the existing permissions.
11. Ensure that no new permissions are being assigned or removed to any user other than asked in IAM_BINDING field.
12. **Update the file**: Update the file(s) as per information in IAM Binding.
13. **Test the file**: Test the file(s) to ensure that the changes made are correct.
    """
    return self._binding_prompt_format
