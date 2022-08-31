FROM docker.io/library/debian@sha256:e3bb8517d8dd28c789f3e8284d42bd8019c05b17d851a63df09fd9230673306f as k8s
RUN apt update -y && apt install curl -y
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/arm64/kubectl"
RUN curl -LO "https://dl.k8s.io/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/arm64/kubectl.sha256"
RUN ls -lah kubectl
RUN ls -lah kubectl.sha256
RUN echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check
RUN install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

FROM docker.io/library/debian@sha256:e3bb8517d8dd28c789f3e8284d42bd8019c05b17d851a63df09fd9230673306f as irsa-tokengen
WORKDIR /workdir
RUN mkdir bin
RUN apt update && apt install wget -y
RUN wget https://github.com/isaaguilar/irsa-tokengen/releases/download/v1.0.0/irsa-tokengen-v1.0.0-linux-arm64.tgz && \
    tar xzf irsa-tokengen-v1.0.0-linux-arm64.tgz && mv irsa-tokengen bin/irsa-tokengen

FROM docker.io/library/debian@sha256:e3bb8517d8dd28c789f3e8284d42bd8019c05b17d851a63df09fd9230673306f as bin
WORKDIR /workdir
RUN mkdir bin
COPY --from=k8s /usr/local/bin/kubectl bin/kubectl
COPY --from=irsa-tokengen /workdir/bin/irsa-tokengen bin/irsa-tokengen

FROM docker.io/library/ubuntu@sha256:64162ac111b666daf1305de1888eb67a3033f62000f5ff781fe529aff8f88b09
ENV USER_UID=2000 \
    USER_NAME=tfo-runner \
    HOME=/home/tfo-runner
COPY usersetup script-toolset.sh /
RUN  /script-toolset.sh && /usersetup
COPY --from=bin /workdir/bin /usr/local/bin
COPY entrypoint /usr/local/bin/entrypoint
USER 2000
ENTRYPOINT ["/usr/local/bin/entrypoint"]