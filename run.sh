#!/bin/bash
ansible_folder="$HOME/ansible/"
docker build -t ansible-popos "$ansible_folder"
if [ -n "$1" ]; then
    docker run --privileged -it -v "$ansible_folder:/home/devuser/ansible" --rm ansible-popos bash -c "ansible-playbook $* local.yml; bash"
else
    docker run --privileged -it -v "$ansible_folder:/home/devuser/ansible" --rm ansible-popos bash
fi
