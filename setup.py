# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='SSOS',
    version='0.0.1',
    description='Python script to find saddest song spotify',
    long_description=readme,
    author='Markus Bilz',
    author_email='mail@markusbilz.com',
    url='https://github.com/KarelZe/SSOS',
    license=license,
    packages=find_packages(exclude='docs')
)

