##
## Author(s):
##    - Cedric GESTES <gestes@aldebaran-robotics.com>
##
## Copyright (C) 2010, 2011 Aldebaran Robotics
##

import os
import sys
import shlex
import glob
import logging
import qitools.sh
import qibuild

LOGGER = logging.getLogger("qibuild.toc.project")

class Project:
    """ store information about a project:
         - source directory
         - build  directory
         - build  configuration
         - dependencies
    """
    def __init__(self, directory):
        self.directory       = directory
        self.name            = os.path.split(directory)[-1]
        self.depends         = list()
        self.rdepends        = list()

        #build related flags
        self.cmake_flags     = list()
        self.build_directory = None

    def get_sdk_dir(self):
        return os.path.join(self.build_directory, "sdk")

    def update_depends(self, toc):
        """ update project dependency list """
        deps  = toc.configstore.get("project", self.name, "depends", default="").split()
        rdeps = toc.configstore.get("project", self.name, "rdepends", default="").split()
        self.depends.extend(deps)
        self.rdepends.extend(rdeps)

    def update_build_config(self, toc, build_directory_name):
        """ Update cmake_flags
           - add flags from the build_config
           - add flags from the project config
           - add flags from the command line
        """
        self.build_directory = os.path.join(self.directory, build_directory_name)
        #create the build_directory if it does not exists
        if not os.path.exists(self.build_directory):
            os.makedirs(self.build_directory)

        if toc.build_config:
            build_config_flags = toc.configstore.get("build", toc.build_config, "cmake", "flags", default=None)
            if build_config_flags:
                self.cmake_flags.extend(shlex.split(build_config_flags))

        project_flags = toc.configstore.get(self.name, "build", "cmake", "flags", default=None)
        if project_flags:
            self.cmake_flags.extend(shlex.split(project_flags))

        if toc.build_type:
            self.cmake_flags.append("CMAKE_BUILD_TYPE=%s" % (toc.build_type.toupper()))

        if toc.toolchain.name != "system":
            self.cmake_flags.append("QI_TOOLCHAIN_NAME=%s" % (toc.toolchain.name))

        if toc.cmake_flags:
            self.cmake_flags.extend(toc.cmake_flags)

    def set_custom_build_directory(self, build_dir):
        """ could be used to override the default build_directory
        """
        self.build_directory = build_dir
        #create the build_directory if it does not exists
        if not os.path.exists(self.build_directory):
            os.makedirs(self.build_directory)

    def __str__(self):
        res = ""
        res += "Project: %s\n" % (self.name)
        res += "  directory       = %s\n" % self.directory
        res += "  depends         = %s\n" % self.depends
        res += "  rdepends        = %s\n" % self.rdepends
        res += "  cmake_flags     = %s\n" % self.cmake_flags
        res += "  build_directory = %s" % self.build_directory
        return res




def get_qibuild_cmake_framework_path():
    """ return the path to the QiBuild Cmake framework """
    return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "cmake"))

def bootstrap(project, dep_sdk_dirs):
    """Generate the find_deps.cmake for the given project
    """
    build_dir = project.build_directory

    to_write  = "#############################################\n"
    to_write += "#QIBUILD AUTOGENERATED FILE. DO NOT EDIT.\n"
    to_write += "#############################################\n"
    to_write += "\n"
    to_write += "#QIBUILD CMAKE FRAMEWORK PATH:\n"
    to_write += "set(CMAKE_MODULE_PATH \"%s\")\n" % get_qibuild_cmake_framework_path()
    to_write += "\n"
    to_write += "#DEPENDENCIES:\n"
    for dep_sdk_dir in dep_sdk_dirs:
        to_write += "list(APPEND CMAKE_PREFIX_PATH \"%s\")\n" % qitools.sh.to_posix_path(dep_sdk_dir)

    output_path = os.path.join(build_dir, "dependencies.cmake")
    with open(output_path, "w") as output_file:
        output_file.write(to_write)
    LOGGER.debug("Wrote %s", output_path)


def configure(project, flags=None, toolchain_file=None, generator=None):
    """ Call cmake with correct options
    if toolchain_file is None a t001chain file is generated in the cmake binary directory.
    if toolchain_file is "", then CMAKE_TOOLCHAIN_FILE is not specified.
    """

    #TODO: guess generator

    if not os.path.exists(project.directory):
        raise qibuild.ConfigureException("source dir: %s does not exist, aborting" % project.directory)

    if not os.path.exists(os.path.join(project.directory, "CMakeLists.txt")):
        LOGGER.info("Not calling cmake for %s", os.path.basename(project.directory))
        return

    # Set generator (mandatory on windows, because cmake does not
    # autodetect visual studio compilers very well)
    cmake_args = []
    if generator:
        cmake_args.extend(["-G", generator])

    # Make a copy so that we do not modify
    # the list used by the called
    if flags:
        cmake_flags = flags[:]
    else:
        cmake_flags = list()
    cmake_flags.extend(project.cmake_flags)

    if toolchain_file:
        cmake_flags.append("CMAKE_TOOLCHAIN_FILE=" + toolchain_file)

    cmake_args.extend(["-D" + x for x in cmake_flags])

    qibuild.cmake(project.directory, project.build_directory, cmake_args)


def make(project, build_type, num_jobs=1, nmake=False, target=None):
    """Build the project"""
    build_dir = project.build_directory
    LOGGER.debug("[%s]: building in %s", project.name, build_dir)
    if sys.platform.startswith("win32") and not nmake:
        sln_files = glob.glob(build_dir + "/*.sln")
        if len(sln_files) == 0:
            LOGGER.debug("Not calling msbuild for %s", os.path.basename(build_dir))
            return

        if len(sln_files) != 1:
            err_message = "Found several sln files: "
            err_message += ", ".join(sln_files)
            raise qibuild.MakeException(err_message)
        sln_file = sln_files[0]
        qibuild.msbuild(sln_file, build_type=build_type, target=target)
    else:
        if not os.path.exists(os.path.join(build_dir, "Makefile")):
            LOGGER.debug("Not calling make for %s", os.path.basename(build_dir))
            return
        if sys.platform.startswith("win32"):
            qibuild.nmake(build_dir, target=target)
        else:
            qibuild.make(build_dir, num_jobs=num_jobs, target=target)
