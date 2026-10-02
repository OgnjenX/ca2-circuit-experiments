#include "../calibration_config.h"
#include "../core_config.h"
#include "../setup.h"
#include "../readout_config.h"

#include <carlsim.h>
#include <callback.h>
#include <neuron_monitor.h>
#include <algorithm>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
struct Events : SpikeGenerator {
    std::vector<std::vector<int>> events;
    Events(int n, const std::string& path) : events(n) {
        std::ifstream f(path);
        if (!f)
            throw std::runtime_error("Missing events: " + path);
        int t, id;
        while (f >> t >> id) {
            if (t < 0 || id < 0 || id >= n)
                throw std::runtime_error("Invalid spike event");
            events[id].push_back(t);
        }
        if (!f.eof())
            throw std::runtime_error("Malformed events: " + path);
        for (auto& v : events) {
            std::sort(v.begin(), v.end());
            if (std::adjacent_find(v.begin(), v.end()) != v.end())
                throw std::runtime_error("Duplicate same-cell same-ms events");
        }
    }
    int nextSpikeTime(CARLsim*, int, int i, int current, int last, int end) override {
        const auto& v = events[i];
        auto it = std::lower_bound(v.begin(), v.end(), std::max(current, last + 1));
        return it != v.end() && *it < end ? *it : -1;
    }
};
int main(int argc, char** argv) {
    if (argc != 6 && argc != 7 && argc != 8) {
        std::cerr
            << "Usage: circuit core|readout|calibration seed duration_ms substeps event_directory [inhibitory_gain] [all|pyramidal]\n";
        return 2;
    }
    std::string mode = argv[1], dir = argv[5];
    int seed = std::stoi(argv[2]), duration = std::stoi(argv[3]), steps = std::stoi(argv[4]);
    if ((mode != "core" && mode != "readout" && mode != "calibration") || seed < 0 ||
        duration < 1 || steps < 1 || steps > 100)
        return 2;
    float inhibitory_gain = argc >= 7 ? std::stof(argv[6]) : 1.0f;
    if (inhibitory_gain < 0 || inhibitory_gain > 1000)
        return 2;
    std::string inhibitory_scope = argc == 8 ? argv[7] : "all";
    if (inhibitory_scope != "all" && inhibitory_scope != "pyramidal")
        return 2;
    std::srand(seed);
    if (mode == "calibration") {
        Events ec(10818, dir + "/MEC_LII_Stellate.txt"), ca3(4096, dir + "/CA3_Pyramidal.txt");
        CARLsim sim("ca2_calibration", GPU_MODE, USER, 0, seed);
        const auto groups = ca2_nominal::configure_calibration(sim);
        sim.setSpikeGenerator(groups.MEC_LII_Stellate, &ec);
        sim.setSpikeGenerator(groups.CA3_Pyramidal, &ca3);
        sim.setIntegrationMethod(RUNGE_KUTTA4, steps);
        sim.setupNetwork();
        sim.setSpikeMonitor(groups.CA2_Pyramidal, "DEFAULT");
        sim.setSpikeMonitor(groups.MEC_LII_Stellate, "DEFAULT");
        sim.setSpikeMonitor(groups.CA3_Pyramidal, "DEFAULT");
        groups.monitor_CA2->startRecording();
        sim.runNetwork(duration / 1000, duration % 1000);
        groups.monitor_CA2->stopRecording();
    } else if (mode == "core") {
        Events ec(10818, dir + "/MEC_LII_Stellate.txt"), ca3(4096, dir + "/CA3_Pyramidal.txt");
        CARLsim sim("ca2_core", GPU_MODE, USER, 0, seed);
        std::vector<short int> core_inhibitory_connections, core_pyramidal_inhibitory_connections;
        const auto groups = ca2_nominal::configure_core(
            sim, core_inhibitory_connections, core_pyramidal_inhibitory_connections);
        std::vector<NeuronMonitor*> inhibitory_monitors;
        for (int group : {groups.CA2_Basket,
                          groups.CA2_Wide_Arbor_Basket,
                          groups.CA2_Bistratified,
                          groups.CA2_SP_SR})
            inhibitory_monitors.push_back(sim.setNeuronMonitor(group, "DEFAULT"));
        sim.setSpikeGenerator(groups.MEC_LII_Stellate, &ec);
        sim.setSpikeGenerator(groups.CA3_Pyramidal, &ca3);
        sim.setIntegrationMethod(RUNGE_KUTTA4, steps);
        sim.setupNetwork();
        ca2_nominal::setup_monitors(sim, groups);
        if (inhibitory_gain != 1.0f)
            for (short int id : (inhibitory_scope == "all" ? core_inhibitory_connections
                                                           : core_pyramidal_inhibitory_connections))
                sim.scaleWeights(id, inhibitory_gain, true);
        sim.setSpikeMonitor(groups.MEC_LII_Stellate, "DEFAULT");
        sim.setSpikeMonitor(groups.CA3_Pyramidal, "DEFAULT");
        for (auto* m : inhibitory_monitors)
            m->startRecording();
        groups.monitor_CA2->startRecording();
        sim.runNetwork(duration / 1000, duration % 1000);
        groups.monitor_CA2->stopRecording();
        for (auto* m : inhibitory_monitors)
            m->stopRecording();
    } else {
        Events pyr(18956, dir + "/CA2_Pyramidal.txt"), basket(105, dir + "/CA2_Basket.txt"),
            wide(147, dir + "/CA2_Wide_Arbor_Basket.txt"), bi(79, dir + "/CA2_Bistratified.txt"),
            sp(94, dir + "/CA2_SP_SR.txt"), ca3(4096, dir + "/CA3_Pyramidal.txt");
        CARLsim sim("ca1_readout", GPU_MODE, USER, 0, seed);
        const auto groups = ca2_nominal::configure_readout(sim);
        NeuronMonitor* monitor_CA1 = sim.setNeuronMonitor(groups.CA1_Pyramidal, "DEFAULT");
        sim.setSpikeGenerator(groups.CA2_Pyramidal, &pyr);
        sim.setSpikeGenerator(groups.CA2_Basket, &basket);
        sim.setSpikeGenerator(groups.CA2_Wide_Arbor_Basket, &wide);
        sim.setSpikeGenerator(groups.CA2_Bistratified, &bi);
        sim.setSpikeGenerator(groups.CA2_SP_SR, &sp);
        sim.setSpikeGenerator(groups.CA3_Pyramidal, &ca3);
        sim.setIntegrationMethod(RUNGE_KUTTA4, steps);
        sim.setupNetwork();
        for (int group : {groups.CA2_Pyramidal,
                          groups.CA2_Basket,
                          groups.CA2_Wide_Arbor_Basket,
                          groups.CA2_Bistratified,
                          groups.CA2_SP_SR,
                          groups.CA3_Pyramidal})
            sim.setSpikeMonitor(group, "DEFAULT");
        sim.setSpikeMonitor(groups.CA1_Pyramidal, "DEFAULT");
        sim.setSpikeMonitor(groups.CA1_Basket, "DEFAULT");
        sim.setSpikeMonitor(groups.CA1_Bistratified, "DEFAULT");
        monitor_CA1->startRecording();
        sim.runNetwork(duration / 1000, duration % 1000);
        monitor_CA1->stopRecording();
    }
    std::cout << "EXPERIMENT_COMPLETE mode=" << mode << " seed=" << seed
              << " duration_ms=" << duration << " substeps=" << steps << std::endl;
    return 0;
}
