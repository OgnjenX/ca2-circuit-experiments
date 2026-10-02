// Preparatory native GPU assay. Backend dynamics sources are included unchanged.
// The generated header pins an exact CSV-derived parameter row and holding bias.
#include <bits/stdc++.h>
#include <cuda_runtime.h>
#define private public
#define protected public
#include <carlsim.cpp>
#undef protected
#undef private
#include "assay_config.h"
#include <callback.h>
struct Quiet : SpikeGenerator {
    int nextSpikeTime(CARLsim*,int,int,int,int,int) override { return -1; }
};

extern "C" cudaError_t __real_cudaMemcpy(void*, const void*, size_t, cudaMemcpyKind);

namespace {
struct Observer {
    SNN* snn = nullptr;
    RuntimeData* state = nullptr;
    int neuron = -1, net = -1, steps = 0;
    uint64_t rows = 0;
    FILE* trace = nullptr;
} observer;
void checked(cudaError_t result) {
    if (result != cudaSuccess) throw std::runtime_error(cudaGetErrorString(result));
}
template<class T> T read_device(const T* address) {
    T value;
    checked(__real_cudaMemcpy(&value, address, sizeof(value), cudaMemcpyDeviceToHost));
    return value;
}
template<class T> void write_device(T* address, T value) {
    checked(__real_cudaMemcpy(address, &value, sizeof(value), cudaMemcpyHostToDevice));
}
}

extern "C" cudaError_t __wrap_cudaMemcpy(void* destination, const void* source,
                                          size_t size, cudaMemcpyKind kind) {
    cudaError_t result = __real_cudaMemcpy(destination, source, size, kind);
    if (result != cudaSuccess || !observer.trace || kind != cudaMemcpyDeviceToDevice
        || destination != observer.state->voltage || source != observer.state->nextVoltage)
        return result;
    try {
        const int n = observer.neuron;
        const int substep = int(observer.rows % observer.steps) + 1;
        const int ms = observer.snn->simTime;
        // Snapshot follows the existing complete substep DtoD copy; no state is written.
        const float v = read_device(observer.state->voltage+n);
        const float u = read_device(observer.state->recovery+n);
        const int refractory = read_device(observer.state->Izh_ref_c+n);
        const bool spike = read_device(observer.state->curSpike+n);
        if (size != sizeof(float)*observer.snn->networkConfigs[observer.net].numNReg)
            throw std::runtime_error("Unexpected voltage copy size");
        if (ms != int(observer.rows / observer.steps))
            throw std::runtime_error("Unexpected GPU substep clock");
        const double t_end = double(ms) + double(substep)/observer.steps;
        std::fprintf(observer.trace, "%.17g,%.17g,%.17g,%d,%d\n",
                     t_end,double(v),double(u),refractory,int(spike));
        ++observer.rows;
    } catch (const std::exception& e) {
        std::fprintf(stderr,"Observer failed: %s\n", e.what());
        std::abort(); // Preserve failed trace; never continue with incomplete observations.
    }
    return result;
}

