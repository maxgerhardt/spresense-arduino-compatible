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
assert isdir(FRAMEWORK_DIR)

mcu = board_config.get("build.mcu", "")
mcu_type = mcu[:-2]
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

def add_upload_protocol_defines(board, upload_protocol):
    if upload_protocol == "serial":
        env.Append(
            CPPDEFINES=[("CONFIG_MAPLE_MINI_NO_DISABLE_DEBUG", 1)])
    elif upload_protocol == "dfu":
        env.Append(CPPDEFINES=["SERIAL_USB"])
    else:
        env.Append(
            CPPDEFINES=[
                ("CONFIG_MAPLE_MINI_NO_DISABLE_DEBUG", 1),
                "SERIAL_USB"
            ])

    is_generic = board.startswith("generic") or board == "hytiny_stm32f103t"
    if upload_protocol in ("stlink", "dfu", "jlink") and is_generic:
        env.Append(CPPDEFINES=["GENERIC_BOOTLOADER"])

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
        "-fpermissive",
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
    ],
    CPPPATH=[
        join(FRAMEWORK_DIR, "cores", "arduino", "api", "deprecated"),
    ],
    LINKFLAGS=[
        "-ggdb"
        "-mthumb",
        "-mcpu=%s" % board_config.get("build.cpu"),
        "-mfloat-abi=hard",
        "-mfpu=fpv4-sp-d16"
        "-Xlinker",
        "--entry=__start"
        "-nodefaultlibs"
        "-nostartfiles",
        "-Wl,--defsym,__reserved_ramsize=1572864-786432",
        # linkerscript
        "-Wl,--gc-sections",
        '-Wl,-Map="%s"' % join("${BUILD_DIR}", "${PROGNAME}.map"),
        "-u spresense_main"
    ],
    LIBS=[
        # All freaking libs
        "gcc",
        "m",
        "supc++_nano",
    ],
#    LIBPATH=[join(CMSIS_DIR, "DSP", "Lib", "GCC")],
)

env.ProcessFlags(board_config.get("build.framework_extra_flags.arduino", ""))

#
# Linker requires preprocessing with correct RAM|ROM sizes
#

if not board_config.get("build.ldscript", ""):
    if not isfile(join(env.subst(variant_dir), "ramconfig.ld")):
        print("Warning! Cannot find linker script for the current target!\n")
    env.Append(
        LINKFLAGS=[
            (
                "-Wl,--default-script",
                join(
                    inc_variant_dir,
                    board_config.get("build.arduino.ldscript", "ramconfig.ld"),
                ),
            )
        ]
    )

#
# Process configuration flags
#

cpp_defines = env.Flatten(env.get("CPPDEFINES", []))

process_standard_library_configuration(cpp_defines)
add_upload_protocol_defines(board_name, upload_protocol)
# defining HAL_UART_MODULE_ENABLED causes build failure 'uart_debug_write' was not declared in this scope
#process_usart_configuration(cpp_defines)
process_usb_configuration(cpp_defines)

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
