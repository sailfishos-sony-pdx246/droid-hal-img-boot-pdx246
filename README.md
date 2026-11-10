# droid-hal-img-boot-pdx246

LVM boot images for the Sailfish OS port to the Sony Xperia 10 VI (pdx246,
XQ-ES54/XQ-ES72), built from `mer-hybris/hybris-initrd` (submodule `initrd`,
pinned to 7b972b6). Building and installing the port are described in
[main](https://github.com/sailfishos-sony-pdx246/main): `BUILD.md` (this
repository is its step `imgboot`) and `INSTALL.md`.

| Package | File | Goes to |
|---|---|---|
| `droid-hal-pdx246-img-boot` | `/boot/hybris-boot.img`, plus a copy of `/lib/modules/<kernel>` | `boot_a`. On a package upgrade its %post registers the oneshot `flash-bootimg.sh` from droid-config, which writes boot_a, vendor_boot_a, dtbo_a and vendor_dlkm_a together as one set. |
| `droid-hal-pdx246-img-recovery` | `/boot/hybris-recovery.img` | Nowhere automatically. It is the USB/telnet debug image: flash it to `boot_a` by hand, never to `recovery_a`. |

## One matched set

An install consists of four images, and all four come from one Sailfish OS
build:

| Image | Package | Partition |
|---|---|---|
| `hybris-boot.img` | `droid-hal-pdx246-img-boot` (this repo) | `boot_a` |
| `vendor_boot.img` | `droid-hal-pdx246-vendor_boot` (droid-hal-pdx246) | `vendor_boot_a` |
| `dtbo.img` | `droid-hal-pdx246-kernel-dtbo` (droid-hal-pdx246) | `dtbo_a` |
| `vendor_dlkm.img`, `vendor_dlkm.release` | `droid-hal-pdx246-vendor_dlkm` (droid-hal-pdx246) | `vendor_dlkm_a` (logical, in super) |

The Sailfish kernel config changes the module CRCs, so the kernel in
`hybris-boot.img` only loads modules from its own build. The spec therefore
Requires `-vendor_boot`, `-kernel-dtbo` and `-vendor_dlkm` at exactly the
version-release of the `droid-hal-pdx246-kernel` it packed (a deviation from the
template, which turns a mismatched set into a build or install error). Never
combine these images with LineageOS ones. The Release is a build stamp, so a
rebuilt img-boot upgrades the installed one.

## Layout

- `rpm/droid-hal-pdx246-img-boot.spec`: device values for
  `initrd/droid-hal-device-img-boot.inc`.
- `initrd-pdx246/`: files that replace hybris-initrd files at build time
  (`recovery-init`), and the patched `droid-hal-device-img-boot.inc` that the
  spec includes (a new release for every build). Each one is generated from
  `patches/initrd/`.
- `tools/check-initrd-overrides.sh`: checks that the overrides still equal
  upstream plus the patches. Run it after any submodule bump.

## Build

The repo is checked out at `$ANDROID_ROOT/hybris/mw/droid-hal-img-boot-pdx246`
(dhd treats packages named `droid-hal-img-boot*` specially) and built after every
`build_packages.sh -d`, with `build_packages.sh -o -N
--mw=droid-hal-img-boot-pdx246`, not with `-b`:

- `--mw` runs dhd's img-boot preparation: it removes the installed img-boot from
  the SDK target and installs the new `droid-hal-pdx246-kernel` and
  `-kernel-modules`. With `-b` the target can keep the previous img-boot, which
  obsoletes `-kernel-modules`, and the build then finds no kernel modules.
- `-o` skips the `git pull` that `--mw` does; `-N` skips its tag check and keeps
  the package version at the kernel version.
