# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='mikegraph',
    version='2.0.0',
    description='Python toolkit for hydraulic network analysis and catchment modeling with MIKE+ databases',
    url='https://github.com/enielsen93/mikegraph',
    author='Emil Nielsen',
    author_email='enielsen93@hotmail.com',
    license='BSD 2-clause',
    packages=['mikegraph'],
    install_requires=['networkx', 'numpy', 'pandas'],
    dependency_links=[
        'https://github.com/enielsen93/networker/tarball/master',
    ],

    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',  
        'Operating System :: POSIX :: Linux',        
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
)