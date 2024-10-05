#!/bin/bash

set -e

while ! [[ $THE_REPLY =~ ^(y|n)$ ]] ; do
    echo "The current 'labs.run.yaml', 'ses_pass.secret', 'ses_user.secret', and 'ses_token.secret' values will be used."
    echo "It is assumed that the good images are stored locally. ECR credentials will not be invoked."
    echo " "
    echo "Are you sure you want to revert and run the previous compose file? y/n"
    
    read -r THE_REPLY
done 

if [[ $THE_REPLY == y ]] ; then 

    echo "Reverting to 'compose.last_good.yaml'"

    cd services/

    cp compose.yaml compose.reverted.yaml
    cp compose.last_good.yaml compose.yaml

    # Backup current working configuration
    # If something goes wrong on deployment, this should help in a rollback.
    # To rollback: `docker compose -f compose.[date].yaml up --detach --remove-orphans`
    # Note that external resources like secrets will need to be manually rolledback as needed.
    docker compose config > compose.$(date +"%F-%H-%M-%S").yaml

    # Deploy
    docker compose up --detach --remove-orphans

    sleep 1
    # Check to see if the docker containers are running as expected. 
    # If there was an error on setup, it won't always be present due to running in detached mode.
    # Logs can be monitored via `docker compose logs -f`
    docker ps

else
    echo "Not reverting"
fi
