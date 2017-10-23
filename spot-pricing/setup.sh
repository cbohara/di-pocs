#!/bin/bash

if [ -z $(which pip) ]; then
	echo "ERROR: You need to have 'pip' installed in order to install 'virtualenv'"
	echo "HINT: You may need to run 'easy_install pip' or 'sudo easy_install pip' depending on your environment"
	exit 1
fi

if [ -z $(which virtualenv) ]; then
	echo "ERROR: You need to have 'virtualenv' installed"
	echo "HINT: You may need to run 'pip install virtualenv' or 'sudo pip install virtualenv' depending on your environment"
	exit 1
fi

if [ ! -d ./venv ]; then
	virtualenv venv
fi

source venv/bin/activate

pip install -r requirements.txt

if [ -z "$PYTHONPATH" ]; then
	export PYTHONPATH=.
else
	export PYTHONPATH=.:$PYTHONPATH
fi