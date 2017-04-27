#!/usr/bin/env python

from distutils.core import setup

setup(name='ansunit',
      version='0.1.4',
      description='Declarative unit testing for answer set programming projects',
      author='Adam M. Smith',
      author_email='adam@adamsmith.as',
      url='https://github.com/rndmcnlly/ansunit',
      license='MIT',
      py_modules=['ansunit'],
      install_requires=['PyYAML'],
     )
