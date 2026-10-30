#!/usr/bin/env python3
"""Execute the pinned, unmodified GApps installer in a disposable offline KVM VM."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

PINS = {
    'system-root-fstab.raw.img':'d004e3186585a57991c8e291cd7abf2c1cad7eb2c82b0c055de82894e0d3c795',
    'vendor-gps-null.raw.img':'7218d1ba6808fe45398cc096356303ea3f59833866c1cababb8aa670f5f6d996',
    'open_gapps-arm-11.0-pico-20220215.zip':'4df52af6b0dcc0f21d6e1dd943ef3088121354179782b9d0d48593ff127b4cc0',
}

INIT = r'''#!/bin/sh
export PATH=/sbin:/bin
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mkdir -p /dev/pts /dev/block
mount -t devpts devpts /dev/pts
fail() { echo "GAPPS_VM_FAILURE: $*"; sync; poweroff -f; }
for m in virtio_pci virtio_blk crc32c_generic ext4 loop binfmt_misc; do
  modprobe "$m" || fail "module $m"
done
for n in 1 2 3 4 5; do [ -b /dev/vdc ] && break; sleep 1; done
mount -t ext4 /dev/vdc /input || fail input_mount
exec > /dev/console 2>&1
echo GAPPS_VM_STARTED
ln -s /dev/vda /dev/block/system
ln -s /dev/vdb /dev/block/vendor
mount -t tmpfs tmpfs /data || fail data_tmpfs
mount -t tmpfs tmpfs /cache || fail cache_tmpfs
mount -t binfmt_misc binfmt_misc /proc/sys/fs/binfmt_misc || fail binfmt_mount
printf '%s\n' ':qemu-arm:M::\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x28\x00:\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff\xff:/bin/qemu-arm-static:' > /proc/sys/fs/binfmt_misc/register || fail binfmt_register
echo '/dev/block/system /system_root ext4 defaults 0 0' > /etc/fstab
echo '/dev/block/vendor /vendor ext4 ro 0 0' >> /etc/fstab
export ANDROID_ROOT=/system_root
unset OSTYPE
/bin/qemu-arm-static /input/busybox-arm uname -m || fail ARM_preflight
# Assert the guest can preserve SELinux xattrs on the independent filesystem.
mount /system_root || fail system_preflight_mount
printf test > /system_root/.gapps-host-xattr-probe
/bin/qemu-arm-static /input/busybox-arm chcon u:object_r:system_file:s0 /system_root/.gapps-host-xattr-probe || fail xattr_preflight
rm /system_root/.gapps-host-xattr-probe
umount /system_root || fail system_preflight_umount
# Original update-binary selects its ARM helper via QEMU's uname translation.
mkdir /recovery-bin
for applet in $(/bin/qemu-arm-static /input/busybox-arm --list); do
  ln -s /input/busybox-arm "/recovery-bin/$applet"
done
/recovery-bin/uname -m || fail binfmt_ARM_preflight
PATH=/recovery-bin:/sbin:/bin /bin/qemu-arm-static /input/busybox-arm ash /input/update-binary 3 3 /input/open_gapps-arm-11.0-pico-20220215.zip > /input/installer-console.txt 2>&1 3>>/input/installer-ui.txt
result=$?
echo "$result" > /input/installer.exit
cat /input/installer-console.txt
cat /input/installer-ui.txt
echo "GAPPS_INSTALLER_EXIT=$result"
sync
umount /system 2>/dev/null
umount /system_root 2>/dev/null
umount /vendor 2>/dev/null
cat /proc/mounts > /input/final-mounts.txt
sync
umount /input || fail input_umount
echo GAPPS_VM_FINISHED
poweroff -f
'''

GETPROP = r'''#!/bin/sh
# Recovery adapter: only read exact ROM properties; never invent unknown values.
for file in /system/build.prop /system/default.prop /system/product/build.prop /system/system_ext/build.prop /vendor/build.prop /default.prop; do
  [ -f "$file" ] || continue
  value=$(sed -n "s/^$1=//p" "$file" | head -n 1)
  if [ -n "$value" ]; then printf '%s\n' "$value"; exit 0; fi
done
exit 0
'''


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as fp:
        for data in iter(lambda:fp.read(4*1024*1024),b''):h.update(data)
    return h.hexdigest()


def run(command, **kwargs):
    return subprocess.run(command,check=True,**kwargs)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work',required=True,type=Path)
    ap.add_argument('--attempt',required=True)
    args=ap.parse_args();work=args.work.resolve()
    if not args.attempt.isalnum():raise ValueError('Simple fresh attempt name required')
    for name,expected in PINS.items():
        if sha(work/'inputs'/name)!=expected:raise ValueError('Input hash mismatch: '+name)
    out=work/('attempt-'+args.attempt);out.mkdir(exist_ok=False)
    pkg=out/'packages';pkg.mkdir()
    for name in ['busybox-static','qemu-user-static']:
        candidates=list((work/'debs').glob(name+'_*.deb'))
        if len(candidates)!=1:raise ValueError('Expected one Debian package '+name)
        run(['dpkg-deb','-x',str(candidates[0]),str(pkg)])
    root=out/'initramfs'
    for name in ['bin','sbin','proc','sys','dev','tmp','etc','input','system','system_root','vendor','data','cache','persist','product','system_ext','apex']:
        (root/name).mkdir(parents=True)
    bb=next(path for path in [pkg/'bin/busybox',pkg/'usr/bin/busybox'] if path.is_file())
    shutil.copyfile(bb,root/'bin/busybox');(root/'bin/busybox').chmod(0o755)
    shutil.copyfile(pkg/'usr/bin/qemu-arm-static',root/'bin/qemu-arm-static');(root/'bin/qemu-arm-static').chmod(0o755)
    applets=subprocess.check_output([str(bb),'--list'],text=True).splitlines()
    for applet in applets:
        if applet!='busybox':(root/'bin'/applet).symlink_to('/bin/busybox')
    (root/'sbin/sh').symlink_to('/bin/busybox')
    for name,text in [('getprop',GETPROP),('setenforce','#!/bin/sh\nexit 0\n'),('logcat','#!/bin/sh\nexit 1\n')]:
        (root/'sbin'/name).write_text(text);(root/'sbin'/name).chmod(0o755)
    kernel=os.uname().release
    modules=set()
    for module in ['virtio_pci','virtio_blk','crc32c_generic','ext4','loop','binfmt_misc']:
        deps=subprocess.check_output(['/usr/sbin/modprobe','-S',kernel,'--show-depends',module],text=True)
        for line in deps.splitlines():
            if line.startswith('insmod '):modules.add(Path(line.split()[1]))
    for source in modules:
        target=root/source.relative_to('/');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    module_root=Path('/lib/modules')/kernel
    for source in module_root.glob('modules.*'):
        if source.is_file():shutil.copyfile(source,root/'lib/modules'/kernel/source.name)
    (root/'init').write_text(INIT);(root/'init').chmod(0o755)
    archive=out/'initramfs.cpio.gz'
    # Paths are generated locally; shell pipeline never interpolates supplied data.
    with archive.open('wb') as fp:
        run(['/bin/sh','-c','find . -print0 | cpio --null -o --format=newc --owner=0:0 | gzip -1'],cwd=root,stdout=fp)
    media=out/'media';media.mkdir()
    zipname='open_gapps-arm-11.0-pico-20220215.zip'
    shutil.copyfile(work/'inputs'/zipname,media/zipname)
    (media/'gapps-config.txt').write_text('skipswypelibs\n')
    with zipfile.ZipFile(media/zipname) as z:
        for name in ['busybox-arm','META-INF/com/google/android/update-binary']:
            target=media/Path(name).name;target.write_bytes(z.read(name));target.chmod(0o755)
    candidate=out/'system-gapps.raw.img'
    shutil.copyfile(work/'inputs/system-root-fstab.raw.img',candidate)
    disk=out/'install-media.raw.img'
    with disk.open('wb') as fp:fp.truncate(512*1024*1024)
    run(['/usr/sbin/mkfs.ext4','-q','-F','-d',str(media),str(disk)])
    command=['/usr/bin/qemu-system-x86_64','-enable-kvm','-m','3072','-smp','2','-nodefaults',
             '-no-reboot','-nographic','-serial','stdio','-monitor','none','-nic','none',
             '-kernel',str(Path('/boot')/('vmlinuz-'+kernel)),'-initrd',str(archive),
             '-append','console=ttyS0 panic=1 rdinit=/init',
             '-drive','file='+str(candidate)+',format=raw,if=virtio',
             '-drive','file='+str(work/'inputs/vendor-gps-null.raw.img')+',format=raw,if=virtio,readonly=on',
             '-drive','file='+str(disk)+',format=raw,if=virtio']
    (out/'command.json').write_text(json.dumps(command,indent=2)+'\n')
    print('Starting isolated KVM installer; log '+str(out/'serial.log'),flush=True)
    with (out/'serial.log').open('wb') as fp:
        result=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=fp,stderr=subprocess.STDOUT,timeout=600)
    report={'qemu_exit':result.returncode,'candidate':str(candidate),'installer_result':'UNASSESSED',
            'system_sha256':sha(candidate),'gapps_config':'skipswypelibs\n',
            'hardware_authorized':False,'input_hashes':PINS,'debian_packages':{p.name:sha(p) for p in (work/'debs').glob('*.deb')}}
    (out/'host-run.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
    print((out/'serial.log').read_text(errors='replace')[-3000:],flush=True)


if __name__=='__main__':main()
