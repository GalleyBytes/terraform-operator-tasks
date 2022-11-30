# FROM alpine/k8s:1.20.7 as k8s
FROM docker.io/library/debian as k8s
RUN apt update -y && apt install curl -y
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/arm64/kubectl"
RUN curl -LO "https://dl.k8s.io/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/arm64/kubectl.sha256"
RUN ls -lah kubectl
RUN ls -lah kubectl.sha256
RUN echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check
RUN install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl


FROM docker.io/library/debian as entrypoint
RUN apt update && apt install clang libcurl4-gnutls-dev uuid-dev -y
WORKDIR /workdir
COPY entrypoint /workdir
RUN clang++ -static-libgcc -static-libstdc++ -std=c++17 entrypoint.cpp -lcurl -o entrypoint

# Must be built on arm64 platform for the correct image to be used
FROM docker.io/library/debian
USER root
RUN apt update -y && apt install bash git gettext jq wget libcurl4-gnutls-dev uuid-dev -y
COPY --from=k8s /usr/local/bin/kubectl /usr/local/bin/kubectl
ENV USER_UID=2000 \
    USER_NAME=tfo-runner \
    HOME=/home/tfo-runner
COPY usersetup /usersetup
RUN  /usersetup
COPY --from=entrypoint /workdir/entrypoint /usr/local/bin/entrypoint
USER 2000
ENTRYPOINT ["/usr/local/bin/entrypoint"]
