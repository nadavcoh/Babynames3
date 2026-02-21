#!/bin/bash
# Activate venv if it exists, otherwise use system python
if [ -d "venv" ]; then
    source venv/bin/activate
fi
python app.py "$@"
