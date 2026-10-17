# droid-hal-img-boot-pdx246: design notes

Written 2026-10-04. Not yet built or flashed. Evidence marked
*(inferred)* was not observed on the device.

Path placeholders used below:
- `$ANDROID_ROOT`: the `hybris-23.2` Android tree. Paths such as
  `device/sony/pdx246/…`, `kernel/sony/sm6450/…`, `system/…` and
  `out/target/product/pdx246/…` are relative to it.
- `<sfos>`: the Sailfish OS port workspace. It holds the reference ports for
  the Xperia 10 IV and 10 V (`<sfos>/pdx225/`, `<sfos>/pdx235/`) and the
  port's working notes (`<sfos>/notes/`, not public).
- `<lineageos tree>`: the LineageOS 23.2 checkout of the pdx246 port.

Short names:
- "ref initrd": the hybris-initrd clone in
  `<sfos>/pdx235/droid-hal-img-boot-sony-xqdc72/initrd`, read with
  `git show <commit>:<file>`.
- "dhd": mer-hybris/droid-hal-device at be67bbc (droid-hal-pdx246's pin), for
  example `<sfos>/pdx225/droid-hal-pdx225/dhd`.
- "findings.md": `<sfos>/notes/analysis/adaptation-map-2026-10-04/findings.md`.
- "PORTING-NOTES": `PORTING-NOTES.md` of the LineageOS port's notes.
- "IRCLOGS.md": `<sfos>/pdx225/sailfish-on-murray/IRCLOGS.md`
  (#sailfishos-porters logs kept by the 10 IV port).
- "mb2": `/usr/bin/mb2` inside the Platform SDK.

## What this repo is

The repo builds the LVM-route boot image the same way the 10 IV and 10 V
ports do: `mer-hybris/hybris-initrd` (submodule `initrd`) builds a busybox
initrd, packs it with the kernel from `droid-hal-pdx246-kernel` into
`hybris-boot.img`, and finds the LVM volume group `sailfish` on the GPT
partition `userdata`. On pdx246 that initrd depends on the Sailfish-built
`vendor_boot` far more than on the reference devices, because UFS and USB
are modules there (D5).

hybris-boot.img is one of four images that form one matched set from one
Sailfish OS build: hybris-boot.img (this repo, boot_a), vendor_boot.img
(droid-hal-pdx246-vendor_boot, vendor_boot_a), dtbo.img
(droid-hal-pdx246-kernel-dtbo, dtbo_a) and vendor_dlkm.img with
vendor_dlkm.release (droid-hal-pdx246-vendor_dlkm, vendor_dlkm_a). D8, D9.

Files:
- `rpm/droid-hal-pdx246-img-boot.spec`
- `initrd-pdx246/recovery-init` (override)
- `patches/initrd/0001-…patch` (the source of the override)
- `tools/check-initrd-overrides.sh`
- `SUBMODULES.md`, `README.md`, `REUSE.toml`, `LICENSES/`, `.gitignore`

---

## Decisions

### D1. Name, location, packages, build command

- The repo lives at `$ANDROID_ROOT/hybris/mw/droid-hal-img-boot-pdx246`. The
  name starts with `droid-hal-img-boot` because dhd's `buildmw` special-cases
  that prefix: it removes the old img-boot from the target and installs the
  kernel and modules first (dhd `helpers/util.sh:278-298`).
- The spec is `rpm/droid-hal-pdx246-img-boot.spec`, after the reference's
  `rpm/droid-hal-pdx235-img-boot.spec`
  (`<sfos>/pdx235/droid-hal-img-boot-sony-xqdc72/rpm/`) and the official
  `mer-hybris/droid-hal-img-boot-sony-murray/rpm/droid-hal-pdx225-img-boot.spec`.
- Packages, from ref initrd `7b972b6:droid-hal-device-img-boot.inc`:
  - `droid-hal-pdx246-img-boot` (:177) holds `/boot/hybris-boot.img` and a
    copy of `/lib/modules/<kver>`. It Provides and Obsoletes
    `droid-hal-pdx246-kernel-modules` (:232-240) and runs `depmod` in %post
    (:527).
  - `droid-hal-pdx246-img-recovery` (:258-266, :486-495) holds
    `/boot/hybris-recovery.img`.
  - No `-vendor_boot` or `-init_boot` subpackage: neither
    `vendor_boot_mkbootimg_cmd` nor `init_boot_mkbootimg_cmd` is defined
    (:281-291, :269-279).
- Build command, from `$ANDROID_ROOT` in the Platform SDK, after
  `build_packages.sh -d` and again after every later `-d` (D9):
  ```
  rpm/dhd/helpers/build_packages.sh -o -N --mw=droid-hal-img-boot-pdx246
  ```
  - `--mw=<name>` uses the existing directory `hybris/mw/<name>` and runs
    dhd's `buildmw` with its img-boot preparation (util.sh:278-298): remove
    the installed img-boot from the target, then install
    `droid-hal-pdx246-kernel` and `-kernel-modules` from droid-local-repo.
  - `-o` (offline) skips buildmw's `git pull` (util.sh:262-265) and the
    target's `zypper ref`. This repo has no upstream to pull from.
  - `-N` skips the tag check: `get_package_version` dies on an untagged repo
    (util.sh:268-271, :96-129). It also passes `--no-fix-version` to mb2, so
    the package version stays the kernel version (D10).
- **Not `build_packages.sh -b`.** `-b` (`buildpkg`, util.sh:350-360) skips
  the img-boot preparation. Then every rebuild after a `-d`, which is exactly
  the case D9 requires, very likely fails *(inferred from the code of mb2,
  libsolv and the .inc; not run)*:
  1. mb2's `--output-dir` implies `--search-output-dir` (mb2:906-908). Every
     build_packages.sh build therefore runs `zypper in <BuildRequires>` and
     then `zypper dup --from ~plus-repo-1` over droid-local-repo
     (mb2:1845-1855).
  2. droid-local-repo still holds the img-boot of the previous build. It
     Obsoletes `droid-hal-pdx246-kernel-modules < 5.10.269` and Provides it
     (.inc:239-240); dhd's packages are version 0.0.6.
  3. libsolv treats an obsoleting package as an update candidate, so the dup
     replaces the freshly built kernel-modules with the old img-boot.
  4. The .inc's `rpm -q` and `rpm -ql droid-hal-pdx246-kernel-modules`
     (:155-157) then find no package: no kernel version, no module list.
  If `-b` is ever used, run these two steps before it:
  `sdk-assistant maintain sony-pdx246-aarch64 zypper -n rm droid-hal-img-boot`,
  then
  `sdk-assistant maintain sony-pdx246-aarch64 zypper -n --plus-repo $ANDROID_ROOT/droid-local-repo/pdx246 in --allow-unsigned-rpm droid-hal-pdx246-kernel droid-hal-pdx246-kernel-modules`.
- mb2 installs the remaining BuildRequires (tools, busybox-static, hw-ramdisk
  and others) into the target. The first time that is a download (T13).
- buildmw's cpio fix is not needed: the SDK target `sony-pdx246-aarch64`
  already has GNU cpio (`cpio-2.15+git3` in its rpmdb) and no
  busybox-symlinks-cpio.

### D2. hybris-initrd pin: 7b972b6, not the reference's ecb295c

See SUBMODULES.md. In short:
- `afb537a` makes a normal boot load only `modules.load`, the 86 first-stage
  modules that include UFS (ref initrd `7b972b6:main-init:17-25`,
  `usr/bin/functions.sh:10-29`).
- The recovery image keeps loading `modules.load.recovery` (302 modules).
- `recovery-init` is identical at both pins.

### D3. mkbootimg_cmd

```
mkbootimg --header_version 4 --os_version 16.0.0 --os_patch_level 2026-09 --kernel %{kernel} --ramdisk %{initrd} --output
```

- **Header v4**, as the LineageOS boot.img
  (`device/sony/pdx246/BoardConfig.mk:59,73`; the unpacked LineageOS boot.img
  is v4, see findings.md, boot-layout FACTS).
- **No `--dtb`, `--base`, `--pagesize`.** For v3 and later, mkbootimg writes a
  dtb only into vendor_boot and uses a fixed 4096 page size
  (`system/tools/mkbootimg/mkbootimg.py:616-626`, `:657-658`). The dtb the
  device uses is the one in vendor_boot_a.
- **No `--cmdline`.** The device branch puts the whole cmdline in
  `BOARD_KERNEL_CMDLINE`, including `audit=0`
  (`device/sony/pdx246/BoardConfig.mk:68-71`, commit d7d7056). On header v4
  that lands in vendor_boot, and the bootloader appends it to the boot
  image's cmdline. The LineageOS boot.img's cmdline is empty too.
  - `audit=0` here would only be a duplicate.
  - `androidboot.selinux=permissive` (pdx235 spec line 3, murray, Nagara) is
    left out on purpose. Under Sailfish OS nothing reads it: the hybris patch
    compiles out droid-hal-init's `StatusFromProperty()`/`IsEnforcing()`, and
    systemd does the SELinux setup
    (`hybris-patches/system/core/0017-hybris-Disable-SELinux.patch:26,192-209`).
  - The kernel has `CONFIG_SECURITY_SELINUX_DEVELOP=y`
    (`out/target/product/pdx246/obj/KERNEL_OBJ/.config:6766`), so a
    permissive `/etc/selinux/config` from droid-config works without a cmdline
    flag.
  - If a later finding needs a boot-only argument (one LineageOS recovery must
    not get), add it here. Everything else belongs in `BOARD_KERNEL_CMDLINE`.
- **`--os_version 16.0.0 --os_patch_level 2026-09`** are the values of the
  flashed LineageOS boot.img (findings.md boot-layout FACTS; vendor/lineage
  bp4a `RELEASE_PLATFORM_SECURITY_PATCH` 2026-09-01).
  - A lower patch level than the TEE has seen may invalidate KeyMint keys
    *(inferred)*.
  - Raise both together with the LineageOS base.
- No AVB footer or vbmeta macros (new in `4f6bf7a`). vbmeta is flashed with
  verification disabled (flags 3), so the bootloader accepts an unsigned
  boot_a (orange state; `device/sony/pdx246/BoardConfig.mk:254-278`,
  `device/sony/pdx246/flash.sh:15-74`, per findings.md). If vbmeta is ever
  reflashed without `--disable-verity --disable-verification`, this image will
  no longer boot.
- Size limit: boot_a is 100663296 bytes (`BoardConfig.mk:184`). The kernel is
  about 45 MB. Check both images after the first build (TODO T7).

### D4. initrd_use_lz4 1 is required, not a preference

- The bootloader loads the vendor ramdisk (LZ4) and puts this ramdisk right
  behind it.
  - Evidence: AOSP vendor_boot design, and LineageOS on pdx246 boots LZ4
    vendor ramdisk + LZ4 generic ramdisk this way (verified working).
- The kernel's initramfs unpacker picks a decompressor per segment by magic
  (`kernel/sony/sm6450/init/initramfs.c:485-516`; table in
  `lib/decompress.c:52-58`). Each segment could therefore use its own format,
  but only if the previous decompressor stops at the segment boundary.
- `unlz4` in buffer mode does not stop there
  (`lib/decompress_unlz4.c:118-169`). After a chunk it reads the next 4
  bytes:
  - a new LZ4 legacy magic: it carries on;
  - 0: it stops;
  - anything else: it treats the bytes as a chunk length.
- So a gzip ramdisk (`1f 8b 08 00`) right after the LZ4 vendor ramdisk would
  be decoded as a corrupt LZ4 chunk ("Decoding failed", then "decompressor
  failed"), and /init would never be unpacked *(inferred from the code, not
  tested)*.
- LZ4 behind LZ4 is the proven case. hybris-initrd's LZ4 mode is the same
  legacy format Android uses (`moslo-build.sh -l` runs
  `lz4 -f -l -12 --favor-decSpeed`,
  github.com/sailfishos/hw-ramdisk `initfs/scripts/moslo-build.sh`; ref initrd
  `mksfosinitrd.sh:24-27,194-196`).
- The Sailfish kernel has both `CONFIG_RD_LZ4=y` and `CONFIG_RD_GZIP=y`
  (`KERNEL_OBJ/.config:193,198`).

### D5. Kernel modules: what the initrd loads and from where

- Neither image carries modules of its own. mksfosinitrd copies modules only
  in the vendor_boot modes (ref initrd `mksfosinitrd.sh:175-191`). This spec
  uses none of them.
- The modules come from vendor_boot_a's ramdisk: 302 `.ko` files with
  `modules.load` (86), `modules.load.recovery` (302) and `modules.dep`
  directly in `/lib/modules`.
  - Evidence: the vendor ramdisk of the LineageOS vendor_boot.img, unpacked
    with `unpack_bootimg`; `device/sony/pdx246/BoardConfig.mk:136-140`.
- The two archives merge at `/lib/modules`. The hybris ramdisk's skeleton has
  `/lib` and `/lib/modules` as real directories (hw-ramdisk
  `initfs/skeleton/dir-list`), and the kernel's cpio extraction keeps an
  existing directory of the same type. *(inferred; check with T5)*
- `load_kernel_modules` (ref initrd `usr/bin/functions.sh:10-29`):
  - symlinks `/lib/modules/$(uname -r)` to `/lib/modules`;
  - runs `busybox-static modprobe <name>` for each line of the selected list.
- vendor_boot's `modules.dep` uses absolute `/lib/modules/x.ko` paths (seen
  in the unpacked ramdisk), which work through that symlink.
- busybox's small modprobe did not do this properly. The full modprobe
  arrived in `sailfishos/busybox` a37f6d1, tag 1.36.1+git9 (JB#63804). It is
  the same fix hybris-boot needed (`external/busybox` c2563fb).
  - The 5.1.0.11 target has busybox 1.36.1+git10 (strings of the target's
    rpmdb).
  - The spec adds `BuildRequires: busybox-static >= 1.36.1+git9`, so an older
    target fails at build time, not at boot.
- Lists by mode (ref initrd `7b972b6:main-init:17-25`):
  - normal (`hybris-boot.img`): `modules.load`. UFS is in it
    (`device/sony/pdx246/modules.load:64` ufs_qcom, plus phy-qcom-ufs*,
    ufshcd-crypto-qti, hwkm). dwc3-msm, msm_drm and touch are not. They load
    later from vendor_dlkm (`vendor_dlkm.modules.load:112` dwc3-msm, `:262`
    msm_drm).
  - recovery (`hybris-recovery.img`): `modules.load.recovery`, which adds
    dwc3-msm and its PHYs (`recovery.modules.load:112`) and msm_drm (`:209`).
- Consequences:
  - The normal boot has no USB and no display in the initrd. On failure
    `normal-init` shows a yamui message, which nothing draws on pdx246, and
    runs `reboot2 recovery` (ref initrd `normal-init:22-27`). That boots
    recovery_a, the LineageOS recovery, on the Sailfish kernel and
    vendor_boot (TODO T8).
  - Use the recovery image for debugging (D6).
  - busybox ignores `modules.blocklist`. So the recovery image also loads
    wil6210 (blocklisted, but in the recovery list; findings.md). It is
    harmless without the 11ad hardware *(inferred)*.
  - No udev and no firmware helper run in the initrd, and the cmdline forces
    the sysfs fallback. A synchronous `request_firmware` in a probe would
    wait 60 s. The 86-module normal list is lower risk than the 302 list
    (TODO T3).
- Every module in vendor_boot and vendor_dlkm must match this image's kernel
  (MODVERSIONS, about 10,000 changed CRCs). Hence D8/D9.

### D6. USB/telnet debug path and the recovery-init override

- Only `recovery-init` (in `hybris-recovery.img`) brings up USB: an RNDIS
  gadget, 10.42.66.66, udhcpd, and telnetd running the recovery menu (ref
  initrd `recovery-init:37-73,132-166`).
- Its `usb_setup_configfs` has two steps:
  - it reads `androidboot.usbcontroller` from `/proc/bootconfig`
    (`a600000.dwc3`, from `BoardConfig.mk:94-97`);
  - it writes `peripheral` through `/sys/class/udc/<udc>/device/../mode`.
- On pdx246 the UDC exists only after `peripheral` is written to
  `/sys/bus/platform/devices/a600000.ssusb/mode`. The device's own recovery
  does exactly this (`device/sony/pdx246/rootdir/etc/init.recovery.qcom.rc:32-36`).
  Unpatched, there is no gadget and no telnet.
- This is the same problem hybris-boot's init-script had. It was fixed on
  branch hybris-23.2 in 24dc2d0.
- Fix: the override `initrd-pdx246/recovery-init` is the upstream file plus
  one block before the generic mode write. If `/sys/class/udc/<udc>` is
  missing, the block:
  1. takes the glue name from `androidboot.usb.dwc3_msm`, or else
     `<address>.ssusb`, as the device rc does;
  2. waits up to 5 s for the glue's `mode` attribute (dwc3-msm may still be
     probing);
  3. writes `peripheral`;
  4. waits up to 5 s for the UDC;
  5. logs the result to kmsg.
  Devices whose UDC already exists skip the block.
- The code was tested with busybox ash against a fake sysfs: the UDC appears
  after 0.6 s; with the mode attribute late and no UDC, it times out after
  about 6 s. Not yet tested on the device (T3).
- Mechanism:
  - The .inc copies `initrd-<device>/*` over the initrd tree before building
    (ref initrd `droid-hal-device-img-boot.inc:307-311`). Only whole-file
    overrides are possible: the device spec cannot add to the .inc's
    `%build`.
  - The override is generated from
    `patches/initrd/0001-recovery-init-Switch-dwc3-msm-glue-to-peripheral-when-the-UDC-is-missing.patch`.
  - `tools/check-initrd-overrides.sh` checks that override = upstream +
    patch, so a submodule bump cannot silently freeze an old recovery-init.
    It was tested on a throwaway copy of the repo: ok at both pins, and it
    fails on a tampered override and on an override without a patch.
  - The patch applies with `git apply` and `patch -p1` (blob `c7d9a9f` =
    upstream at both pins).
- This fix covers only the recovery/debug initrd. The normal initrd has no
  USB at all (D5), and in the running OS droid-config's
  `usb-moded-configfs-setup.sh` has its own timed fallback (see the contract
  below).
- Also for hybris-boot 24dc2d0, outside this repo: it checks for
  `<glue>/mode` once without waiting. If dwc3-msm probes late there, the same
  5 s wait would help.
- Not changed: `rndis_bam.rndis` (its mkdir fails harmlessly on GKI), and
  `echo /bin/mdev > /proc/sys/kernel/hotplug`, which fails harmlessly because
  `CONFIG_UEVENT_HELPER` is unset (`KERNEL_OBJ/.config:1774`). `/dev` is
  devtmpfs (`:1775-1776`).

### D7. Other macros

| Macro | Value | Why |
|---|---|---|
| `root_part_label` | `userdata` | sailfish.img001 goes to userdata (sda96). `root-mount` finds it by GPT label (ref initrd `sbin/root-mount:27-42`). `find-mmc-bypartlabel` scans `sd[a-z]*` and waits about 5 s plus 5 s (github.com/sailfishos/initrd-helpers `find-mmc-bypartlabel`). |
| `lvm_root_size` | `10000` | The reference uses this value, and the hybris-initrd maintainer: "we have been using 10000 on newer devices" (IRCLOGS.md:797). pdx246 has the same 128 GB class of storage (userdata about 98.8 GiB). |
| `initrd_use_lz4` | `1` | D4 |
| `display_brightness_path` | `/sys/class/backlight/panel0-backlight/brightness` | `init.recovery.qcom.rc:29`; `init.qcom.rc:182` |
| `display_brightness` | `1024` | The panel range is 0..4095 (`kernel/sony/sm6450-devicetrees/qcom/parrot-sde-display-qrd.dtsi:3-9`, `bl-max-level`/`brightness-max-level` 4095), so 1024 is 25 %, as murray, Nagara and pdx235 use. Only the recovery image has a display (D5). Confirm `max_brightness` on the device (T1). |
| `bcb_part_label` | not set | `bcb-clear` zeroes misc's first 2 KiB and reboots if any boot command is present (ref initrd `sbin/bcb-clear`). On pdx246 recovery is a separate partition the bootloader picks itself. A stale "boot-recovery" would boot recovery_a before this initrd runs, so the reboot gains nothing and only risks loops. |
| `factory_part_label` | default `fimage` (absent) | There is no fimage partition. A factory reset from Settings therefore fails in `root-mount` and reboots to recovery_a, the same as on the reference ports. droid-config should hide or document this (T12). |
| `battery_capacity_*` | defaults | The threshold is 0, so this is unused. The default glob `*_battery` would not match pdx246's `battery` supply *(inferred)*. |
| `initrd_combined`, `initrd_separate_ramdisks`, `vendor_boot_mkbootimg_cmd`, `init_boot_mkbootimg_cmd`, `custom_bootconfig`, avbtool macros | not set | D3, D8 |

### D8. Who ships which image, and on-device updates (option P)

All four images are one matched set from one Sailfish OS build.

| Image | Built by | Package | First install (D11) | When the package is upgraded on the phone |
|---|---|---|---|---|
| hybris-boot.img | this repo | droid-hal-pdx246-img-boot | `boot_a`, from the bootloader | the .inc's %post registers the oneshot `/var/lib/platform-updates/flash-bootimg.sh` (:520-525); it writes the boot set (below) |
| hybris-recovery.img | this repo | droid-hal-pdx246-img-recovery | not flashed; by hand to boot_a for debugging | **none**: droid-config ships no `flash-recoveryimg.sh` (the .inc's %post only tries to register it, :492-495, and add-preinit-oneshot refuses a missing job). recovery_a stays the LineageOS ramdisk-only recovery, because the bootloader rejects a recovery image with a kernel (findings.md boot-layout FACTS; PORTING-NOTES:3761-3763) |
| vendor_boot.img | Android build (`vendorbootimage`, part of hybris-hal) | droid-hal-pdx246-vendor_boot (dhd `enable_vendor_boot_update 1`) | `vendor_boot_a`, from the bootloader | dhd's %post registers `flash-vendor_boot.sh`; it writes the boot set |
| dtbo.img | Android build | droid-hal-pdx246-kernel-dtbo (always built by dhd; `enable_dtbo_update 1` adds the oneshot) | `dtbo_a`, from the bootloader | `flash-dtbo.sh`; it writes the boot set |
| vendor_dlkm.img, vendor_dlkm.release | Android build (`vendor_dlkmimage`); the release file names the kernel release of that build | droid-hal-pdx246-vendor_dlkm | `vendor_dlkm_a` (logical, in super), from fastbootd | the package's %post registers `flash-vendor_dlkm.sh` |

**The boot set** (droid-config-pdx246, `pdx246-kernel-set.sh`, function
`ks_flash_boot_set`, called by flash-bootimg.sh, flash-vendor_boot.sh and
flash-dtbo.sh):
- writes boot_a, vendor_boot_a and dtbo_a together. Whichever of the three
  oneshots runs first writes all three; the others find them up to date.
- writes nothing unless the kernel release in `/boot/hybris-boot.img` equals
  `/boot/vendor_dlkm.release`, i.e. hybris-boot.img and the droid-hal images
  belong to one build. Otherwise it exits non-zero and stays registered.
- checks every write with `ks_part_matches` (the partition starts with
  exactly the image's bytes).
- when the kernel release changes, it also registers flash-vendor_dlkm.sh,
  and flashes nothing if it cannot.
- when it rewrites vendor_boot_a, it writes
  `/var/lib/platform-updates/.pdx246-set-written` with
  `/proc/sys/kernel/random/boot_id`.

**flash-vendor_dlkm.sh** (droid-config-pdx246):
- writes vendor_dlkm_a in preinit, before `/vendor_dlkm` is mounted, and only
  once the running kernel is the one the modules were built for
  (`uname -r` = `/boot/vendor_dlkm.release`): the first boot of a new kernel.
- exits 1 and stays registered while `.pdx246-set-written` holds the current
  boot_id. In the boot that rewrote vendor_boot_a, the initrd had already
  loaded the old first-stage modules, so the new second-stage modules wait
  one more boot. This also covers a rebuild that changes only the modules and
  keeps the kernel release.
- fails early if `CPUCHECK_STRING` is found neither in the DT model nor in
  `/proc/cpuinfo` (flash-partition would otherwise exit 0 without writing).
- maps vendor_dlkm_a read-write under a private dm name from the super
  metadata (parse-android-dynparts, slot a). It never writes the metadata, so
  the partition cannot grow; an image larger than vendor_dlkm_a has to be
  flashed from fastbootd.
- verifies the written partition: unsparse the image with simg2img if it is
  sparse, then `cmp` the first image-size bytes of the partition against it.
  On a mismatch it fails and stays registered.

Status: drafted; the read-only parts checked on the phone 2026-10-17 (droid-config
D21: release extraction fixed for BusyBox, CPU check, slot check, read-back
comparison), the upgrades themselves not yet run (droid-config R11). Until it is
tested, do kernel updates with the D11 flash procedure. Q1 asks the user to
confirm P.

Why the Android-built vendor_boot, not one built here:
- The alternative is `vendor_boot_mkbootimg_cmd` with droid-hal's
  `have_custom_vendor_boot`, as the official murray image does
  (github.com/mer-hybris/droid-hal-img-boot-sony-murray, spec) and as the
  Nagara LVM repo did. That repo is now marked "Not used anymore".
1. A v4 vendor_boot carries the cmdline, the bootconfig
   (`androidboot.hardware=qcom`, `usbcontroller`, `memcg`), the dtb, the load
   offsets and the full vendor ramdisk. The Android build generates all of
   these from BoardConfig.mk. Rebuilding them in a spec creates a second
   source of truth for each, and mksfosinitrd's vendor_boot mode packs only
   `lib/modules` (ref initrd `mksfosinitrd.sh:109-112,183-191`). That drops
   the ramdisk's `system/etc/fstab.default` and first-stage fs tools.
2. The rescue path depends on that layout. LineageOS recovery_a is
   ramdisk-only and boots with boot_a's kernel and vendor_boot_a. It is only
   known to work with the Android-built vendor ramdisk (T8).
3. hybris-initrd needs nothing in vendor_boot except `lib/modules`, which the
   Android vendor ramdisk already has (D5).
4. This matches the decided install route ("Sailfish-built vendor_boot.img")
   and what Nagara does now. droid-config-sony-nagara's `flash-config.sh`
   flashes `vendor_boot.img`, its pattern Requires
   `droid-hal-%{device}-vendor_boot`, and its droid-hal sets
   `enable_vendor_boot_update`.

The cost of this choice is that hybris-boot.img (this package) and the other
three images (droid-hal) come from two source packages. D9 pins them
together.

**Slot a only.** Nagara's scripts write both slots
(`flash-partition boot_a …; flash-partition boot_b …`). On pdx246 Sailfish
OS runs from slot a only, and every script and flash step uses explicit `_a`
names. Slot b holds no bootable LineageOS (Virtual A/B keeps one copy of the
dynamic partitions); rollback means reflashing the saved slot-a LineageOS
set. Slot a must be marked successful, or the bootloader fails over to the
empty slot b after about 7 boots: droid-config's `pdx246-mark-slot.service`
does that once the boot HAL runs (after droid-hal-init).

**Never update boot without vendor_boot.** If boot_a got a new kernel while
vendor_boot_a kept the old modules, UFS would not load: no root, and
LineageOS recovery fails too, because it needs the same modules. Only
fastboot from the bootloader key combo recovers the phone. The boot set
above prevents this:
- `enable_vendor_boot_update` and `enable_dtbo_update` are mandatory in
  droid-hal, so the three oneshots exist;
- the img-boot %post is unconditional in the .inc, and the set logic, not
  the order of the oneshots, decides what is written.

### D9. Same-build pin for vendor_boot, dtbo and vendor_dlkm (deviation from the template)

The spec adds:
```
Requires: droid-hal-pdx246-vendor_boot = <version-release of the droid-hal-pdx246-kernel it packed>
Requires: droid-hal-pdx246-kernel-dtbo = <same>
Requires: droid-hal-pdx246-vendor_dlkm = <same>
```
- The value comes from `rpm -q` at build time, the same way the .inc reads
  the kernel version (:150-158).
- It is empty while rpmspec only queries BuildRequires, before the kernel is
  installed. In that case no Requires is emitted.
- All droid-hal-pdx246 subpackages of one build share version-release:
  dhd's `Release: %{rel_date}` (dhd `droid-hal-device.inc:199`), and the
  `vendor_dlkm` subpackage of droid-hal-pdx246.spec sets no version of its
  own.
- Effect: mic cannot assemble an image, and zypper cannot install, a
  hybris-boot.img whose kernel does not match the vendor_boot (first-stage
  modules, dtb), dtbo and vendor_dlkm (second-stage modules) next to it.
  `build_packages.sh -d` deletes the previous droid-hal-pdx246 RPMs except
  the img-* ones (dhd `util.sh:155`), so an img-boot that was not rebuilt
  after a `-d` has unsatisfiable Requires. Rebuild this package after every
  `-d` with the D1 command.
- The official template does not do this. The 10 IV porter was only told to
  put `-vendor_boot` and `-kernel-dtbo` into the patterns (IRCLOGS.md:804-811).
  This is Q3.
- img-boot's own release changes with every build since 2026-10-17 (D10, V1),
  so a rebuild that pins a newer droid-hal build is an upgrade.

### D10. Package version

- Locally, the .inc sets `Version: %{localver}`, the kernel version cut at
  the first `-` (5.10.269), with `Release: 1` (:159, :179-184).
- mb2 overrides Version from git tags unless `--no-fix-version` is given
  ("No tags describe the HEAD, will not fix package version": mb2:1960-1990).
  The D1 command passes `-N`, which sets `--no-fix-version`, so the version is
  the kernel version even if the repo is tagged later. The Obsoletes of
  droid-hal-pdx246-kernel-modules (0.0.6) then works.
- **V1, implemented 2026-10-17:** the spec defines `img_boot_release` as a
  build stamp, `%(date +'%%Y%%m%%d%%H%%M')` like dhd's `rel_date`, and
  includes `initrd-pdx246/droid-hal-device-img-boot.inc`, which is hybris-initrd's
  .inc plus `patches/initrd/0002` (`Release: %{?img_boot_release}%{!?img_boot_release:1}`;
  tools/check-initrd-overrides.sh checks it, and the patch is an upstream
  candidate). Every build now upgrades the installed package, including
  the 5.10.269-1 builds on phones so far (rpm compares 2026... > 1); OBS
  replaces the release with its own counter anyway. The tag route below was
  not taken: it would change Version and needs the Obsoletes rechecked. What
  follows is the original analysis.
- **TODO V1 (as found):** Release is 1 for every rebuild with the same
  kernel sublevel. A rebuild with a new kernel commit, or one that pins a
  newer droid-hal build, is still 5.10.269-1. On the phone, zypper would not
  see it as an update, and the installed img-boot would keep requiring the
  old droid-hal version-release (D9), which blocks the droid-hal upgrade. The
  on-device update path of D8 is therefore unreliable until this changes. It
  must change per build before any update channel exists:
  - either tag the repo and drop `-N`, so that mb2 derives the version from
    the tag (the tag must sort above dhd's 0.0.6 and keep the Obsoletes of
    kernel-modules working);
  - or derive Release from the droid-hal release (the value D9 already reads).
    The .inc hard-codes `Release: 1`, so this needs a hybris-initrd change
    (upstream) or a whole-file override of the .inc.
- Do not upload droid-hal's own img-boot or img-recovery anywhere. A
  higher-versioned one wins (IRCLOGS.md:1032-1035). droid-hal must define
  `have_custom_img_boot` and `have_custom_img_recovery`.

### D11. Flash procedure (implemented by droid-config-pdx246)

droid-config's `sparse/boot/flash-config.sh` (FLASH_OPS for dcd's
`flash.sh`), `flash-preflight.sh` and `flashing-README.txt` implement it.
**fastbootd first**:

```
# in the Sony bootloader (fastboot mode)
fastboot getvar secure                 # flash.sh dry run: getvar_fail_if secure yes
fastboot --set-active=a
fastboot reboot fastboot
./flash-preflight.sh                   # runs its getvars in fastbootd
# in fastbootd
fastboot flash vendor_dlkm_a vendor_dlkm.img
fastboot flash userdata sailfish.img001
fastboot reboot bootloader
# in the bootloader
fastboot flash boot_a hybris-boot.img
fastboot flash vendor_boot_a vendor_boot.img
fastboot flash dtbo_a dtbo.img
fastboot --set-active=a
fastboot reboot
```

- Why fastbootd first: on the first install, recovery_a (ramdisk-only; it
  hosts fastbootd) still boots on LineageOS's boot_a kernel and
  vendor_boot_a, which is known to work. With the bootloader partitions
  first, fastbootd would have to start on the Sailfish kernel and
  vendor_boot, which is untested (T8).
- `flash-preflight.sh` (droid-config, shipped through out-of-image-files)
  exits 1 with a clear message unless, in fastbootd,
  `fastboot getvar current-slot` is `a`,
  `fastboot getvar snapshot-update-status` is `none` and
  `fastboot getvar is-logical:vendor_dlkm_a` is `yes`. The getvars run in
  fastbootd, because the Sony bootloader fails many getvar names. Reason:
  fastbootd looks up logical partitions in the current slot's metadata and
  writes resized tables to every metadata slot
  (`system/core/fastboot/device/utility.cpp:201-223`), and it refuses
  userdata during a pending snapshot merge only after the vendor_dlkm_a flash
  has already cancelled that partition's snapshot
  (`commands.cpp:81-87, 587-619`; status from `variables.cpp:464-486`).
- (a) Before flashing, LineageOS must be installed on slot a and booted once
  to the home screen and left a minute, so the Virtual A/B merge completes.
- (b) Re-flashing over an installed Sailfish OS: fastbootd then runs on the
  Sailfish kernel. If `fastboot reboot fastboot` does not reach fastbootd,
  flash the saved LineageOS boot_a, vendor_boot_a and dtbo_a from the
  bootloader first, then run `./flash.sh` again.
- (c) If flash.sh stops halfway (USB drop, the pdx246 "TRAP 2" of
  PORTING-NOTES), reconnect until `fastboot devices` lists the phone, run
  `fastboot reboot bootloader`, and start `./flash.sh` again. fastbootd
  answers `secure: yes` (LineageOS recovery has `ro.secure=1`), so a rerun
  started in fastbootd stops at the dry run; flash-config's
  `GETVAR_ERROR_secure` therefore adds: "If the phone shows the fastbootd
  screen (e.g. after an interrupted run), run fastboot reboot bootloader and
  start ./flash.sh again."
- (d) Slot b holds no bootable LineageOS (Virtual A/B keeps one copy of the
  dynamic partitions); rollback = reflash the saved slot-a LineageOS set.
- Explicit `_a` names throughout. Large images (userdata, vendor_dlkm) go
  through fastbootd, which reports a usable max-download-size.

---

## Contract with the other adaptation repos

**Packages and pins.** droid-hal-pdx246 (`rpm/`, dhd be67bbc) builds
droid-hal-pdx246 with -devel, -users, -tools, -kernel, -kernel-modules,
-detritus, -kernel-dtbo, -vendor_boot and -vendor_dlkm. This repo
(`hybris/mw/droid-hal-img-boot-pdx246`, hybris-initrd 7b972b6) builds
droid-hal-pdx246-img-boot and -img-recovery. droid-config-pdx246 and its
sub-packages come from `hybris/droid-configs` (droid-hal-configs 1dae7f2),
droid-hal-version-pdx246 from `hybris/droid-hal-version-pdx246`
(droid-hal-version 09c2745).

**Images.** hybris-boot.img (img-boot), vendor_boot.img (droid-hal
-vendor_boot), dtbo.img (-kernel-dtbo), vendor_dlkm.img and
vendor_dlkm.release (-vendor_dlkm). All four are one matched set from one
Sailfish OS build.

**droid-hal-pdx246 (`rpm/`)** must:
- define `have_custom_img_boot 1` and `have_custom_img_recovery 1`. Otherwise
  dhd builds packages with the same names (dhd `droid-hal-device.inc:287-310`;
  unchanged in master 775f6c0).
- define `enable_vendor_boot_update 1` and `enable_dtbo_update 1` (D8).
- **not** define `have_custom_vendor_boot`. Otherwise dhd builds
  `kernel-modules-vendor_boot` and no vendor_boot.img (dhd :364-383, :1045-1049).
- keep building the `tools` subpackage (the default). The .inc
  BuildRequires `droid-hal-pdx246-tools` for mkbootimg (:196-200, dhd :254-262).
- not define `installable_zip` at all (findings.md CRITIC).
  `enable_kernel_update` has no effect once `have_custom_img_boot` is set (dhd :287-300).
- ship `/boot/vendor_dlkm.img` and `/boot/vendor_dlkm.release` in
  droid-hal-pdx246-vendor_dlkm, at the same version-release as -kernel,
  -vendor_boot and -kernel-dtbo; its %post registers `flash-vendor_dlkm.sh`.
  This spec Requires all three at that version-release (D9).

**droid-config-pdx246 (`hybris/droid-configs`)** must:
- in the patterns, Require `droid-hal-pdx246-img-boot`,
  `droid-hal-pdx246-img-recovery` (for the zip), `droid-hal-pdx246-vendor_boot`,
  `droid-hal-pdx246-kernel-dtbo` and `droid-hal-pdx246-vendor_dlkm`, and
  **not** `droid-hal-pdx246-kernel-modules` (IRCLOGS.md:804-808). img-boot
  provides the modules, and leaving kernel-modules out keeps
  `mic create loop` (findings.md CRITIC, dhd `build_packages.sh:410-427`).
- ship `sparse/var/lib/platform-updates/flash-bootimg.sh`,
  `flash-vendor_boot.sh` and `flash-dtbo.sh`, all writing the boot set
  through `ks_flash_boot_set`, and `flash-vendor_dlkm.sh`, as described in
  D8: slot a only, never `_b`.
- ship no `flash-recoveryimg.sh`.
- set `/var/lib/flash-partition/device-info` (CPUCHECK_STRING = DT model,
  TODO T14; blkid mode is fine).
- attach `/boot/hybris-boot.img`, `/boot/hybris-recovery.img`,
  `/boot/vendor_boot.img`, `/boot/dtbo.img` and `/boot/vendor_dlkm.img` in
  `kickstart/attachment/pdx246` (`/boot/vendor_dlkm.release` stays in the rootfs only).
- flash in the D11 order (FLASH_OPS, `flash-preflight.sh`,
  `flashing-README.txt` with (a) to (d), the extended `GETVAR_ERROR_secure`).
- USB in the running OS: `usb-moded-configfs-setup.sh` gets a timed
  fallback: after droid-hal-init, wait up to 30 s for
  `/sys/class/udc/a600000.dwc3`; if absent, write `peripheral` to
  `/sys/bus/platform/devices/a600000.ssusb/mode` and log it. It is marked as
  a bring-up aid, to be dropped once the Type-C role switch is shown to work.
  This repo's fix covers only the recovery/debug initrd (D6).
- slot marking: ship `sparse/usr/lib/systemd/system/pdx246-mark-slot.service`
  (After=droid-hal-init.service, Type=oneshot,
  ExecStart=/bin/sh /usr/bin/droid/droid-bootctl.sh,
  WantedBy=multi-user.target, with the wants symlink), so slot a is marked
  once the boot HAL runs.

**Kernel / device branch and build:** the cmdline lives in
`BOARD_KERNEL_CMDLINE` only (D3). On the host, after
`lunch lineage_pdx246-bp4a-userdebug`:
`PORT_ARCH=aarch64 make hybris-hal droidmedia vendor_dlkmimage audio.hidl_compat.default`.
Then, in the Platform SDK from `$ANDROID_ROOT`: `build_packages.sh -d`, `-c`,
`-o --mw` (after checking out pulseaudio-modules-droid 14.2.106),
`--mw=https://github.com/sailfish-on-nabu/parse-android-dynparts`,
`--mw=https://github.com/sailfishos/sensorfw --spec=rpm/sensorfw-qt5-binder.spec`, `-g`,
this repo with `-o -N --mw=droid-hal-img-boot-pdx246` (D1), `-v`, `-i`.

---

## First-boot test plan (every flash and reboot needs the user's OK; announce the series and its end)

Preconditions:
- LineageOS 23.2 on slot a, booted once to the home screen and left a
  minute, so the Virtual A/B merge is complete (D11 a; flash-preflight.sh
  checks it).
- The saved slot-a LineageOS set of that release (boot, vendor_boot, dtbo,
  vendor_dlkm, recovery) is at hand: it is the only rollback (D11 d).
- hybris-boot.img, vendor_boot.img, dtbo.img and vendor_dlkm.img come from
  one Sailfish OS build.

1. Extract the images from the local repo:
   `rpm2cpio droid-hal-pdx246-img-boot-*.rpm | cpio -idv ./boot/hybris-boot.img`,
   and the same for img-recovery. Check them with
   `unpack_bootimg.py --boot_img …`:
   - header 4, empty cmdline, os 16.0.0 / 2026-09;
   - the ramdisk starts with `02 21 4c 18` (LZ4 legacy);
   - size at most 100663296.
2. Install with `./flash.sh` (D11: fastbootd first, then the bootloader).
   It ends in the bootloader. Before the first boot, put the debug image in
   place of hybris-boot.img: try `fastboot boot hybris-recovery.img`; whether
   Sony's bootloader allows that is open (T2). Otherwise
   `fastboot flash boot_a hybris-recovery.img`, then `fastboot reboot`.
   Expected:
   - RNDIS on the host;
   - `telnet 10.42.66.66` opens the recovery menu. Use **only "Shell"**: the
     reset items wipe userdata.
   Check:
   - `dmesg | grep -e initrd: -e 'USB:'` (the module loading time, the T3
     firmware gaps);
   - `ls /sys/class/udc`, `ls -la /lib /lib/modules | head` (T5);
   - `find-mmc-bypartlabel userdata` should print `/dev/sda96`;
   - `lvm vgchange -a y sailfish`, then mount `/dev/sailfish/root` by hand.
3. From the bootloader, flash `hybris-boot.img` to boot_a and boot normally.
   Expected: the USB fallback of `usb-moded-configfs-setup.sh` gives RNDIS
   within about 30 s of droid-hal-init, and `pdx246-mark-slot.service` marks
   slot a successful (`fastboot getvar all`: slot-successful:a:yes).
4. If the normal boot fails, it reboots to recovery_a (LineageOS recovery on
   the Sailfish kernel, T8) or loops. Go back to step 2 with the debug image
   in boot_a. Never use recovery's persisted logs as evidence (DRAM decay).

---

## TODOs (device data or runtime tests)

- **T1** `cat /sys/class/backlight/panel0-backlight/max_brightness` (expected
  4095). Adjust `display_brightness`.
- **T2** Does Sony's bootloader support `fastboot boot` of a v4 boot image
  with vendor_boot from the partition? (findings.md boot-layout OPEN)
- **T3** In the recovery image: how long do the 302 modules take to load, are
  there 60 s firmware gaps, does the UDC appear after the mode write, do RNDIS
  and telnet work? If loading stalls, a further override (functions.sh:
  dwc3-msm and its PHYs first, or a short `/sys/class/firmware/timeout` that
  is reset before switch_root) is the next step. Not written yet, because it
  is speculative.
- **T4** Normal image: are the 86 first-stage modules enough for UFS to come
  up, and does `userdata` show up within `find-mmc-bypartlabel`'s about 10 s?
- **T5** Do the vendor and hybris ramdisks merge at `/lib/modules`
  (`ls -la /lib/modules | head`, `ls /lib/modules | wc -l` = 302 + lists)?
- **T6** After the first build: `rpm -q busybox-static` in the target, which
  should be ≥ 1.36.1+git9 (git10 expected).
- **T7** Sizes of hybris-boot.img and hybris-recovery.img, each at most
  100663296.
- **T8** Does LineageOS recovery_a still boot (adb, fastbootd) on the Sailfish
  kernel and Sailfish vendor_boot? It is the rescue path of D5 and D8, and
  the fastbootd of every re-flash over Sailfish OS (D11 b).
- **T9** Does `/dev/watchdog` exist in the initrd (main-init writes `V`)?
  `CONFIG_WATCHDOG_NOWAYOUT` is unset (`KERNEL_OBJ/.config:3316`), so this is
  low risk. Watch for resets during long first boots.
- **T10** KeyMint, fingerprint and keystore keep working with
  `os_patch_level 2026-09`.
- **T11** Does yamui draw in the recovery image (msm_drm loaded)? A blank
  screen is acceptable; telnet is what matters.
- **T12** Factory reset is unsupported (no fimage). Decide how droid-config
  presents this.
- **T13** The first build installs the .inc's BuildRequires into the target
  from the Sailfish OS 5.1.0.11 repositories: hw-ramdisk, initrd-helpers,
  initrd-logos, yamui, openssh, lvm2, cryptsetup, e2fsprogs, lz4, oneshot,
  busybox-static and others. **That is a download and needs the user's OK.**
  zypper shows the size when asked.
- **T14** The DT model string for droid-config's device-info (needs `adb root`).
  flash-vendor_dlkm.sh fails early until CPUCHECK_STRING matches it.
- **V1** img-boot's Release must change per build before any update channel
  exists (D10).

## Open questions for the user

- **Q1 answered 2026-10-17: P** (the user: "P is fine"). Tests: droid-config R11.
- **Q1 vendor_dlkm on kernel updates (as asked).** Option P is drafted across the repos
  (D8): droid-hal-pdx246-vendor_dlkm's %post and the boot set register
  `flash-vendor_dlkm.sh`, which rewrites vendor_dlkm_a in preinit at the first
  boot of the new kernel. Confirm P, or choose:
  - **(M)** No on-device kernel updates. Every kernel change is the D11 flash
    series. Then droid-hal drops the %post of -vendor_dlkm, and droid-config
    drops flash-vendor_dlkm.sh and the add-preinit-oneshot branch of the boot
    set.
  - **(N)** Nagara's method. A `droid-hal-pdx246-vendor-dlkm` package ships
    the build's vendor_dlkm tree into the rootfs at `/vendor_dlkm`
    (github.com/sailfishos-sony-nagara/droid-hal-vendor-dlkm), and nothing
    mounts or writes vendor_dlkm_a. Nagara's flash-config flashes boot,
    dtbo, vendor_boot and userdata only.

  P's remaining risks: it is untested on the phone; it writes inside super
  through its own dm mapping (only within vendor_dlkm_a's extents, metadata
  untouched); an image that outgrew the partition still needs fastbootd.
- **Q2** Confirm the hybris-initrd pin at upstream head 7b972b6 (used now;
  normal boot loads only the 86 first-stage modules) rather than the
  reference's ecb295c (all 302 on every boot).
- **Q3** Keep D9's same-build `Requires` on vendor_boot, kernel-dtbo and
  vendor_dlkm (used now)? It deviates from the official template, but it
  turns a mismatched set into a build or install error instead of a phone
  without UFS.
- **Q4** The override `initrd-pdx246/recovery-init` keeps Jolla's and OMP's
  notices and adds `SPDX-FileCopyrightText: Johannes Meyer zum Alten Borgloh`
  (still GPL-2.0-only). hybris-boot 24dc2d0 added no such line to
  init-script. Keep the line or drop it?

---

## PROVENANCE

Licences (changed 2026-10-11, the user's decision: each repository takes the
licence of the official code it builds on): files written for this port are
GPL-2.0-only like hybris-initrd (they were Apache-2.0 before), the
documentation is CC-BY-SA-4.0; Jolla's files keep GPL-2.0-only.

| File | Origin | Licence handling |
|---|---|---|
| `rpm/droid-hal-pdx246-img-boot.spec` | new. The macro interface is documented in mer-hybris/hybris-initrd@7b972b6:`droid-hal-device-img-boot.inc` (lines 1-127); the values come from pdx246 facts cited above. The shared macro lines (root_part_label userdata, display_brightness_path/1024, initrd_use_lz4 1, lvm_root_size 10000, the %include, BuildRequires python3-base) are functional and also in Jolla's mer-hybris/droid-hal-img-boot-sony-murray `rpm/droid-hal-pdx225-img-boot.spec`. The unlicensed sharks-dev spec was read for comparison, not copied. | GPL-2.0-only header in file (user) |
| `initrd-pdx246/recovery-init` | derived from mer-hybris/hybris-initrd@7b972b6:`recovery-init` (identical at ecb295c), plus one marked block | GPL-2.0-only kept. Jolla Mobile Ltd, Open Mobile Platform LLC and Jolla Ltd notices kept, with the years of that file's own header. User line added (Q4) |
| `patches/initrd/0001-recovery-init-Switch-dwc3-msm-glue-to-peripheral-when-the-UDC-is-missing.patch` | new patch against mer-hybris/hybris-initrd@7b972b6:`recovery-init` (context lines are Jolla's) | GPL-2.0-only with the upstream holders plus the user, via REUSE.toml |
| `tools/check-initrd-overrides.sh` | new | GPL-2.0-only header in file |
| `.gitignore` | new | GPL-2.0-only header in file |
| `REUSE.toml` | new | GPL-2.0-only header in file |
| `NOTES.md`, `README.md`, `SUBMODULES.md` | new | CC-BY-SA-4.0 via REUSE.toml |
| `.gitmodules` (created by `git submodule add`, SUBMODULES.md) | generated by git | GPL-2.0-only via REUSE.toml (it cannot carry a header) |
| `LICENSES/GPL-2.0-only.txt` | standard licence text, copied from `$ANDROID_ROOT/device/sony/pdx246/LICENSES/` | licence text (REUSE `LICENSES/`) |
| `LICENSES/CC-BY-SA-4.0.txt` | licence text in the form `reuse download` writes it, copied from the LineageOS 23.2 tree (`packages/apps/Twelve/LICENSES/CC-BY-SA-4.0.txt`) | licence text (REUSE `LICENSES/`) |
| `initrd/` (submodule, not in this repo) | mer-hybris/hybris-initrd@7b972b6f9498358bdf0a9df6ea1e2587405244c3 | GPL-2.0-only (Jolla), unchanged |

Nothing from Jolla's closed components and nothing from sharks-dev's
unlicensed files is included.
