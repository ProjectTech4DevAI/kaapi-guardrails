#!/usr/bin/env bash

set -e
set -x

coverage run -m pytest app/tests
coverage report --show-missing
coverage html --title "${@-coverage}"
coverage xml