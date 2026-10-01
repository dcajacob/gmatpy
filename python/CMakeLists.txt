cmake_minimum_required(VERSION 3.19)
project(GmatHpop LANGUAGES C CXX)

# v0.1 packages Linux wheels. Fail explicitly rather than advertise untested ports.
if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
  message(FATAL_ERROR "gmat-hpop 0.1 supports Linux builds only")
endif()
find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
set(GMAT_PYTHON_EXTENSION_ONLY ON)
set(HPOP_PYTHON_VERSION "${Python3_VERSION_MAJOR}.${Python3_VERSION_MINOR}")
set(HPOP_API_TARGET "gmat_py${Python3_VERSION_MAJOR}${Python3_VERSION_MINOR}")
set(GMAT_PYTHON3_VERSIONS "${HPOP_PYTHON_VERSION}" CACHE STRING "" FORCE)
# Preserve the build frontend's selected interpreter when GMAT rediscovers Python.
set(GMAT_PYTHON3${Python3_VERSION_MINOR}_ROOT_DIR "${Python3_ROOT_DIR}" CACHE PATH "" FORCE)
set(GMAT_INCLUDE_GUI OFF CACHE BOOL "" FORCE)
set(GMAT_INCLUDE_QT_GUI OFF CACHE BOOL "" FORCE)
set(GMAT_INCLUDE_CSALT OFF CACHE BOOL "" FORCE)
set(GMAT_INCLUDE_API ON CACHE BOOL "" FORCE)
set(API_GENERATE_PYTHON ON CACHE BOOL "" FORCE)
set(API_GENERATE_JAVA OFF CACHE BOOL "" FORCE)
set(GMAT_BUILDOUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/engine-output" CACHE PATH "" FORCE)
set(SYS_PATH "$ENV{PATH}" CACHE STRING "" FORCE)

# The core has all forces used by v0.1; no GUI, optimizer, or Python-callback plugins.
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
if(NOT TARGET ${HPOP_API_TARGET})
  message(FATAL_ERROR "GMAT did not build bindings for Python ${HPOP_PYTHON_VERSION}")
endif()
target_compile_definitions(${HPOP_API_TARGET} PRIVATE GMAT_HPOP_PACKAGE)
# Optimize the numerical engine normally. Generated binding glue needs little
# optimization and is otherwise exceptionally expensive to compile.
target_compile_options(${HPOP_API_TARGET} PRIVATE -O1)
foreach(TARGET IN ITEMS GmatUtil GmatBase ${HPOP_API_TARGET})
  set_target_properties(${TARGET} PROPERTIES INSTALL_RPATH "$ORIGIN")
endforeach()
add_custom_target(gmat_hpop_wheel DEPENDS ${HPOP_API_TARGET})
install(TARGETS GmatUtil GmatBase ${HPOP_API_TARGET}
        LIBRARY DESTINATION gmat_hpop/_native COMPONENT HPOP)
get_target_property(HPOP_SWIG_DIR ${HPOP_API_TARGET} SWIG_SUPPORT_FILES_DIRECTORY)
install(FILES "${HPOP_SWIG_DIR}/gmat_py.py"
        DESTINATION gmat_hpop/_native COMPONENT HPOP)

# Keep scientific inputs, excluding plots, sample missions, and GUI assets.
set(HPOP_DATA "${CMAKE_CURRENT_SOURCE_DIR}/../application/data")
foreach(DIR IN ITEMS planetary_coeff time icrf atmosphere/earth)
  install(DIRECTORY "${HPOP_DATA}/${DIR}/"
          DESTINATION "gmat_hpop/data/${DIR}" COMPONENT HPOP)
endforeach()
install(FILES "${HPOP_DATA}/gravity/earth/EGM96.cof" "${HPOP_DATA}/gravity/earth/JGM3.cof"
              "${HPOP_DATA}/gravity/earth/JGM2.cof"
        DESTINATION gmat_hpop/data/gravity/earth COMPONENT HPOP)
install(FILES "${HPOP_DATA}/planetary_ephem/de/leDE1941.405"
        DESTINATION gmat_hpop/data/planetary_ephem/de COMPONENT HPOP)
install(FILES "${HPOP_DATA}/planetary_ephem/spk/DE405AllPlanets.bsp"
        DESTINATION gmat_hpop/data/planetary_ephem/spk COMPONENT HPOP)
install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/../application/License.txt"
        DESTINATION gmat_hpop/licenses RENAME GMAT.txt COMPONENT HPOP)
set(HPOP_XERCES_SOURCE_DIR "" CACHE PATH "Xerces source tree for dependency notices")
if(HPOP_XERCES_SOURCE_DIR)
  install(FILES "${HPOP_XERCES_SOURCE_DIR}/LICENSE"
          DESTINATION gmat_hpop/licenses RENAME Xerces-LICENSE.txt COMPONENT HPOP)
  install(FILES "${HPOP_XERCES_SOURCE_DIR}/NOTICE"
          DESTINATION gmat_hpop/licenses RENAME Xerces-NOTICE.txt COMPONENT HPOP)
endif()
