#! /bin/bash
THIS_DIR=`pwd`

if [ $# -eq 0 ]
then
	LAUNCH_FRONTEND=true
	WITH_CONFIG=0
else
	LAUNCH_FRONTEND=false
	WITH_CONFIG=$1
fi

pip install --upgrade -r requirements.txt

cd $THIS_DIR/lib/Core
pip install --upgrade -r requirements.txt

cd $THIS_DIR
python setup.py $WITH_CONFIG