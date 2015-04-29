FROM docker.mujin.co.jp/mujin/debian:wheezy

RUN \
    apt-get update -y && \
    apt-get install -y --force-yes --no-install-recommends build-essential cmake git ssh gnome-common yelp-tools sudo apt-file rsync python-dev python-pip nano vim && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --upgrade pip

RUN \
    git clone --branch=master --depth=10 https://github.com/mujin/jhbuild.git /usr/src/jhbuild && \
    cd /usr/src/jhbuild && \
    git checkout -qf {{VERSION}} && \
    ./autogen.sh --prefix=/usr/local && \
    make && \
    make install && \
    cd / && \
    rm -rf /usr/src/jhbuild

RUN \
    groupadd -g 999 jhbuild && \
    useradd -u 999 -g 999 -s /bin/bash -d /home/jhbuild -m jhbuild && \
    gpasswd -a jhbuild staff && \
    gpasswd -a jhbuild sudo && \
    echo "jhbuild ALL=(ALL:ALL) NOPASSWD: ALL" > /etc/sudoers.d/jhbuild

USER jhbuild
WORKDIR /home/jhbuild

ADD entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

