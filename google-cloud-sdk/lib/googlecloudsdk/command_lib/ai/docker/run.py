# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Functions required to interact with Docker to run a container."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.ai import errors
from googlecloudsdk.command_lib.ai import local_util
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files


def _DockerRunOptions(enable_gpu=False,
                      container_home_to_mount=None,
                      extra_run_opts=None):
  """Returns a list of 'docker run' options.

  Args:
    enable_gpu: (bool) using GPU or not
    container_home_to_mount: (str) $HOME directory in the container
    extra_run_opts: (List[str]) other custom docker run options
  """
  if extra_run_opts is None:
    extra_run_opts = []

  runtime = ["--runtime", "nvidia"] if enable_gpu else []

  mount = []
  if container_home_to_mount is not None:
    mount = ["-v", "{}:{}".format(files.GetHomeDir(), container_home_to_mount)]

  return ["--rm"] + runtime + mount + ["--ipc", "host"] + extra_run_opts


def RunContainer(image, enable_gpu=False, run_args=None, user_args=None):
  """Calls `docker run` on a given image with specified arguments.

  Args:
    image: (Image) Represents the image to run, containing info like image name,
      home directory, entrypoint etc.
    enable_gpu: (bool) Whether to use GPU
    run_args: (List[str]) Extra custom options to apply to `docker run` after
      our defaults.
    user_args: (List[str]) Extra user defined arguments to supply to the
      entrypoint.

  Raises:
    DockerError: An error occurred when executing `docker run`
  """
  # TODO(b/177787660): add interactive mode option

  if run_args is None:
    run_args = []

  if user_args is None:
    user_args = []

  run_opts = _DockerRunOptions(enable_gpu, image.default_home, run_args)

  command = ["docker", "run"] + run_opts + [image.name] + user_args

  command_str = " ".join(command)
  log.info("Running command: {}".format(command_str))

  return_code = local_util.ExecuteCommand(command)
  if return_code != 0:
    error_msg = """
        Docker failed with error code {code}.
        Command: {cmd}
        """.format(
            code=return_code, cmd=command_str)
    raise errors.DockerError(error_msg, command, return_code)
