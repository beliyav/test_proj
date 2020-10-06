import os
from setuptools import setup, find_packages


def load_requires(extras_name=None):
    filepath = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    with open(filepath) as fp:
        return fp.read()


setup(
    name='server',
    version='1.0',
    packages=find_packages(exclude=['tests']),
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.md')).read(),
    install_requires=load_requires(),
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'run_api = server.__main__:main'
        ]
    }
)
