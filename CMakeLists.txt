cmake_minimum_required(VERSION 3.22)
project(memdif3d VERSION 0.1.0 LANGUAGES Fortran)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

option(MEMDIF3D_OPENMP "Build with OpenMP" OFF)

set(CMAKE_Fortran_MODULE_DIRECTORY ${CMAKE_BINARY_DIR}/mod)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})

configure_file(src/version.f90.in ${CMAKE_BINARY_DIR}/generated/version.f90 @ONLY)

add_executable(memdif3d
  ${CMAKE_BINARY_DIR}/generated/version.f90
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
  set_tests_properties(version PROPERTIES PASS_REGULAR_EXPRESSION "MEMDIF3D ${PROJECT_VERSION}")
  add_test(NAME no_arguments COMMAND memdif3d)
  set_tests_properties(no_arguments PROPERTIES PASS_REGULAR_EXPRESSION "Usage")
endif()

install(TARGETS memdif3d RUNTIME DESTINATION bin)
