# Copyright 2022-present Maximilian Gerhardt <maximilian.gerhardt@rub.de>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Arduino

Arduino Wiring-based Framework allows writing cross-platform software to
control devices attached to a wide range of Arduino boards to create all
kinds of creative coding, interactive objects, spaces or physical experiences.
"""

import json
from os.path import isfile, isdir, join

from platformio.util import get_systype

from SCons.Script import COMMAND_LINE_TARGETS, DefaultEnvironment

env = DefaultEnvironment()
platform = env.PioPlatform()
board_config = env.BoardConfig()
board_name = env.subst("$BOARD")

FRAMEWORK_DIR = platform.get_package_dir("framework-arduinosonyspresense")
SDK_DIR = platform.get_package_dir("tool-arduinosonyspresensesdk")
assert isdir(FRAMEWORK_DIR)
assert isdir(SDK_DIR)

env.ProcessFlags(board_config.get("build.framework_extra_flags.arduino", ""))

#
# Process configuration flags
#

cpp_defines = env.Flatten(env.get("CPPDEFINES", []))

# default settings
debug_enabled = False
target_core = ("main", None)
libraries = list()

if "PIO_FRAMEWORK_ARDUINO_ENABLE_DEBUG" in cpp_defines:
    debug_enabled = True
    env.Append(CPPDEFINES=["BRD_DEBUG"])
if "PIO_FRAMEWORK_ARDUINO_CORE_MAIN_CORE" in cpp_defines:
    pass
if "PIO_FRAMEWORK_ARDUINO_CORE_SUB_CORE_1" in cpp_defines:
    target_core = ("sub", 1)
    env.Append(CPPDEFINES=[("SUBCORE", 1)])
    libs
if "PIO_FRAMEWORK_ARDUINO_CORE_SUB_CORE_2" in cpp_defines:
    target_core = ("sub", 2)
    env.Append(CPPDEFINES=[("SUBCORE", 2)])
if "PIO_FRAMEWORK_ARDUINO_CORE_SUB_CORE_3" in cpp_defines:
    target_core = ("sub", 3)
    env.Append(CPPDEFINES=[("SUBCORE", 3)])
if "PIO_FRAMEWORK_ARDUINO_CORE_SUB_CORE_4" in cpp_defines:
    target_core = ("sub", 4)
    env.Append(CPPDEFINES=[("SUBCORE", 4)])
if "PIO_FRAMEWORK_ARDUINO_CORE_SUB_CORE_5" in cpp_defines:
    target_core = ("sub", 5)
    env.Append(CPPDEFINES=[("SUBCORE", 5)])

if target_core[0] == "main":
    libraries = [
        "libapps.a", "libarch.a", "libarm_cortexM4lf_math.a", "libaudio.a", "libbinfmt.a", "libboard.a", "libboards.a", 
        "libc.a", "libcmsis_nn.a", "libdrivers.a", "libfs.a", "libmm.a", "libnet.a", "libnnablart.a", "libsched.a", 
        "libsslutils.a", "libxx.a"
    ]
else:
    libraries = [
        "libapps.a", "libarch.a", "libarm_cortexM4lf_math.a", "libbinfmt.a", "libboard.a", "libboards.a", "libc.a", 
        "libcmsis_nn.a", "libdrivers.a", "libfs.a", "libmm.a", "libsched.a", "libxx.a"
    ]

build_type_prefix = "" if target_core[0] == "main" else "subcore-"
build_type = build_type_prefix + "release" if not debug_enabled else "debug"
kernel_path = join(SDK_DIR, build_type)
libpath = join(kernel_path, "nuttx", "libs")

original_variant = board_config.get("build.arduino.variant", "spresense")
# subcores use a different variant
variant = original_variant if target_core[0] == "main" else "spresense_sub"

computed_libs = [File(join(libpath, l)) for l in libraries]
computed_libs.extend([
    "gcc",
    "m",
    "supc++_nano"
])

mcu = board_config.get("build.mcu", "")
variant = board_config.get(
    "build.variant", board_config.get("build.arduino.variant", "spresense"))

variants_dir = (
    join("$PROJECT_DIR", board_config.get("build.variants_dir"))
    if board_config.get("build.variants_dir", "")
    else join(FRAMEWORK_DIR, "variants")
)
variant_dir = join(variants_dir, variant)
inc_variant_dir = variant_dir
if "windows" not in get_systype().lower() and not (
    set(["_idedata", "idedata"]) & set(COMMAND_LINE_TARGETS) and " " not in variant_dir
):
    inc_variant_dir = variant_dir.replace("(", r"\(").replace(")", r"\)")

upload_protocol = env.subst("$UPLOAD_PROTOCOL")

def get_arduino_board_id(board_config, mcu):
    # User-specified value
    if board_config.get("build.arduino.board", ""):
        return board_config.get("build.arduino.board")
    return "spresense_ast"


board_id = get_arduino_board_id(board_config, mcu)

env.Append(
    ASFLAGS=["-D__ASSEMBLY__", "-ggdb", "-gdwarf-3", "-x", "assembler-with-cpp"],
    CFLAGS=["-std=gnu11"],
    CXXFLAGS=[
        "-std=gnu++11",
        "-fno-rtti",
        "-fno-exceptions",
        "-fno-use-cxa-atexit",
        "-fpermissive",
    ],
    CCFLAGS=[
        "-Os",  # optimize for size
        "-MMD",
        "-Wall",
        "-mabi=aapcs",
        "-mfpu=fpv4-sp-d16",
        "-mfloat-abi=hard",
        "-pipe", 
        "-mcpu=%s" % board_config.get("build.cpu"),
        "-mthumb",
        "-ffunction-sections",  # place each function in its own section
        "-fdata-sections",
        "-fno-builtin",
        "-fno-strict-aliasing",
        "-fno-strength-reduce",
        "-fomit-frame-pointer",
        "--param",
        "max-inline-insns-single=500",
        "-ggdb",
        "-gdwarf-3"
    ],
    CPPDEFINES=[
        ("ARDUINO", 10816),
        ("F_CPU", "$BOARD_F_CPU"), # for compatiblity
        "ARDUINO_ARCH_SPRESENSE",
        "ARDUINO_%s" % board_id,
        ("BOARD_NAME", '\\"%s\\"' % board_id),
        "CONFIG_WCHAR_BUILTIN",
        "CONFIG_HAVE_DOUBLE",
        "__NuttX__"
    ],
    CPPPATH=[
        join(FRAMEWORK_DIR, "cores", "spresense"),
        join(FRAMEWORK_DIR, "cores", "spresense", "avr"),
        join(kernel_path, "nuttx", "include", "libcxx"),
        join(kernel_path, "nuttx", "include"),
        join(kernel_path, "nuttx", "arch"),
        join(kernel_path, "nuttx", "arch", "chip"),
        join(kernel_path, "sdk", "include"),
        join(kernel_path, "sdk", "modules", "include"),
        join(kernel_path, "sdk", "apps", "include"),
        join(kernel_path, "sdk", "system", "include"),
        join(kernel_path, "sdk", "externals", "include"),
        join(kernel_path, "sdk", "externals", "include", "cmsis"),
    ],
    LINKFLAGS=[
        "-ggdb",
        "-mthumb",
        "-mcpu=%s" % board_config.get("build.cpu"),
        "-mfloat-abi=hard",
        "-mfpu=fpv4-sp-d16",
        "-Xlinker",
        "--entry=__start",
        "-nodefaultlibs",
        "-nostartfiles",
        "-Wl,--defsym,__reserved_ramsize=1572864-%d" % board_config.get("upload.maximum_size"),
        # linkerscript
        "-Wl,--gc-sections",
        '-Wl,-Map="%s"' % join("${BUILD_DIR}", "${PROGNAME}.map"),
        "-u spresense_main"
    ],
    LIBS=computed_libs,
#    LIBPATH=[join(CMSIS_DIR, "DSP", "Lib", "GCC")],
)


# copy CCFLAGS to ASFLAGS (-x assembler-with-cpp mode)
env.Append(ASFLAGS=env.get("CCFLAGS", [])[:])

env.Append(
    LIBSOURCE_DIRS=[
        join(FRAMEWORK_DIR, "libraries"),
    ]
)

#
# Target: Build Core Library
#

libs = []

if "build.variant" in board_config:
    variant_dir = join(variants_dir, variant)
    env.Append(
        CPPPATH=[variant_dir],
        LIBPATH=[variant_dir]
    )
    env.BuildSources(join("$BUILD_DIR", "FrameworkArduinoVariant"), variant_dir)

libs.append(env.BuildLibrary(
    join("$BUILD_DIR", "FrameworkArduino"), join(FRAMEWORK_DIR, "cores", "spresense")
))

env.Prepend(LIBS=libs)
