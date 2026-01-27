#!/usr/bin/env bash

set -e
set -x

coverage run -m pytest app/tests -m "not slow and not redteam"
coverage report --show-missing
coverage html --title "${@-coverage}"
coverage xml