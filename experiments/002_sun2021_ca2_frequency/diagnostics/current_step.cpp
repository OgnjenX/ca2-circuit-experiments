#include <carlsim.h>
#include <callback.h>
#include <neuron_monitor.h>
#include <string>
#include "neuron_config.h"
struct Quiet:SpikeGenerator{int nextSpikeTime(CARLsim*,int,int,int,int,int)override{return -1;}};
int main(int argc,char** argv){
    CARLsim sim("independent_current_step",std::string(argv[1])=="gpu"?GPU_MODE:CPU_MODE,SILENT,0,42);
    int target=sim.createGroup("target",1,EXCITATORY_NEURON);configure(sim,target);
    int input=sim.createSpikeGeneratorGroup("quiet",1,EXCITATORY_NEURON);Quiet quiet;
    sim.connect(input,target,"full",RangeWeight(0.f),1,RangeDelay(1),RadiusRF(-1),SYN_FIXED);
    sim.setSTP(input,target,false,STPu(.3f,0),STPtauU(80.f,0),STPtauX(120.f,0),STPtdAMPA(5.f,0),STPtdNMDA(150.f,0),STPtdGABAa(6.f,0),STPtdGABAb(150.f,0),STPtrNMDA(0.f,0),STPtrGABAb(0.f,0));
    sim.setSpikeGenerator(input,&quiet);auto* monitor=sim.setNeuronMonitor(target,"DEFAULT");sim.setSpikeMonitor(target,"DEFAULT");
    sim.setIntegrationMethod(RUNGE_KUTTA4,std::stoi(argv[2]));sim.setupNetwork();monitor->startRecording();
    sim.setExternalCurrent(target,HOLDING);sim.runNetwork(5,0,false);
    sim.setExternalCurrent(target,HOLDING+100.f);sim.runNetwork(0,100,false);
    sim.setExternalCurrent(target,HOLDING);sim.runNetwork(0,200,false);monitor->stopRecording();
}
