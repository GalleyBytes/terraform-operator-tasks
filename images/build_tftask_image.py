#!/usr/bin/env python3
#
# Example Usage:
#
#   ## Build a single manifest (a manifest consists of all images of the same version under a single tag)
#   python3 build-tftask-image.py --dockerhubrepo isaaguilar/terraform-arm64 --org galleybyes --image tftaskv1 --tag 1.0.9
#
#   ## Build all the images by not specifying a tag
#   python3 build-tftask-image.py --dockerhubrepo isaaguilar/terraform-arm64 --org galleybyes --image tftaskv1
#
#   ## Force rebuilding (this should not be used for production images)
#   python3 build-tftask-image.py --dockerhubrepo isaaguilar/terraform-arm64 --org galleybyes --image tftaskv1 --tag 1.0.9 --nocache
#
import argparse
import builder
import requests
import base64
import os

ignore_versions = ["0.11.0-beta1", "0.11.0", "0.11.1", "0.11.2", "0.11.3", "0.11.4", "0.11.5", "0.11.6", "0.11.7", "0.11.8"]

def terraform_versions(url):
    print(url)
    versions = []
    while True:
        resp = requests.get(f"{url}")
        data = resp.json()
        for item in data["results"]:
            if item["name"] not in versions:
                versions.append(item["name"])
        url = data.get("next")
        if not url:
            break
    return versions

def unbuilt_versions(host, org, image, tags, already_built_tags):
    versions = []
    for tag in tags:
        if builder.release_manifest_exists(host, org, image, tag, already_built_tags):
            print(f"Release manifest {tag} already exists")
            continue
        versions.append(tag)
    return versions


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-H", "--host", required=False, default="ghcr.io", help="Container repo hostname")
    parser.add_argument('-d', '--dockerhubrepo', required=True, help="Dockerhub owner/image (to tags)")
    parser.add_argument('-o', '--org', required=True, help="Github organization owner of image")
    parser.add_argument('-i', '--image', required=True, help="Container Image (no tags)")
    parser.add_argument('-t', '--tag', required=False, help="Tag of container image")
    parser.add_argument('-p', '--platform', required=False, help="Platform/architecture for the container image")
    parser.add_argument('-b', '--skipbuild', required=False, default=False, action='store_true', help="Skip the builds")
    parser.add_argument('-r', '--release', required=False, default=False, action='store_true', help="Release the manifest")
    parser.add_argument('--deletelocal', required=False, default=False, action='store_true', help="Remove image on host")
    parser.add_argument('--norebuild', required=False, default=False, action='store_true', help="Skip if tag exists. Only works if platform is defined.")
    parser.add_argument('--nocache', required=False, default=False, action='store_true', help="Tag of container image")
    args = parser.parse_args()

    # This is a public repo and does not need auth
    built_versions = terraform_versions(f"https://registry.hub.docker.com/v2/repositories/{args.dockerhubrepo}/tags/?page=1")

    image = builder.image_name(args.image)
    already_built_tags = builder.find_built_tags(args.host, args.org, image)
    if args.tag:
        all_available_versions = [args.tag]
    else:
        all_available_versions = unbuilt_versions(args.host, args.org, image, built_versions, already_built_tags)

    versions_to_build = []
    for version in all_available_versions:
        if version in ignore_versions:
            continue
        versions_to_build.append(version)
    print("the following versions need to be built in ghcr.io", versions_to_build)

    builder.docker_login(args.org)
    for version in versions_to_build:
        if builder.release_manifest_exists(args.host, args.org, image, args.tag, already_built_tags):
            print(f"Tag {args.tag} already exists")
            continue
        if not args.skipbuild:
            if args.norebuild:
                # Only works if a platform is defined
                if args.platform:
                    arch = args.platform.split("/")[1]
                    if f"{version}-{arch}" in already_built_tags:
                        print(f"Tag {version}-{arch} already exists")
                        continue
            built = builder.build(args.host, args.org, image, version, args.nocache, args.platform)
        else:
            built = True
        if args.deletelocal:
            builder.delete_local_image(args.host, args.org, image, version, args.platform)
            builder.delete_local_image("docker.io", "isaaguilar", "terraform-arm64", version, args.platform)
        if args.release and built:
            builder.release_manifest(args.org, image, version)