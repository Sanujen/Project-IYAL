# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Project IYAL'
copyright = '2025, Sanujen Premkumar, Sathveegan Yogendrarajah, Nisanthan Sivarasa'
author = 'Sanujen Premkumar, Sathveegan Yogendrarajah, Nisanthan Sivarasa'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",      # Automatically generates docs from docstrings
    "sphinx.ext.napoleon",     # Supports Google- and NumPy-style docstrings
    "sphinx.ext.viewcode",     # Adds links to source code
    "sphinx_autodoc_typehints"  # Parses Python type hints
]

templates_path = ['_templates']
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ['_static']

import os
import sys
sys.path.insert(0, os.path.abspath("../../"))