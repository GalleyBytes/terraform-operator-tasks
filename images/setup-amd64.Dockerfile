FROM alpine/k8s:1.20.7 as k8s

FROM docker.io/library/alpine as entrypoint
RUN apk add clang curl-dev build-base
WORKDIR /workdir
COPY entrypoint /workdir
RUN clang++ -static-libgcc -static-libstdc++ -std=c++17 entrypoint.cpp -lcurl -o entrypoint

FROM alpine/git:user
USER root
RUN apk add gettext jq bash
COPY --from=k8s /usr/bin/kubectl /usr/local/bin/kubectl
ENV USER_UID=2000 \
    USER_NAME=tfo-runner \
    HOME=/home/tfo-runner
COPY usersetup /usersetup
RUN  /usersetup
COPY --from=entrypoint /workdir/entrypoint /usr/local/bin/entrypoint
USER 2000
ENTRYPOINT ["entrypoint"]
