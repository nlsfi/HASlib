#!/bin/bash
pip uninstall galileo-has-decoder
python setup.py bdist_wheel
pip install dist/galileo_has_decoder-1.0.2-py3-none-any.whl
