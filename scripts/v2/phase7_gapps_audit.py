#!/usr/bin/env python3
"""Independent, read-only audit of the isolated original-installer output."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import time

from ext4_readonly import Ext4Image


def sha(data): return hashlib.sha256(data).hexdigest()


def require(ok, reason):
    if not ok: raise ValueError(reason)


def read(fs,path): return fs.read_inode(fs.resolve(path))


def owner(fs,inode):
    group,index=divmod(inode.number-1,fs.inodes_per_group)
    raw=fs.pread(fs.inode_size,fs._inode_table_block(group)*fs.block_size+index*fs.inode_size)
    return (struct.unpack_from('<H',raw,2)[0] | struct.unpack_from('<H',raw,120)[0]<<16,
            struct.unpack_from('<H',raw,24)[0] | struct.unpack_from('<H',raw,122)[0]<<16)


def tree(fs):
    result={}
    def visit(path,inode):
        item={'mode':oct(inode.mode),'owner':owner(fs,inode),'size':inode.size}
        if inode.kind==0x8000:item['sha256']=sha(fs.read_inode(inode))
        elif inode.kind==0xa000:item['symlink']=fs.read_symlink(inode)
        result[path]=item
        if inode.kind!=0x4000:return
        data=fs.read_inode(inode);pos=0
        while pos+8<=len(data):
            num,length,nlen,kind=struct.unpack_from('<IHBB',data,pos)
            require(length>=8 and pos+length<=len(data),'Invalid ext4 directory')
            name=data[pos+8:pos+8+nlen].decode()
            if num and name not in ['.','..']:visit(path.rstrip('/')+'/'+name,fs.inode(num))
            pos+=length
    visit('/',fs.inode(2));return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--attempt',required=True,type=Path)
    ap.add_argument('--base',required=True,type=Path)
    args=ap.parse_args();out=args.attempt.resolve();candidate=out/'system-gapps.raw.img'
    report_path=out/'audit.json'
    if report_path.exists():report_path.rename(out/('audit.previous-'+str(time.time_ns())+'.json'))
    report_path.write_text(json.dumps({'status':'AUDIT_IN_PROGRESS','hardware_authorized':False})+'\n')
    require(sha(args.base.read_bytes())=='d004e3186585a57991c8e291cd7abf2c1cad7eb2c82b0c055de82894e0d3c795','Base identity mismatch')
    serial=(out/'serial.log').read_text()
    require('GAPPS_VM_FINISHED' in serial and 'GAPPS_INSTALLER_EXIT=0' in serial,'Original installer did not complete successfully')
    debug='/usr/sbin/debugfs'
    media=out/'install-media.raw.img'
    def media_read(path):
        return subprocess.check_output([debug,'-R','cat '+path,str(media)],stderr=subprocess.DEVNULL)
    require(media_read('/installer.exit').strip()==b'0','Installer exit file mismatch')
    console=media_read('/installer-console.txt');(out/'installer-console.txt').write_bytes(console)
    ui=media_read('/installer-ui.txt');(out/'installer-ui.txt').write_bytes(ui)
    log=media_read('/open_gapps_log.txt');(out/'open_gapps_log.txt').write_bytes(log)
    mounts=media_read('/final-mounts.txt');(out/'final-mounts.txt').write_bytes(mounts)
    require(not any(b' '+p+b' ' in mounts for p in [b'/system',b'/system_root',b'/vendor']),'Candidate still mounted at guest handoff')
    require(b'Installation complete!' in ui,'Installer completion UI missing')
    check=subprocess.run(['/usr/sbin/e2fsck','-fn',str(candidate)],capture_output=True)
    (out/'e2fsck.stdout').write_bytes(check.stdout);(out/'e2fsck.stderr').write_bytes(check.stderr)
    require(check.returncode==0,'Filesystem check failed')
    metadata=[]
    with Ext4Image(args.base) as before,Ext4Image(candidate) as after:
        require(sha(read(after,'/fstab.flox'))=='bf0bf1502b5caf18a6d5de927c39a2185f9d60afacb05c1618e79ecc5657e6da','NBD root fstab changed')
        protected=['/init.flox.rc','/system/etc/init/hw/init.rc','/system/bin/init','/system/bin/netd',
                   '/system/etc/selinux/plat_sepolicy.cil','/system/etc/selinux/plat_file_contexts']
        for path in protected:require(read(before,path)==read(after,path),'Protected file changed: '+path)
        props=read(after,'/system/etc/g.prop').decode()
        policy=read(before,'/system/etc/selinux/plat_file_contexts').decode()
        require('/system/lib(64)?(/.*)?' in policy and 'u:object_r:system_lib_file:s0' in policy,
                'Expected target library rule absent')
        require('/(product|system/product)/overlay(/.*)?' in policy and 'u:object_r:vendor_overlay_file:s0' in policy,
                'Expected target overlay rule absent')
        def expected_label(path):
            # Independent restricted consumer of the exact target rules above.
            require(path.startswith(('/system/app/','/system/priv-app/','/system/etc/',
                                     '/system/framework/','/system/lib/','/system/product/','/system/addon.d/')),
                    'New path outside audited rule scope: '+path)
            if path.startswith('/system/lib/'):return 'system_lib_file'
            return 'vendor_overlay_file' if '/overlay/' in path else 'system_file'
        for value in ['ro.addon.arch=arm','ro.addon.sdk=30','ro.addon.open_type=pico','ro.addon.open_version=20220215']:
            require(value+'\n' in props,'Wrong installed GApps marker')
        backup=read(after,'/system/addon.d/70-gapps.sh').decode()
        match=re.search(r'list_files\(\)\s*\{\s*cat <<EOF\n(.*?)\nEOF',backup,re.S)
        require(match,'Missing original addon manifest')
        files=['/system/'+p for p in match.group(1).splitlines() if p]+['/system/addon.d/70-gapps.sh']
        require(any('PrebuiltGmsCore' in p for p in files) and any('Phonesky' in p for p in files),'Core Play components absent')
        for path in files:
            inode=after.resolve(path)
            require(inode.kind==0x8000 and inode.size>0,'Missing/empty installed file: '+path)
            mode=0o755 if path.endswith('/70-gapps.sh') else 0o644
            require(inode.mode&0o7777==mode and owner(after,inode)==(0,0),'Installed ownership/mode mismatch: '+path)
            ea=subprocess.check_output([debug,'-R','ea_list <'+str(inode.number)+'>',str(candidate)],stderr=subprocess.DEVNULL).decode()
            label=expected_label(path)
            require('security.selinux' in ea and 'u:object_r:'+label+':s0' in ea,'SELinux label mismatch: '+path)
            metadata.append({'path':path,'mode':oct(mode),'owner':[0,0],'label':label,'sha256':sha(after.read_inode(inode))})
        old_tree,new_tree=tree(before),tree(after)
        directories=[];symlinks=[]
        delta_nodes={p for p in new_tree if p not in old_tree or old_tree[p]!=new_tree[p]}
        for path in sorted(delta_nodes):
            inode=after.resolve(path,follow_final=False)
            if inode.kind not in {0x4000,0xa000}:continue
            mode=0o755 if inode.kind==0x4000 else 0o777
            require(inode.mode&0o7777==mode and owner(after,inode)==(0,0),'New node ownership/mode mismatch: '+path)
            ea=subprocess.check_output([debug,'-R','ea_list <'+str(inode.number)+'>',str(candidate)],stderr=subprocess.DEVNULL).decode()
            label=expected_label(path)
            require('security.selinux' in ea and 'u:object_r:'+label+':s0' in ea,'New node label mismatch: '+path)
            if inode.kind==0xa000:
                require(after.resolve(path).size>0,'Dangling new symlink: '+path);symlinks.append(path)
            else:directories.append(path)
    delta={'added':sorted(set(new_tree)-set(old_tree)),'removed':sorted(set(old_tree)-set(new_tree)),
           'changed':[p for p in sorted(set(old_tree)&set(new_tree)) if old_tree[p]!=new_tree[p]]}
    (out/'filesystem-delta.json').write_text(json.dumps(delta,indent=2)+'\n')
    (out/'installed-file-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    report={'status':'HOST_PASS','runtime':'IMPLEMENTED_UNPROVEN','hardware_authorized':False,
            'system_sha256':sha(candidate.read_bytes()),'installer_exit':0,'e2fsck':0,
            'installed_files_checked':len(metadata),'root_fstab':'unchanged','protected_files':protected,
            'new_directories_checked':directories,
            'new_symlinks_checked':symlinks,
            'delta_counts':{k:len(v) for k,v in delta.items()}}
    (out/'audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
