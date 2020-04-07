#!/usr/bin/env python

from setuptools import setup

# This repository uses pbr - Python Build Reasonableness
# https://docs.openstack.org/pbr/latest/
# The version is set by the current git tag + describe status.
# The rest of the config data is in setup.cfg
setup(
    setup_requires=['pbr>=1.9', 'setuptools>=17.1'],
    pbr=True,
)
