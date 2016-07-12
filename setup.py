from setuptools import setup, find_packages
import sys

install_requires = ['boto', 'konfig', 'paramiko']
description = ''

classifiers = ["Programming Language :: Python",
               "License :: OSI Approved :: Apache Software License",
               "Development Status :: 1 - Planning"]


setup(name='lambdabuilder',
      version="0.1",
      url='https://github.com/tarekziade/boom',
      packages=find_packages(),
      long_description=description,
      description=("Tools to build & run AWS Lambdas"),
      include_package_data=True,
      zip_safe=False,
      classifiers=classifiers,
      install_requires=install_requires,
      test_suite='unittest2.collector',
      entry_points="""
      [console_scripts]
      lambdabuilder = lambdabuilder:main
      """)
