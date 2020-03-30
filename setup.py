#!/usr/bin/env python

from setuptools import setup

# This repository uses pbr - Python Build Reasonableness
# The version is set by the current git tag + describe status.
setup(
    setup_requires=['pbr>=1.9', 'setuptools>=17.1'],
    pbr=True,
)
