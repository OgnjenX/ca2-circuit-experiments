cmake_minimum_required(VERSION 3.25)
project(ca2_circuit_experiments LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Prefer the project's environment for both IDE and command-line checks.
if(NOT DEFINED Python3_EXECUTABLE AND EXISTS "${CMAKE_SOURCE_DIR}/.venv/bin/python")
    set(Python3_EXECUTABLE "${CMAKE_SOURCE_DIR}/.venv/bin/python" CACHE FILEPATH "Python interpreter")
endif()
find_package(Python3 3.12 REQUIRED COMPONENTS Interpreter)

enable_testing()
add_test(NAME repository_integrity
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/scripts/verify_repository.py")
add_test(NAME shared_python_tools
    COMMAND "${Python3_EXECUTABLE}" -m unittest discover -s tests -v)
set_tests_properties(repository_integrity shared_python_tools PROPERTIES
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    ENVIRONMENT "PYTHONPATH=${CMAKE_SOURCE_DIR}/src")

option(CA2_BUILD_MODELS "Build the editable C++ harnesses against the recorded GPU backend" ON)
set(CA2_RUNTIME_ROOT "${CMAKE_SOURCE_DIR}/data/workspaces/experiment_001" CACHE PATH "Prepared experiment runtime")

if(CA2_BUILD_MODELS)
    find_package(CUDAToolkit REQUIRED)
    find_package(Threads REQUIRED)
    set(backend "${CA2_RUNTIME_ROOT}/simulator-reversal-variant")
    if(NOT EXISTS "${backend}/libcarlsim.a.4.0.0")
        message(FATAL_ERROR "Prepare the runtime first: python scripts/fetch_artifacts.py runtime, then python scripts/prepare_workspace.py data/workspaces/experiment_001. Or configure with -DCA2_BUILD_MODELS=OFF for Python checks only.")
    endif()

    add_library(carlsim_recorded STATIC IMPORTED)
    set_target_properties(carlsim_recorded PROPERTIES
        IMPORTED_LOCATION "${backend}/libcarlsim.a.4.0.0"
        INTERFACE_INCLUDE_DIRECTORIES "${backend}/carlsim/interface/inc;${backend}/carlsim/kernel/inc;${backend}/carlsim/monitor")

    function(add_model target source)
        add_executable(${target} "${source}")
        target_link_libraries(${target} PRIVATE carlsim_recorded CUDA::cudart CUDA::curand Threads::Threads)
    endfunction()

    add_model(ca2_nominal models/ca2_carlsim/nominal/src/circuit.cpp)
    add_model(ca2_sensitivity models/ca2_carlsim/sensitivity/src/circuit.cpp)
    add_model(ca1_adequacy models/ca2_carlsim/ca1_adequacy/src/circuit.cpp)
    add_model(ca2_baseline models/ca2_carlsim/nominal/src/baseline.cpp)

    add_test(NAME native_configuration_calls
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/scripts/check_native_call_trace.py"
            --compiler "${CMAKE_CXX_COMPILER}")
endif()
