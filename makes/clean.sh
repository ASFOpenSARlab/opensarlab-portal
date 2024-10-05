set -e

echo "Current working directory is '$(pwd)'"

while ! [[ $THE_REPLY =~ ^(y|n)$ ]] ; do
    echo "- The current docker compose services will be shutdown."
    echo "- All local docker images will be pruned."
    echo "- All backup compose.*.yaml files will be deleted."
    echo "- All other intermidate files will be deleted."
    echo "- *All* local Docker containers and images will be deleted."
    echo "Sudo access will be required to delete some jupyterhub files."
    echo " "
    echo "Are you sure you want to clean? y/n"
    
    read -r THE_REPLY
done

if [[ $THE_REPLY == y ]] ; then 

    echo "Downing docker compose"
    cd services
    if [ -z compose.yaml ]; then
        docker compose down
    fi
    cd ..

    echo "Removing compose files"
    rm -f services/compose.yaml
    rm -f services/compose.*.yaml

    echo "Remove other intermediate files"
    rm -f labs.run.yaml
    rm -f services/portal/usr/local/etc/labs.yaml
    rm -f services/portal/etc/jupyterhub/jupyterhub_config.py
    rm -f services/nginx/etc/nginx/conf.d/default.conf
    rm -f services/useretc/app/notifications/ical.yaml
    sudo rm -rf services/srv/*

    echo "Pruning images"
    echo 'y' | docker image prune

    echo "Remove local docker images"
    docker rmi -f $(docker image ls -q)
fi
