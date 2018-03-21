# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Session Dumper."""

from __future__ import absolute_import
from __future__ import division
import abc
import copy
import io
import json
import random
import sys

from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_attr_os
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.resource import yaml_printer
from googlecloudsdk.core.util import files

import six
from six.moves import builtins
from six.moves import StringIO


class _Mock(object):
  """A class to mock and unmock a function."""

  def __init__(self, target, function, new=None, return_value=None):
    if new is None:
      new = lambda *args, **kwargs: return_value
    self._target = target
    self._function = function
    self._real_function = getattr(target, function)
    self._new = new

  def Start(self):
    setattr(self._target, self._function, self._new)

  def Stop(self):
    setattr(self._target, self._function, self._real_function)


class _StreamCapturerBase(io.IOBase):
  """A base class for input/output stream capturers."""

  def __init__(self, real_stream):
    self._real_stream = real_stream
    self._capturing_stream = StringIO()

  def isatty(self, *args, **kwargs):
    return True

  def flush(self):
    self._capturing_stream.flush()
    self._real_stream.flush()

  def GetValue(self):
    return self._capturing_stream.getvalue()


class OutputStreamCapturer(_StreamCapturerBase):
  """A file-like object that captures all the information wrote to stream."""

  def write(self, *args, **kwargs):
    self._capturing_stream.write(*args, **kwargs)
    self._real_stream.write(*args, **kwargs)

  def writelines(self, *args, **kwargs):
    self._capturing_stream.writelines(*args, **kwargs)
    self._real_stream.writelines(*args, **kwargs)


class InputStreamCapturer(_StreamCapturerBase):
  """A file-like object that captures all the information read from stream."""

  def read(self, *args, **kwargs):
    result = self._real_stream.read(*args, **kwargs)
    self._capturing_stream.write(result)
    return result

  def readline(self, *args, **kwargs):
    result = self._real_stream.readline(*args, **kwargs)
    self._capturing_stream.writelines([result])
    return result

  def readlines(self, *args, **kwargs):
    result = self._real_stream.readline(*args, **kwargs)
    self._capturing_stream.writelines(result)
    return result


@six.add_metaclass(abc.ABCMeta)
class FileIoCapturerBase(object):  # pytype: disable=ignored-abstractmethod
  """A base class to capture fileIO."""

  def __init__(self):
    self._outputs = []
    self._private_outputs = []
    self._real_open = builtins.open
    self._real_private = files.OpenForWritingPrivate
    self._mocks = (
        _Mock(builtins, 'open', new=self.Open),
        _Mock(files, 'OpenForWritingPrivate', new=self.OpenForWritingPrivate),
    )

  def Mock(self):
    for m in self._mocks:
      m.Start()

  @abc.abstractmethod
  def Open(self, name, mode='r', buffering=-1):
    pass

  @abc.abstractmethod
  def OpenForWritingPrivate(self, path, binary=False):
    pass

  def Unmock(self):
    for m in self._mocks:
      m.Stop()

  def GetOutputs(self):
    return self._GetResult(self._outputs)

  def GetPrivateOutputs(self):
    return self._GetResult(self._private_outputs)

  @staticmethod
  def _GetResult(array):
    result = []
    for f in array:
      f['capturer'].flush()
      result.append({
          'name': f['name'],
          'content': f['capturer'].GetValue() if hasattr(
              f['capturer'], 'GetValue') else f['capturer'].getvalue()
      })
    return result

  @staticmethod
  def _ShouldCaptureFile(name, frame):
    if name == properties.VALUES.core.capture_session_file.Get():
      return False
    if name.endswith('.py'):
      if frame.f_code.co_name in ('updatecache',):
        return False
    return True

  @staticmethod
  def _Save(array, name, capturer):
    array.append({'name': name, 'capturer': capturer})


class FileIoCapturer(FileIoCapturerBase):
  """A class to capture all the fileIO of the session."""

  def __init__(self):
    super(FileIoCapturer, self).__init__()
    self._inputs = []
    self.Mock()

  def Open(self, name, mode='r', buffering=-1):
    if not self._ShouldCaptureFile(name, sys._getframe().f_back):  # pylint: disable=protected-access
      return self._real_open(name, mode, buffering)
    if 'w' in mode:
      capturer = OutputStreamCapturer(self._real_open(name, mode, buffering))
      self._Save(self._outputs, name, capturer)
    else:
      capturer = InputStreamCapturer(self._real_open(name, mode, buffering))
      self._Save(self._inputs, name, capturer)
    return capturer

  def OpenForWritingPrivate(self, path, binary=False):
    capturer = OutputStreamCapturer(self._real_private(path, binary))
    self._Save(self._private_outputs, path, capturer)
    return capturer

  def GetInputs(self):
    return self._GetResult(self._inputs)


