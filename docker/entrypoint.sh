#!/bin/sh
# The job of this entrypoint file is to create matching user and group for the host user
# such that any build file generated will have the correct permissions.

if [ -z "$JHBUILD_USER_HOME" ] || [ -z "$JHBUILD_USER" ] || [ -z "$JHBUILD_GROUP" ] || [ -z "$JHBUILD_USER_ID" ] || [ -z "$JHBUILD_GROUP_ID" ]; then
    exec ${*:-/bin/bash}
    exit
fi

# create user
sudo groupadd -f -g $JHBUILD_GROUP_ID $JHBUILD_GROUP > /dev/null 2>&1 || true
sudo useradd -u $JHBUILD_USER_ID -g $JHBUILD_GROUP_ID -s /bin/bash -d $JHBUILD_USER_HOME $JHBUILD_USER > /dev/null 2>&1 || true
sudo usermod -u $JHBUILD_USER_ID -g $JHBUILD_GROUP_ID -s /bin/bash -d $JHBUILD_USER_HOME $JHBUILD_USER > /dev/null 2>&1 || true
sudo gpasswd -a $JHBUILD_USER staff > /dev/null 2>&1 || true

# grant sudo access
sudo gpasswd -a $JHBUILD_USER sudo > /dev/null 2>&1 || true
sudo sh -c "echo \"$JHBUILD_USER ALL=(ALL:ALL) NOPASSWD: ALL\" > /etc/sudoers.d/$JHBUILD_USER"

# setting up deployment key
sudo mkdir -p $JHBUILD_USER_HOME > /dev/null 2>&1 || true
sudo chown $JHBUILD_USER:$JHBUILD_GROUP $JHBUILD_USER_HOME > /dev/null 2>&1 || true

cd ${JHBUILD_HOME:-$JHBUILD_USER_HOME} && exec sudo -E -H -u $JHBUILD_USER ${*:-/bin/bash}
