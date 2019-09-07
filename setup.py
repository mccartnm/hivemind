from setuptools import find_packages
from distutils.core import setup

with open('README.md') as f:
    ld = f.read()

setup(
    name='hivemind',
    version='0.0.1',
    packages=['hivemind'],
    license='MIT',
    description='Python fault tolerant micro-service ecosystem on a budget',
    author='',
    long_description=ld,
    long_description_content_type="text/markdown",
    url = 'https://github.com/mccartnm/hivemind',
    author_email='mccartneyworks@gmail.com',
    keywords=[
        'backend',
        'fault-tolerant',
        'micro-service',
        'nodes',
        'abstract'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
    ],
    install_requires=[],
)
