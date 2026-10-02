#include <carlsim.h>
#include <callback.h>
#include <neuron_monitor.h>

#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include "slice_config.h"

class PulseInput : public SpikeGenerator {
public:
    PulseInput(int active, const std::string& path) : active_(active) {
        std::ifstream input(path);
        if (!input) throw std::runtime_error("Missing pulse schedule");
        int t;
        while (input >> t) times_.push_back(t);
        if (!input.eof() || times_.empty() || times_.front() < 0 ||
            !std::is_sorted(times_.begin(), times_.end()) ||
            std::adjacent_find(times_.begin(), times_.end()) != times_.end())
            throw std::runtime_error("Invalid pulse schedule");
    }

    int nextSpikeTime(CARLsim*, int, int cell, int current, int last, int end) override {
        if (cell >= active_) return -1;
        auto event = std::lower_bound(times_.begin(), times_.end(), std::max(current, last + 1));
        return event != times_.end() && *event < end ? *event : -1;
    }

private:
    int active_;
    std::vector<int> times_;
};

int main(int argc, char** argv) {
    try {
        if (argc != 7) {
            std::cerr << "Usage: assay seed active duration_ms steps pulse_file holding_pA\n";
            return 2;
        }
        const int seed = std::stoi(argv[1]);
        const int active = std::stoi(argv[2]);
        const int duration = std::stoi(argv[3]);
        const int steps = std::stoi(argv[4]);
        const float holding = std::stof(argv[6]);
        if (seed < 0 || active < 1 || active > 10818 || duration <= 4950 || steps < 1 || steps > 100)
            throw std::runtime_error("Arguments outside assay bounds");

        PulseInput input(active, argv[5]);
        std::srand(seed);
        CARLsim sim("ca2_slice", GPU_MODE, USER, 0, seed);
        const int target = configure_target(sim);
        const int source = configure_source(sim, target);
        sim.setSpikeGenerator(source, &input);
        auto* monitor = sim.setNeuronMonitor(target, "DEFAULT");
        sim.setSpikeMonitor(target, "DEFAULT");
        sim.setSpikeMonitor(source, "DEFAULT");
        sim.setIntegrationMethod(RUNGE_KUTTA4, steps);
        sim.setupNetwork();
        sim.setExternalCurrent(target, holding);

        // Settle the unchanged intrinsic model before recording the assay window.
        sim.runNetwork(4, 950);
        monitor->startRecording();
        const int remaining = duration - 4950;
        sim.runNetwork(remaining / 1000, remaining % 1000);
        monitor->stopRecording();
        std::cout << "ASSAY_COMPLETE seed=" << seed << " active=" << active
                  << " duration_ms=" << duration << " steps=" << steps << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 2;
    }
}
