cmake_minimum_required(VERSION 3.19)
project(GmatPy LANGUAGES C CXX)

# Current builds package Linux wheels. Fail explicitly rather than advertise untested ports.
if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
  message(FATAL_ERROR "gmatpy currently supports Linux builds only")
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
set(GMAT_INCLUDE_QT_GUI OFF CACHE BOOL "" FORCE)
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
target_compile_options(${GMAT_PY_API_TARGET} PRIVATE -O1)
foreach(TARGET IN ITEMS GmatUtil GmatBase ${GMAT_PY_API_TARGET})
  set_target_properties(${TARGET} PROPERTIES INSTALL_RPATH "$ORIGIN")
endforeach()
add_custom_target(gmatpy_wheel DEPENDS ${GMAT_PY_API_TARGET})
# Wheels copy symlink targets as separate files. Keep the versioned runtime
# libraries and omit the unversioned linker aliases. Unversioned modules are
# still installed normally by NAMELINK_SKIP.
install(TARGETS GmatUtil GmatBase ${GMAT_PY_API_TARGET}
        LIBRARY DESTINATION gmatpy/_native COMPONENT GMAT_PY NAMELINK_SKIP)
get_target_property(GMAT_PY_SWIG_DIR ${GMAT_PY_API_TARGET} SWIG_SUPPORT_FILES_DIRECTORY)
install(FILES "${GMAT_PY_SWIG_DIR}/gmat_py.py"
        DESTINATION gmatpy/_native COMPONENT GMAT_PY)

# Keep scientific inputs, excluding plots, sample missions, and GUI assets.
set(GMAT_PY_DATA "${CMAKE_CURRENT_SOURCE_DIR}/../application/data")
foreach(DIR IN ITEMS planetary_coeff time icrf atmosphere/earth)
  install(DIRECTORY "${GMAT_PY_DATA}/${DIR}/"
          DESTINATION "gmatpy/data/${DIR}" COMPONENT GMAT_PY)
endforeach()
install(FILES "${GMAT_PY_DATA}/gravity/earth/EGM96.cof" "${GMAT_PY_DATA}/gravity/earth/JGM3.cof"
              "${GMAT_PY_DATA}/gravity/earth/JGM2.cof"
        DESTINATION gmatpy/data/gravity/earth COMPONENT GMAT_PY)
install(FILES "${GMAT_PY_DATA}/planetary_ephem/de/leDE1941.405"
        DESTINATION gmatpy/data/planetary_ephem/de COMPONENT GMAT_PY)
install(FILES "${GMAT_PY_DATA}/planetary_ephem/spk/DE405AllPlanets.bsp"
        DESTINATION gmatpy/data/planetary_ephem/spk COMPONENT GMAT_PY)
install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/../application/License.txt"
        DESTINATION gmatpy/licenses RENAME GMAT.txt COMPONENT GMAT_PY)