int main(int argc, char** argv) {
    if (argc != 5 || std::string(argv[1]) != "--run-frozen"
        || !std::getenv("CA2_WHITEBIRCH_FROZEN_RUN_AUTHORIZED")) {
        std::fprintf(stderr,"Preparatory harness: execution requires the gated build_driver.py. No neuron executed.\n");
        return 2;
    }
    try {
        const int steps=std::stoi(argv[2]);
        const int current=std::stoi(argv[3]);
        if ((steps!=20 && steps!=40 && steps!=80) || current<0 || current>1000 || current%100)
            throw std::runtime_error("Invalid preregistered timestep/current");
        CARLsim sim("003_whitebirch_intrinsic", GPU_MODE, SILENT, 0, 73);
        const int group=sim.createGroup("CA2_Pyramidal",1,EXCITATORY_NEURON,0,GPU_CORES);
        sim.setNeuronParameters(group,ASSAY_C,ASSAY_K,ASSAY_VR,ASSAY_VT,ASSAY_A,ASSAY_B,
                                ASSAY_VPEAK,ASSAY_VMIN,ASSAY_D,ASSAY_REFRACTORY);
        sim.setIntegrationMethod(RUNGE_KUTTA4,steps);
        // Auxiliary silent zero-weight connection satisfies native allocation assumptions.
        // It contributes no events/current and is not an artificial cell sample.
        Quiet quiet;
        const int input=sim.createSpikeGeneratorGroup("quiet",1,EXCITATORY_NEURON,0,GPU_CORES);
        sim.connect(input,group,"full",RangeWeight(0.f),1,RangeDelay(1),RadiusRF(-1),SYN_FIXED);
        sim.setSTP(input,group,false,STPu(.3f,0),STPtauU(80.f,0),STPtauX(120.f,0),
                   STPtdAMPA(5.f,0),STPtdNMDA(150.f,0),STPtdGABAa(6.f,0),STPtdGABAb(150.f,0),
                   STPtrNMDA(0.f,0),STPtrGABAb(0.f,0));
        sim.setSpikeGenerator(input,&quiet);
        sim.setupNetwork();
        SNN* snn=sim._impl->snn_;
        const GroupConfigMD& config=snn->groupConfigMDMap.at(group);
        RuntimeData& state=snn->runtimeData[config.netId];
        if (state.memType != GPU_MEM || config.lStartN!=config.lEndN)
            throw std::runtime_error("Actual single-neuron GPU allocation required");
        checked(cudaSetDevice(config.netId));
        const int n=config.lStartN;
        write_device(state.voltage+n,-70.0f);
        write_device(state.nextVoltage+n,-70.0f);
        write_device(state.recovery+n,float(ASSAY_U_HOLD));
        write_device(state.Izh_ref_c+n,0);
        write_device(state.curSpike+n,false);
        // Validate float32 initialization before any runNetwork call.
        if (read_device(state.voltage+n)!=-70.0f || read_device(state.nextVoltage+n)!=-70.0f
            || read_device(state.recovery+n)!=float(ASSAY_U_HOLD)
            || read_device(state.Izh_ref_c+n)!=0 || read_device(state.curSpike+n))
            throw std::runtime_error("Initial-state roundtrip failed");
        FILE* trace=std::fopen(argv[4],"wx");
        if (!trace) throw std::runtime_error("Trace path exists or cannot be created");
        observer.snn=snn; observer.state=&state; observer.neuron=n; observer.net=config.netId;
        observer.steps=steps; observer.trace=trace;
        std::fprintf(trace,"time_ms,v_mV,u_pA,ref_counter,curSpike\n");
        std::fprintf(trace,"0,-70,%.17g,0,0\n",double(float(ASSAY_U_HOLD)));
        const float hold=float(ASSAY_I_HOLD);
        const float pulse=hold+float(current);
        std::printf("{\"mode\":\"GPU_MODE\",\"steps_per_ms\":%d,\"step_current_pA\":%d,"
                    "\"holding_float32_pA\":%.17g,\"pulse_float32_pA\":%.17g,\"initial_u_float32_pA\":%.17g,"
                    "\"parameters_float32\":{\"C\":%.17g,\"k\":%.17g,\"Vr\":%.17g,\"Vt\":%.17g,"
                    "\"a\":%.17g,\"b\":%.17g,\"Vpeak\":%.17g,\"Vmin\":%.17g,\"d\":%.17g},"
                    "\"library_sha256\":\"%s\",\"harness_sha256\":\"%s\",\"header_sha256\":\"%s\","
                    "\"dt_float32_ms\":%.17g,\"refractory_period\":%d}\n",
                    steps,current,double(hold),double(pulse),double(float(ASSAY_U_HOLD)),
                    double(read_device(state.Izh_C+n)),double(read_device(state.Izh_k+n)),
                    double(read_device(state.Izh_vr+n)),double(read_device(state.Izh_vt+n)),
                    double(read_device(state.Izh_a+n)),double(read_device(state.Izh_b+n)),
                    double(read_device(state.Izh_vpeak+n)),double(read_device(state.Izh_c+n)),
                    double(read_device(state.Izh_d+n)),ASSAY_LIBRARY_SHA256,ASSAY_HARNESS_SHA256,
                    std::getenv("CA2_WHITEBIRCH_HEADER_SHA256") ? std::getenv("CA2_WHITEBIRCH_HEADER_SHA256") : "unrecorded",
                    double(snn->networkConfigs[config.netId].timeStep),read_device(state.Izh_ref+n));
        sim.setExternalCurrent(group,hold);
        sim.runNetwork(0,100,false);
        sim.setExternalCurrent(group,pulse);
        sim.runNetwork(1,0,false);
        sim.setExternalCurrent(group,hold);
        sim.runNetwork(0,100,false);
        observer.trace=nullptr;
        std::fclose(trace);
        if (observer.rows != uint64_t(1200)*steps)
            throw std::runtime_error("Incorrect substep snapshot count");
        return 0;
    } catch (const std::exception& e) {
        observer.trace=nullptr;
        std::fprintf(stderr,"Native GPU assay failed: %s\n",e.what());
        return 1;
    }
}
