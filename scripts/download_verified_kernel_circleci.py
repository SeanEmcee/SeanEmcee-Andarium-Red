#!/usr/bin/env python3
"""Download exact, unexpired verified kernel artifact from a prior GitHub Actions run."""
import json, os, urllib.request, zipfile, io, pathlib
repo='SeanEmcee/SeanEmcee-Andarium-Red'
run=os.environ['KERNEL_RUN_ID']
name='andarium-pinned-android17-abi29-4k-kernel-'+os.environ['KERNEL_SOURCE_SHA']
headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
def request(url):
    return urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=180)
with request(f'https://api.github.com/repos/{repo}/actions/runs/{run}/artifacts?per_page=100') as r:
    artifacts=json.load(r)['artifacts']
matches=[a for a in artifacts if a['name']==name and not a['expired']]
if len(matches)!=1: raise SystemExit('Expected exactly one unexpired kernel artifact')
with request(matches[0]['archive_download_url']) as r:
    archive=r.read()
dest=pathlib.Path('.build/android-kernel')
dest.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(io.BytesIO(archive)) as z:
    for item in z.infolist():
        p=pathlib.PurePosixPath(item.filename)
        if p.is_absolute() or '..' in p.parts or item.is_dir() and not p.parts:
            raise SystemExit('Unsafe artifact entry')
        if item.external_attr >> 16 & 0o170000 == 0o120000:
            raise SystemExit('Symlink artifact entry rejected')
        z.extract(item,dest)
print('Downloaded kernel artifact',matches[0]['id'])
