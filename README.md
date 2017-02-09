# pytest-check-links

pytest plugin that checks URLs for HTML-containing files.

Supported files:

- .html
- .md (TODO: select renderer)
- .ipynb (requires nbconvert)

Install:

    pip install pytest-check-links

Use:

    pytest --check-links mynotebook.ipynb


TODO:

- pick a markdown renderer (probably commonmark) or make the markdown renderer pluggable
- options for validating links (allow absolute links, only remote or local, etc.)
- check internal links (`#anchors`)
- find URLs in Python docstrings
- test myself, obvs!
