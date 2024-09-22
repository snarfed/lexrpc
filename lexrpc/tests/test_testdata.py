"""Unit tests for canned data in testdata/.
"""
import json
from pathlib import Path
import os
from unittest import TestCase

from ..base import Base, ValidationError


# All test data files live in testdata/.
prevdir = os.getcwd()
os.chdir(os.path.join(os.path.dirname(__file__), 'testdata/'))

lexicons = [json.load(f.open()) for f in Path('catalog').iterdir()]
base = Base(lexicons=lexicons)

tests = {}

def test_name(input):
  return 'test_' + input['name'].replace(' ', '_')


for input in json.load(Path('record-data-valid.json').open()):
    def test(self):
        # shouldn't raise
        base._maybe_validate(input['data']['$type'], 'record', input['data'])
    tests[test_name(input)] = test

for input in json.load(Path('record-data-invalid.json').open()):
    def test(self):
        with self.assertRaises(ValidationError):
            base._maybe_validate(input['data']['$type'], 'record', input['data'])
    tests[test_name(input)] = test


os.chdir(prevdir)

TestDataTest = type('TestDataTest', (TestCase,), tests)
