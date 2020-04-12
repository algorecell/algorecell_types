
from setuptools import setup, find_packages

NAME = 'algorecell_types'

setup(name=NAME,
    version='9999',
    author = "Loïc Paulevé",
    author_email = "loic.pauleve@labri.fr",
    url = "https://github.com/algorecell/algorecell_types",
    description = 'Generic types for reprogramming predictions from logical models',
    install_requires = [
        "colomoto_jupyter",
        "pandas",
        "pydot",
    ],
    classifiers=[
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],
    packages = find_packages()
)

