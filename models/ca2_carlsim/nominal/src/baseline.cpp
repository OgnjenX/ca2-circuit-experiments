#include "../old_config.h"
#include "../setup.h"
#include "../fresh_config.h"

#include <carlsim.h>
#include <cstdlib>
#include <iostream>
#include <string>
int main(int argc, char** argv) {
    if (argc != 5) {
        std::cerr << "Usage: baseline old|fresh seed duration_ms rk4_substeps\n";
        return 2;
    }
    const std::string config = argv[1];
    int seed = std::stoi(argv[2]), duration = std::stoi(argv[3]), steps = std::stoi(argv[4]);
    if ((config != "old" && config != "fresh") || seed < 0 || duration < 1 || steps < 1 ||
        steps > 100)
        return 2;
    CARLsim sim("ca2_baseline", GPU_MODE, USER, 0, seed);
    if (config == "old") {
        const auto groups = ca2_nominal::configure_old(sim);
        sim.setIntegrationMethod(RUNGE_KUTTA4, steps);
        sim.setupNetwork();
        ca2_nominal::setup_monitors(sim, groups);
        sim.setExternalCurrent(groups.CA2_Pyramidal, 300.0f);
        sim.runNetwork(duration / 1000, duration % 1000);
    } else {
        const auto groups = ca2_nominal::configure_fresh(sim);
        sim.setIntegrationMethod(RUNGE_KUTTA4, steps);
        sim.setupNetwork();
        ca2_nominal::setup_monitors(sim, groups);
        sim.setExternalCurrent(groups.CA2_Pyramidal, 300.0f);
        sim.runNetwork(duration / 1000, duration % 1000);
    }
    std::cout << "EXPERIMENT_COMPLETE config=" << config << " seed=" << seed
              << " duration_ms=" << duration << " rk4_substeps=" << steps << std::endl;
    return 0;
}
