cmake_minimum_required(VERSION 3.19)
project(GmatPy LANGUAGES C CXX)
set(GMAT_PY_PROFILE "extended" CACHE STRING "GMAT Py profile: minimal or extended")
if(NOT GMAT_PY_PROFILE MATCHES "^(minimal|extended)$")
  message(FATAL_ERROR "GMAT_PY_PROFILE must be minimal or extended")
endif()
if(GMAT_PY_PROFILE STREQUAL "minimal")
  set(GMAT_ENABLE_SPICE OFF CACHE BOOL "" FORCE)
  set(GMAT_PY_HAS_SPICE false)
else()
  set(GMAT_ENABLE_SPICE ON CACHE BOOL "" FORCE)
  set(GMAT_PY_HAS_SPICE true)
endif()

# Windows x64 is an explicit qualification path; other ports stay gated.
option(GMAT_PY_EXPERIMENTAL_WINDOWS "Enable Windows x64 qualification builds" OFF)
if(WIN32)
  if(NOT GMAT_PY_EXPERIMENTAL_WINDOWS OR NOT MSVC OR NOT CMAKE_SIZEOF_VOID_P EQUAL 8
     OR NOT CMAKE_CXX_COMPILER_ARCHITECTURE_ID STREQUAL "x64")
    message(FATAL_ERROR "Windows qualification requires MSVC x64 and GMAT_PY_EXPERIMENTAL_WINDOWS=ON")
  endif()
elseif(APPLE)
  option(GMAT_PY_EXPERIMENTAL_MACOS "Enable native single-architecture macOS qualification" OFF)
  list(LENGTH CMAKE_OSX_ARCHITECTURES GMAT_PY_MAC_ARCH_COUNT)
  if(NOT GMAT_PY_EXPERIMENTAL_MACOS OR NOT GMAT_PY_MAC_ARCH_COUNT EQUAL 1
     OR NOT CMAKE_OSX_ARCHITECTURES MATCHES "^(arm64|x86_64)$")
    message(FATAL_ERROR "macOS qualification requires one explicit native arm64/x86_64 architecture and GMAT_PY_EXPERIMENTAL_MACOS=ON")
  endif()
