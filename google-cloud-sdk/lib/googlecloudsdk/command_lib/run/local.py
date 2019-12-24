# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Library for manipulating serverless local development setup."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import yaml

_POD_AND_SERVICES_TEMPLATE = """
apiVersion: v1
kind: Pod
metadata:
  name: {service}
  labels:
    service: {service}
spec:
  containers:
  - name: {service}-container
    image: {image}
    env:
    - name: PORT
      value: "8080"
    ports:
    - containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: {service}
spec:
  type: LoadBalancer
  selector:
    service: {service}
  ports:
  - protocol: TCP
    port: 8080
    targetPort: 8080
"""


def CreatePodAndService(service_name, image_name):
  """Create a pod and service specification for a service.

  Args:
    service_name: Name of the service.
    image_name: Image tag.

  Returns:
    List of dictionary objects representing the service and image yaml.
  """
  yaml_text = _POD_AND_SERVICES_TEMPLATE.format(
      service=service_name, image=image_name)
  return yaml.load_all(yaml_text)
