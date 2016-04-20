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

"""Debug resource transforms and symbols dict.

NOTICE: Each TransformFoo() method is the implementation of a foo() transform
function. Even though the implementation here is in Python the usage in resource
projection and filter expressions is language agnostic. This affects the
Pythonicness of the Transform*() methods:
  (1) The docstrings are used to generate external user documentation.
  (2) The method prototypes are included in the documentation. In particular the
      prototype formal parameter names are stylized for the documentation.
  (3) The types of some args, like r, are not fixed until runtime. Other args
      may have either a base type value or string representation of that type.
      It is up to the transform implementation to silently do the string=>type
      conversions. That's why you may see e.g. int(arg) in some of the methods.
  (4) Unless it is documented to do so, a transform function must not raise any
      exceptions. The `undefined' arg is used to handle all unusual conditions,
      including ones that would raise exceptions.
"""


def TransformShortStatus(r, undefined=''):
  """Returns a short description of the status of a logpoint or snapshot.

  Status will be one of ACTIVE, COMPLETED, or a short error description. If
  the status is an error, there will be additional information available in the
  status field of the object.

  Args:
    r: a JSON-serializable object
    undefined: Returns this value if the resource is not a valid status.

  Returns:
    One of ACTIVE, COMPLETED, or an error description.

  Example:
    --format="table(id, location, short_status()())"
  """
  if isinstance(r, dict):
    if not r.get('isFinalState'):
      return 'ACTIVE'
    status = r.get('status')
    if not status or not isinstance(status, dict) or not status.get('isError'):
      return 'COMPLETED'
    refers_to = status.get('refersTo')
    if refers_to:
      return '{0}_ERROR'.format(refers_to)
  return undefined

_TRANSFORMS = {
    'short_status': TransformShortStatus,
}


def GetTransforms():
  """Returns the debug specific resource transform symbol table."""
  return _TRANSFORMS
