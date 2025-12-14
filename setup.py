"""
Setup script for F1 Season Calculator.

This allows installing the package in development mode with: pip install -e .
"""
from setuptools import setup

setup(
    name='F1_Season_Calculator',
    version='1.0.0',
    description='A Python-based tool to analyze Formula 1 championship scenarios',
    py_modules=['__init__', 'db', 'app'],
    packages=['championship'],
    include_package_data=True,
    install_requires=[
        'pandas',
        'Flask',
        'flasgger',
        'numpy',
        'python-dotenv',
    ],
    python_requires='>=3.6',
)
