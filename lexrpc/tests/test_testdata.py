"""Unit tests for canned data in testdata/.
"""
import json
from pathlib import Path
import os
from unittest import TestCase

import dag_json

from ..base import Base, ValidationError


# All test data files live in testdata/.
prevdir = os.getcwd()
os.chdir(os.path.join(os.path.dirname(__file__), 'testdata/'))

lexicons = [json.load(f.open()) for f in Path('catalog').iterdir()]
base = Base(lexicons=lexicons)

tests = {}

def test_name(input):
  return 'test_' + input['name'].replace(' ', '_')


for input in dag_json.decode(Path('record-data-valid.json').read_bytes(),
                             dialect='atproto'):
    def test_fn():
        data = input['data']
        # shouldn't raise
        return lambda self: base.maybe_validate(data['$type'], 'record', data)

    tests[test_name(input)] = test_fn()

for input in dag_json.decode(Path('record-data-invalid.json').read_bytes(),
                                  dialect='atproto'):
    def test_fn():
        data = input['data']
        def test(self):
            with self.assertRaises(ValidationError):
                base.maybe_validate(data['$type'], 'record', data)
        return test

    tests[test_name(input)] = test_fn()


os.chdir(prevdir)

TestDataTest = type('TestDataTest', (TestCase,), tests)
