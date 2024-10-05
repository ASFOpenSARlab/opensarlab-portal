#!/bin/bash

set -xe

echo "Current directory is $(pwd)"

# Git commit hash
export BUILD_TAG=$(date +"%F-%H-%M-%S")
COMMIT_HEAD=$(git rev-parse --short HEAD)

# Get some env
export AWS_REGION=$(yq '.parameters.aws_region' labs.run.yaml)
DEPLOY_MYDEVLAB=$(yq '.parameters.deploy_mydevlab' labs.run.yaml)
USE_AWSECR=$(yq '.parameters.use_awsecr' labs.run.yaml)
DOCKER_REGISTRY_DOMAIN=$(yq '.parameters.docker_registry_domain' labs.run.yaml)
CONTAINER_NAMESPACE=$(yq '.parameters.container_namespace' labs.run.yaml)
MATURITY_NAMESPACE=$(yq '.parameters.maturity_namespace' labs.run.yaml)

# Create default.conf
cat labs.run.yaml | j2 --format=yaml services/nginx/etc/nginx/conf.d/default.conf.j2 > services/nginx/etc/nginx/conf.d/default.conf

# Create portal's jupyterhub_config
cat labs.run.yaml | j2 --format=yaml services/portal/etc/jupyterhub/jupyterhub_config.py.j2 > services/portal/etc/jupyterhub/jupyterhub_config.py

# Copy admin username info to User_info handler
cat labs.run.yaml | j2 --format=yaml services/portal/usr/local/lib/python3.10/dist-packages/jupyterhub/handlers/native_user_info.py.j2 > services/portal/usr/local/lib/python3.10/dist-packages/jupyterhub/handlers/native_user_info.py

# Copy labs.yaml to jupyterhub
cp labs.run.yaml services/portal/usr/local/etc/labs.yaml

# Copy notifications config values
cat labs.run.yaml | j2 --format=yaml services/useretc/app/notifications/ical.yaml.j2 > services/useretc/app/notifications/ical.yaml

# Copy configs 
# Do something here

# Create mydevlab files
if [[ $DEPLOY_MYDEVLAB == 'True' ]]
then
    cat labs.run.yaml | j2 --format=yaml services/mydevlab/lab.yaml.j2 > services/mydevlab/lab.yaml
    cat services/mydevlab/lab.yaml | j2 --format=yaml services/mydevlab/jupyterhub_config.py.j2 > services/mydevlab/jupyterhub_config.py
fi

# Don't override any possible AWS_PROFILE unless specifically given in labs.run.yaml
MAYBE_AWS_PROFILE=$(yq '.parameters.aws_profile' labs.run.yaml)
if [[ $MAYBE_AWS_PROFILE != 'null' ]]
then
    export AWS_PROFILE=$MAYBE_AWS_PROFILE
fi

# Log into ECR
if [[ $USE_AWSECR == 'True' ]]
then
    echo "Logging into AWS ECR...";
    aws ecr get-login-password | 
        docker login --username AWS --password-stdin $DOCKER_REGISTRY_DOMAIN
fi

export REGISTRY_URI=$DOCKER_REGISTRY_DOMAIN/$CONTAINER_NAMESPACE

BUILD_TAG=$BUILD_TAG.$MATURITY_NAMESPACE
COMMIT_HEAD=$COMMIT_HEAD.$MATURITY_NAMESPACE
LATEST=latest.$MATURITY_NAMESPACE

# Build images
pushd services/portal
docker build -f dockerfile -t $REGISTRY_URI/portal:$BUILD_TAG .
popd

pushd services/nginx
docker build -f dockerfile -t $REGISTRY_URI/nginx:$BUILD_TAG .
popd

pushd services/useretc
docker build -f dockerfile -t $REGISTRY_URI/useretc:$BUILD_TAG .
popd

# Tag images
docker tag $REGISTRY_URI/portal:$BUILD_TAG $REGISTRY_URI/portal:$COMMIT_HEAD
docker tag $REGISTRY_URI/portal:$BUILD_TAG $REGISTRY_URI/portal:$LATEST

docker tag $REGISTRY_URI/nginx:$BUILD_TAG $REGISTRY_URI/nginx:$COMMIT_HEAD
docker tag $REGISTRY_URI/nginx:$BUILD_TAG $REGISTRY_URI/nginx:$LATEST

docker tag $REGISTRY_URI/useretc:$BUILD_TAG $REGISTRY_URI/useretc:$COMMIT_HEAD
docker tag $REGISTRY_URI/useretc:$BUILD_TAG $REGISTRY_URI/useretc:$LATEST

# Push images
docker push $REGISTRY_URI/portal:$COMMIT_HEAD
docker push $REGISTRY_URI/portal:$BUILD_TAG
docker push $REGISTRY_URI/portal:$LATEST

docker push $REGISTRY_URI/nginx:$COMMIT_HEAD
docker push $REGISTRY_URI/nginx:$BUILD_TAG
docker push $REGISTRY_URI/nginx:$LATEST

docker push $REGISTRY_URI/useretc:$COMMIT_HEAD
docker push $REGISTRY_URI/useretc:$BUILD_TAG
docker push $REGISTRY_URI/useretc:$LATEST

if [[ $DEPLOY_MYDEVLAB == 'True' ]]
then

    pushd services/mydevlab
    docker build -f dockerfile -t $REGISTRY_URI/mydevlab:$BUILD_TAG .
    popd

    docker tag $REGISTRY_URI/mydevlab:$BUILD_TAG $REGISTRY_URI/mydevlab:$COMMIT_HEAD
    docker tag $REGISTRY_URI/mydevlab:$BUILD_TAG $REGISTRY_URI/mydevlab:$LATEST

    docker push $REGISTRY_URI/mydevlab:$COMMIT_HEAD
    docker push $REGISTRY_URI/mydevlab:$BUILD_TAG
    docker push $REGISTRY_URI/mydevlab:$LATEST

fi

# Add image_hash_tag to labs.run.yaml
yq -i '.parameters.image_hash_tag = strenv(BUILD_TAG)' labs.run.yaml
