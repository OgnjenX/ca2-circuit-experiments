from pathlib import Path
import struct
import numpy as np
COUNTS={'CA2_Pyramidal':18956,'CA2_Basket':105,'CA2_Wide_Arbor_Basket':147,'CA2_Bistratified':79,'CA2_SP_SR':94,'CA3_Pyramidal':4096,'MEC_LII_Stellate':10818,'CA1_Pyramidal':128,'CA1_Basket':819,'CA1_Bistratified':1962}
def spikes(path,name,duration=250):
 p=Path(path)/f'spk_{name}.dat';raw=p.read_bytes();assert len(raw)>=20 and (len(raw)-20)%8==0
 a=np.frombuffer(raw,dtype=[('t','<i4'),('id','<i4')],offset=20).copy()
 assert (a['t']>=0).all() and (a['t']<duration).all() and (a['id']>=0).all() and (a['id']<COUNTS[name]).all()
 assert len(set(zip(a['t'].tolist(),a['id'].tolist())))==len(a)
 return a
def voltage(path,name,duration=250):
 p=Path(path)/f'n_{name}.dat';raw=p.read_bytes();assert len(raw)>=24
 magic,version,x,y,z,maxmon=struct.unpack('<ifiiii',raw[:24]);assert magic==206661979
 n=min(128,COUNTS[name]);a=np.frombuffer(raw,dtype=[('t','<u4'),('id','<u4'),('v','<f4'),('u','<f4'),('I','<f4')],offset=24)
 assert len(a)==duration*n and (a['id']<n).all() and (a['t']<duration).all()
 assert all(np.isfinite(a[col]).all() for col in ['v','u','I'])
 v=np.full((n,duration),np.nan);v[a['id'],a['t']]=a['v'];assert np.isfinite(v).all()
 return v
