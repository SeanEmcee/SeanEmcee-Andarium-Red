#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fetch pinned ordinary Android guest apps from official release URLs.

Never trusts a filename: every byte count and SHA-256 must match the approved
publisher's release. Network use is explicit, source package ships no APKs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SOURCE))
import host_firstboot as firstboot
from install_source_overlay import (MAGISK_RELEASE_URL,MAGISK_RELEASE_SHA256,MAGISK_RELEASE_SIZE,
                                    TITANIUM_RELEASE_URL,TITANIUM_RELEASE_SHA256,TITANIUM_RELEASE_SIZE)

SOURCES={
    'magisk':('Magisk-v31.1.apk',MAGISK_RELEASE_URL,MAGISK_RELEASE_SIZE,MAGISK_RELEASE_SHA256),
    'titanium':('Titanium-v157.apk',TITANIUM_RELEASE_URL,TITANIUM_RELEASE_SIZE,TITANIUM_RELEASE_SHA256),
    'appmanager':('AppManager-v4.1.1.apk',firstboot.APPMANAGER_RELEASE_URL,firstboot.APPMANAGER_RELEASE_SIZE,firstboot.APPMANAGER_RELEASE_SHA256),
    'termux':('Termux-v0.118.3-arm64.apk',firstboot.TERMUX_RELEASE_URL,firstboot.TERMUX_RELEASE_SIZE,firstboot.TERMUX_RELEASE_SHA256),
    'fdroid':('FDroid-v2.0.1.apk',firstboot.FDROID_RELEASE_URL,firstboot.FDROID_RELEASE_SIZE,firstboot.FDROID_RELEASE_SHA256),
    'heliboard':('HeliBoard-v4.2-release.apk',firstboot.HELIBOARD_RELEASE_URL,firstboot.HELIBOARD_RELEASE_SIZE,firstboot.HELIBOARD_RELEASE_SHA256),
}


def verify(path: Path, *, size: int, digest: str) -> None:
    if not path.is_file() or path.stat().st_size != size:
        raise ValueError('APK byte count does not match pinned publisher asset')
    h=hashlib.sha256()
    with path.open('rb') as f:
        for piece in iter(lambda:f.read(1024*1024),b''):
            h.update(piece)
    if h.hexdigest()!=digest:
        raise ValueError('APK SHA-256 does not match pinned publisher asset')
    with zipfile.ZipFile(path) as archive:
        if 'AndroidManifest.xml' not in archive.namelist() or archive.testzip() is not None:
            raise ValueError('Official asset is not a valid Android APK')


def fetch_one(name: str, out: Path) -> dict:
    filename,url,size,digest=SOURCES[name]
    if not url.startswith('https://'):
        raise ValueError('Source URL must use HTTPS')
    dest=out/filename
    if dest.exists():
        verify(dest,size=size,digest=digest)
        return {'app':name,'path':str(dest),'status':'verified-existing'}
    out.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix='.verified-apk.',suffix='.tmp',dir=out,delete=False) as tmp:
        temp=Path(tmp.name)
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Andarium-Red-Source-Builder/1.0'})
        received=0
        with urllib.request.urlopen(req,timeout=45) as res, temp.open('wb') as f:
            if not res.geturl().startswith('https://'):
                raise ValueError('Download redirected away from HTTPS')
            while True:
                chunk=res.read(1<<20)
                if not chunk:break
                received+=len(chunk)
                if received>size:raise ValueError('APK download exceeds official release byte count')
                f.write(chunk)
        verify(temp,size=size,digest=digest)
        temp.replace(dest)
        return {'app':name,'path':str(dest),'status':'downloaded-and-verified'}
    finally:
        temp.unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--only',nargs='+',choices=sorted(SOURCES),default=sorted(SOURCES))
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    if args.dry_run:
        print(json.dumps({name: {'filename':SOURCES[name][0],'bytes':SOURCES[name][2],
                                 'sha256':SOURCES[name][3],'source':SOURCES[name][1]}
                          for name in args.only},indent=2))
        return
    for name in args.only:
        print(json.dumps(fetch_one(name,args.out.resolve())))

if __name__=='__main__':main()
