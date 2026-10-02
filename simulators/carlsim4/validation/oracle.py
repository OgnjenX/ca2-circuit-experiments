"""Independent float64 oracle: analytical impulse convolution, not backend state updates."""
import math
import numpy as np

def expected(duration, edges, static=False):
    out=np.zeros((duration,4),dtype=np.float64)
    for edge in edges:
        td=edge['tau']; rise=edge['rise']; u=0.; x=1.; last=None
        for emit in edge['events']:
            arrival=emit+edge['delay']-1 # readback after tick t; delay=1 is delivered in emission tick
            release=1.
            if edge['stp'] and not static:
                if last is not None:
                    dt=arrival-last
                    u*=math.exp(-dt/80.)
                    x=1-(1-x)*math.exp(-dt/120.)
                u+=.3*(1-u)
                release=u*x/.3
                x*=1-u
                last=arrival
            for t in range(arrival,duration):
                age=t-arrival
                fast=.01*edge['active']*release*math.exp(-age/td)
                slow=.01*edge['active']*release*math.exp(-age/(td*3))
                if rise:
                    peak=(td*3)*rise*math.log((td*3)/rise)/((td*3)-rise)
                    scale=1/(math.exp(-peak/(td*3))-math.exp(-peak/rise))
                    slow=.01*edge['active']*release*scale*(math.exp(-age/(td*3))-math.exp(-age/rise))
                out[t,2 if edge['inh'] else 0]+=fast
                out[t,3 if edge['inh'] else 1]+=slow
    return out
