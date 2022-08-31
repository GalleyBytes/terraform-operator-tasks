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

def unbuilt_versions(org, image, tags):
    versions = []

    host = "ghcr.io"
    url = f"https://{host}/v2/{org}/{image}"
    headers = {}
    try:
        ghcr_auth = base64.b64encode(os.environ["GITHUB_TOKEN"].encode())
        headers["Authorization"] = f"Bearer {ghcr_auth.decode()}"
    except KeyError as e:
        print("Require GITHUB_TOKEN", e)
        exit(1)
    tags_list_response = requests.get(f"{url}/tags/list", headers=headers)
    if tags_list_response.status_code != 200:
        tags_list_json = tags_list_response.json()
        for err in  tags_list_json["errors"]:
            if err["code"] == "NAME_UNKNOWN":
                return tags
        print(tags_list_json)
        exit(2)

    for tag in tags:

        if builder.tag_exists(tags_list_response.json(), tag):
            manifest_response = requests.get(f"{url}/manifests/{tag}", headers=headers)
            if manifest_response.status_code != 200:
                print(manifest_response.json())
                exit(3)

            if builder.manifest_contains_archs(manifest_response.json(), [platform["architecture"] for platform in builder.platforms]):
                print("Tag already exists")
                continue
            versions.append(tag)
    return versions


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dockerhubrepo', required=True, help="Dockerhub owner/image (to tags)")
    parser.add_argument('-o', '--org', required=True, help="Github organization owner of image")
    parser.add_argument('-i', '--image', required=True, help="Container Image (no tags)")
    parser.add_argument('-t', '--tag', required=False, help="Tag of container image")
    parser.add_argument('--nocache', required=False, default=False, action='store_true', help="Tag of container image")
    args = parser.parse_args()

    # This is a public repo and does not need auth
    built_versions = terraform_versions(f"https://registry.hub.docker.com/v2/repositories/{args.dockerhubrepo}/tags/?page=1")

    if args.tag:
        versions_to_build = [args.tag]
    else:
        versions_to_build = unbuilt_versions(args.org, args.image, built_versions)

    print("the following versions need to be built in ghcr.io", versions_to_build)

    for version in versions_to_build:
        builder.build(args.org, args.image, version, args.nocache)