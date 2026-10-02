#include <carlsim.h>
#include <callback.h>
#include <algorithm>
#include <fstream>
#include <iomanip>
#include <vector>
#include <string>
struct Events: SpikeGenerator {
    int active; std::vector<int> times;
    int nextSpikeTime(CARLsim*,int,int cell,int now,int last,int end) override {
        if(cell>=active) return -1;
        auto p=std::lower_bound(times.begin(),times.end(),std::max(now,last+1));
        return p!=times.end() && *p<end?*p:-1;
    }
};
void kinetics(CARLsim& sim,int pre,int post,bool stp,float td,float rise) {
    sim.setSTP(pre,post,stp,STPu(.3f,0),STPtauU(80.f,0),STPtauX(120.f,0),
        STPtdAMPA(td,0),STPtdNMDA(td*3,0),STPtdGABAa(td,0),STPtdGABAb(td*3,0),
        STPtrNMDA(rise,0),STPtrGABAb(rise,0));
}
int main(int argc,char** argv) {
    // mode, spec file, output; spec: duration order; rows: n active E/I STP tau rise delay count times...
    std::ifstream in(argv[2]); int duration,reverse; in>>duration>>reverse;
    CARLsim sim("impulse",std::string(argv[1])=="gpu"?GPU_MODE:CPU_MODE,SILENT,0,42);
    int target=sim.createGroup("target",1,EXCITATORY_NEURON);
    sim.setNeuronParameters(target,.02f,.2f,-65.f,8.f);
    int auxiliary=sim.createGroup("auxiliary",1,EXCITATORY_NEURON);
    sim.setNeuronParameters(auxiliary,.02f,.2f,-65.f,8.f);
    std::vector<Events*> events;
    int n,active,inh,stp,delay,count;float td,rise;
    while(in>>n>>active>>inh>>stp>>td>>rise>>delay>>count) {
        Events* e=new Events;e->active=active;
        for(int i=0,t;i<count;++i){in>>t;e->times.push_back(t);}
        int pre=sim.createSpikeGeneratorGroup("input"+std::to_string(events.size()),n,inh?INHIBITORY_NEURON:EXCITATORY_NEURON);
        sim.connect(pre,target,"full",RangeWeight(.01f),1,RangeDelay(delay),RadiusRF(-1),SYN_FIXED,1.f,1.f);
        sim.connect(pre,auxiliary,"full",RangeWeight(.01f),1,RangeDelay(delay),RadiusRF(-1),SYN_FIXED,1.f,1.f);
        // same pre-group has static and dynamic outgoing connections; order must not disable the other edge
        if(reverse){kinetics(sim,pre,auxiliary,false,td,rise);kinetics(sim,pre,target,stp,td,rise);}
        else{kinetics(sim,pre,target,stp,td,rise);kinetics(sim,pre,auxiliary,false,td,rise);}
        sim.setSpikeGenerator(pre,e);events.push_back(e);
    }
    sim.setupNetwork();
    std::ofstream out(argv[3]);out<<std::setprecision(10);
    for(int t=0;t<duration;++t){
        sim.runNetwork(0,1,false);
        out<<t;
        for(int g:{target,auxiliary}) out<<","<<sim.getConductanceAMPA(g)[0]<<","<<sim.getConductanceNMDA(g)[0]<<","<<sim.getConductanceGABAa(g)[0]<<","<<sim.getConductanceGABAb(g)[0];
        out<<"\n";
    }
    // CARLsim destruction happens before process cleanup; callbacks intentionally live throughout it.
}
