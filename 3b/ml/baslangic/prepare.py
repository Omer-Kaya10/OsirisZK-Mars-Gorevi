"""Download genuine AI4Mars and HiRISE examples and create small reproducible subsets."""
import argparse, csv, hashlib, io, json, random, re, shutil, urllib.request, zipfile
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
HIRISE_URL = 'https://zenodo.org/records/1048301/files/hirise-map-proj.zip?download=1'

# HiRISE v1'de her görüntünün döndürülmüş/çevrilmiş kopyaları vardır (-fh, -fv, -brt, -r90, -r180, -r270).
# Aynı kaynağın kopyaları farklı kümelere düşerse test sonucu şişer; bu yüzden ayrım kaynak görüntüye göre yapılır.
AUG = re.compile(r'-(fh|fv|brt|r90|r180|r270)$', re.I)
def source_key(fname): return AUG.sub('', Path(fname).stem)
def split_of(key, seed):
    h = int(hashlib.sha1(f'{seed}:{key}'.encode()).hexdigest(), 16) % 10
    return 'train' if h < 8 else ('val' if h == 8 else 'test')

def download_hirise(n, seed):
    out=DATA/'hirise'; out.mkdir(parents=True,exist_ok=True)
    archive=DATA/'hirise-map-proj.zip'
    if not archive.exists():
        print('Downloading original HiRISE v1 (47.3 MB) from Zenodo...')
        urllib.request.urlretrieve(HIRISE_URL,archive)
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        label_files=[p for p in names if Path(p).name=='labels-map-proj.txt']
        if not label_files: raise RuntimeError('labels-map-proj.txt not found in archive')
        labels={}
        for line in z.read(label_files[0]).decode('utf-8-sig').splitlines():
            bits=line.strip().split()
            if len(bits)>=2: labels[Path(bits[0]).name]=bits[1]
        images={Path(p).name:p for p in names if p.lower().endswith(('.jpg','.jpeg','.png')) and not p.startswith('__MACOSX')}
        groups={}
        for fname,category in labels.items():
            if fname in images: groups.setdefault(category,[]).append(fname)
        if not groups: raise RuntimeError('No matching labeled image filenames in HiRISE archive')
        rng=random.Random(seed)
        for files in groups.values():rng.shuffle(files)
        chosen=[]
        while len(chosen)<min(n,sum(map(len,groups.values()))):
            did=False
            for category in sorted(groups):
                if groups[category]: chosen.append((groups[category].pop(),category));did=True
                if len(chosen)>=n: break
            if not did:break
        rng.shuffle(chosen)
        manifest=[]
        for idx,(fname,cat) in enumerate(chosen):
            split=split_of(source_key(fname),seed)
            dest=out/split/cat/fname;dest.parent.mkdir(parents=True,exist_ok=True)
            with z.open(images[fname]) as src,open(dest,'wb') as dst:shutil.copyfileobj(src,dst)
            manifest.append({'file':str(dest.relative_to(ROOT)),'class_id':cat,'split':split,'source':source_key(fname)})
        with open(out/'manifest.csv','w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=['file','class_id','split','source']);w.writeheader();w.writerows(manifest)
        print('HiRISE splits:',dict(Counter(a['split'] for a in manifest)),'· kaynak görüntü:',len({a['source'] for a in manifest}))
        print('HiRISE:',len(manifest),'images; classes',dict(Counter(a['class_id'] for a in manifest)))

def download_ai4mars(n,seed):
    try:from datasets import load_dataset
    except ImportError as e:raise RuntimeError('Install dependencies: pip install -r requirements.txt') from e
    out=DATA/'ai4mars';out.mkdir(parents=True,exist_ok=True)
    # Streams only the required records rather than fetching the entire 6.5GB dataset.
    stream=load_dataset('hassanjbara/AI4MARS',split='train',streaming=True)
    manifest=[]
    for item in stream:
        if not item.get('has_labels',True) or item.get('label_mask') is None:continue
        i=len(manifest)
        image=item['image'];mask=item['label_mask']
        if not isinstance(image,Image.Image):image=Image.open(io.BytesIO(image['bytes']))
        if not isinstance(mask,Image.Image):mask=Image.open(io.BytesIO(mask['bytes']))
        # Nearest neighbor preserves exact discrete class IDs.
        image=image.convert('RGB').resize((256,256),Image.Resampling.BILINEAR)
        mask=np.array(mask)
        if mask.ndim==3: mask=mask[:,:,0]
        mask=Image.fromarray(mask.astype('uint8')).resize((256,256),Image.Resampling.NEAREST)
        split='train' if i%10<8 else ('val' if i%10==8 else 'test')
        p=out/split/'images'/f'{i:04d}.jpg';m=out/split/'masks'/f'{i:04d}.png'
        p.parent.mkdir(parents=True,exist_ok=True);m.parent.mkdir(parents=True,exist_ok=True)
        image.save(p,quality=90);mask.save(m)
        manifest.append({'image':str(p.relative_to(ROOT)),'mask':str(m.relative_to(ROOT)),'split':split})
        if len(manifest)>=n: break
    with open(out/'manifest.csv','w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['image','mask','split']);w.writeheader();w.writerows(manifest)
    print('AI4Mars:',len(manifest),'image-mask pairs')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',choices=['hirise','ai4mars','both'],default='both')
    p.add_argument('--hirise-count',type=int,default=300);p.add_argument('--ai4mars-count',type=int,default=120)
    p.add_argument('--seed',type=int,default=42)
    a=p.parse_args()
    if a.dataset in ('hirise','both'):download_hirise(a.hirise_count,a.seed)
    if a.dataset in ('ai4mars','both'):download_ai4mars(a.ai4mars_count,a.seed)
