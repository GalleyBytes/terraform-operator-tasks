ARG TF_IMAGE
FROM alpine/k8s:1.20.7 as k8s

FROM ubuntu:20.04 as irsa-tokengen
WORKDIR /workdir
RUN mkdir bin
RUN apt update && apt install wget -y
RUN wget https://github.com/isaaguilar/irsa-tokengen/releases/download/v1.0.0/irsa-tokengen-v1.0.0-linux-amd64.tgz && \
    tar xzf irsa-tokengen-v1.0.0-linux-amd64.tgz && mv irsa-tokengen bin/irsa-tokengen

FROM docker.io/library/alpine as entrypoint
RUN apk add clang curl-dev build-base
WORKDIR /entry
COPY entry /entry
RUN clang++ -static-libgcc -static-libstdc++ -std=c++17 entrypoint.cpp -lcurl -o entrypoint

FROM ubuntu:latest as bin
WORKDIR /workdir
RUN mkdir bin
COPY --from=k8s /usr/bin/kubectl bin/kubectl
COPY --from=irsa-tokengen /workdir/bin/irsa-tokengen bin/irsa-tokengen
COPY --from=entrypoint /entry/entrypoint bin/entrypoint

FROM hashicorp/terraform:${TF_IMAGE}
RUN apk add bash jq
COPY --from=bin /workdir/bin /usr/local/bin
ENV USER_UID=2000 \
    USER_NAME=tfo-runner \
    HOME=/home/tfo-runner
COPY usersetup /usersetup
RUN  /usersetup
USER 2000
ENTRYPOINT ["/usr/local/bin/entrypoint"]
