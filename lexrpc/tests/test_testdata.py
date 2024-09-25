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

def test_name(name):
  return 'test_' + name.replace(' ', '_')


# valid records
for input in dag_json.decode(Path('record-data-valid.json').read_bytes(),
                             dialect='atproto'):
    def test_fn():
        data = input['data']
        def test(self):
          # shouldn't raise
          base.maybe_validate(data['$type'], 'record', data)
        return test

    tests[test_name('record_valid_' + input['name'])] = test_fn()

# invalid records
for input in dag_json.decode(Path('record-data-invalid.json').read_bytes(),
                                  dialect='atproto'):
    def test_fn():
        data = input['data']
        def test(self):
            with self.assertRaises(ValidationError):
                base.maybe_validate(data['$type'], 'record', data)
        return test

    tests[test_name('record_invalid_' + input['name'])] = test_fn()

# valid lexicons
for input in json.load(Path('lexicon-valid.json').open()):
    def test_fn():
        lexicon = input['lexicon']
        def test(self):
          # shouldn't raise
          Base([lexicon])
        return test

    tests[test_name('lexicon_valid_' + input['name'])] = test_fn()

# invalid lexicons
for input in json.load(Path('lexicon-invalid.json').open()):
    def test_fn():
        lexicon = input['lexicon']
        def test(self):
            with self.assertRaises(ValidationError):
                Base([lexicon])
        return test

    tests[test_name('lexicon_invalid_' + input['name'])] = test_fn()


os.chdir(prevdir)

TestDataTest = type('TestDataTest', (TestCase,), tests)
