# Packaging preflight only; native architecture, ABI and PIC still need validation.
function(gmatpy_check_source_dependencies)
  if(NOT CSPICE_DIR AND DEFINED ENV{CSPICE_DIR})
    set(CSPICE_DIR "$ENV{CSPICE_DIR}" CACHE PATH "Target-native CSPICE root" FORCE)
  endif()
  if(NOT CSPICE_DIR)
    if(WIN32)
      set(platform_dir windows)
    elseif(APPLE)
      set(platform_dir macosx)
    else()
      set(platform_dir linux)
    endif()
    if(CMAKE_SIZEOF_VOID_P EQUAL 8)
      set(bits 64)
    else()
      set(bits 32)
    endif()
    find_path(CSPICE_DIR NAMES include/SpiceUsr.h
      PATHS "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/../../depends/cspice/${platform_dir}/cspice${bits}"
      NO_DEFAULT_PATH)
  endif()
  if(WIN32)
    set(library_name cspice.lib)
  else()
    set(library_name cspice.a)
  endif()
  if(NOT F2C_DIR AND DEFINED ENV{F2C_DIR})
    set(F2C_DIR "$ENV{F2C_DIR}" CACHE PATH "Directory containing f2c.h" FORCE)
  endif()
  if(F2C_DIR)
    set(f2c_header "${F2C_DIR}/f2c.h")
  else()
    set(f2c_header "${CSPICE_DIR}/include/f2c.h")
  endif()
  if(NOT EXISTS "${CSPICE_DIR}/include/SpiceUsr.h"
     OR NOT EXISTS "${CSPICE_DIR}/lib/${library_name}"
     OR NOT EXISTS "${f2c_header}")
    message(FATAL_ERROR
      "GMAT Py source-build dependency missing. No compatible prebuilt wheel was selected.\n"
      "The source archive does not bundle the external CSPICE/f2c dependency.\n"
      "For the published standard CPython 3.14 wheels, use:\n"
      "  uv python pin 3.14\n"
      "  uv add --no-build-package gmatpy gmatpy==0.2.0\n"
      "For a deliberate native source build, provide a target-native PIC CSPICE tree\n"
      "containing include/SpiceUsr.h, include/f2c.h and lib/${library_name}, using\n"
      "  -Ccmake.define.CSPICE_DIR=/absolute/path/to/cspice\n"
      "or the CSPICE_DIR environment variable. If f2c.h is separate, also pass\n"
      "  -Ccmake.define.F2C_DIR=/absolute/path/to/f2c/include\n"
      "Current CSPICE_DIR: '${CSPICE_DIR}'; f2c header: '${f2c_header}'.\n"
      "See docs/installation.rst or https://gmatpy.readthedocs.io/en/latest/installation.html\n"
      "for native source-build prerequisites. MATLAB is not required for GMAT Py.")
  endif()
endfunction()
