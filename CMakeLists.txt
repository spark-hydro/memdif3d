cmake_minimum_required(VERSION 3.22)
project(memdif3d VERSION 0.1.0 LANGUAGES Fortran)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

option(MEMDIF3D_OPENMP "Build with OpenMP" OFF)

set(CMAKE_Fortran_MODULE_DIRECTORY ${CMAKE_BINARY_DIR}/mod)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})

# ---- banner information (src/version.f90.in) ----
set(MEMDIF3D_AUTHOR "iHydro M&D" CACHE STRING "Lab or developer name shown in the banner")
set(MEMDIF3D_DEPARTMENT "CECE Dept." CACHE STRING "Department shown in the banner")
set(MEMDIF3D_INSTITUTION "Texas Tech University" CACHE STRING "Institution shown in the banner")
set(MEMDIF3D_CONTACT "seonggyu.park@ttu.edu" CACHE STRING "Contact (e-mail) shown in the banner")

execute_process(COMMAND git describe --tags --always --dirty
  WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
  OUTPUT_VARIABLE BANNER_GIT_TAG OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET RESULT_VARIABLE git_rc)
if(NOT git_rc EQUAL 0 OR NOT BANNER_GIT_TAG)
  set(BANNER_GIT_TAG "unknown")
endif()

if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
  set(BANNER_COMPILER "gfortran ${CMAKE_Fortran_COMPILER_VERSION}")
elseif(CMAKE_Fortran_COMPILER_ID STREQUAL "IntelLLVM")
  set(BANNER_COMPILER "Intel ifx ${CMAKE_Fortran_COMPILER_VERSION}")
else()
  set(BANNER_COMPILER "${CMAKE_Fortran_COMPILER_ID} ${CMAKE_Fortran_COMPILER_VERSION}")
endif()
set(BANNER_BUILD_TYPE "${CMAKE_BUILD_TYPE}")
string(TIMESTAMP BANNER_BUILT "%Y-%m-%d %H:%M:%S UTC" UTC)

# apostrophes would end the Fortran string literal
foreach(v AUTHOR DEPARTMENT INSTITUTION CONTACT)
  string(REPLACE "'" "''" BANNER_${v} "${MEMDIF3D_${v}}")
  string(REPLACE "\"" "\"\"" BANNER_${v} "${BANNER_${v}}")
endforeach()

configure_file(src/version.f90.in ${CMAKE_BINARY_DIR}/generated/version.f90 @ONLY)

add_executable(memdif3d
  ${CMAKE_BINARY_DIR}/generated/version.f90
  src/kinds_mod.f90
  src/banner_mod.f90
  src/input_mod.f90
  src/solver_mod.f90
  src/output_mod.f90
  src/memdif3d.f90)

if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
  target_compile_options(memdif3d PRIVATE -Wall -Wextra -ffree-line-length-none)
  target_compile_options(memdif3d PRIVATE
    "$<$<CONFIG:Debug>:-g;-O0;-fcheck=all;-fbacktrace;-ffpe-trap=invalid,zero,overflow>"
    "$<$<CONFIG:Release>:-O3>")
elseif(CMAKE_Fortran_COMPILER_ID MATCHES "Intel")
  if(WIN32)
    target_compile_options(memdif3d PRIVATE
      "$<$<CONFIG:Debug>:/Od;/Zi;/check:all;/traceback>"
      "$<$<CONFIG:Release>:/O2>")
  else()
    target_compile_options(memdif3d PRIVATE
      "$<$<CONFIG:Debug>:-g;-O0;-check;all;-traceback>"
      "$<$<CONFIG:Release>:-O2>")
    target_link_options(memdif3d PRIVATE -static-intel)
  endif()
endif()

if(MEMDIF3D_OPENMP)
  find_package(OpenMP REQUIRED COMPONENTS Fortran)
  target_link_libraries(memdif3d PRIVATE OpenMP::OpenMP_Fortran)
endif()

include(CTest)
if(BUILD_TESTING)
  add_test(NAME version COMMAND memdif3d --version)
  set_tests_properties(version PROPERTIES PASS_REGULAR_EXPRESSION "memdif3d ${PROJECT_VERSION}")
  add_test(NAME no_arguments COMMAND memdif3d)
  set_tests_properties(no_arguments PROPERTIES PASS_REGULAR_EXPRESSION "Usage")

  find_package(Python3 COMPONENTS Interpreter)
  if(Python3_Interpreter_FOUND)
    # package files carry the whole model: prototype solver vs. reference step
    add_test(NAME input_files_reproduce_reference
      COMMAND ${Python3_EXECUTABLE} -I ${CMAKE_SOURCE_DIR}/tools/memdif_proto.py
              ${CMAKE_SOURCE_DIR}/data/reduced_matrix/memdif3d.nam)
    # full executable: field/probe output vs. prototype, restart, --fresh
    add_test(NAME run_reduced_matrix
      COMMAND ${Python3_EXECUTABLE} -I ${CMAKE_SOURCE_DIR}/tests/test_run.py $<TARGET_FILE:memdif3d>
              ${CMAKE_SOURCE_DIR}/data/reduced_matrix/memdif3d.nam)
    set_tests_properties(run_reduced_matrix PROPERTIES PASS_REGULAR_EXPRESSION "PASS" TIMEOUT 300)
    # other grids, off-centre source, sorption, advection; sealed box (mass balance, analytic end state); stability guard
    add_test(NAME other_geometries
      COMMAND ${Python3_EXECUTABLE} -I ${CMAKE_SOURCE_DIR}/tests/test_cases.py $<TARGET_FILE:memdif3d>)
    set_tests_properties(other_geometries PROPERTIES PASS_REGULAR_EXPRESSION "PASS" TIMEOUT 300)
    # animations need numpy, matplotlib and Pillow (see environment.yml); the test skips itself without them
    add_test(NAME animate_smoke
      COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/test_animate.py $<TARGET_FILE:memdif3d>
              ${CMAKE_SOURCE_DIR}/data/reduced_matrix/memdif3d.nam)
    set_tests_properties(animate_smoke PROPERTIES PASS_REGULAR_EXPRESSION "PASS|SKIP" SKIP_REGULAR_EXPRESSION "SKIP" TIMEOUT 300)
  endif()
endif()

install(TARGETS memdif3d RUNTIME DESTINATION bin)
