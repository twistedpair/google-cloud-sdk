# Copyright 2015 Google Inc. All Rights Reserved.

"""Tests for the api_map_generator.py script."""

import os

from googlecloudsdk.scripts import api_map_generator
from googlecloudsdk.tests.lib import test_case


class ApiMapGeneratorTest(test_case.Base):

  def SetUp(self):
    self.client_file_infos = []
    self._AddInfo('fruits', 'orange', 'v1', 'v1', True)
    self._AddInfo('fruits', 'orange', 'v2', 'v2', False)
    self._AddInfo('fruits', 'banana', 'v2beta', 'v2beta', False)
    self._AddInfo('fruits', 'banana', 'v2_staging', 'v2', True)
    self._AddInfo('fruits', 'pear', 'v7_test', 'v7_test', True)

  def _AddInfo(self, root_path, api, version_label, version, is_default):
    info_format = ('{root_path}{sep}{api}{sep}{version_label}{sep}'
                   '{api}_{version}_client.py:{is_default}')
    info = info_format.format(root_path=root_path,
                              api=api,
                              version_label=version_label,
                              version=version,
                              is_default=is_default,
                              sep=os.sep)
    self.client_file_infos.append(info)

  def testGetAPIsMap(self):
    expected_map = {
        'orange': {
            'v1': api_map_generator.APIDef(
                'fruits.orange.v1.orange_v1_client.OrangeV1',
                'fruits.orange.v1.orange_v1_messages', True),
            'v2': api_map_generator.APIDef(
                'fruits.orange.v2.orange_v2_client.OrangeV2',
                'fruits.orange.v2.orange_v2_messages')
        },
        'banana': {
            'v2beta': api_map_generator.APIDef(
                'fruits.banana.v2beta.banana_v2beta_client.BananaV2beta',
                'fruits.banana.v2beta.banana_v2beta_messages'),
            'v2_staging': api_map_generator.APIDef(
                'fruits.banana.v2_staging.banana_v2_client.BananaV2',
                'fruits.banana.v2_staging.banana_v2_messages', True)
        },
        'pear': {
            'v7_test': api_map_generator.APIDef(
                'fruits.pear.v7_test.pear_v7_test_client.PearV7Test',
                'fruits.pear.v7_test.pear_v7_test_messages', True)
        }
    }
    actual_map = api_map_generator._GetAPIsMap(self.client_file_infos)
    self.assertEquals(expected_map, actual_map)

  def testGetAPIsMapMultipleClientsForSameAPIVersion(self):
    self._AddInfo('fruits', 'orange', 'v1', 'v1', True)

    with self.assertRaises(Exception) as exp:
      api_map_generator._GetAPIsMap(self.client_file_infos)
      self.assertEquals(str(exp), 'Multiple clients found for [orange:v1]!')

  def testGetAPIsMapMultipleDefaultsClientsForAPI(self):
    self._AddInfo('fruits', 'pear', 'v1', 'v1', True)

    with self.assertRaises(Exception) as ctx:
      api_map_generator._GetAPIsMap(self.client_file_infos)

    msg = str(ctx.exception)
    self.assertEquals(msg, 'Multiple default clients found for [pear]!')

  def testGetAPIsMapNoDefaultsClientsForAPIs(self):
    self._AddInfo('fruits', 'fig', 'v1', 'v1', False)
    self._AddInfo('fruits', 'lime', 'v2', 'v1', False)

    with self.assertRaises(Exception) as ctx:
      api_map_generator._GetAPIsMap(self.client_file_infos)

    msg = str(ctx.exception)
    self.assertEquals(msg, 'No default clients found for [fig, lime]!')


if __name__ == '__main__':
  test_case.main()
