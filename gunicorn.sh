#!/bin/sh
# Sample startup file
export FLASK_APP=vmon
export FLASK_ENV=production
# Uncomment to bind to UNIX socket
# ./venv/bin/gunicorn --chdir vmon 'vmon:app' -w 1 --threads 10 -b unix:vmon.sock -m 007
# Uncomment to bind to TCP socket
#./venv/bin/gunicorn --chdir vmon 'vmon:app' -w 1 --threads 10 -b 0.0.0.0:5000
