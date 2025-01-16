FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV USER=devuser

# basic configuration for container
RUN apt update && apt install -y \
    software-properties-common \
    curl \
    ansible \
    sudo \
    git \
    python3-pip \
    unzip \
    fzf \
    zsh 

# create no root user
RUN useradd -m -s /bin/zsh ${USER} && echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# switch to non-root user
USER ${USER}

RUN mkdir /home/${USER}/ansible \
  && python3 -m pip install github3.py

# Set the working directory
WORKDIR /home/${USER}/ansible

# copy ansible files to container
COPY . .

# run zsh shell
CMD ["/bin/zsh"]
