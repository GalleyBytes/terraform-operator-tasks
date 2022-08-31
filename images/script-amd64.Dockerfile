FROM alpine/k8s:1.20.7 as k8s

FROM ubuntu:20.04 as irsa-tokengen
WORKDIR /workdir
RUN mkdir bin
RUN apt update && apt install wget -y
RUN wget https://github.com/isaaguilar/irsa-tokengen/releases/download/v1.0.0/irsa-tokengen-v1.0.0-linux-amd64.tgz && \
    tar xzf irsa-tokengen-v1.0.0-linux-amd64.tgz && mv irsa-tokengen bin/irsa-tokengen

FROM ubuntu:latest as bin
WORKDIR /workdir
RUN mkdir bin
COPY --from=k8s /usr/bin/kubectl bin/kubectl
COPY --from=irsa-tokengen /workdir/bin/irsa-tokengen bin/irsa-tokengen

FROM docker.io/ubuntu:latest
ENV USER_UID=2000 \
    USER_NAME=tfo-runner \
    HOME=/home/tfo-runner
COPY usersetup script-toolset.sh /
RUN  /script-toolset.sh && /usersetup
COPY --from=bin /workdir/bin /usr/local/bin
COPY entrypoint /usr/local/bin/entrypoint
USER 2000
ENTRYPOINT ["/usr/local/bin/entrypoint"]