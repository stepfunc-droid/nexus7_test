#!/usr/bin/env python3
"""Mac-only preservation of pinned Q2 inputs and a private online snapshot."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from nexus7_runtime import clone, digest, require

ROOT = Path(__file__).resolve().parents[2]
DEST = Path.home()/'nexus7'
BOOT = '50377dc8b9b304b00b300fa7927e56733c841d5d2ece9a90602874bb7f99c799'
LK = 'a76f4e138e5eaf5fa902bbee97604e7f5a06830c0f2028a3829c5b2985860c3a'
BASE = '060ba738de5fa0fa8e1d18e8db54fa31e48cc4826a870a060b444f2624498d5a'
DISK = '3cf28c2392d9daa945ae9e7b4edb52883330947a3ae4d9c74bb71e80d45ee811'


def main():
    release=DEST/'releases/20261030-Q2-gps-off'
    require(not release.exists(), 'Release already exists; never overwrite')
    require(not DEST.exists() or DEST.is_dir(), 'Destination is not a directory')
    src=ROOT/'out/phase6-v2-gps-null-R/pristine-Q1.raw.img'
    require(digest(src)==BASE,'Pristine Q1 source mismatch')
    boot=ROOT/'out/phase6-v2-root-route-O/artifacts/diagnostic.img'
    lk=ROOT/'out/lk2nd-flo-fastboot.img'
    require(digest(boot)==BOOT and digest(lk)==LK,'Boot input mismatch')
    for sub in ['masters','snapshots','disks','tools','runs','provenance']:
        (release/sub).mkdir(parents=True,exist_ok=False)
    release.chmod(0o700)
    master=release/'masters/lineage18.1-gps-off-clean.raw.img'
    clone(src,master)
    with master.open('r+b') as fp:
        fp.seek(1573912576+37246084)
        require(fp.read(4)==bytes.fromhex('70b502f0'),'Unexpected original GPS bytes')
        fp.seek(1573912576+37246084);fp.write(bytes.fromhex('00207047'))
        fp.flush();os.fsync(fp.fileno())
    require(digest(master)==DISK,'Reconstructed Q2 master mismatch')
    master.chmod(0o400)
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    snapshot=release/'snapshots/Q2-desktop-online.raw.img'
    clone(ROOT/'out/phase6-v2-gps-null-R/disk.raw.img',snapshot)
    snapshot.chmod(0o400)
    print('Master and online snapshot cloned; current live disk/server untouched',flush=True)
    files={}
    def copy(source,target):
        require(not target.exists(),'Destination exists')
        shutil.copyfile(source,target);require(digest(source)==digest(target),'Copy mismatch')
        files[str(target.relative_to(release))]=digest(target)
    copy(boot,release/'boot.img');copy(lk,release/'lk2nd.img')
    for name in ['phase6_v2_nbd_observed_server.py','nbd_partition_trace_server.py','phase6_v2_observe_usb.py']:
        copy(ROOT/'scripts/v2'/name,release/'tools'/name)
    copy(ROOT/'scripts/v2/nexus7_runtime.py',release/'nexus7.py')
    copy(ROOT/'scripts/v2/start-nbd.sh',release/'start-nbd.sh');(release/'start-nbd.sh').chmod(0o755)
    copy(ROOT/'out/phase6-v2-gps-null-R/partition-trace-map.json',release/'partition-trace-map.json')
    copy(ROOT/'out/phase6-v2-gps-null-R/result.json',release/'provenance/pre-run-host-gate.json')
    copy(ROOT/'diskless-v2/PHASE6_GPS_NULL_RUN_Q2.md',release/'provenance/Q2-result.md')
    files[str(master.relative_to(release))]=DISK
    files[str(snapshot.relative_to(release))]=digest(snapshot)
    state={'release':'20261030-Q2-gps-off','source_HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
           'snapshot_utc':now,'files':files,'evidence':'REAL_DEVICE_FACT: Q2 reached desktop; HOST_FACT: packaged bytes verified; new launcher IMPLEMENTED_UNPROVEN',
           'online_snapshot':'Filesystem consistency UNVERIFIED; live APFS clone, not clean shutdown; not newly boot-tested',
           'master':'Exact pre-run Q2 bytes, reconstructed from pinned pristine Q1 + four GPS bytes',
           'GPS':'unavailable, user accepted','data':'private images; never commit to Git',
           'existing_live_runtime':'unchanged original path/server12963/caffeinate14159'}
    (release/'release.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    (release/'SHA256SUMS').write_text(''.join(h+'  '+name+'\n' for name,h in sorted(files.items())))
    (release/'README.md').write_text('''# Nexus 7 无盘启动：Q2 成功版本

GPS 不可用；已实机完成 LineageOS 18.1 设置并进入桌面。新打包的启动脚本尚未实机运行。
boot.img / lk2nd.img 与成功运行输入完全一致。masters 是成功启动前的干净磁盘；每次新建数据环境会重新初始化。
snapshots/Q2-desktop-online.raw.img 保存归档时的用户设置，但属于在线快照，文件系统一致性未验证，并非干净关机备份。

以下命令在连接 Nexus 的 Mac 上执行，需要 PATH 中有 python3(3.11+) 和 fastboot：

    cd /Users/zhangjw/nexus7/releases/20261030-Q2-gps-off
    python3 nexus7.py verify
    python3 nexus7.py new-disk daily
    python3 nexus7.py serve disks/daily.raw.img

首次创建 daily 后，以后继续使用同一磁盘即可保留设置。不要重复 new-disk，也不要直接导出 masters/snapshots。
serve 等待 USB 出现；保持此终端打开，在另一终端、设备已进入 stock fastboot 时执行：

    cd /Users/zhangjw/nexus7/releases/20261030-Q2-gps-off
    python3 nexus7.py boot

boot 依次校验并 RAM 启动 lk2nd 和 boot.img，不刷写内部存储。NBD 仅绑定172.16.42.2:10810。
Mac 的专用 RNDIS/Ethernet Gadget 服务须手动配置172.16.42.2/255.255.255.0；路由器0.0.0.0。脚本不修改管理网卡。
设备运行时不可拔 USB、休眠/关闭 Mac 或停止 NBD。退出监控不停止后台存储服务；日志中的 server.pid 用于辨认服务。
只有设备已经关机或确认进入 fastboot 后才能停止该服务。当前旧版本服务仍在运行时，serve 会拒绝抢占10810。
图片和初始化数据仅存本地，不提交 Git。原始实验目录仍保留；本次归档不迁移正在运行的文件。
''')
    inputs=DEST/'inputs';inputs.mkdir(exist_ok=True)
    gapps=Path.home()/'Downloads/open_gapps-arm-11.0-pico-20220215.zip'
    copied=inputs/gapps.name
    require(not copied.exists(),'GApps destination exists')
    shutil.copyfile(gapps,copied)
    require(digest(gapps)==digest(copied),'GApps copy mismatch')
    with zipfile.ZipFile(copied) as z:
        require(z.testzip() is None,'GApps ZIP CRC failure')
        props=z.read('g.prop').decode()
        require('ro.addon.arch=arm\n' in props and 'ro.addon.sdk=30\n' in props and
                'ro.addon.open_type=pico\n' in props,'Wrong GApps variant')
    (inputs/(gapps.name+'.sha256')).write_text(digest(copied)+'  '+gapps.name+'\n')
    (DEST/'README.md').write_text('''# Nexus 7 正式使用资源

releases/20261030-Q2-gps-off/：已成功进桌面的无 GApps、GPS 不可用版本，含镜像、校验和使用说明。
inputs/：用户提供的 Open GApps ARM Android11 Pico ZIP 及 SHA256。GApps 尚未安装，后续单独派生版本。
当前设备仍使用原 nexus7_test 中的磁盘；归档不会移动或中断正在使用的文件。
''')
    report={'release':str(release),'master_sha256':DISK,'snapshot_sha256':files[str(snapshot.relative_to(release))],
            'snapshot_utc':now,'snapshot_consistency':'UNVERIFIED_ONLINE','boot_sha256':BOOT,'lk2nd_sha256':LK,
            'gapps_sha256':digest(copied),'gapps_properties':props,'live_runtime_untouched':True,
            'hardware_authorized':False}
    (ROOT/'out/phase7-archive-result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__': main()
