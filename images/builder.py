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
from docker.errors import BuildError

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

def docker_login(org):
    try:
        resp = docker.from_env().login(
            registry = "ghcr.io/",
            reauth = True,
            username = org,
            password = os.environ["GITHUB_TOKEN"])
        print(resp)
    except KeyError as e:
        print("Require GITHUB_TOKEN", e)
        exit(1)

def find_built_tags(host, org, image):
    headers = {}
    try:
        ghcr_auth = base64.b64encode(os.environ["GITHUB_TOKEN"].encode())
        headers["Authorization"] = f"Bearer {ghcr_auth.decode()}"
    except KeyError as e:
        print("Require GITHUB_TOKEN", e)
        exit(1)

    tags = []
    tag_list_link=f"https://{host}/v2/{org}/{image}/tags/list?n=0"
    while True:
        print(tag_list_link)
        tags_list_response = requests.get(tag_list_link, headers=headers)
        if tags_list_response.status_code != 200:
            tags_list_json = tags_list_response.json()
            for err in  tags_list_json["errors"]:
                if err["code"] != "NAME_UNKNOWN":
                    print(tags_list_json)
                    exit(2)
        data = tags_list_response.json()
        if data.get("tags"):
            tags+=data["tags"]
        else:
            break
        if tags_list_response.headers.get("Link") is not None:
            if 'rel="next"' in tags_list_response.headers["Link"]:
                tag_list_link = f'https://{host}/v2/galleybytes/{image}/tags/list?last={data["tags"][-1]}&n=0'
            else:
                break
        else:
            break

    return tags

def release_manifest_exists(host, org, image, tag, already_built_tags):
    url = f"https://{host}/v2/{org}/{image}"

    headers = {}
    try:
        ghcr_auth = base64.b64encode(os.environ["GITHUB_TOKEN"].encode())
        headers["Authorization"] = f"Bearer {ghcr_auth.decode()}"
    except KeyError as e:
        print("Require GITHUB_TOKEN", e)
        exit(1)

    if already_built_tags is None:
        return False

    if tag in already_built_tags:
        # In order for this to be true, it must exist and contain all the expected platforms
        manifest_response = requests.get(f"{url}/manifests/{tag}", headers=headers)
        if manifest_response.status_code != 200:
            print(manifest_response.raw)
            exit(3)

        if manifest_contains_archs(manifest_response.json(), [platform["architecture"] for platform in platforms]):
            return True
    return False


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
    name = s
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


def print_logs(logs):
    for log in logs:
        if log.get("stream"):
            print(log.get("stream"), end="")
        if log.get("aux"):
            print(log.get("aux"))

def build(host, org, image, tag, nocache=False, build_platform=None):
    repo = f"{host}/{org}/{image}"

    # Linux builds
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
        if build_platform is not None and build_platform != platform_string:
            continue

        variant = platform.get("variant")
        if variant is not None:
            platform_string = f"{platform_os}/{architecture}/{variant}"

        dockerfile = file_name(image, platform.get("architecture"), platform.get("variant"))

        archtag =f"{tag}-{architecture}"
        print(f"will build {archtag}")
        try:
            b, build_logs = client.images.build(
                path=".",
                dockerfile=dockerfile,
                tag=f"{repo}:{archtag}",
                rm=True,
                quiet=False,
                nocache=nocache,
                platform=platform_string,
                buildargs={"TF_IMAGE": tag}
            )
        except BuildError as e:
            print(e)
            print_logs(e.build_log)
            exit(4)
        print_logs(build_logs)

        for line in client.images.push(repo, tag=archtag, stream=True, decode=True):
            print(line)



    if build_platform is not None:
        return

    return True

def delete_local_image(host, org, image, tag, build_platform=None):
    repo = f"{host}/{org}/{image}"

    client = docker.from_env()
    if host == "docker.io":
        try:
            client.images.remove(f"{repo}:{tag}")
        except BuildError as e:
            print(e)
            exit(6)
        return

    # Linux builds
    for platform in platforms:
        platform_os = platform.get("os")
        if platform_os is None:
            continue
        platform_string = f"{platform_os}"

        architecture = platform.get("architecture")
        if architecture is None:
            continue
        platform_string = f"{platform_os}/{architecture}"
        if build_platform is not None and build_platform != platform_string:
            continue

        variant = platform.get("variant")
        if variant is not None:
            platform_string = f"{platform_os}/{architecture}/{variant}"

        archtag =f"{tag}-{architecture}"
        print(f"will build {archtag}")
        try:
            client.images.remove(f"{repo}:{archtag}")
        except BuildError as e:
            print(e)
            exit(5)


def release_manifest(org, image, tag):
    host = "ghcr.io"
    image = image_name(image)
    repo = f"{host}/{org}/{image}"
    expected_builds = []
    for platform in platforms:
        architecture = platform.get("architecture")
        if architecture is None:
            continue
        expected_builds.append((repo, f"{tag}-{architecture}"))

    stdout = os.system(f"docker manifest create {repo}:{tag} {builds_amend_cli(expected_builds)}")
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

        baseurl = f"https://api.github.com/orgs/{org}/packages/container/{image}/versions"
        nexturl = baseurl
        while True:
            packages_response = requests.get(nexturl, headers=headers)
            if packages_response.status_code != 200:
                print(packages_response.json())
                break

            for version in packages_response.json():
                if archtag in version["metadata"]["container"]["tags"]:
                    print(f"Will delete {archtag}")
                    version_id = version["id"]
                    delete_response = requests.delete(f"{baseurl}/{version_id}", headers=headers)
                    print(delete_response.status_code)
                    if delete_response.status_code != 204:
                        print(delete_response.json())

            if packages_response.headers.get("Link") is not None:
                if 'rel="next"' in packages_response.headers["Link"]:
                    # The value of 'Link' format is '<urlnext>; rel="next", <urllast>; rel="last"'
                    nexturl = packages_response.headers["Link"].split(";")[0].lstrip("<").rstrip(">")
                else:
                    break
            else:
                break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--org', required=True, help="Github organization owner of image")
    parser.add_argument('-i', '--image', required=True, help="Container Image (no tags)")
    parser.add_argument('-t', '--tag', required=True, help="Tag of container image")
    parser.add_argument('-p', '--platform', required=False, help="Platform/architecture for the container image")
    parser.add_argument('-b', '--skipbuild', required=False, default=False, action='store_true', help="Skip the builds")
    parser.add_argument('-r', '--release', required=False, default=False, action='store_true', help="Release the manifest")
    parser.add_argument('-D', '--delete', required=False, default=False, action='store_true', help="Tag of container image")
    parser.add_argument("-H", "--host", required=False, default="ghcr.io", help="Container repo hostname")
    parser.add_argument('--nocache', required=False, default=False, action='store_true', help="Tag of container image")
    args = parser.parse_args()

    image = image_name(args.image)

    if args.delete:
        delete_builds(args.tag, args.org, image)
        exit(0)

    tags = find_built_tags(args.host, args.org, image)

    if release_manifest_exists(args.host, args.org, image, args.tag, tags):
        print(f"Tag {args.tag} already exists")
        exit(0)

    if not args.skipbuild:
        docker_login(args.org)
        build(args.host, args.org, image, args.tag, args.nocache, args.platform)

    if args.release:
        release_manifest(args.org, image, args.tag)

