# -*- coding: utf-8 -*-
"""
setup.py - boilerplate
"""
import sys
from setuptools import setup
from setuptools.command.test import test as TestCommand

class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to pytest")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def run_tests(self):
        import shlex
        import pytest

        if not self.pytest_args:
            targs = []
        else:
            targs = shlex.split(self.pytest_args)

        errno = pytest.main(targs)
        sys.exit(errno)

def readme():
    with open('README.md') as f:
        return f.read()

INSTALL_REQUIRES = [
    'numpy',
    'scipy',
    'astropy',
    'matplotlib',
]

EXTRAS_REQUIRE = {
    'all':[
        'cdips',
        'gyrointerp',
        'aesthetic'
    ]
}

###############
## RUN SETUP ##
###############

# run setup.
version = "0.0.0"
setup(
    name='pbls',
    version=version,
    description=(
        "Search for Transits in the presence of Rotation"
    ),
    long_description=readme(),
    long_description_content_type="text/markdown",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Astronomy",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ],
    keywords='astronomy',
    url='https://github.com/lgbouma/pbls',
    author='Luke Bouma',
    author_email='bouma.luke@gmail.com',
    license='MIT',
    packages=[
        'pbls',
    ],
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    tests_require=['pytest',],
    cmdclass={'test':PyTest},
    include_package_data=True,
    zip_safe=False,
)
