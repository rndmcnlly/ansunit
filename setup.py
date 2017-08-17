#!/usr/bin/env python

from setuptools import setup

setup(name='ansunit',
      version='0.1.7',
      description='Declarative unit testing for answer set programming projects',
      author='Adam M. Smith',
      author_email='adam@adamsmith.as',
      url='https://github.com/rndmcnlly/ansunit',
      license='MIT',
      packages=['ansunit'],
      install_requires=['PyYAML'],
      entry_points={'console_scripts': { 'ansunit = ansunit:main'}}
)
