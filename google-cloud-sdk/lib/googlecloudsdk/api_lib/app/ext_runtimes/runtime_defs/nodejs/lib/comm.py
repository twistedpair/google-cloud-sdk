# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import sys

def _write_msg(**message):
    """Write a message to standard output.

    Args:
        **message: ({str: object, ...}) A JSON message encoded in keyword
            arguments.
    """
    json.dump(message, sys.stdout)
    sys.stdout.write('\n')
    sys.stdout.flush()


def error(message, *args):
    _write_msg(type='error', message=message % args)


def warn(message, *args):
    _write_msg(type='warn', message=message % args)


def info(message, *args):
    _write_msg(type='info', message=message % args)


def debug(message, *args):
    _write_msg(type='debug', message=message % args)


def print_status(message, *args):
    _write_msg(type='print_status', message=message % args)


def send_runtime_params(params):
    """Send runtime parameters back to the controller.

    Args:
        params: ({str: object, ...}) Set of runtime parameters.  Must be
            json-encodable.
    """
    _write_msg(type='runtime_parameters', runtime_data=params)


def get_config():
    """Request runtime parameters from the controller.

    Returns:
      (object) The runtime parameters represented as an object.
    """
    _write_msg(type='get_config')
    return dict_to_object(json.loads(sys.stdin.readline()))


def dict_to_object(json_dict):
    """Converts a dictionary to a python object.

    Converts key-values to attribute-values.

    Args:
      json_dict: ({str: object, ...})

    Returns:
      (object)
    """
    class Object(object):
        pass
    obj = Object()
    for name, val in json_dict.iteritems():
        if isinstance(val, dict):
          val = dict_to_object(val)
        setattr(obj, name, val)
    return obj


class RuntimeDefinitionRoot(object):
    """Abstraction that allows us to access files in the runtime definiton."""

    def __init__(self, path):
        self.root = path

    def read_file(self, *name):
        with open(os.path.join(self.root, *name)) as src:
            return src.read()


class FileGenerationContext(object):
    """An abstraction on top of filesystem writes.

    This is normally used from the generate_configs script.  It allows the
    script to write to either the application root directory or to gen_file
    messages depending on how it was invoked.

    Instances of FileGenerationContext are normally created with the
    CreateFromArgv() method which knows how to generate the correct object
    depending from the arg list of a generate_configs script.

    """

    @classmethod
    def create_from_argv(cls, argv):
        if len(argv) == 1:
            return _DeploymentGenerationContext()
        else:
            return _FileSysGenerationContext(sys.argv[1])

    def gen_file(self, name, contents):
        """Generate a file.

        This generates a file either to the filesystem or to an output message, as
        appropriate.

        Args:
            name: (str) the filename, relative to the root of the docker context.
            contents: (str) file contents.
        """
        raise NotImplementedError()

    def is_deploy(self):
        """Returns true (bool) if this is a deployment context."""
        raise NotImplementedError()

    def exists(self, filename):
        """Returns true if the file already exists and should not be emitted."""
        raise NotImplementedError()

    def has_generated_files(self):
        """Returns true if any files were generated."""
        raise NotImplementedError()


class _DeploymentGenerationContext(FileGenerationContext):

    def __init__(self):
        self._has_generated_files = False

    def gen_file(self, name, contents):
        _write_msg(type='gen_file', filename=name, contents=contents)

    def is_deploy(self):
        return True

    def exists(self, filename):
        # In deployment context, all generated files are temporary and are always
        # emitted.
        return False

    def has_generated_files(self):
        return self._has_generated_files


class _FileSysGenerationContext(FileGenerationContext):

    def __init__(self, root):
        self.root = root
        self._has_generated_files = False

    def gen_file(self, name, contents):
        with open(os.path.join(self.root, name), 'w') as dst:
            dst.write(contents)
        self._has_generated_files = True

    def is_deploy(self):
        return False

    def exists(self, filename):
        return os.path.exists(os.path.join(self.root, filename))

    def has_generated_files(self):
        return self._has_generated_files
