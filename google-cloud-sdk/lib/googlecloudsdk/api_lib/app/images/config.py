# Copyright 2014 Google Inc. All Rights Reserved.

"""Magic constants for images module."""

# The version of the docker API the docker-py client uses.
# Warning: other versions might have different return values for some functions.
DOCKER_PY_VERSION = '1.18'

# Timeout of HTTP request from docker-py client to docker daemon, in seconds.
DOCKER_D_REQUEST_TIMEOUT = 300

DOCKER_IMAGE_NAME_FORMAT = '{display}.{module}.{version}'
DOCKER_IMAGE_NAME_DOMAIN_FORMAT = '{domain}.{display}.{module}.{version}'

# Name of the a Dockerfile.
DOCKERFILE = 'Dockerfile'

# A map of runtimes values if they need to be overwritten to match our
# base Docker images naming rules.
CANONICAL_RUNTIMES = {'java7': 'java'}
