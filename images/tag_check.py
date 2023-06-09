#!/usr/bin/env python3
# Usage:
#   ./tag_check.py --host ghcr.io --org galleybytes --image terraform-operator --t v0.12.0
#   Exits 1 when true and 0 when false
from builder import image_name, ghcr_scrape_tags
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--org', required=True, help="Github organization owner of image")
    parser.add_argument('-i', '--image', required=True, help="Container Image (no tags)")
    parser.add_argument('-t', '--tag', required=True, help="Tag of container image")
    parser.add_argument("-H", "--host", required=False, default="ghcr.io", help="Container repo hostname")
    args = parser.parse_args()

    image = image_name(args.image)
    tags = ghcr_scrape_tags(args.host, args.org, image)

    exit(args.tag in tags)

