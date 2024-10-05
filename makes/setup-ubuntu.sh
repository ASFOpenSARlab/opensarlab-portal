#! /bin/bash

echo "Docker should already be installed. Checking..."
service docker status

sudo echo
sudo apt update
sudo apt install -y \
    python3 \
    python3-pip \
    jq

python3 -m pip install \
    pyyaml \
    j2cli[yaml] \
    Jinja2

sudo mkdir -p /usr/local/lib/docker/cli-plugins/
sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

mkdir -p /tmp/install_this/
(cd /tmp/install_this/ && \
wget "https://github.com/mikefarah/yq/releases/download/v4.24.5/yq_linux_amd64.tar.gz" -O - | \
    tar xz -C /tmp/install_this/ && \
    sudo mv yq_linux_amd64 /usr/bin/yq)
(cd /tmp/install_this/ && \
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    sudo ./aws/install --update)
rm -r /tmp/install_this/
