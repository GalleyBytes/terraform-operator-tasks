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
    args = parser.parse_args()
    image = "terraform-operator-setup"

    builder.build(args.org, image, args.tag)
