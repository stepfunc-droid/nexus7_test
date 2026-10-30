#!/usr/bin/env python3
"""Mac packaging gate: replace p1 only and retain every other Q2 disk byte."""
import hashlib
import json
import os
from pathlib import Path
import shutil

from nexus7_runtime import clone, digest, require

ROOT=Path(__file__).resolve().parents[2]
HOME=Path.home()/'nexus7'
SYSTEM_SHA='98e58fa4070666b4f1ff5ab7d8c15617bf1237fa4e0c0f3cee617031a4d62401'
BASE_SHA='3cf28c2392d9daa945ae9e7b4edb52883330947a3ae4d9c74bb71e80d45ee811'


def main():
    base=HOME/'releases/20261030-Q2-gps-off'
    system=HOME/'gapps-work/installer-H/system-gapps.raw.img'
    audit=json.loads((system.parent/'audit.json').read_text())
    require(audit['status']=='HOST_PASS' and audit['system_sha256']==SYSTEM_SHA,'Independent audit not PASS')
    require(len(audit['new_directories_checked'])>0,'Missing directory metadata audit')
    require(system.stat().st_size==1572864000 and digest(system)==SYSTEM_SHA,'Candidate p1 mismatch')
    release=HOME/'releases/20261030-gapps-pico'
    require(not release.exists(),'Release already exists; never overwrite')
    for name in ['masters','disks','tools','runs','provenance']:(release/name).mkdir(parents=True,exist_ok=False)
    release.chmod(0o700)
    master=release/'masters/lineage18.1-gapps-pico-gps-off-clean.raw.img'
    original=base/'masters/lineage18.1-gps-off-clean.raw.img'
    clone(original,master);master.chmod(0o600)
    start,end=1048576,1573912576
    with system.open('rb') as src,master.open('r+b') as dst:
        dst.seek(start)
        shutil.copyfileobj(src,dst,4*1024*1024);dst.flush();os.fsync(dst.fileno())
    # Independent composed-image check: source full hash, p1 stream identity and
    # exact equality outside p1 (tables, vendor, all fresh writable partitions).
    require(original.stat().st_size==master.stat().st_size==6246367232,'Disk geometry changed')
    old_hash,new_hash,p1_hash=hashlib.sha256(),hashlib.sha256(),hashlib.sha256()
    with original.open('rb') as src,master.open('rb') as dst,system.open('rb') as p1:
        pos=0
        while pos<master.stat().st_size:
            stop=min(master.stat().st_size,pos+4*1024*1024)
            if pos<start<stop:stop=start
            if pos<end<stop:stop=end
            a,b=src.read(stop-pos),dst.read(stop-pos)
            require(len(a)==len(b)==stop-pos,'Short disk read')
            old_hash.update(a);new_hash.update(b)
            if start<=pos<end:
                require(b==p1.read(stop-pos),'Composed p1 differs from audited source');p1_hash.update(b)
            else:require(a==b,'Unexpected disk change outside p1')
            pos=stop
    require(old_hash.hexdigest()==BASE_SHA and p1_hash.hexdigest()==SYSTEM_SHA,'Source/partition pin mismatch')
    master.chmod(0o400)
    files={}
    pins=json.loads((base/'release.json').read_text())['files']
    for name in ['boot.img','lk2nd.img','partition-trace-map.json','tools/phase6_v2_nbd_observed_server.py','tools/nbd_partition_trace_server.py']:
        require(digest(base/name)==pins[name],'Base asset changed: '+name)
        shutil.copyfile(base/name,release/name);files[name]=digest(release/name)
    shutil.copyfile(ROOT/'scripts/v2/nexus7_runtime.py',release/'nexus7.py');files['nexus7.py']=digest(release/'nexus7.py')
    shutil.copyfile(ROOT/'scripts/v2/start-nbd.sh',release/'start-nbd.sh');(release/'start-nbd.sh').chmod(0o755)
    files['start-nbd.sh']=digest(release/'start-nbd.sh')
    shutil.copyfile(ROOT/'scripts/v2/phase6_v2_observe_usb.py',release/'tools/phase6_v2_observe_usb.py')
    files['tools/phase6_v2_observe_usb.py']=digest(release/'tools/phase6_v2_observe_usb.py')
    for name in ['audit.json','installed-file-metadata.json','filesystem-delta.json','host-run.json','label-restoration.json','installer-ui.txt','open_gapps_log.txt','e2fsck.stdout','e2fsck.stderr']:
        source=system.parent/name
        shutil.copyfile(source,release/'provenance'/name);files['provenance/'+name]=digest(source)
    files[str(master.relative_to(release))]=new_hash.hexdigest()
    info={'release':'20261030-gapps-pico','master_file':str(master.relative_to(release)),
          'files':files,'system_sha256':SYSTEM_SHA,'base_disk_sha256':BASE_SHA,
          'disk_outside_p1':'byte-identical to clean Q2; fresh userdata/cache/persist unchanged',
          'evidence':'HOST_FACT: exact original GApps installer + metadata/fs/whole-disk gates; IMPLEMENTED_UNPROVEN on Nexus',
          'GPS':'unavailable, preserved','startup':'user-operated manual test, no agent hardware transition'}
    info['gapps_config']='skipswypelibs (retain stock keyboard; omit optional gesture libraries only)'
    (release/'release.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
    (release/'SHA256SUMS').write_text(''.join(h+'  '+name+'\n' for name,h in sorted(files.items())))
    working=release/'disks/daily.raw.img';clone(master,working);working.chmod(0o600)
    (release/'README.md').write_text('''# LineageOS18.1 + Open GApps Pico / 无盘启动

HOST_FACT：原包安装器完成，ext4检查通过，GApps文件及目录的权限/SELinux标签通过，只有p1改变。
尚未在Nexus实机验证这一GApps版本。GPS仍不可用。新data需要重新完成设置；旧成功版本和用户快照保留。

在连接设备的Mac上操作。先把设备手动关机，然后音量下+电源进入stock fastboot。不要选择Recovery，不刷写任何分区。
终端一：

    cd /Users/zhangjw/nexus7/releases/20261030-gapps-pico
    python3 nexus7.py stop-nbd
    python3 nexus7.py serve disks/daily.raw.img

stop-nbd只有在同一设备/端口的fastboot身份正确时才停止旧的已识别NBD进程。serve会等待USB以太网出现。
终端二：

    cd /Users/zhangjw/nexus7/releases/20261030-gapps-pico
    python3 nexus7.py boot

boot脚本校验文件和设备，依次执行fastboot boot lk2nd.img、校验lk2nd、fastboot boot boot.img。
如果希望直接逐条输入fastboot命令（与boot脚本二选一，不要重复）：

    fastboot -s 07a117ae boot lk2nd.img
    fastboot -s 07a117ae getvar product

只有product确认是lk2nd-msm8960后，继续：

    fastboot -s 07a117ae boot boot.img

保持Mac、USB和NBD运行。首次GApps启动需要完成新的初始化；本次成功标准是进入Google设置/桌面且无卡死，随后打开Play商店验证。
出现错误就保留终端输出和runs/目录，停止重复启动；不要直接刷写内部存储或停止仍被设备使用的NBD。
masters是只读干净母盘；以后正常使用沿用disks/daily.raw.img即可保留设置。另一个独立数据环境可用new-disk命令创建。
使用boot脚本时，两次RAM启动命令及校验结果自动记录在runs/中；USB记录900秒，NBD统计每5秒。观察到期或退出监控均不停止后台根存储服务。
''')
    report={'status':'HOST_PASS','runtime':'IMPLEMENTED_UNPROVEN','release':str(release),
            'boot_sha256':files['boot.img'],'lk2nd_sha256':files['lk2nd.img'],
            'system_sha256':SYSTEM_SHA,'master_sha256':new_hash.hexdigest(),
            'outside_p1':'byte-identical','working_disk':str(working),'agent_hardware_commands':0}
    (ROOT/'out/phase7-gapps-package-result.json').write_text(json.dumps(report,indent=2)+'\n')
    (HOME/'README.md').write_text('''# Nexus 7 正式使用资源

releases/20261030-Q2-gps-off/：实机成功的无GApps版本及独立在线桌面快照，保留备用。
releases/20261030-gapps-pico/：带Open GApps Pico的独立镜像，主机检查通过，等待用户手动实机启动。操作见其中README.md。
inputs/：原始GApps包和校验值。gapps-work/：安装工作和证据；不属于日常运行依赖。
当前旧NBD服务仍指向nexus7_test原路径；只在设备已进入fastboot后按新版本说明切换。
''')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
