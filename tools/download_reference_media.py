#!/usr/bin/env python3
"""Download a user-requested Archive.org image privately and verify its digest.

Archive metadata establishes transport integrity, not Microsoft authenticity.
Inspect the contained build before assigning the image to a reference profile.
"""
import argparse,hashlib,json,re,time,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def download(identifier,filename,output):
    if not re.fullmatch(r'[a-zA-Z0-9_.-]+',identifier):raise ValueError('Invalid Archive identifier')
    metadata_url='https://archive.org/metadata/'+identifier
    metadata=json.load(urllib.request.urlopen(metadata_url,timeout=30))
    row=next(item for item in metadata['files'] if item['name']==filename)
    if not filename.lower().endswith(('.iso','.exe')) or not row.get('sha1'):raise ValueError('Select a hashed image or original system update')
    size=int(row['size'])
    if not 1000000<size<2000000000:raise ValueError('Unexpected reference image size')
    url='https://archive.org/download/'+identifier+'/'+urllib.parse.quote(filename,safe='')
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():raise FileExistsError(output)
    partial=output.with_suffix('.part')
    with urllib.request.urlopen(url,timeout=60) as response,partial.open('xb') as target:
        count=0;reported=0
        while True:
            data=response.read(1024*1024)
            if not data:break
            count+=len(data)
            if count>size:raise ValueError('Download exceeds metadata size')
            target.write(data)
            if count-reported>=32*1024*1024:reported=count;print(identifier,count,'/',size,flush=True)
    sha1=hashlib.file_digest(partial.open('rb'),'sha1').hexdigest()
    if partial.stat().st_size!=size or sha1!=row['sha1']:raise ValueError('Reference image size or SHA-1 does not match Archive metadata')
    sha256=hashlib.file_digest(partial.open('rb'),'sha256').hexdigest();partial.replace(output)
    report={'archive_item':'https://archive.org/details/'+identifier,'metadata_url':metadata_url,'download_url':url,
            'title':metadata.get('metadata',{}).get('title'),'filename':filename,'size':size,'sha1':sha1,'sha256':sha256,
            'archive_digest_matches':True,'original_microsoft_authenticity_verified':False,
            'installed_build_verified':False,'downloaded_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('identifier');p.add_argument('filename');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if not a.output.resolve().is_relative_to((ROOT/'private').resolve()):p.error('Reference media belongs under the private project directory')
    download(a.identifier,a.filename,a.output)
if __name__=='__main__':main()
