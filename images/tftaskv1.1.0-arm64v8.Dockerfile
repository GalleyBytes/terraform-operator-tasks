ARG TF_IMAGE

FROM docker.io/library/debian as k8s
RUN apt update -y && apt install curl -y
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/arm64/kubectl"
RUN curl -LO "https://dl.k8s.io/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/arm64/kubectl.sha256"
RUN ls -lah kubectl
RUN ls -lah kubectl.sha256
RUN echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check
RUN install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

FROM docker.io/library/debian as irsa-tokengen
WORKDIR /workdir
RUN mkdir bin
RUN apt update && apt install wget -y
RUN wget https://github.com/isaaguilar/irsa-tokengen/releases/download/v1.0.0/irsa-tokengen-v1.0.0-linux-arm64.tgz && \
    tar xzf irsa-tokengen-v1.0.0-linux-arm64.tgz && mv irsa-tokengen bin/irsa-tokengen

FROM docker.io/library/debian as entrypoint
RUN apt update && apt install clang libcurl4-gnutls-dev -y
WORKDIR /entry
COPY entry /entry
RUN clang++ -static-libgcc -static-libstdc++ -std=c++17 entrypoint.cpp -lcurl -o entrypoint

FROM docker.io/library/debian as bin
WORKDIR /workdir
RUN mkdir bin
COPY --from=k8s /usr/local/bin/kubectl bin/kubectl
COPY --from=irsa-tokengen /workdir/bin/irsa-tokengen bin/irsa-tokengen
COPY --from=entrypoint /entry/entrypoint bin/entrypoint

FROM ghcr.io/galleybytes/terraform-arm64:${TF_IMAGE} as terraform

FROM docker.io/library/alpine:3.16.2
RUN apk add bash jq git openssh
COPY --from=bin /workdir/bin /usr/local/bin
ENV USER_UID=2000 \
    USER_NAME=tfo-runner \
    HOME=/home/tfo-runner
COPY usersetup /usersetup
RUN  /usersetup
USER 2000
ENTRYPOINT ["/usr/local/bin/entrypoint"]
COPY --from=terraform /usr/local/bin/terraform /usr/local/bin
