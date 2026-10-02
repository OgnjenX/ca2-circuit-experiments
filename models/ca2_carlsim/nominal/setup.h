#pragma once

#include <carlsim.h>

namespace ca2_nominal {

template <typename Groups> inline void setup_monitors(CARLsim& sim, const Groups& groups) {
    sim.setSpikeMonitor(groups.CA2_Pyramidal, "DEFAULT");

    sim.setSpikeMonitor(groups.CA2_Basket, "DEFAULT");

    sim.setSpikeMonitor(groups.CA2_Wide_Arbor_Basket, "DEFAULT");

    sim.setSpikeMonitor(groups.CA2_Bistratified, "DEFAULT");

    sim.setSpikeMonitor(groups.CA2_SP_SR, "DEFAULT");
}

} // namespace ca2_nominal
