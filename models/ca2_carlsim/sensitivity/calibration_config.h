#pragma once

#include <carlsim.h>
#include <neuron_monitor.h>

namespace ca2_sensitivity {

struct CalibrationGroups {
    int CA2_Pyramidal;
    int MEC_LII_Stellate;
    int CA3_Pyramidal;
    NeuronMonitor* monitor_CA2;
};

inline CalibrationGroups configure_calibration(CARLsim& sim) {
    int CA2_Pyramidal = sim.createGroup("CA2_Pyramidal", 128, EXCITATORY_NEURON, 0, GPU_CORES);
    sim.setNeuronParameters(CA2_Pyramidal,
                            1630.0,
                            5.9432435,
                            -72.58829,
                            -58.78362,
                            0.0011350543,
                            -15.885261,
                            19.99006,
                            -62.646779,
                            74.0,
                            1);
    int MEC_LII_Stellate =
        sim.createSpikeGeneratorGroup("MEC_LII_Stellate", 10818, EXCITATORY_NEURON);
    int CA3_Pyramidal = sim.createSpikeGeneratorGroup("CA3_Pyramidal", 4096, EXCITATORY_NEURON);
    sim.connect(CA3_Pyramidal,
                CA2_Pyramidal,
                "random",
                RangeWeight(0.0f, 1.0f, 2.0f),
                0.10385675220818946f,
                RangeDelay(1),
                RadiusRF(-1),
                SYN_PLASTIC,
                1.3173580093137258f,
                0.0f);
    sim.setSTP(CA3_Pyramidal,
               CA2_Pyramidal,
               true,
               STPu(0.2223897477450981f, 0),
               STPtauU(26.37611124019608f, 0),
               STPtauX(385.28406637254903f, 0),
               STPtdAMPA(6.088500132352945f, 0),
               STPtdNMDA(150.0f, 0),
               STPtdGABAa(6.0f, 0),
               STPtdGABAb(150.0f, 0),
               STPtrNMDA(0.0f, 0),
               STPtrGABAb(0.0f, 0));
    sim.connect(MEC_LII_Stellate,
                CA2_Pyramidal,
                "random",
                RangeWeight(0.0f, 1.0f, 2.0f),
                0.0084661227921748f,
                RangeDelay(1),
                RadiusRF(-1),
                SYN_PLASTIC,
                2.1476304960784307f,
                0.0f);
    sim.setSTP(MEC_LII_Stellate,
               CA2_Pyramidal,
               true,
               STPu(0.25328488754901973f, 0),
               STPtauU(45.805902774509796f, 0),
               STPtauX(328.3802538235294f, 0),
               STPtdAMPA(4.788581445098041f, 0),
               STPtdNMDA(150.0f, 0),
               STPtdGABAa(6.0f, 0),
               STPtdGABAb(150.0f, 0),
               STPtrNMDA(0.0f, 0),
               STPtrGABAb(0.0f, 0));
    NeuronMonitor* monitor_CA2 = sim.setNeuronMonitor(CA2_Pyramidal, "DEFAULT");

    return {CA2_Pyramidal, MEC_LII_Stellate, CA3_Pyramidal, monitor_CA2};
}

} // namespace ca2_sensitivity
