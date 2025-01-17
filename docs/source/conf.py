# Configuration file for the Sphinx documentation builder.

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
import mock
from sphinx_gallery.sorting import FileNameSortKey

sys.path.insert(0, os.path.abspath('../../..'))
sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('../../mowl'))
sys.path.insert(0, os.path.abspath('../../gateway/src/main/scala/org'))
# -- Project information

project = 'MOWL'
copyright = '2021, BORG'
author = 'BORG'

release = '0.1.0'
version = '0.1.0'
# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx_gallery.gen_gallery',
#    'IPython.sphinxext.ipython_console_highlighting'
]

examples_dirs = [
    '../../examples/'
]

gallery_dirs = [
    'examples/']

sphinx_gallery_conf = {
    'examples_dirs': examples_dirs,   # path to your example scripts
    'gallery_dirs': gallery_dirs,  # path to where to save gallery generated output

    "within_subsection_order": FileNameSortKey
}

autodoc_member_order = 'bysource'


intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}

intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# -- Options for HTML output

html_theme = 'sphinx_rtd_theme'

# -- Options for EPUB output
epub_show_urls = 'footnote'

#html_logo = 'mowl-logo.jpg'
html_logo = 'mowl_white_background_colors_2048x2048px.png'
#html_logo = 'mowl_black_background_colors_2048x2048px.png'


# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
source_suffix = ['.rst', '.md']

# The master toctree document.
master_doc = 'index'

autodoc_mock_imports = ['org', 'uk', 'java', 'numpy', 'jpype', 'de', 'pandas', 'scipy', 'sklearn', 'owlready2', 'gensim', 'torch', 'rdflib', 'networkx', 'pykeen', 'node2vec', 'matplotlib', 'tqdm', 'click']
