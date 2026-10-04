# SPDX-FileCopyrightText: Johannes Meyer zum Alten Borgloh
# SPDX-License-Identifier: Apache-2.0
#
# LVM boot image for the Sony Xperia 10 VI (pdx246): builds hybris-boot.img
# (flashed to boot_a) and the debug image hybris-recovery.img (USB telnet
# shell; flashed to boot_a by hand, never to recovery_a). The recipe is
# initrd/droid-hal-device-img-boot.inc from mer-hybris/hybris-initrd
# (GPL-2.0-only), which also documents every macro set here. NOTES.md gives the
# evidence for each value.
#
# This package does NOT build vendor_boot.img: droid-hal-pdx246 ships the
# Android-built one (enable_vendor_boot_update), and with it the dtb, the full
# kernel cmdline, the bootconfig and the vendor ramdisk whose lib/modules the
# initrd loads. Do not define vendor_boot_mkbootimg_cmd or init_boot_*.

%define device pdx246

# Boot header v4 like LineageOS's boot.img. A v4 boot image holds only the
# kernel, this ramdisk, a cmdline and the OS version fields; base, page size
# and offsets belong to vendor_boot, and mkbootimg drops --dtb for v3+.
# No --cmdline: the whole cmdline (BOARD_KERNEL_CMDLINE incl. audit=0) is in
# vendor_boot and the bootloader appends it, so anything here would only be a
# duplicate. androidboot.selinux is not read by anything under Sailfish OS
# (droid-hal-init's SELinux setup is compiled out by hybris-patches 0017).
# os_version/os_patch_level match the LineageOS boot.img the TEE has seen;
# never set them lower (KeyMint), raise them with the LineageOS base.
%define mkbootimg_cmd mkbootimg --header_version 4 --os_version 16.0.0 --os_patch_level 2026-09 --kernel %{kernel} --ramdisk %{initrd} --output

# The LVM volume group "sailfish" is on the GPT partition "userdata" (sda96),
# found by label, so no device path is hard-coded.
%define root_part_label userdata

# The root LV grows to 10000 MB on first boot; home takes the rest of
# userdata (about 89 GiB).
%define lvm_root_size 10000

# The bootloader places the LZ4 (legacy) vendor ramdisk directly in front of
# this ramdisk. The kernel's unlz4 reads on into whatever follows and can only
# step over another LZ4 stream (or zero padding); a gzip ramdisk right behind
# it is taken for a corrupt LZ4 chunk. So this ramdisk has to be LZ4 too.
%define initrd_use_lz4 1

# Panel backlight (DCS, 0..4095). The initrd sets this while yamui shows text;
# only the recovery image loads msm_drm, so the normal boot shows nothing.
%define display_brightness_path /sys/class/backlight/panel0-backlight/brightness
%define display_brightness 1024

# mkbootimg from droid-hal-pdx246-tools is a python3 script.
BuildRequires:  python3-base
# load_kernel_modules runs "busybox-static modprobe" on vendor_boot's modules;
# only 1.36.1+git9 and later have the full modprobe that does that properly
# (sailfishos/busybox a37f6d1, JB#63804). Without it there is no UFS, no root.
BuildRequires:  busybox-static >= 1.36.1+git9

# hybris-boot.img carries the kernel of the installed droid-hal-pdx246-kernel.
# It forms one matched set with vendor_boot.img (first-stage modules, dtb),
# dtbo.img and vendor_dlkm.img (second-stage modules), which must come from
# the same droid-hal-pdx246 build: the Sailfish kernel config changes the
# module CRCs, so any other vendor_boot leaves the initrd without UFS and any
# other vendor_dlkm leaves Sailfish OS without Wi-Fi, audio and modem. Pin all
# three to that build. Rebuild this package after every build_packages.sh -d,
# with build_packages.sh -o -N --mw=droid-hal-img-boot-pdx246 (README.md).
# TODO (NOTES.md D10): the .inc sets Release 1, so every rebuild with the same
# kernel sublevel has the same version-release; that must change per build
# before any update channel exists.
%define pdx246_dhd_vr %(rpm -q --qf '[%%{version}-%%{release}]' droid-hal-%{device}-kernel 2>/dev/null | grep -v 'is not installed' || :)
%if "%{pdx246_dhd_vr}" != ""
Requires:       droid-hal-%{device}-vendor_boot = %{pdx246_dhd_vr}
Requires:       droid-hal-%{device}-kernel-dtbo = %{pdx246_dhd_vr}
Requires:       droid-hal-%{device}-vendor_dlkm = %{pdx246_dhd_vr}
%endif

%include initrd/droid-hal-device-img-boot.inc
