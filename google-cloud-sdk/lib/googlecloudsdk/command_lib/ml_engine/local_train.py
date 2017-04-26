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
"""Utilities for running training jobs locally."""
import atexit
import json
import os
import subprocess

from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log


def MakeProcess(module_name,
                package_root,
                args=None,
                cluster=None,
                task_type=None,
                index=None,
                **extra_popen_args):
  """Make a Popen object that runs the module, with the correct env.

  If task_type is 'master' instead replaces the current process with the
  subprocess via execution_utils.Exec
  Args:
    module_name: str. Name of the module to run, e.g. trainer.task
    package_root: str. Absolute path to the package root for the module.
      used as CWD for the subprocess.
    args: [str]. Additional user args. Any relative paths will not work.
    cluster: dict. Cluster configuration dictionary. Suitable for passing to
      tf.train.ClusterSpec.
    task_type: str. Task type of this process. Only relevant if cluster is
      specified.
    index: int. Task index of this process.
    **extra_popen_args: extra args passed to Popen. Used for testing.
  Returns:
    a subprocess.Popen object corresponding to the subprocesses or an int
    corresponding to the return value of the subprocess
    (if task_type is 'master')
  """
  if args is None:
    args = []
  python = execution_utils.GetPythonExecutable()
  cmd = [python, '-m', module_name] + args
  config = {
      'job': {'job_name': module_name, 'args': args},
      'task': {'type': task_type, 'index': index} if cluster else {},
      'cluster': cluster or {},
      'environment': 'cloud'
  }
  log.info(('launching training process:\n'
            'command: {cmd}\n config: {config}').format(
                cmd=' '.join(cmd),
                config=json.dumps(config, indent=2, sort_keys=True)))

  env = os.environ.copy()
  # the tf_config environment variable is used to pass the tensorflow
  # configuration options to the training module. the module specific
  # arguments are passed as comand line arguments.
  env['TF_CONFIG'] = json.dumps(config)
  if task_type == 'master':
    return execution_utils.Exec(
        cmd, env=env, no_exit=True, cwd=package_root, **extra_popen_args)
  else:
    task = subprocess.Popen(
        cmd,
        env=env,
        cwd=package_root,
        **extra_popen_args
    )
    atexit.register(execution_utils.KillSubprocess, task)
    return task


def RunDistributed(module_name,
                   package_root,
                   num_ps,
                   num_workers,
                   start_port,
                   user_args=None):
  """Create a cluster configuration and start processes for the cluster.

  Args:
    module_name: str. Python module to use as the task.
    package_root: str. Absolute path to the package root of the module.
    num_ps: int. Number of parameter servers
    num_workers: int. Number of workers.
    start_port: int. First port for the contiguous block of ports used
      by the cluster.
    user_args: [str]. Additional user args for the task. Any relative paths will
      not work.
  Returns:
    int. the retval of 'master' subprocess
  """
  ports = range(start_port, start_port + num_ps + num_workers + 1)
  cluster = {
      'master': ['localhost:{port}'.format(port=ports[0])],
      'ps': ['localhost:{port}'.format(port=p)
             for p in ports[1:num_ps + 1]],
      'worker': ['localhost:{port}'.format(port=p)
                 for p in ports[num_ps + 1:]]
  }
  for task_type, addresses in cluster.items():
    if task_type != 'master':
      for i in range(len(addresses)):
        MakeProcess(module_name,
                    package_root,
                    args=user_args,
                    task_type=task_type,
                    index=i,
                    cluster=cluster)
  return MakeProcess(module_name,
                     package_root,
                     args=user_args,
                     task_type='master',
                     index=0,
                     cluster=cluster)