@six.add_metaclass(abc.ABCMeta)
class _StateMock(object):  # pytype: disable=ignored-abstractmethod
  """A class to represent a simple mock."""

  def __init__(self, default_value):
    self.default_value = default_value

  @abc.abstractmethod
  def Capture(self):
    pass

  @abc.abstractmethod
  def Mock(self, test, value):
    pass


class _FunctionStateMock(_StateMock):
  """A class to mock a call to some function."""

  def __init__(self, target, func, default_value):
    super(_FunctionStateMock, self).__init__(default_value)
    self._func_to_call = getattr(target, func)  # pylint: disable=invalid-name
    self._target = target
    self._func = func

  def Capture(self):
    return self._func_to_call()

  def Mock(self, test, value):
    test.StartObjectPatch(self._target, self._func, return_value=value)


class _RandomStateMock(_StateMock):
  """A class to mock random."""

  def __init__(self):
    super(_RandomStateMock, self).__init__(0)

  def Capture(self):
    # Create a new unique random seed: the state is different each run and
    # hashes will be different with high probability
    random_seed = hash(random.getstate())
    random.seed(random_seed)
    return random_seed

  def Mock(self, unused_test, value):
    random.seed(value)


class classproperty(object):  # pylint: disable=invalid-name
  """Decorator that can be used to make @classmethod like @properties."""

  def __init__(self, property_fn):
    self.fget = property_fn

  def __get__(self, unused_instance, typ):
    return self.fget(typ)


def GetHttpRequestDict(uri, method, body, headers):
  return {
      'uri': uri,
      'method': method,
      'body': body,
      'headers': _FilterHeaders(headers)
  }


def _FilterHeaders(headers):
  return {
      k: v for k, v in six.iteritems(headers) if _KeepHeader(k)
  }


def _KeepHeader(header):
  if header.startswith(b'x-google'):
    return False
  if header in (b'user-agent', b'Authorization', b'content-length',):
    return False
  return True