elseif(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
  message(FATAL_ERROR "gmatpy currently supports Linux builds and experimental Windows x64/macOS only")
endif()
find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
set(GMAT_PYTHON_EXTENSION_ONLY ON)
set(GMAT_PY_PYTHON_VERSION "${Python3_VERSION_MAJOR}.${Python3_VERSION_MINOR}")
set(GMAT_PY_API_TARGET "gmat_py${Python3_VERSION_MAJOR}${Python3_VERSION_MINOR}")
set(GMAT_PYTHON3_VERSIONS "${GMAT_PY_PYTHON_VERSION}" CACHE STRING "" FORCE)
# Preserve the build frontend's selected interpreter when GMAT rediscovers Python.
set(GMAT_PYTHON3${Python3_VERSION_MINOR}_ROOT_DIR "${Python3_ROOT_DIR}" CACHE PATH "" FORCE)
set(GMAT_INCLUDE_GUI OFF CACHE BOOL "" FORCE)
set(GMAT_INCLUDE_DATA_UPDATER OFF CACHE BOOL "" FORCE)
set(GMAT_INCLUDE_CSALT OFF CACHE BOOL "" FORCE)
set(GMAT_INCLUDE_API ON CACHE BOOL "" FORCE)
set(API_GENERATE_PYTHON ON CACHE BOOL "" FORCE)
set(API_GENERATE_JAVA OFF CACHE BOOL "" FORCE)
set(GMAT_BUILDOUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/engine-output" CACHE PATH "" FORCE)
set(SYS_PATH "$ENV{PATH}" CACHE STRING "" FORCE)

# The core supplies the current interfaces; no GUI, optimizer, or Python-callback plugins.
file(STRINGS "${CMAKE_CURRENT_SOURCE_DIR}/../plugins/CMakeLists.txt" PLUGIN_OPTIONS
     REGEX "^OPTION\\(PLUGIN_")
foreach(LINE IN LISTS PLUGIN_OPTIONS)
  string(REGEX MATCH "PLUGIN_[A-Z0-9_]+" PLUGIN_OPTION "${LINE}")
  set(${PLUGIN_OPTION} OFF CACHE BOOL "" FORCE)
endforeach()
# Defined empty cache entries suppress find_path/find_file discovery, even if
# the developer has additional plugin trees alongside this checkout.
set(GMAT_PROPRIETARYPLUGINS_PATH "" CACHE PATH "" FORCE)
set(GMAT_ADDITIONAL_PLUGINS "" CACHE FILEPATH "" FORCE)

add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/.." engine EXCLUDE_FROM_ALL)
if(NOT TARGET ${GMAT_PY_API_TARGET})
  message(FATAL_ERROR "GMAT did not build bindings for Python ${GMAT_PY_PYTHON_VERSION}")
endif()
target_compile_definitions(${GMAT_PY_API_TARGET} PRIVATE GMAT_PY_PACKAGE)
# Optimize the numerical engine normally. Generated binding glue needs little
# optimization and is otherwise exceptionally expensive to compile.
if(MSVC)
  target_compile_options(${GMAT_PY_API_TARGET} PRIVATE /O1)
else()
  target_compile_options(${GMAT_PY_API_TARGET} PRIVATE -O1)
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
  foreach(TARGET IN ITEMS GmatUtil GmatBase ${GMAT_PY_API_TARGET})
    set_target_properties(${TARGET} PROPERTIES INSTALL_RPATH "$ORIGIN")
  endforeach()
elseif(APPLE)
  foreach(TARGET IN ITEMS GmatUtil GmatBase)
    # Upstream R2026a is a release label, not a valid Mach-O numeric version.
    # Keep one physical dylib per target in the wheel, with relocatable IDs.
    set_property(TARGET ${TARGET} PROPERTY VERSION)
    set_property(TARGET ${TARGET} PROPERTY SOVERSION)
    set_target_properties(${TARGET} PROPERTIES
      MACHO_CURRENT_VERSION "0.2.0" MACHO_COMPATIBILITY_VERSION "0.2.0"
      MACOSX_RPATH TRUE INSTALL_NAME_DIR "@rpath" BUILD_WITH_INSTALL_NAME_DIR TRUE)
  endforeach()
  foreach(TARGET IN ITEMS GmatUtil GmatBase ${GMAT_PY_API_TARGET})
    set_target_properties(${TARGET} PROPERTIES INSTALL_RPATH "@loader_path"
      INSTALL_RPATH_USE_LINK_PATH FALSE)
  endforeach()
endif()
add_custom_target(gmatpy_wheel DEPENDS ${GMAT_PY_API_TARGET})
# Wheels copy symlink targets as separate files. Keep the versioned runtime
# libraries and omit the unversioned linker aliases. Unversioned modules are
# still installed normally by NAMELINK_SKIP.
install(TARGETS GmatUtil GmatBase ${GMAT_PY_API_TARGET}
        LIBRARY DESTINATION gmatpy/_native COMPONENT GMAT_PY NAMELINK_SKIP
        RUNTIME DESTINATION gmatpy/_native COMPONENT GMAT_PY)
get_target_property(GMAT_PY_SWIG_DIR ${GMAT_PY_API_TARGET} SWIG_SUPPORT_FILES_DIRECTORY)
install(FILES "${GMAT_PY_SWIG_DIR}/gmat_py.py"
        DESTINATION gmatpy/_native COMPONENT GMAT_PY)

# GMAT Py modification (2026-10-01): distribute selected inputs and component
# notices; omit optional weather datasets whose redistribution terms are unresolved.
set(GMAT_PY_DATA "${CMAKE_CURRENT_SOURCE_DIR}/../application/data")
set(GMAT_PY_DATA_FILES
  atmosphere/earth/EarthExponentialAtmosphereData.txt
  gravity/earth/EGM96.cof
  gravity/earth/JGM2.cof
  gravity/earth/JGM3.cof
  icrf/ICRF_ERFA_Table.txt
  planetary_coeff/NUTATION.DAT
  planetary_coeff/SPICEEarthCurrentKernel.bpc
  planetary_coeff/SPICEEarthPredictedKernel.bpc
  planetary_coeff/SPICELunaCurrentKernel.bpc
  planetary_coeff/SPICELunaFrameKernel.tf
  planetary_coeff/SPICEPlanetaryConstantsKernel.tpc
  planetary_coeff/earth_latest_high_prec.bpc
  planetary_coeff/eopc04_08.62-now
  planetary_ephem/de/gmatpy_de405_1941_2201.405
  planetary_ephem/spk/gmatpy_de405_all_planets.bsp
  time/SPICELeapSecondKernel.tls
  time/tai-utc.dat
)
if(GMAT_PY_PROFILE STREQUAL "minimal")
  list(FILTER GMAT_PY_DATA_FILES EXCLUDE REGEX "(^planetary_ephem/spk/|/SPICE|/earth_latest_high_prec)")
endif()
string(REPLACE ";" "\", \"" GMAT_PY_JSON_FILES "${GMAT_PY_DATA_FILES}")
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/BUILD_PROFILE.json"
  "{\"schema_version\": 1, \"profile\": \"${GMAT_PY_PROFILE}\", \"spice\": ${GMAT_PY_HAS_SPICE}, \"data_files\": [\"${GMAT_PY_JSON_FILES}\"]}\n")
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/BUILD_PROFILE.json" DESTINATION gmatpy COMPONENT GMAT_PY)
foreach(DATA_FILE IN LISTS GMAT_PY_DATA_FILES)
  get_filename_component(DATA_DIR "${DATA_FILE}" DIRECTORY)
  install(FILES "${GMAT_PY_DATA}/${DATA_FILE}"
          DESTINATION "gmatpy/data/${DATA_DIR}" COMPONENT GMAT_PY)
endforeach()
install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/../application/License.txt"
        DESTINATION gmatpy/licenses RENAME GMAT.txt COMPONENT GMAT_PY)
