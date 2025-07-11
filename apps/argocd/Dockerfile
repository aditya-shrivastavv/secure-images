ARG BASE_IMAGE=cgr.dev/chainguard/wolfi-base
####################################################################################################
# Builder image
# Initial stage which pulls prepares build dependencies and CLI tooling we need for our final image
# Also used as the image in CI jobs so needs all dependencies
####################################################################################################
# FROM docker.io/library/golang:1.23.3@sha256:73f06be4578c9987ce560087e2e2ea6485fb605e3910542cadd8fa09fc5f3e31 AS builder
FROM reg.mini.dev/mini_k3dt4hsjastyedyczo4inphwaf6obael/go:latest-dev AS builder

RUN echo 'deb http://deb.debian.org/debian buster-backports main' >> /etc/apt/sources.list

RUN apt-get update && apt-get install --no-install-recommends -y \
    openssh-server \
    nginx \
    unzip \
    fcgiwrap \
    git \
    git-lfs \
    make \
    wget \
    gcc \
    sudo \
    zip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /tmp

COPY hack/install.sh hack/tool-versions.sh ./
COPY hack/installers installers

RUN ./install.sh helm-linux && \
    INSTALL_PATH=/usr/local/bin ./install.sh kustomize

####################################################################################################
# Argo CD UI stage
####################################################################################################
FROM --platform=$BUILDPLATFORM docker.io/library/node:23.1@sha256:db2ab3844812aac5e7822dd3c8d0112c9561e189818e3aae02805f98616e7f52 AS argocd-ui

WORKDIR /src
COPY ["ui/package.json", "ui/yarn.lock", "./"]

RUN yarn install --network-timeout 200000 && \
    yarn cache clean

COPY ["ui/", "."]

ARG ARGO_VERSION=3.0.6
ENV ARGO_VERSION=$ARGO_VERSION
ARG TARGETARCH
RUN HOST_ARCH=$TARGETARCH NODE_ENV='production' NODE_ONLINE_ENV='online' NODE_OPTIONS=--max_old_space_size=8192 yarn build

####################################################################################################
# Argo CD Build stage which performs the actual build of Argo CD binaries
####################################################################################################
FROM --platform=$BUILDPLATFORM reg.mini.dev/mini_k3dt4hsjastyedyczo4inphwaf6obael/go:latest-dev AS argocd-build

WORKDIR /go/src/github.com/argoproj/argo-cd

COPY go.* ./
RUN go mod download

# Perform the build
COPY . .
COPY --from=argocd-ui /src/dist/app /go/src/github.com/argoproj/argo-cd/ui/dist/app
ARG TARGETOS
ARG TARGETARCH
# These build args are optional; if not specified the defaults will be taken from the Makefile
ARG GIT_TAG=v3.0.6
ARG BUILD_DATE
ARG GIT_TREE_STATE=clean
ARG GIT_COMMIT
RUN GIT_COMMIT=$GIT_COMMIT \
    GIT_TREE_STATE=$GIT_TREE_STATE \
    GIT_TAG=$GIT_TAG \
    BUILD_DATE=$BUILD_DATE \
    GOOS=$TARGETOS \
    GOARCH=$TARGETARCH \
    make argocd-all

####################################################################################################
# Final image
####################################################################################################
FROM $BASE_IMAGE

LABEL org.opencontainers.image.source="https://github.com/argoproj/argo-cd"
ENV ARGOCD_USER_ID=999

# gpg-wrapper called here: https://github.com/argoproj/argo-cd/blob/master/util/gpg/gpg.go#L475
COPY hack/gpg-wrapper.sh /usr/local/bin/gpg-wrapper.sh
# called here https://github.com/argoproj/argo-cd/blob/0c21ef95983adce4908b958861fc08e088e05740/util/git/client.go#L659
COPY hack/git-verify-wrapper.sh /usr/local/bin/git-verify-wrapper.sh

USER root
RUN apk add git git-lfs helm kustomize zip gpg tini

RUN addgroup -g $ARGOCD_USER_ID argocd && \
    adduser -S -u $ARGOCD_USER_ID -g argocd argocd && \
    mkdir -p /home/argocd && \
    chown argocd:0 /home/argocd && \
    chmod g=u /home/argocd

COPY --from=argocd-build /go/src/github.com/argoproj/argo-cd/dist/argocd* /usr/local/bin/

# We can probably delete entrypoint scripts as no longer used
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN ln -s /usr/local/bin/entrypoint.sh /usr/local/bin/uid_entrypoint.sh

WORKDIR /app/config/ssh
RUN touch ssh_known_hosts && mkdir /etc/ssh && \
    ln -s /app/config/ssh/ssh_known_hosts /etc/ssh/ssh_known_hosts

WORKDIR /app/config
RUN mkdir -p tls && \
    mkdir -p gpg/source && \
    mkdir -p gpg/keys && \
    chown argocd gpg/keys && \
    chmod 0700 gpg/keys

ENV USER=argocd

WORKDIR /home/argocd
USER root
RUN ln -s /usr/local/bin/argocd /usr/local/bin/argocd-server && \
    ln -s /usr/local/bin/argocd /usr/local/bin/argocd-repo-server && \
    ln -s /usr/local/bin/argocd /usr/local/bin/argocd-cmp-server && \
    ln -s /usr/local/bin/argocd /usr/local/bin/argocd-application-controller && \
    ln -s /usr/local/bin/argocd /usr/local/bin/argocd-dex && \
    ln -s /usr/local/bin/argocd /usr/local/bin/argocd-notifications && \
    ln -s /usr/local/bin/argocd /usr/local/bin/argocd-applicationset-controller && \
    ln -s /usr/local/bin/argocd /usr/local/bin/argocd-k8s-auth

USER $ARGOCD_USER_ID
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["argocd"]
