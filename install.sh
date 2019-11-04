#!/bin/bash

init_mac() {
  echo "install mac dependencies"
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
  brew install pipenv ffmpeg
}

init_linux() {

  YUM_CMD=$(which yum)
  APT_GET_CMD=$(which apt-get)
  PACKAGES="docker-ce docker-ce-cli containerd.io pipenv ffmpeg"

  echo "Install linux packages" 

  if [ ! -z $YUM_CMD ]; then
    sudo yum update -y && sudo yum -y install yum-utils device-mapper-persistent-data lvm2 \
    sudo yum-config-manager \
    --add-repo \
    https://download.docker.com/linux/centos/docker-ce.repo \
    sudo yum -y update && sudo yum -y install $PACKAGES

  elif [ ! -z $APT_GET_CMD ]; then
    sudo apt-get update -y && sudo apt-get install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common -y && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add - \
    && sudo add-apt-repository \
    "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) \
    stable" -y && sudo apt-get update -y && sudo apt-get install -y $PACKAGES
  fi

  # install docker-compose
  sudo curl -L "https://github.com/docker/compose/releases/download/1.24.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  sudo chmod +x /usr/local/bin/docker-compose

  # add docker group
  sudo groupadd docker
  sudo usermod -aG docker $USER

  # start docker daemon
  sudo systemctl enable docker && sudo systemclt start docker
}

# check which OS
unameOut="$(uname -s)"
case "${unameOut}" in
    Linux*)     machine=linux && init_linux;;
    Darwin*)    machine=mac && init_mac;;
    *)          machine=Other && echo "not supprt non *inx OS yet" && exit 1
esac

# setup python virtual environment and dependencies
pipenv install

# https://github.com/localstack/localstack mac need to specify TMPDIR
if [ $machine=mac ]; then
  TMPDIR=/private$TMPDIR docker-compose -f localstack/docker-compose.yml up -d
else
  docker-compose -f localstack/docker-compose.yml up -d
fi

