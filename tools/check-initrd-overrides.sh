#!/bin/sh
# SPDX-FileCopyrightText: Johannes Meyer zum Alten Borgloh
# SPDX-License-Identifier: GPL-2.0-only
#
# The files in initrd-pdx246/ replace whole files of the hybris-initrd
# submodule at build time (droid-hal-device-img-boot.inc copies them over
# initrd/). Each one is generated from the submodule's file plus one patch in
# patches/initrd/, so that a submodule bump cannot silently drop upstream
# changes. This script rebuilds every override from initrd/ and the patches
# and compares.
#
#   tools/check-initrd-overrides.sh           check, exit 1 on a difference
#   tools/check-initrd-overrides.sh --update  rewrite initrd-pdx246/ from
#                                             initrd/ and the patches
#
# Run it after every change of the initrd submodule pin. A patch that no
# longer applies has to be redone by hand against the new upstream file.

set -eu

top=$(cd "$(dirname "$0")/.." && pwd)
update=0
[ "${1:-}" = "--update" ] && update=1

if [ ! -f "$top/initrd/droid-hal-device-img-boot.inc" ]; then
    echo "initrd/ is not checked out (git submodule update --init)" >&2
    exit 1
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

status=0
for p in "$top"/patches/initrd/*.patch; do
    [ -e "$p" ] || continue
    for f in $(sed -n 's#^+++ b/##p' "$p"); do
        mkdir -p "$tmp/$(dirname "$f")"
        cp -p "$top/initrd/$f" "$tmp/$f"
    done
    if ! (cd "$tmp" && patch -p1 --quiet --no-backup-if-mismatch < "$p"); then
        echo "FAIL: $(basename "$p") does not apply to initrd/" >&2
        status=1
        continue
    fi
    for f in $(sed -n 's#^+++ b/##p' "$p"); do
        if [ $update -eq 1 ]; then
            mkdir -p "$top/initrd-pdx246/$(dirname "$f")"
            cp -p "$tmp/$f" "$top/initrd-pdx246/$f"
            echo "updated initrd-pdx246/$f"
        elif cmp -s "$tmp/$f" "$top/initrd-pdx246/$f"; then
            echo "ok: initrd-pdx246/$f = initrd/$f + $(basename "$p")"
        else
            echo "FAIL: initrd-pdx246/$f differs from initrd/$f + $(basename "$p")" >&2
            status=1
        fi
    done
done

# An override without a patch would hide upstream changes for good.
for o in $(cd "$top/initrd-pdx246" && find . -type f | sed 's#^\./##'); do
    if ! grep -q -x -F "+++ b/$o" "$top"/patches/initrd/*.patch; then
        echo "FAIL: initrd-pdx246/$o has no patch in patches/initrd/" >&2
        status=1
    fi
done

exit $status
