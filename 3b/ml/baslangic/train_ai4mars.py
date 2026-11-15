import argparse, json
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.utils.data import DataLoader,Dataset
ROOT=Path(__file__).resolve().parent
class MarsDataset(Dataset):
 def __init__(self,split):
  self.base=ROOT/'data/ai4mars'/split;self.images=sorted((self.base/'images').glob('*.jpg'))
 def __len__(self):return len(self.images)
 def __getitem__(self,i):
  f=self.images[i];x=np.asarray(Image.open(f).convert('RGB'),dtype=np.float32).transpose(2,0,1)/255.0
  m=np.asarray(Image.open(self.base/'masks'/(f.stem+'.png')))
  if m.ndim==3:m=m[:,:,0]
  m=m.astype(np.int64);m[~np.isin(m,[0,1,2,3])]=255
  return torch.tensor(x),torch.tensor(m)
class SmallUNet(nn.Module):
 def __init__(self):
  super().__init__()
  def block(a,b):return nn.Sequential(nn.Conv2d(a,b,3,padding=1),nn.ReLU(),nn.Conv2d(b,b,3,padding=1),nn.ReLU())
  self.e1=block(3,16);self.e2=block(16,32);self.center=block(32,64)
  self.d2=block(96,32);self.d1=block(48,16);self.head=nn.Conv2d(16,4,1)
 def forward(self,x):
  a=self.e1(x);b=self.e2(nn.functional.max_pool2d(a,2));c=self.center(nn.functional.max_pool2d(b,2))
  d=self.d2(torch.cat([nn.functional.interpolate(c,size=b.shape[-2:],mode='bilinear',align_corners=False),b],1))
  return self.head(self.d1(torch.cat([nn.functional.interpolate(d,size=a.shape[-2:],mode='bilinear',align_corners=False),a],1)))
def main():
 p=argparse.ArgumentParser();p.add_argument('--epochs',type=int,default=5);p.add_argument('--batch',type=int,default=4);a=p.parse_args()
 train=MarsDataset('train');val=MarsDataset('val');test=MarsDataset('test');device='cuda' if torch.cuda.is_available() else 'cpu'
 if not len(train) or not len(val):raise RuntimeError('Run prepare.py first')
 model=SmallUNet().to(device);opt=torch.optim.AdamW(model.parameters(),lr=.001);best=(-1,0,None);history=[]
 def iou(ds):
  model.eval();I=torch.zeros(4,device=device);U=torch.zeros(4,device=device)
  with torch.no_grad():
   for x,y in DataLoader(ds,batch_size=a.batch):
    x,y=x.to(device),y.to(device);pred=model(x).argmax(1);valid=y!=255
    for k in range(4):I[k]+=(((pred==k)&(y==k))&valid).sum();U[k]+=(((pred==k)|(y==k))&valid).sum()
  per=[(I[k]/U[k]).item() if U[k]>0 else None for k in range(4)];ok=[v for v in per if v is not None]
  return (sum(ok)/len(ok) if ok else float('nan')),per
 for epoch in range(a.epochs):
  model.train();losses=[]
  for x,y in DataLoader(train,batch_size=a.batch,shuffle=True):
   x,y=x.to(device),y.to(device);opt.zero_grad();pred=model(x)
   loss=nn.functional.cross_entropy(pred,y,ignore_index=255);loss.backward();opt.step();losses.append(loss.item())
  miou,_=iou(val)
  print(f'epoch {epoch+1}: loss={sum(losses)/len(losses):.4f}, validation_mIoU={miou:.3f}')
  history.append({'epoch':epoch+1,'loss':round(sum(losses)/len(losses),4),'val_mIoU':round(miou,4)})
  if miou>best[0]:best=(miou,epoch+1,{k:v.detach().clone() for k,v in model.state_dict().items()})
 # En iyi doğrulama epoku; test kümesi yalnız burada, bir kez.
 model.load_state_dict(best[2]);tm,per=iou(test) if len(test) else (float('nan'),[None]*4)
 print(f'best epoch {best[1]} (val mIoU {best[0]:.3f}) · TEST mIoU={tm:.3f} · soil/bedrock/sand/big rock IoU={per}')
 torch.save(model.state_dict(),ROOT/'ai4mars_unet.pt')
 json.dump({'dataset':'AI4Mars (hassanjbara/AI4MARS aynası, train bölümünden alt küme)','model':'SmallUNet','classes':['soil','bedrock','sand','big rock'],
  'counts':{'train':len(train),'val':len(val),'test':len(test)},'best_epoch':best[1],'test':{'mIoU':tm,'IoU':per},'history':history},open(ROOT/'ai4mars_rapor.json','w'),indent=1)
 print('Saved ai4mars_unet.pt and ai4mars_rapor.json')
if __name__=='__main__':main()
