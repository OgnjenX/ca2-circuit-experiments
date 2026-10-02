#pragma once

// An API recorder for refactor checks. It does not simulate neurons or a GPU.
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

const int EXCITATORY_NEURON = 1, INHIBITORY_NEURON = 2, GPU_CORES = 3;
const int GPU_MODE = 4, USER = 5, RUNGE_KUTTA4 = 6, SYN_PLASTIC = 7;

inline void trace_arguments() {}
template <typename First, typename... Rest>
inline void trace_arguments(const First& first, const Rest&... rest) {
    std::cout << '\t' << std::setprecision(17) << first;
    trace_arguments(rest...);
}
template <typename... Args> inline void trace_call(const char* name, const Args&... args) {
    std::cout << name;
    trace_arguments(args...);
    std::cout << '\n';
}

struct TraceParameter {
    std::string value;
    template <typename... Args> TraceParameter(const char* name, const Args&... args) {
        std::ostringstream stream;
        stream << name << std::setprecision(17);
        int unused[] = {0, ((void)(stream << ',' << args), 0)...};
        (void)unused;
        value = stream.str();
    }
};
inline std::ostream& operator<<(std::ostream& stream, const TraceParameter& parameter) {
    return stream << parameter.value;
}
#define TRACE_PARAMETER(name)                                                                      \
    struct name : TraceParameter {                                                                 \
        template <typename... Args> name(const Args&... args) : TraceParameter(#name, args...) {}  \
    };
TRACE_PARAMETER(RangeWeight)
TRACE_PARAMETER(RangeDelay)
TRACE_PARAMETER(RadiusRF)
TRACE_PARAMETER(STPu)
TRACE_PARAMETER(STPtauU)
TRACE_PARAMETER(STPtauX)
TRACE_PARAMETER(STPtdAMPA)
TRACE_PARAMETER(STPtdNMDA)
TRACE_PARAMETER(STPtdGABAa)
TRACE_PARAMETER(STPtdGABAb)
TRACE_PARAMETER(STPtrNMDA)
TRACE_PARAMETER(STPtrGABAb)
#undef TRACE_PARAMETER

class CARLsim;
struct SpikeGenerator {
    virtual ~SpikeGenerator() = default;
    virtual int nextSpikeTime(CARLsim*, int, int, int, int, int) = 0;
};
struct NeuronMonitor {
    int group;
    explicit NeuronMonitor(int id) : group(id) {}
    void startRecording() {
        trace_call("startRecording", group);
    }
    void stopRecording() {
        trace_call("stopRecording", group);
    }
};
class CARLsim {
    int next_group = 0;
    short int next_connection = 0;
    std::vector<std::unique_ptr<NeuronMonitor>> monitors;

  public:
    template <typename... Args> CARLsim(const Args&... args) {
        trace_call("CARLsim", args...);
    }
    template <typename... Args> int createGroup(const Args&... args) {
        trace_call("createGroup", next_group, args...);
        return next_group++;
    }
    template <typename... Args> int createSpikeGeneratorGroup(const Args&... args) {
        trace_call("createSpikeGeneratorGroup", next_group, args...);
        return next_group++;
    }
    template <typename... Args> short int connect(const Args&... args) {
        trace_call("connect", next_connection, args...);
        return next_connection++;
    }
    NeuronMonitor* setNeuronMonitor(int group, const char* path) {
        trace_call("setNeuronMonitor", group, path);
        monitors.emplace_back(new NeuronMonitor(group));
        return monitors.back().get();
    }
    void setSpikeGenerator(int group, SpikeGenerator* generator) {
        trace_call("setSpikeGenerator", group);
        // Compare callback binding and event delivery without recording pointer addresses.
        trace_call("firstSpike", group, generator->nextSpikeTime(this, group, 0, 0, -1, 10));
    }
#define TRACE_METHOD(name)                                                                         \
    template <typename... Args> void name(const Args&... args) {                                   \
        trace_call(#name, args...);                                                                \
    }
    TRACE_METHOD(setNeuronParameters)
    TRACE_METHOD(setSTP)
    TRACE_METHOD(setSpikeMonitor)
    TRACE_METHOD(setIntegrationMethod)
    TRACE_METHOD(setupNetwork)
    TRACE_METHOD(setExternalCurrent)
    TRACE_METHOD(scaleWeights)
    TRACE_METHOD(runNetwork)
#undef TRACE_METHOD
};
