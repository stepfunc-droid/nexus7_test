#!/usr/bin/env python3
"""Restore only installer-added/changed nodes from exact ROM file_contexts."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from ext4_readonly import Ext4Image
from phase7_gapps_audit import tree


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',required=True,type=Path)
    ap.add_argument('--base',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--source-sha256',required=True)
    args=ap.parse_args();source=args.source.resolve();out=args.output.resolve()
    if hashlib.sha256((source/'system-gapps.raw.img').read_bytes()).hexdigest()!=args.source_sha256:
        raise ValueError('Exact original-installer result mismatch')
    out.mkdir(exist_ok=False)
    candidate=out/'system-gapps.raw.img'
    subprocess.run(['cp','--reflink=auto',str(source/'system-gapps.raw.img'),str(candidate)],check=True)
    for name in ['serial.log','host-run.json']:shutil.copyfile(source/name,out/name)
    (out/'install-media.raw.img').symlink_to(source/'install-media.raw.img')
    with Ext4Image(args.base) as before,Ext4Image(candidate) as after:
        product_alias=before.resolve('/product',follow_final=False)
        if product_alias.kind!=0xa000 or before.read_symlink(product_alias)!='/system/product':
            raise ValueError('Expected target /product alias absent')
        policy=before.read_inode(before.resolve('/system/etc/selinux/plat_file_contexts'))
        old,new=tree(before),tree(after)
        paths=sorted(p for p in new if p not in old or old[p]!=new[p])
        nodes={p:after.resolve(p,follow_final=False) for p in paths}
    contexts=out/'frozen-plat-file-contexts';contexts.write_bytes(policy)
    lib=ctypes.CDLL('libselinux.so.1',use_errno=True)
    class Opt(ctypes.Structure):_fields_=[('type',ctypes.c_int),('value',ctypes.c_char_p)]
    lib.selabel_open.argtypes=[ctypes.c_uint,ctypes.POINTER(Opt),ctypes.c_uint];lib.selabel_open.restype=ctypes.c_void_p
    lib.selabel_lookup_raw.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_char_p),ctypes.c_char_p,ctypes.c_int]
    lib.freecon.argtypes=[ctypes.c_char_p];lib.selabel_close.argtypes=[ctypes.c_void_p]
    option=Opt(3,str(contexts).encode());handle=lib.selabel_open(0,ctypes.byref(option),1)
    if not handle:raise OSError(ctypes.get_errno(),'Cannot load exact target contexts')
    commands=[];records=[]
    for index,path in enumerate(paths):
        inode=nodes[path];result=ctypes.c_char_p()
        # Query the demonstrated Android /product namespace: using a physical
        # /system/product prefix can prefer Linux's generic /system regex.
        lookup='/product'+path[len('/system/product'):] if path.startswith('/system/product/') else path
        if lib.selabel_lookup_raw(handle,ctypes.byref(result),lookup.encode(),inode.mode):
            raise OSError(ctypes.get_errno(),'No target context for '+path)
        context=result.value.decode();lib.freecon(result)
        # Use raw inode identity so symlinks themselves are labelled.
        previous=subprocess.check_output(['/usr/sbin/debugfs','-R','ea_list <'+str(inode.number)+'>',str(candidate)],stderr=subprocess.DEVNULL).decode()
        if '"'+context+'\\000"' in previous or '"'+context+'"' in previous:continue
        data=out/('context-'+str(index)+'.bin');data.write_bytes(context.encode()+b'\0')
        commands.append('ea_set -f '+str(data)+' <'+str(inode.number)+'> security.selinux')
        records.append({'path':path,'lookup_path':lookup,'inode':inode.number,'context':context,'previous_ea':previous})
    lib.selabel_close(handle)
    script=out/'restore-labels.debugfs';script.write_text('\n'.join(commands)+'\n')
    run=subprocess.run(['/usr/sbin/debugfs','-w','-f',str(script),str(candidate)],capture_output=True,check=True)
    (out/'restore-labels.stdout').write_bytes(run.stdout);(out/'restore-labels.stderr').write_bytes(run.stderr)
    (out/'label-restoration.json').write_text(json.dumps({'source_installer_system_sha256':args.source_sha256,
        'file_contexts_sha256':hashlib.sha256(policy).hexdigest(),'nodes':records},indent=2)+'\n')
    print('Target-policy metadata restored on',len(records),'nodes; independent audit required')


if __name__=='__main__':main()
