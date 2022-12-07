"""setuptools setup module for lexrpc.

Docs: https://lexrpc.readthedocs.io/
"""
from setuptools import setup, find_packages


setup(name='lexrpc',
      version='0.0.0',
      description="Python implementation of AT Protocol's XRPC + Lexicon",
      long_description=open('README.md').read(),
      long_description_content_type='text/markdown',
      url='https://github.com/snarfed/lexrpc',
      packages=find_packages(),
      author='Ryan Barrett',
      author_email='lexrpc@ryanb.org',
      license='Public domain',
      python_requires='>=3.6',
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'Environment :: Web Environment',
          'License :: OSI Approved :: MIT License',
          'License :: Public Domain',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10',
          'Programming Language :: Python :: 3.11',
          'Topic :: Software Development :: Libraries :: Python Modules',
      ],
      keywords=['XRPC', 'Lexicon', 'AT Protocol', 'ATP'],
      install_requires=[
          'requests>=2.0',
      ],
)
