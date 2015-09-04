#!/bin/bash

set -e
set -x

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    eval "$(pyenv init -)"
    source ~/.venv/bin/activate
fi

python --version
doit pyflakes

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    py.test --ignore-flaky -s -v
else
    py.test --ignore-flaky
fi


if [[ $TRAVIS_PYTHON_VERSION == '2.7' ]]; then
    doit coverage
fi
