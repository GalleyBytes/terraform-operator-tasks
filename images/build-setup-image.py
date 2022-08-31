#!/usr/bin/env python3
#
# Example Usage:
#
#   ## Build a single manifest (a manifest consists of all images of the same version under a single tag)
#   python3 build-setup-image.py --org galleybyes --tag 1.0.0
#
# Note there is no need to specify the "image" because this scirpt is specific to the "setup" image
#
import argparse
import builder

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--org', required=True, help="Github organization owner of image")
    parser.add_argument('-t', '--tag', required=True, help="Tag of container image")
    parser.add_argument('-b', '--skipbuild', required=False, default=False, action='store_true', help="Skip the builds")
    parser.add_argument('-r', '--release', required=False, default=False, action='store_true', help="Release the manifest")
    args = parser.parse_args()
    image = "terraform-operator-setup"

    if not args.skipbuild:
        builder.build(args.org, image, args.tag)

    if args.release:
        builder.release_manifest(args.org, image, args.tag)
