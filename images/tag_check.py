#!/usr/bin/env python3
#
# USAGE:
#   ./tag_check.py --host ghcr.io --org galleybytes --image terraform-operator --t v0.12.0
#   ./tag_check.py --host ghcr.io --org galleybytes --image terraform-operator --t v0.12.0 --ismultiarch
#
# RESULTS:
#   Without checking multiarch,
#       exits 1 when tag exists
#       exits 0 when tag does not exist
#   For multiarch,
#       exits 1 when a multi-arch image is found
#       exits 0 when tag does not exist OR is not multi-arch
from builder import image_name, ghcr_scrape_tags, release_manifest_exists
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--org', required=True, help="Github organization owner of image")
    parser.add_argument('-i', '--image', required=True, help="Container Image (no tags)")
    parser.add_argument('-t', '--tag', required=True, help="Tag of container image")
    parser.add_argument("-H", "--host", required=False, default="ghcr.io", help="Container repo hostname")
    parser.add_argument("--ismultiarch", required=False, default=False, action="store_true", help="Check if tag is multi-arch")
    args = parser.parse_args()

    image = image_name(args.image)
    tags = ghcr_scrape_tags(args.host, args.org, image)
    if args.ismultiarch:
        exit(release_manifest_exists(args.host, args.org, image, args.tag, tags))
    exit(args.tag in tags)

