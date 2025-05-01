# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
from pathlib import Path


def setup_paths():
    """Setup project path for sphinx and verify that it's valid"""
    for idx, dir in enumerate(["../../../../python/src/acp_sdk"]):
        src_dir = Path(os.path.abspath(dir))
        if not src_dir.exists():
            raise Exception(f"Provided project directory '{src_dir}' does not exists!")

        sys.path.insert(idx, str(src_dir.absolute()))


setup_paths()


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "ACP SDK"
copyright = "2025, IBM Corp."
author = "IBM Corp."

# -- General configuration ---------------------------------ß------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.autosummary",
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "sphinx.ext.duration",
    "sphinx.ext.extlinks",
    "sphinx.ext.githubpages",
    "sphinx.ext.graphviz",
    "sphinx.ext.ifconfig",
    "sphinx.ext.imgconverter",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinxcontrib.autodoc_pydantic",
    "sphinx_toolbox.collapse",
]

napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_ivar = False

autosectionlabel_prefix_document = True
templates_path = ["_templates"]
html_sidebars = {
    "**": [
        "sidebar/brand.html",
        "sidebar/search.html",
        "sidebar/scroll-start.html",
        "sidebar/navigation.html",
        "versioning.html",
        "sidebar/scroll-end.html",
        "sidebar/variant-selector.html",
    ]
}
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autoclass_content
autoclass_content = "class"

rst_prolog = """
.. role:: sh(code)
   :language: sh
.. role:: bash(code)
   :language: bash
.. role:: fish(code)
   :language: fish
.. role:: zsh(code)
   :language: zsh
.. role:: toml(code)
   :language: toml
.. role:: python(code)
   :language: python
.. |V| unicode:: ✅ 0xA0 0xA0
   :trim:

"""
autodoc_typehints = "description"
autodoc_class_signature = "separated"
autodoc_pydantic_model_show_field_summary = False
autodoc_pydantic_model_show_json = False
autodoc_pydantic_settings_show_json = False
autodoc_mock_imports = ["transformers", "langchain", "llama-index", "localserver"]
autodoc_default_options = {"exclude-members": "__weakref__,__new__"}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
# html_theme = "alabaster"
html_static_path = ["_static"]
html_title = "ACP SDK"

html_theme_options = {
    "light_css_variables": {
        "font-stack": "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, Segoe UI, Arial, sans-serif",
        "font-stack--monospace": "'IBM Plex Mono', 'SFMono-Regular', Menlo, Consolas, Lucida Console, monospace",
    },
    "footer_icons": [
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/acp-sdk/",
            "html": """
                <svg version="1.1" xmlns="http://www.w3.org/2000/svg"  stroke="currentColor" fill="currentColor" stroke-width="0" width="16px" height="16" viewBox="0 0 512 512">
                    <path d="M454,305.8294373l-91.1191101,33.691803v106.4807434L181.94487,512V298.2970276l179.8842926-66.8633728V58.8240128L454,92.4968643V305.8294373z M276.8390503,363.3849487c-15.7174377,5.7245483-28.4572144,23.9239502-28.4515686,40.6481018c0.0061646,16.7174377,12.7523499,25.6329346,28.4636841,19.919281c15.7173462-5.7247009,28.4602051-23.9217834,28.4544983-40.6459656C305.303009,366.5810547,292.5565491,357.6635437,276.8390503,363.3849487z M334.6160889,212.4997864l-180.3925323,66.8782959l0.2966461,135.7604065l-64.2104874,22.9912415L0,405.2594604V191.9265442l90.704361-33.6917877V51.7543259L232.9717102,0l101.6443787,32.4636765V212.4997864z M215.2144775,94.8330383c-15.7174835,5.7222672-28.4621582,23.9249802-28.458725,40.6499329c0.0025787,16.725235,12.750824,25.6462555,28.4683228,19.9248505c15.7174988-5.7219086,28.4623871-23.9248047,28.4592285-40.6498184C243.6806641,98.0326996,230.9319763,89.1116333,215.2144775,94.8330383z"/>
                </svg>
            """,  # noqa: E501
            "class": "",
        },
        {
            "name": "GitHub",
            "url": "https://github.com/i-am-bee/acp",
            "html": """
                <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"></path>
                </svg>
            """,  # noqa: E501
            "class": "",
        },
    ],
}
html_css_files = ["custom.css"]
