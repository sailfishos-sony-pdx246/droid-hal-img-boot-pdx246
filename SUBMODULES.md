# Submodules of droid-hal-img-boot-pdx246

When this repository is created (at
`$ANDROID_ROOT/hybris/mw/droid-hal-img-boot-pdx246`), it has exactly one
submodule:

| Path | URL | Pin (exact commit) | Upstream date |
|---|---|---|---|
| `initrd` | `https://github.com/mer-hybris/hybris-initrd.git` | `7b972b6f9498358bdf0a9df6ea1e2587405244c3` | 2026-09-04, "Merge pull request #74 from mer-hybris/jb65068" (head of `master`) |

The spec includes `initrd/droid-hal-device-img-boot.inc`, so the path must be
`initrd`. The repo name must start with `droid-hal-img-boot`, because dhd's
`util.sh` treats such packages specially (see NOTES.md, D1).

Placeholders: `$ANDROID_ROOT` is the `hybris-23.2` Android tree, `<sfos>` the
Sailfish OS port workspace that holds the reference checkouts.

## Why 7b972b6 and not the reference pin ecb295c

The 10 IV and 10 V community ports (`sharks-dev/droid-hal-img-boot-sony-xqdc72`,
local checkouts in `<sfos>/pdx225/` and `<sfos>/pdx235/`) pin
`ecb295c773899edb21c4a67a134a8e874a3ff21b` (2026-06-26). 7b972b6 is that pin
plus five commits (`git log ecb295c..7b972b6` in the reference checkout):

- `afb537a` "[initrd] Load modules.load in normal boot. JB#64727". A normal
  boot now loads `modules.load` (86 first-stage modules on pdx246, UFS
  included). Only the recovery image loads `modules.load.recovery` (302,
  including USB, msm_drm, kgsl and touch). At ecb295c every boot loads all
  302 before the root is mounted: no udev and no firmware helper run then,
  and pdx246 forces the sysfs firmware fallback, so this path is the one most
  likely to stall. Jolla made this change for devices that, like pdx246, carry
  their modules in vendor_boot.
- `4f6bf7a` adds optional avbtool macros for the boot image. They are not
  used here: vbmeta is flashed with verification disabled.
- `55b4a23` adds `bcb_part_label`. It is not used here (NOTES.md, D7).

`recovery-init`, the one file this repo overrides, is byte-identical at both
commits, so the override and its patch fit either pin.

The hybris-initrd maintainer told the 10 IV porter to use the latest submodule
(`<sfos>/pdx225/sailfish-on-murray/IRCLOGS.md:830`, "you can use latest
submodule").

## Creating it without a network download

Both commits are already on disk: the reference checkout's submodule clone
has `origin/master` = 7b972b6 (`git cat-file -t 7b972b6` gives `commit`, and
`git archive 7b972b6` works). A local clone is enough:

```sh
cd $ANDROID_ROOT/hybris/mw/droid-hal-img-boot-pdx246      # after git init
git clone --no-hardlinks --no-checkout \
    <sfos>/pdx235/droid-hal-img-boot-sony-xqdc72/.git/modules/initrd initrd
git -C initrd remote set-url origin https://github.com/mer-hybris/hybris-initrd.git
git -C initrd checkout --detach 7b972b6f9498358bdf0a9df6ea1e2587405244c3
git submodule add https://github.com/mer-hybris/hybris-initrd.git initrd   # registers the existing clone, no fetch
git submodule status        # must print 7b972b6f9498358bdf0a9df6ea1e2587405244c3 initrd
tools/check-initrd-overrides.sh
```

`--no-hardlinks` keeps the new clone independent of the reference checkout:
no shared object files and no alternates.

`git submodule add` creates `.gitmodules`. It cannot carry a licence header;
REUSE.toml covers it.

## When the pin moves

1. Move the submodule and run `tools/check-initrd-overrides.sh`.
2. If a patch in `patches/initrd/` no longer applies, redo it against the new
   upstream file. Then run `tools/check-initrd-overrides.sh --update`.
3. Read the new `droid-hal-device-img-boot.inc` for changed macros or
   BuildRequires (`git diff <old> <new> -- droid-hal-device-img-boot.inc`).
