"""
Sphinx configuration file for nucmass documentation.
"""

import os
import sys

# Add source directory to path for autodoc
sys.path.insert(0, os.path.abspath("../src"))

# -- Project information -----------------------------------------------------
project = "nucmass"
copyright = "2024-2026, Nuclear Mass Toolkit Contributors"
author = "Nuclear Mass Toolkit Contributors"
version = "1.1.0"
release = "1.1.0"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
]

# Napoleon settings for Google/NumPy style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_use_param = True
napoleon_use_rtype = True

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "undoc-members": True,
    "show-inheritance": True,
}
autodoc_typehints = "description"

# Autosummary settings
autosummary_generate = True

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}

# Templates and static files
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
html_theme = "alabaster"
html_static_path = ["_static"]

# Alabaster theme options
html_theme_options = {
    "description": "Nuclear Mass Data Toolkit for Researchers",
    "github_user": "unixtime",
    "github_repo": "nucmass",
    "github_button": True,
    "github_type": "star",
    "fixed_sidebar": True,
    "sidebar_collapse": True,
}

html_sidebars = {
    "**": [
        "about.html",
        "navigation.html",
        "relations.html",
        "searchbox.html",
    ]
}

# -- Extension configuration -------------------------------------------------
# MathJax configuration for rendering equations
mathjax3_config = {
    "tex": {
        "macros": {
            "keV": r"\text{keV}",
            "MeV": r"\text{MeV}",
        }
    }
}
