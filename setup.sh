#!/bin/bash
# שם טוב — setup script
set -e
echo "Setting up שם טוב..."
python3 -m venv venv
venv/bin/pip install -r requirements.txt
echo ""
echo "Done! Run with:"
echo "  venv/bin/python app.py"
echo ""
echo "Or for network access:"
echo "  venv/bin/python app.py --host 0.0.0.0 --port 5000"
