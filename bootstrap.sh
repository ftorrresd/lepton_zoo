#!/bin/bash

# install micromamba
wget https://github.com/mamba-org/micromamba-releases/releases/download/2.3.2-0/micromamba-linux-64
mv micromamba-linux-64 bin/micromamba
chmod +x bin/micromamba

# create env
rm -rf venv
bin/micromamba create -y -p ./venv -c conda-forge --file environment.yml
