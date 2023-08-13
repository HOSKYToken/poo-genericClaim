#!/bin/bash

source ../venv/bin/activate

# Check if the virtual environment is activated
if [ -n "$VIRTUAL_ENV" ]; then
    echo "Virtual environment is activated: $VIRTUAL_ENV"
else
    echo "Virtual environment is NOT activated. Please activate the virtual environment first."
    exit 1
fi

export PYTHONPATH="../src:$PYTHONPATH"