class SessionCapturer(object):
  """Captures the session to file."""
  capturer = None  # is SessionCapturer if session is being captured

  def __init__(self, capture_streams=True):
    self._records = []
    self._interactive_ux_style = (
        properties.VALUES.core.interactive_ux_style.Get())
    properties.VALUES.core.interactive_ux_style.Set(
        properties.VALUES.core.InteractiveUXStyles.TESTING.name)
    self._disable_color = properties.VALUES.core.disable_color.Get()
    properties.VALUES.core.disable_color.Set(True)
    if capture_streams:
      self._streams = (OutputStreamCapturer(sys.stdout),
                       OutputStreamCapturer(sys.stderr),)
      sys.stdout, sys.stderr = self._streams  # pylint: disable=unpacking-non-sequence
      log.Reset(*self._streams)
      self._stdin = InputStreamCapturer(sys.stdin)
      sys.stdin = self._stdin
      self._fileio = FileIoCapturer()
    else:
      self._streams = None
      self._stdin = None
      self._fileio = None

  def CaptureHttpRequest(self, uri, method, body, headers):
    self._records.append({
        'request': GetHttpRequestDict(uri, method, body, headers)
    })

  def CaptureHttpResponse(self, response, content):
    self._records.append({
        'response': {
            'response': _FilterHeaders(response),
            'content': self._ToList(six.text_type(content))
        }})

  def CaptureArgs(self, args):
    """Captures command line args."""
    specified_args = {}
    command = args.command_path[1:]
    for k, v in six.iteritems(args.GetSpecifiedArgs()):
      if not k.startswith('--'):
        if isinstance(v, six.string_types):
          command.append(v)
        elif isinstance(v, list):
          command += v
        else:
          raise Exception('Unknown args type {}'.format(type(v)))
      elif k != '--capture-session-file':
        specified_args[k] = v
    self._records.append({
        'args': {
            'command': ' '.join(command),
            'specified_args': specified_args
        }
    })

  _STATE_MOCKS = None

  @classproperty
  def STATE_MOCKS(cls):  # pylint: disable=invalid-name
    if cls._STATE_MOCKS is None:
      cls._STATE_MOCKS = {
          'interactive_console': _FunctionStateMock(
              console_io, 'IsInteractive', False),
          'random_seed': _RandomStateMock(),
          'term_size': _FunctionStateMock(
              console_attr_os, 'GetTermSize', (80, 24))
      }
    return cls._STATE_MOCKS

  def CaptureState(self):
    state = {}
    for k, v in six.iteritems(self.STATE_MOCKS):
      result = v.Capture()
      if result != v.default_value:
        state[k] = result
    self._records.append({
        'state': state
    })

  def CaptureProperties(self, all_values):
    values = copy.deepcopy(all_values)
    for k in ('capture_session_file', 'account'):
      if k in values['core']:
        values['core'].pop(k)
    self._records.append({
        'properties': values
    })

  def CaptureException(self, exc):
    self._records.append({
        'exception': {
            'type': str(type(exc)),
            'message': exc.message
        }
    })

  def Print(self, stream, printer_class=yaml_printer.YamlPrinter):
    self._Finalize()
    printer = printer_class(stream)
    for record in self._FinalizeRecords(self._records):
      printer.AddRecord(record)

  def _Finalize(self):
    """Finalize records, restore state."""
    if self._streams is not None:
      for stream in self._streams + (self._stdin,):
        stream.flush()
      self._fileio.Unmock()
      output = {}
      if self._streams[0].GetValue():
        output['stdout'] = self._streams[0].GetValue()
      if self._streams[1].GetValue():
        output['stderr'] = self._streams[1].GetValue()
      if self._fileio.GetOutputs():
        output['files'] = self._fileio.GetOutputs()
      if self._fileio.GetPrivateOutputs():
        output['private_files'] = self._fileio.GetPrivateOutputs()
      self._records.append({
          'output': output
      })
      inputs = {}
      if self._stdin.GetValue():
        inputs['stdin'] = self._stdin.GetValue()
      if self._fileio.GetInputs():
        inputs['files'] = self._fileio.GetInputs()
      self._records.insert(3, {
          'input': inputs
      })
    properties.VALUES.core.interactive_ux_style.Set(self._interactive_ux_style)
    properties.VALUES.core.disable_color.Set(self._disable_color)

  @staticmethod
  def _FinalizePrimitive(primitive):
    if (isinstance(primitive, six.text_type) or
        isinstance(primitive, six.binary_type)):
      project = properties.VALUES.core.project.Get()
      if not project:
        return primitive
      return primitive.replace(project, 'fake-project')
    elif (isinstance(primitive, (float, type(None))) or
          isinstance(primitive, six.integer_types)):
      return primitive
    else:
      raise Exception('Unknown primitive type {}'.format(type(primitive)))

  def _FinalizeRecords(self, records):
    if isinstance(records, dict):
      return {
          self._FinalizePrimitive(k):
              self._FinalizeRecords(v) for k, v in six.iteritems(records)
      }
    elif isinstance(records, (list, tuple)):
      return [
          self._FinalizeRecords(r) for r in records
      ]
    else:
      return self._FinalizePrimitive(records)

  def _ToList(self, response):
    """Transforms a response to a batch request into a list.

    The list is more human-readable than plain response as it contains
    recognized json dicts.

    Args:
      response: str, The response to be transformed.

    Returns:
      list, The result of transformation.
    """

    # Check if the whole response is json
    try:
      return [{'json': json.loads(response)}]
    except ValueError:
      pass

    result = []
    while True:
      json_content_idx = response.find('Content-Type: application/json;')
      if json_content_idx == -1:
        result.append(response)
        break
      json_start_idx = response.find(
          '\r\n\r\n{', json_content_idx) + len('\r\n\r\n')
      json_end_idx = response.find('}\n\r\n', json_start_idx) + 1
      if json_end_idx <= json_start_idx:
        result.append(response)
        break
      try:
        parts = [response[:json_start_idx],
                 {'json': json.loads(response[json_start_idx:json_end_idx])}]
      except ValueError:
        parts = [response[:json_end_idx]]
      result += parts
      response = response[json_end_idx:]
    return result
