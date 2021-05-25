# Lint as: python3
# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Helpers for create commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.privateca import base as privateca_base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.privateca import flags_v1
from googlecloudsdk.command_lib.privateca import resource_args
from googlecloudsdk.command_lib.util.args import labels_util


def _ParseCAResourceArgs(args):
  """Parses, validates and returns the resource args from the CLI.

  Args:
    args: The parsed arguments from the command-line.

  Returns:
    Tuple containing the Resource objects for (CA, source CA, issuer).
  """
  resource_args.ValidateResourceIsCompleteIfSpecified(args, 'kms_key_version')
  resource_args.ValidateResourceIsCompleteIfSpecified(args, 'issuer')
  resource_args.ValidateResourceIsCompleteIfSpecified(args, 'from_ca')

  ca_ref = args.CONCEPTS.certificate_authority.Parse()

  resource_args.ValidateResourceLocation(
      ca_ref, 'CERTIFICATE_AUTHORITY', version='v1')

  kms_key_version_ref = args.CONCEPTS.kms_key_version.Parse()
  if kms_key_version_ref and ca_ref.locationsId != kms_key_version_ref.locationsId:
    raise exceptions.InvalidArgumentException(
        '--kms-key-version',
        'KMS key must be in the same location as the Certificate Authority '
        '({}).'.format(ca_ref.locationsId))

  issuer_ref = args.CONCEPTS.issuer.Parse() if hasattr(args, 'issuer') else None
  source_ca_ref = args.CONCEPTS.from_ca.Parse()

  if source_ca_ref and source_ca_ref.Parent().RelativeName() != ca_ref.Parent(
  ).RelativeName():
    raise exceptions.InvalidArgumentException(
        '--from-ca',
        'The provided source CA must be a part of the same pool as the specified CA to be created.'
    )

  return (ca_ref, source_ca_ref, issuer_ref)


def CreateCAFromArgs(args, is_subordinate):
  """Creates a GA CA object from CA create flags.

  Args:
    args: The parser that contains the flag values.
    is_subordinate: If True, a subordinate CA is returned, otherwise a root CA.

  Returns:
    A tuple for the CA to create with (CA object, CA ref, issuer).
  """

  client = privateca_base.GetClientInstance(api_version='v1')
  messages = privateca_base.GetMessagesModule(api_version='v1')

  ca_ref, source_ca_ref, issuer_ref = _ParseCAResourceArgs(args)
  pool_ref = ca_ref.Parent()
  source_ca = None

  if source_ca_ref:
    source_ca = client.projects_locations_caPools_certificateAuthorities.Get(
        messages
        .PrivatecaProjectsLocationsCaPoolsCertificateAuthoritiesGetRequest(
            name=source_ca_ref.RelativeName()))
    if not source_ca:
      raise exceptions.InvalidArgumentException(
          '--from-ca', 'The provided source CA could not be retrieved.')

  ca_pool = client.projects_locations_caPools.Get(
      messages.PrivatecaProjectsLocationsCaPoolsGetRequest(
          name=pool_ref.RelativeName()))

  keyspec = flags_v1.ParseKeySpec(args)
  if ca_pool.tier == messages.CaPool.TierValueValuesEnum.DEVOPS and keyspec.cloudKmsKeyVersion:
    raise exceptions.InvalidArgumentException(
        '--kms-key-version',
        'The DevOps tier does not support user-specified KMS keys.')

  subject_config = messages.SubjectConfig(
      subject=messages.Subject(), subjectAltName=messages.SubjectAltNames())
  if args.IsSpecified('subject'):
    subject_config.subject = flags_v1.ParseSubject(args)
  elif source_ca:
    subject_config.subject = source_ca.config.subjectConfig.subject

  if flags_v1.SanFlagsAreSpecified(args):
    subject_config.subjectAltName = flags_v1.ParseSanFlags(args)
  elif source_ca:
    subject_config.subjectAltName = source_ca.config.subjectConfig.subjectAltName
  flags_v1.ValidateSubjectConfig(subject_config, is_ca=True)

  # Populate x509 params to default.
  x509_parameters = flags_v1.ParseX509Parameters(args, is_ca_command=True)
  if source_ca and not flags_v1.X509ConfigFlagsAreSpecified(args):
    x509_parameters = source_ca.config.x509Config

  # Args.validity will be populated to default if not specified.
  lifetime = flags_v1.ParseValidityFlag(args)
  if source_ca and not args.IsSpecified('validity'):
    lifetime = source_ca.lifetime

  labels = labels_util.ParseCreateArgs(
      args, messages.CertificateAuthority.LabelsValue)

  new_ca = messages.CertificateAuthority(
      type=messages.CertificateAuthority.TypeValueValuesEnum.SUBORDINATE
      if is_subordinate else
      messages.CertificateAuthority.TypeValueValuesEnum.SELF_SIGNED,
      lifetime=lifetime,
      config=messages.CertificateConfig(
          subjectConfig=subject_config, x509Config=x509_parameters),
      keySpec=keyspec,
      gcsBucket=None,
      labels=labels)

  return (new_ca, ca_ref, issuer_ref)


def ValidateIssuingCA(ca_name):
  """Checks that a CA is valid to be issuing Certificate Authority for a subordinate.

  Args:
    ca_name: The resource name of the issuing Certificate Authority.

  Raises:
    InvalidArgumentException if the CA does not exist or is not enabled.
  """
  try:
    client = privateca_base.GetClientInstance(api_version='v1')
    messages = privateca_base.GetMessagesModule(api_version='v1')
    ca = client.projects_locations_caPools_certificateAuthorities.Get(
        messages
        .PrivatecaProjectsLocationsCaPoolsCertificateAuthoritiesGetRequest(
            name=ca_name))
    if ca.state != messages.CertificateAuthority.StateValueValuesEnum.ENABLED:
      raise exceptions.InvalidArgumentException(
          '--issuer',
          'The issuing Certificate Authority [{}] is not in ENABLED state. Please enable it and try again.'
          .format(ca_name))
  except apitools_exceptions.HttpNotFoundError:
    raise exceptions.InvalidArgumentException(
        '--issuer',
        'The issuing Certificate Authority [{}] was not found. Please verify this information is correct and try again.'
        .format(ca_name))
