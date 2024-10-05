#!/bin/bash

set -xe

# Get some env
export AWS_REGION=$(yq '.parameters.aws_region' labs.run.yaml)
DEPLOY_MYDEVLAB=$(yq '.parameters.deploy_mydevlab' labs.run.yaml)
USE_AWSECR=$(yq '.parameters.use_awsecr' labs.run.yaml)
DOCKER_REGISTRY_DOMAIN=$(yq '.parameters.docker_registry_domain' labs.run.yaml)
CONTAINER_NAMESPACE=$(yq '.parameters.container_namespace' labs.run.yaml)
IMAGE_HASH_TAG=$(yq '.parameters.image_hash_tag' labs.run.yaml)
SES_TOKEN_NAME=$(yq '.parameters.ses_token_name' labs.run.yaml)
SSO_TOKEN_NAME=$(yq '.parameters.sso_token_name' labs.run.yaml)

# Don't override any possible AWS_PROFILE unless specifically given in labs.run.yaml
MAYBE_AWS_PROFILE=$(yq '.parameters.aws_profile' labs.run.yaml)
if [[ $MAYBE_AWS_PROFILE != 'null' ]]
then
    export AWS_PROFILE=$MAYBE_AWS_PROFILE
fi

# Create docker-compose file
cat labs.run.yaml | j2 --format=yaml services/compose.yaml.j2 > services/compose.yaml

# Log into ECR
if [[ $USE_AWSECR == 'True' ]]
then
    echo "Logging into AWS ECR...";
    aws ecr get-login-password | 
        docker login --username AWS --password-stdin $DOCKER_REGISTRY_DOMAIN
fi

export REGISTRY_URI=$DOCKER_REGISTRY_DOMAIN/$CONTAINER_NAMESPACE

# Pull in the wanted images
docker pull $REGISTRY_URI/portal:$IMAGE_HASH_TAG
docker pull $REGISTRY_URI/nginx:$IMAGE_HASH_TAG
docker pull $REGISTRY_URI/useretc:$IMAGE_HASH_TAG

unset COMPOSE_PROFILES

if [[ $DEPLOY_MYDEVLAB == 'True' ]]
then
    docker pull $REGISTRY_URI/mydevlab:$IMAGE_HASH_TAG
fi

set +x

# Retrieve SSO token
SSO_SECRET=$(aws secretsmanager get-secret-value --secret-id $SSO_TOKEN_NAME --output json)
if [[ -z "$SSO_SECRET" ]]
then
    echo "Could not get sso-token"
    exit 1
fi

echo $SSO_SECRET | jq -r '.SecretString' > services/secrets/sso_token.secret

# Retrieve SES creds
SES_CREDS=$(aws secretsmanager get-secret-value --secret-id $SES_TOKEN_NAME --output json \
    | jq -r '.SecretString')

if [[ -z "$SES_CREDS" ]]
then
    echo "Could not get ses-creds"
    exit 1
fi

echo $SES_CREDS | cut -d' ' -f1 > services/secrets/ses_user.secret
echo $SES_CREDS | cut -d' ' -f2 > services/secrets/ses_pass.secret
echo $SES_CREDS | cut -d' ' -f3 > services/secrets/ses_url.secret

set -x

# Backup current working configuration
# If something goes wrong on deployment, this should help in a rollback.
# To rollback: `docker compose -f compose.[date].yaml up --detach --remove-orphans`
# Note that external resources like secrets will need to be manually rolledback as needed.
docker compose -f services/compose.yaml config > services/compose.$(date +"%F-%H-%M-%S").yaml

# Deploy
cd services
docker compose up --detach --remove-orphans
cd ..

sleep 1
# Check to see if the docker containers are running as expected. 
# If there was an error on setup, it won't always be present due to running in detached mode.
# Logs can be monitored via `docker compose logs -f`
docker ps

# Check to see if minimum services are running
$MIN_NUMBER_OF_PS
if [[ $DEPLOY_MYDEVLAB == 'True' ]]
then
    MIN_NUMBER_OF_PS=4
else
    MIN_NUMBER_OF_PS=3
fi

if [[ $(docker ps | grep $CONTAINER_NAMESPACE | wc -l) == $MIN_NUMBER_OF_PS ]]
then
    echo "All services are running as expected."
    cp services/compose.yaml services/compose.last_good.yaml
else
    echo "WARNING: A service did not start as expected."

    if ! [[ -f "services/compose.last_good.yaml" ]] ; then 
        echo "There is no last good config to revert to.."
    else
        echo "To revert and run last good config, run 'make revert'"
    fi
fi
