#!/bin/bash

if [ -z $(which pip) ]; then
	sudo easy_install pip
fi

if [ -z $(which virtualenv) ]; then
	sudo pip install virtualenv
fi

if [ ! -d ./venv ]; then
	virtualenv venv
fi

source venv/bin/activate

pip install -r requirements.txt