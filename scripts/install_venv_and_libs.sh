#!/bin/bash

# First update local pip
sudo apt update
sudo apt install pip
pip install --upgrade pip

# Install virtualenv
pip install virtualenv

# Crate virtual environment (venv) in the current directory
virtualenv venv

# Activate the environment
source ./venv/bin/activate

# Make sure apt and pip are up to date in the venv
sudo apt update
sudo apt install pip
pip install --upgrade pip

# Now upgrade to pyton 3.10
python3.10 -m venv ./venv

# Finally, install the libraries required by poo for python3.10
python3.10 -m pip install atomicwrites
python3.10 -m pip install sqlalchemy
python3.10 -m pip install Flask-SQLAlchemy
python3.10 -m pip install Flask-Cors
python3.10 -m pip install flask_httpauth
python3.10 -m pip install qrcode[pil]
