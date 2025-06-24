#!/bin/bash

# define the py311 venv from scratch; use the latest pbls version on disk
cd ../ ;
tar czf pbls-0.0.0.tar.gz pbls ;
mv pbls-0.0.0.tar.gz $HOME/environments/ ;
cd $HOME/environments/ ;

# NOTE: one dependency is not included in this auto-updated: the
# complexrotators package, https://github.com/lgbouma/cpv, because I have not
# put it on pip yet.
pip3 install --target=$HOME/environments/py311 -r core_requirements.txt ;
pip3 install --target=$HOME/environments/py311 --upgrade pbls-0.0.0.tar.gz ;
rm pbls-0.0.0.tar.gz ;

# move tarballed environment to runtime directory for exporting on OSG
cd $HOME/environments;
tar czf py311.tar.gz py311

cd $HOME/proj/pbls/drivers
mv $HOME/environments/py311.tar.gz .
