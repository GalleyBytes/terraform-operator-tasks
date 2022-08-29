#!/usr/bin/env python3
#
# Usage:
#   ## Standard usage
#   python3 builder.py -o galleybytes -i setup -t 1.0.0
#
#   ## Rebuild from scratch by not using any cached layers
#   python3 builder.py -o galleybytes -i setup -t 1.0.0 --nocache
#
#   ## Delete a manifest from upstream github container registry
#   python builder.py -o galleybytes -i setup -t 1.0.0 --delete
#
# Most of the time, this script will be wrapped in another script. The other
# scripts just add this package to their imports.
#
import requests
import argparse
import os
import base64
import docker

prefix = "terraform-operator"

platforms = [
    {
        "architecture": "amd64",
        "os": "linux",
    },
    {
        "architecture": "arm64",
        "os": "linux",
        "variant": "v8"
    }
]

def tag_exists(data, tag):
    tags = data.get("tags")
    if tags is None:
        return False

    return tag in tags

def manifest_contains_archs(data, desired_architectures):
    manifests = data.get("manifests")
    if manifests is  None:
        return False

    architectures = []
    for manifest in manifests:
        architectures.append(manifest["platform"]["architecture"])

    for architecture in desired_architectures:
        if architecture not in architectures:
            return False

    return True


def image_name(s):
    tostrip = f"{prefix}-"
    if s.startswith(tostrip):
        return s
    return f"{prefix}-{s}"


def file_name(s, architecture=None, variant=None):
    tostrip = f"{prefix}-"
    if s.startswith(tostrip):
        name = s.replace(tostrip, "")
    suffix = "Dockerfile"
    if architecture is not None:
        name = f"{name}-{architecture}"
        if variant is not None:
            name = f"{name}{variant}"
    return f"{name}.{suffix}"


def builds_amend_cli(builds):
    s = ""
    for build in builds:
        s += f" --amend {build[0]}:{build[1]}"
    return s

def build(org, image, tag, nocache):
    image = image_name(image)
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
            if err["code"] != "NAME_UNKNOWN":
                print(tags_list_json)
                exit(2)


    if tag_exists(tags_list_response.json(), tag):
        manifest_response = requests.get(f"{url}/manifests/{tag}", headers=headers)
        if manifest_response.status_code != 200:
            print(manifest_response.raw)
            exit(3)

        if manifest_contains_archs(manifest_response.json(), [platform["architecture"] for platform in platforms]):
            print("Tag already exists")
            exit(0)

    # Linux builds
    builds = []
    client = docker.from_env()
    for platform in platforms:
        platform_os = platform.get("os")
        if platform_os is None:
            continue
        platform_string = f"{platform_os}"

        architecture = platform.get("architecture")
        if architecture is None:
            continue
        platform_string = f"{platform_os}/{architecture}"

        variant = platform.get("variant")
        if variant is not None:
            platform_string = f"{platform_os}/{architecture}/{variant}"

        dockerfile = file_name(image, platform.get("architecture"), platform.get("variant"))
        repo = f"{host}/{org}/{image}"
        archtag =f"{tag}-{architecture}"
        print(f"will build {archtag}")
        b, build_logs = client.images.build(
            path=".",
            dockerfile=dockerfile,
            tag=f"{repo}:{archtag}",
            rm=False,
            quiet=False,
            nocache=nocache,
            platform=platform_string,
            buildargs={"TF_IMAGE": tag}
        )
        for log in build_logs:
            if log.get("stream"):
                print(log.get("stream"), end="")
            if log.get("aux"):
                print(log.get("aux"))

        for line in client.images.push(repo, tag=archtag, stream=True, decode=True):
            print(line)

        builds.append((repo, archtag))

    stdout = os.system(f"docker manifest create {repo}:{tag} {builds_amend_cli(builds)}")
    print(stdout)
    stdout = os.system(f"docker manifest push {repo}:{tag}")
    print(stdout)




def delete_builds(basetag, org, image):
    image = image_name(image)
    tags = [basetag]
    for platform in platforms:
        architecture = platform.get("architecture")
        if architecture is None:
            continue
        tags.append(f"{basetag}-{architecture}")

    for archtag in tags:
        try:
            headers = {}
            gh_auth = os.environ["GITHUB_TOKEN"]
            headers["Authorization"] = f"Bearer {gh_auth}"
        except KeyError as e:
            print("Require GITHUB_TOKEN", e)
            exit(1)

        url = f"https://api.github.com/orgs/{org}/packages/container/{image}/versions"
        packages_response = requests.get(f"{url}", headers=headers)
        if packages_response.status_code != 200:
            print(packages_response.json())
            continue

        for version in packages_response.json():
            if archtag in version["metadata"]["container"]["tags"]:
                print(f"Will delete {archtag}")
                version_id = version["id"]
                delete_response = requests.delete(f"{url}/{version_id}", headers=headers)
                print(delete_response.status_code)
                if delete_response.status_code != 204:
                    print(delete_response.json())



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--org', required=True, help="Github organization owner of image")
    parser.add_argument('-i', '--image', required=True, help="Container Image (no tags)")
    parser.add_argument('-t', '--tag', required=True, help="Tag of container image")
    parser.add_argument('-D', '--delete', required=False, default=False, action='store_true', help="Tag of container image")
    parser.add_argument('--nocache', required=False, default=False, action='store_true', help="Tag of container image")
    args = parser.parse_args()

    if args.delete:
        delete_builds(args.tag, args.org, args.image)
        exit(0)

    build(args.org, args.image, args.tag, args.nocache)

