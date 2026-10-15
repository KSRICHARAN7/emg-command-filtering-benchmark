"""Acquire exact original sources without rewriting any frozen metadata.
DB5 checks provider MD5, recorded SHA256/size, all-member CRC.
DB2 fetches the recorded compressed member range and checks decompression,
member length, CRC and recorded SHA256; not a whole-archive checksum.
"""
from pathlib import Path
import argparse,hashlib,json,urllib.request,zlib,zipfile
R=Path(__file__).resolve().parents[1]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def acquire(dataset,subject):
 if dataset=='db5':
  row=next(x for x in json.loads((R/'data/archive_inventory.json').read_text()) if x['subject']==subject);expected=row['sha256']
 else:
  row=json.loads((R/f'data/replication/DB2_s{subject}.json').read_text());expected=row['member_sha256']
 dest=R/row['local_path'];dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():
  if sha(dest)!=expected:raise ValueError(f'Existing source differs; preserve and inspect {dest}')
  print(f'{dataset} S{subject}: existing source SHA256 verified',flush=True);return
 part=dest.with_suffix('.download-part')
 if part.exists():raise FileExistsError(f'Inspect incomplete download before retry: {part}')
 headers={'User-Agent':'EMG command filtering research reproducibility'}
 if dataset=='db2':
  start,stop=row['compressed_member_range'];headers['Range']=f'bytes={start}-{stop}'
 with urllib.request.urlopen(urllib.request.Request(row['source_url'],headers=headers),timeout=60) as response,part.open('xb') as f:
  dec=zlib.decompressobj(-15) if dataset=='db2' else None;crc=0;compressed=0;written=0
  if dec:
   expected_range=f'bytes {start}-{stop}/{row["archive_size_bytes"]}'
   if response.status!=206 or response.headers.get('Content-Range')!=expected_range:raise ValueError('Provider range/layout changed; stop rather than guess')
  while True:
   chunk=response.read(1024*1024)
   if not chunk:break
   compressed+=len(chunk);out=dec.decompress(chunk) if dec else chunk;f.write(out);written+=len(out);crc=zlib.crc32(out,crc)
  if dec:
   out=dec.flush();f.write(out);written+=len(out);crc=zlib.crc32(out,crc)
 if sha(part)!=expected:raise ValueError('Source SHA256 mismatch; incomplete file retained for inspection')
 if dataset=='db5':
  if written!=row['bytes'] or hashlib.md5(part.read_bytes()).hexdigest()!=row['provider_md5']:raise ValueError('Provider MD5/size mismatch')
  with zipfile.ZipFile(part) as z:
   if z.testzip() is not None:raise ValueError('Archive CRC failure')
 else:
  if not dec.eof or written!=row['member_bytes'] or compressed!=row['compressed_member_bytes'] or f'{crc:08x}'!=row['archive_member_crc32']:raise ValueError('Member integrity failure')
 part.replace(dest);print(f'{dataset} S{subject}: downloaded and verified',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dataset',choices=['db5','db2'],required=True);p.add_argument('--subjects',nargs='+',type=int);a=p.parse_args()
 people=a.subjects or list(range(1,11 if a.dataset=='db5' else 41))
 if any(s<1 or s>(10 if a.dataset=='db5' else 40) for s in people):p.error('Subject outside dataset inventory')
 for s in people:acquire(a.dataset,s)
