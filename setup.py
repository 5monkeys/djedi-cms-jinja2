#!/usr/bin/env python

from setuptools import setup

setup(
    name='djedi-cms-jinja2',
    version='2.0.2',
    description='Jinja variants of the Djedi template tags.',
    author='Christopher Rosell',
    author_email="chrippa@tanuki.se",
    license='BSD',
    py_modules=['djedi_jinja'],
    install_requires=['jinja2', 'djedi-cms'],
)
