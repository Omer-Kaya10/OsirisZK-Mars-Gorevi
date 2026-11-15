import argparse, json
from pathlib import Path
import torch
from torchvision import models,transforms
from PIL import Image
import csv
from torch.utils.data import DataLoader
ROOT=Path(__file__).resolve().parent
class LabeledFolder(torch.utils.data.Dataset):
 def __init__(self,base,split,classes,tf):
  self.tf=tf;self.rows=[];self.mapping={k:i for i,k in enumerate(classes)}
  with open(base/'manifest.csv',newline='',encoding='utf-8') as f:
   for row in csv.DictReader(f):
    if row['split']==split and row['class_id'] in self.mapping:self.rows.append((ROOT/row['file'],self.mapping[row['class_id']]))
 def __len__(self):return len(self.rows)
 def __getitem__(self,i):
  f,label=self.rows[i];return self.tf(Image.open(f).convert('RGB')),label

def main():
 p=argparse.ArgumentParser();p.add_argument('--epochs',type=int,default=5);p.add_argument('--batch',type=int,default=16);a=p.parse_args()
 base=ROOT/'data/hirise';tf=transforms.Compose([transforms.Resize((224,224)),transforms.ToTensor(),transforms.Normalize([.5]*3,[.5]*3)])
 classes=sorted([x.name for x in (base/'train').iterdir() if x.is_dir()]);train=LabeledFolder(base,'train',classes,tf);val=LabeledFolder(base,'val',classes,tf);test=LabeledFolder(base,'test',classes,tf)
 if not len(val):raise RuntimeError('Validation folder empty; download a larger subset')
 model=models.mobilenet_v3_small(weights=None,num_classes=len(classes));device='cuda' if torch.cuda.is_available() else 'cpu';model.to(device)
 opt=torch.optim.AdamW(model.parameters(),lr=.001);best=(-1,0,None);history=[]
 for ep in range(a.epochs):
  model.train();correct=seen=0
  for x,y in DataLoader(train,batch_size=a.batch,shuffle=True):
   x,y=x.to(device),y.to(device);opt.zero_grad();prediction=model(x);loss=torch.nn.functional.cross_entropy(prediction,y);loss.backward();opt.step()
   correct+=(prediction.argmax(1)==y).sum().item();seen+=len(y)
  model.eval();vc=vs=0
  with torch.no_grad():
   for x,y in DataLoader(val,batch_size=a.batch):
    x,y=x.to(device),y.to(device);vc+=(model(x).argmax(1)==y).sum().item();vs+=len(y)
  print(f'epoch {ep+1}: train_accuracy={correct/seen:.3f} val_accuracy={vc/vs:.3f}')
  history.append({'epoch':ep+1,'train_accuracy':round(correct/seen,4),'val_accuracy':round(vc/vs,4)})
  if vc/vs>best[0]:best=(vc/vs,ep+1,{k:v.detach().clone() for k,v in model.state_dict().items()})
 # En iyi doğrulama epoku geri yüklenir; test kümesi yalnız burada, bir kez kullanılır.
 model.load_state_dict(best[2]);model.eval();K=len(classes);cm=[[0]*K for _ in range(K)]
 with torch.no_grad():
  for x,y in DataLoader(test,batch_size=a.batch):
   for t,p_ in zip(y.tolist(),model(x.to(device)).argmax(1).cpu().tolist()):cm[t][p_]+=1
 n=sum(map(sum,cm));acc=sum(cm[i][i] for i in range(K))/n if n else float('nan')
 print(f'best epoch {best[1]} (val {best[0]:.3f}) · TEST accuracy={acc:.3f} ({n} images)')
 torch.save({'model':model.state_dict(),'classes':classes},ROOT/'hirise_model.pt')
 json.dump({'dataset':'HiRISE v1 (Zenodo 1048301)','model':'MobileNetV3-small','classes':classes,'counts':{'train':len(train),'val':len(val),'test':n},
  'best_epoch':best[1],'test':{'accuracy':acc,'confusion':cm},'history':history},open(ROOT/'hirise_rapor.json','w'),indent=1)
 print('Saved hirise_model.pt and hirise_rapor.json')
if __name__=='__main__':main()
