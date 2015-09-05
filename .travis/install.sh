#!/bin/bash

set -e
set -x

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    brew update || brew update

    if which pyenv > /dev/null; then
        eval "$(pyenv init -)"
    fi

    case "${PYTHON_VERSION}" in
        py27)
            brew outdated pyenv || brew upgrade pyenv
            pyenv install 2.7.10
            pyenv global 2.7.10
            ;;
        py33)
            brew outdated pyenv || brew upgrade pyenv
            pyenv install 3.3.6
            pyenv global 3.3.6
            ;;
        py34)
            brew outdated pyenv || brew upgrade pyenv
            pyenv install 3.4.2
            pyenv global 3.4.2
            ;;
        pypy)
            brew outdated pyenv || brew upgrade pyenv
            pyenv install pypy-2.6.1
            pyenv global pypy-2.6.1
            ;;
        pypy3)
            brew outdated pyenv || brew upgrade pyenv
            pyenv install pypy3-2.4.0
            pyenv global pypy3-2.4.0
            ;;
    esac
    pyenv rehash
    python -m pip install --user virtualenv

    python -m virtualenv ~/.venv
    source ~/.venv/bin/activate

    sudo pip install .
    sudo pip install -r dev_requirements.txt python-coveralls
else
    pip install .
    pip install -r dev_requirements.txt python-coveralls
fi


