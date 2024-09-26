"""Unit tests for canned data in testdata/.
"""
import json
from pathlib import Path
import os
from unittest import TestCase

import dag_json

from ..base import Base, ValidationError


def load_file_lines(file):
  """Reads lines from a file and returns them as a set.

  Leading and trailing whitespace is trimmed. Blank lines and lines beginning
  with ``#`` (ie comments) are ignored.

  NOTE: duplicates oauth_dropins.webutil.util.load_file_lines!

  Args:
    file: a file object or other iterable that returns lines

  Returns:
    set of str
  """
  items = []

  for line in file:
    val = line.rstrip('\n')
    if val and not val.startswith('#'):
      items.append(val)

  return items


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

# valid string formats
for file in Path('.').glob('*_syntax_valid.txt'):
    for i, line in enumerate(load_file_lines(file.open())):
        def test_fn():
            format = file.name.split('_')[0]
            val = line
            def test(self):
                try:
                    Base()._validate_string_format(val, format)
                except ValidationError as e:
                    raise ValidationError(f'{val} {e.args[0]}')
            return test

        tests[test_name(f'{file.stem}_{i}')] = test_fn()

# invalid string formats
for file in Path('.').glob('*_invalid.txt'):
    for i, line in enumerate(load_file_lines(file.open())):
        def test_fn():
            format = file.name.split('_')[0]
            val = line
            def test(self):
                with self.assertRaises(ValidationError, msg=val):
                    Base()._validate_string_format(val, format)
            return test

        tests[test_name(f'{file.stem}_{i}')] = test_fn()


os.chdir(prevdir)

TestDataTest = type('TestDataTest', (TestCase,), tests)
