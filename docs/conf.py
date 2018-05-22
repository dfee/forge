#!/usr/bin/env python3

import os
import sys

import pkg_resources


sys.path.insert(0, os.path.abspath('..'))

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx_autodoc_typehints',
    'sphinx_paramlinks',
]

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = 'forge'
author = 'Devin Fee'
copyright = '2018, ' + author  # pylint: disable=W0622, redefined-builtin

v = pkg_resources.get_distribution('forge').parsed_version
version = v.base_version  # type: ignore
release = v.public  # type: ignore

language = None

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
pygments_style = 'sphinx'
highlight_language = 'python3'

html_logo = "_static/forge-vertical.png"
html_theme = "alabaster"
html_theme_options = {
    "font_family": '"Avenir Next", Calibri, "PT Sans", sans-serif',
    "head_font_family": '"Avenir Next", Calibri, "PT Sans", sans-serif',
    "font_size": "16px",
    "page_width": "980px",
}

html_static_path = ['_static']
htmlhelp_basename = 'forgedoc'