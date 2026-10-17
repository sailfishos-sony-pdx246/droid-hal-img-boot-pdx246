# droid-hal-img-boot-pdx246

LVM boot images for the Sailfish OS port to the Sony Xperia 10 VI (pdx246,
XQ-ES54/XQ-ES72), built from `mer-hybris/hybris-initrd` (submodule `initrd`,
pinned to 7b972b6; SUBMODULES.md).

| Package | File | Goes to |
|---|---|---|
| `droid-hal-pdx246-img-boot` | `/boot/hybris-boot.img`, plus a copy of `/lib/modules/<kernel>` | `boot_a`. On a package upgrade its %post registers the oneshot `flash-bootimg.sh` from droid-config, which writes boot_a, vendor_boot_a and dtbo_a together as one set. |
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
version-release of the `droid-hal-pdx246-kernel` it packed (NOTES.md, D9).
Never combine these images with LineageOS ones.

## Layout

- `rpm/droid-hal-pdx246-img-boot.spec`: device values for
  `initrd/droid-hal-device-img-boot.inc`.
- `initrd-pdx246/`: files that replace hybris-initrd files at build time
  (`recovery-init`), and the patched `droid-hal-device-img-boot.inc` that the
  spec includes (a new release for every build). Each one is generated from
  `patches/initrd/`.
- `tools/check-initrd-overrides.sh`: checks that the overrides still equal
  upstream plus the patches. Run it after any submodule bump.
- `NOTES.md`: decisions with evidence, the contract with the other
  adaptation repos, TODOs and provenance. `SUBMODULES.md`: the pin.

## Build

The repo is checked out at `$ANDROID_ROOT/hybris/mw/droid-hal-img-boot-pdx246`.

Android side, on the host, in `$ANDROID_ROOT` with the hybris patches applied:

```sh
export PORT_ARCH=aarch64    # droidmedia's target list depends on it
source build/envsetup.sh
lunch lineage_pdx246-bp4a-userdebug
make hybris-hal droidmedia vendor_dlkmimage audio.hidl_compat.default
```

Packages, in the Platform SDK, from `$ANDROID_ROOT`, in this order:

```sh
rpm/dhd/helpers/build_packages.sh -d
rpm/dhd/helpers/build_packages.sh -c
git clone --recurse-submodules https://github.com/mer-hybris/pulseaudio-modules-droid.git hybris/mw/pulseaudio-modules-droid
git -C hybris/mw/pulseaudio-modules-droid checkout 65edd31f62f22e2eec1f765608ca9c6ae5c4af7b   # 14.2.106
rpm/dhd/helpers/build_packages.sh -o --mw    # offline, so the 14.2.106 checkout is not pulled
rpm/dhd/helpers/build_packages.sh --mw=https://github.com/sailfish-on-nabu/parse-android-dynparts
rpm/dhd/helpers/build_packages.sh --mw=https://github.com/sailfishos/sensorfw --spec=rpm/sensorfw-qt5-binder.spec
rpm/dhd/helpers/build_packages.sh -g    # droidmedia, gst-droid
rpm/dhd/helpers/build_packages.sh -o -N --mw=droid-hal-img-boot-pdx246    # this repo
rpm/dhd/helpers/build_packages.sh -v
rpm/dhd/helpers/build_packages.sh -i
```

Rebuild this package after every later `-d`: its Requires pin the droid-hal
build, and `-d` removes the previous droid-hal RPMs.

Why `-o -N --mw=droid-hal-img-boot-pdx246` and not
`-b hybris/mw/droid-hal-img-boot-pdx246`:
- `--mw` runs dhd's img-boot preparation: it removes the installed img-boot
  from the SDK target and installs the new `droid-hal-pdx246-kernel` and
  `-kernel-modules`. `-b` skips that. mb2 then updates the target from the
  local repo, where the previous img-boot obsoletes `-kernel-modules`, so the
  target very likely ends up with the old img-boot instead of the new kernel
  modules, and the build finds no kernel modules (inferred from the code;
  NOTES.md, D1).
- `-o` skips the `git pull` that `--mw` does; this repo has no upstream.
- `-N` skips the tag check that `--mw` does and keeps the package version
  at the kernel version (NOTES.md, D10).

## Flashing (summary)

droid-config-pdx246 implements the procedure (`flash.sh` with its
`flash-config.sh`, `flash-preflight.sh` and `flashing-README.txt` in the
flashing zip). NOTES.md, D11, has the details.

- Before the first flash, install LineageOS on slot a, boot it once to the
  home screen and leave it a minute, so the Virtual A/B merge completes.
  Keep the LineageOS boot, vendor_boot, dtbo and vendor_dlkm images of that
  release: slot b holds no bootable LineageOS (Virtual A/B keeps one copy of
  the dynamic partitions), so rolling back means reflashing that slot-a set.
- fastbootd first. From the bootloader: the dry run
  (`getvar_fail_if secure yes`, as in droid-hal-configs' `flash.sh`),
  `fastboot --set-active=a`,
  `fastboot reboot fastboot`, `./flash-preflight.sh` (stops unless the current
  slot is a, no snapshot merge is pending and vendor_dlkm_a is logical). From
  fastbootd: `vendor_dlkm_a` and `userdata` (sailfish.img001), then
  `fastboot reboot bootloader`. From the bootloader: `boot_a`
  (hybris-boot.img), `vendor_boot_a`, `dtbo_a`, `fastboot --set-active=a`,
  reboot.
- Why fastbootd first: on the first install, recovery_a (ramdisk-only; it
  hosts fastbootd) still boots on LineageOS's boot_a kernel and
  vendor_boot_a, which is known to work.
- Re-flashing over an installed Sailfish OS: fastbootd then runs on the
  Sailfish kernel. If `fastboot reboot fastboot` does not reach fastbootd,
  flash the saved LineageOS boot_a, vendor_boot_a and dtbo_a from the
  bootloader first, then run `./flash.sh` again.
- If `flash.sh` stops halfway (USB drop, the pdx246 "TRAP 2"), reconnect
  until `fastboot devices` lists the phone, run `fastboot reboot bootloader`,
  and start `./flash.sh` again. A rerun started in fastbootd stops at the dry
  run, because fastbootd reports `secure: yes`.
