#! /bin/bash

sudo echo
echo "Cloudwatch should have already been setup..."
sudo amazon-cloudwatch-agent-ctl -m ec2 -a status

echo "Docker service should already be running..."
sudo service docker status

echo "Install other packages..."
sudo dnf install -y \
    python \
    python-pip \
    git \
    vim \
    jq

echo "Create python env and add other packages..."
python -m venv /home/ec2-user/venv
source /home/ec2-user/venv/bin/activate

python -m pip install \
    pyyaml \
    j2cli[yaml]

sudo mkdir -p /usr/local/lib/docker/cli-plugins/
sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

mkdir -p /tmp/install_this/
(cd /tmp/install_this/ && \
    wget "https://github.com/mikefarah/yq/releases/download/v4.24.5/yq_linux_amd64.tar.gz" -O - |\
    tar xz -C /tmp/install_this/ && \
    sudo mv yq_linux_amd64 /usr/bin/yq)
rm -r /tmp/install_this/

echo "Mount Database volume..."
# https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-using-volumes.html

while ! [[ "$answer_1" =~ ^(y|n)$ ]]; do
  echo "Do you want to format the Portal DB volume attached to /dev/xvdj ?"
  echo "Warning: This should only be done on initial volume creation."
  echo "Warning: Any existing DB files and related user data will be deleted."
  echo "y/n"
  read -r answer_1
done
if [[ "$answer_1" =~ ^(y)$ ]]; then
    while ! [[ "$answer_2" =~ ^(y|n)$ ]]; do
        echo "Are you sure ? y/n"
        read -r answer_2
    done
    if [[ $answer_2 == 'y' ]]
    then
        sudo mkfs -t xfs -f /dev/xvdj
    fi
fi

echo "Mounting /dev/sdj to services/srv..."
sudo mkdir -p services/srv/
sudo mount /dev/xvdj services/srv/
sudo chown -R 1000:1000 services/srv/

echo "Creating systemd script to unmount and detach volume on shutdown"
# Add volume umount and detachment scripts to systemd
# This is to ensure that volumes are handled properly on CloudFormation/EC2 updates
echo "
#!/bin/bash
umount /dev/xvdj
AWS_INSTANCE_ID=$(curl http://169.254.169.254/latest/meta-data/instance-id)
VOL_ID=$(aws ec2 describe-instances --instance-id $AWS_INSTANCE_ID --output text \
    --filters Name=block-device-mapping.device-name,Values=/dev/xvdj \
    --query Reservations[0].Instances[0].BlockDeviceMappings[0].Ebs.VolumeId)
if [[ ! -z "$VOL_ID" ]]; then
    aws ec2 detach-volume --volume-id $VOL_ID --device /dev/xvdj
fi
" > /tmp/umount_and_detach_vol.sh
sudo mv /tmp/umount_and_detach_vol.sh /usr/local/etc/

echo "
[Unit]
Description=Unmount and detach volume from EC2
Before=shutdown.target reboot.target halt.target
Requires=network-online.target network.target

[Service]
KillMode=none
ExecStart=/bin/true
ExecStop=/usr/local/etc/umount_and_detach_vol.sh
RemainAfterExit=yes
Type=oneshot

[Install]
WantedBy=multi-user.target
" > /tmp/umount_and_detach_vol.service
sudo mv /tmp/umount_and_detach_vol.service /usr/lib/systemd/system/

sudo systemctl enable umount_and_detach_vol.service
sudo systemctl start umount_and_detach_vol.service
