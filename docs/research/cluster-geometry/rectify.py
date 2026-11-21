import numpy as np, json
from PIL import Image
import sys,os; U=os.path.join(os.path.dirname(os.path.abspath(__file__)),'photos')+'/'
P={
 'full':( 'IMG_voll_2026-11-15.jpg',[((100,50),(1029,1142)),((900,50),(3193,1192)),((200,300),(1338,1758)),((700,300),(2585,1791)),((500,150),(2093,1423)),((500,200),(2092,1543))]),
 'wide':( 'IMG_wide_2026-11-15.jpg',[((200,50),(1282,1229)),((700,50),(2622,1249)),((300,250),(1571,1724)),((700,250),(2586,1744))]),
 'center':('IMG_center_2026-11-15.jpg',[((400,50),(1849,1214)),((600,50),(2379,1220)),((400,300),(1857,1815)),((600,300),(2351,1825))]),
}
def H(src,dst):
    A=[]
    for (x,y),(u,v) in zip(src,dst):
        A.append([x,y,1,0,0,0,-u*x,-u*y,-u]);A.append([0,0,0,x,y,1,-v*x,-v*y,-v])
    _,_,Vt=np.linalg.svd(np.array(A,float));h=Vt[-1].reshape(3,3);return h/h[2,2]
X0,Y0,X1,Y1,S=-160,-70,1170,446,2
out={}
for name,(f,pts) in P.items():
    s=[p[0] for p in pts];d=[p[1] for p in pts]
    h=H(s,d)  # stream -> photo
    err=[float(np.hypot(*(np.array((lambda q:(q[0]/q[2],q[1]/q[2]))(h@[x,y,1]))-np.array(uv)))) for (x,y),uv in pts]
    # output pixel (i,j) -> stream (X0+i/S, Y0+j/S) -> photo
    T=h@np.array([[1/S,0,X0],[0,1/S,Y0],[0,0,1]]);T=T/T[2,2]
    im=Image.open(U+f).convert('RGB')
    r=im.transform(((X1-X0)*S,(Y1-Y0)*S),Image.PERSPECTIVE,tuple(T.flatten()[:8]),Image.BICUBIC)
    r.save(f'./rect_{name}.png')
    out[name]={'max_err_px':max(err),'H_stream_to_photo':h.tolist()}
print(json.dumps({k:v['max_err_px'] for k,v in out.items()}))
json.dump(out,open('./homographies.json','w'),indent=1)
