#!/bin/bash

init_mac() {
  # check brew installed
  if ! [ -x "$(command -v brew)" ]; then
    echo 'Error: brw is not installed. Please follow instructions on brew.sh to install brew ' >&2
    exit 1
  fi

  # check docker installed
  if ! [ -x "$(command -v docker)" ]; then
    echo 'Error: docker is not installed. Please follow instructions on docker.io to install brew ' >&2
    exit 1
  fi

  # install or upgrade pipenv
  brew install pipenv
  pipenv --python 3.7
}

init_linux() {

  YUM_CMD=$(which yum)
  APT_GET_CMD=$(which apt-get)
  PACKAGES="docker-ce docker-ce-cli containerd.io pipenv"

  echo "Install docker and pipenv" 

  if [ ! -z $YUM_CMD ]; then
    sudo yum update -y && sudo yum -y install $PACKAGES
  elif [ ! -z $APT_GET_CMD ]; then
    sudo apt-get update -y && sudo apt-get install -y $PACKAGES
  fi
}


unameOut="$(uname -s)"
case "${unameOut}" in
    Linux*)     machine=Linux;;
    Darwin*)    machine=Mac;;
    *)          machine=Other
esac
echo ${machine}

init_mac