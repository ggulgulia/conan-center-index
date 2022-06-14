import os
from conans import CMake, ConanFile, tools
from conans.errors import ConanInvalidConfiguration
import conan.tools.files
import textwrap, shutil
import functools

class ogrecmakeconan(ConanFile):
    name = "ogre"
    license = "MIT"
    homepage = "https://github.com/OGRECave/ogre"
    url = "https://github.com/conan-io/conan-center-index"
    description = "A scene-oriented, flexible 3D engine written in C++ "
    topics = ("graphics", "rendering", "engine", "c++")

    settings = "os", "compiler", "build_type", "arch"

    generators = "cmake", "cmake_find_package"
    exports_sources = "CMakeLists.txt", "patches/**"
    #options copied from https://github.com/StatelessStudio/ogre-conan/blob/master/conanfile.py
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "ogre_set_double": [True, False],
        "ogre_glsupport_use_egl": [True, False],
    }

    # default options copied from https://github.com/StatelessStudio/ogre-conan/blob/master/conanfile.py
    default_options = {
        "shared": False,
        "fPIC": True,
        "ogre_set_double": False,
        "ogre_glsupport_use_egl": True,
    }
    exports_sources = "CMakeLists.txt", "patches/**"
    short_paths = True

    def requirements(self):
        self.requires("cppunit/1.15.1")
        self.requires("freeimage/3.18.0")
        self.requires("boost/1.75.0")
        self.requires("freetype/2.11.1")
        self.requires("openexr/2.5.7")
        self.requires("poco/1.11.2")
        self.requires("tbb/2020.3")
        self.requires("zlib/1.2.12")
        self.requires("zziplib/0.13.71")
        self.requires("openssl/1.1.1o", override=True)
        self.requires("xorg/system")
        if self.options.ogre_glsupport_use_egl:
            self.requires("egl/system")
        else:
            self.requires("libglvnd/1.4.0")

    def validate(self):
        """
         OGRE 1.x is very old and will not work with latest gcc, clang and msvc compielrs
         TODO: determine incompatible msvc compilers
        """
        if self.settings.compiler == "gcc" and tools.Version(self.settings.compiler.version) >= 9:
            raise ConanInvalidConfiguration("OGRE 1.x not supported with gcc 11")
        if self.settings.compiler == "clang" and tools.Version(self.settings.compiler.version) >= 9:
            raise ConanInvalidConfiguration("OGRE 1.x not supported with clang 13")

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    @functools.lru_cache(1)
    def _configure_cmake(self):
        cmake = CMake(self)
        cmake.definitions["OGRE_STATIC"] = not self.options.shared
        cmake.definitions["OGRE_CONFIG_DOUBLE"] = self.options.ogre_set_double
        cmake.definitions["OGRE_CONFIG_NODE_INHERIT_TRANSFORM"] = False
        cmake.definitions["OGRE_GLSUPPORT_USE_EGL"] = self.options.ogre_glsupport_use_egl
        if not tools.valid_min_cppstd(self, 11):
            cmake.definitions["CMAKE_CXX_STANDARD"] = 11 # for OpenEXR
        cmake.configure()
        return cmake


    def source(self):
        tools.get(**self.conan_data["sources"][self.version], destination=self._source_subfolder, strip_root=True)
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            tools.patch(**patch)

    def build(self):
        # the pkgs below are not available as conan recipes yet
        # TODO: delte line 200-208 once the conan recipes are available
        ogre_pkg_modules = ["AMDQBS", "Cg", "HLSL2GLSL", "GLSLOptimizer", "OpenGLES", "OpenGLES2", "OpenGLES3", "SDL2", "Softimage", "Wix"]
        ogre_pkg_module_path = os.path.join(self.build_folder, self._source_subfolder, "CMake", "Packages")
        for pkg_module in ogre_pkg_modules:
            pkg_path = os.path.join(ogre_pkg_module_path, f"Find{pkg_module}.cmake")
            if os.path.isfile(pkg_path):
                shutil.copy(pkg_path, self.build_folder)
            else:
                raise RuntimeError(f"The file Find{pkg_module}.cmake is not present in f{ogre_pkg_module_path}!")


        cmake = self._configure_cmake()
        cmake.build()

    def package(self):
        cmake = self._configure_cmake()
        cmake.install()
        tools.rmdir(os.path.join(self.package_folder, "lib", "pkgconfig"))
        tools.rmdir(os.path.join(self.package_folder, "lib", "share"))
        tools.rmdir(os.path.join(self.package_folder, "lib", "OGRE", "cmake"))
        self._create_cmake_module_variables(
            os.path.join(self.package_folder, self._module_file_rel_path),
            tools.Version(self.version)
        )
        
        
    @staticmethod
    def _create_cmake_module_variables(module_file, version):
        content = textwrap.dedent("""\
            set(OGRE_PREFIX_DIR ${{CMAKE_CURRENT_LIST_DIR}}/../..)
            set(OGRE{major}_VERSION_MAJOR {major})
            set(OGRE{major}_VERSION_MINOR {minor})
            set(OGRE{major}_VERSION_PATCH {patch})
            set(OGRE{major}_VERSION_STRING "{major}.{minor}.{patch}")

            set(OGRE_MEDIA_DIR "${{OGRE_PREFIX_DIR}}/share/OGRE/Media")
            set(OGRE_PLUGIN_DIR "${{OGRE_PREFIX_DIR}}/lib/OGRE")
            set(OGRE_CONFIG_DIR "${{OGRE_PREFIX_DIR}}/share/OGRE") 
        """.format(major=version.major, minor=version.minor, patch=version.patch))
        tools.save(module_file, content)


    @property
    def _components(self):
        pkg_name = "OGRE"
        include_prefix = os.path.join("include", "OGRE")
        components = {
            "OgreMain":  {"requires" : ["boost::boost", "cppunit::cppunit", "freeimage::freeimage", "openexr::openexr","freetype::freetype", "tbb::tbb", "xorg::xorg", "zlib::zlib", "zziplib::zziplib", "poco::poco"], 
                            "libs": ["OgreMain"], "include": [include_prefix]},
            "Bites":  {"requires" : ["OgreMain", "Overlay"], "libs": ["OgreBites"], "include": [include_prefix, f"{include_prefix}/Bites"]},
            "HLMS" :  {"requires" : ["OgreMain"], "libs": ["OgreHLMS"], "include": [include_prefix, f"{include_prefix}/HLMS"]},
            "MeshLodGenerator" :  {"requires" : ["OgreMain"], "libs": ["OgreMeshLoadGenerator"], "include": [include_prefix, f"{include_prefix}/MeshLoadGenerator"]},
            "Overlay" :  {"requires" : ["OgreMain"], "libs": ["OgreOverlay"], "include": [include_prefix, f"{include_prefix}/Overlay"]},
            "Paging" :  {"requires" : ["OgreMain"], "libs": ["OgrePaging"], "include": [include_prefix, f"{include_prefix}/Paging"]},
            "Property" :  {"requires" : ["OgreMain"], "libs": ["OgreProperty"], "include": [include_prefix, f"{include_prefix}/Property"]},
            "Python" :  {"requires" : ["OgreMain"], "libs": ["OgrePython"], "include": [include_prefix, f"{include_prefix}/Python"]},
            "RTShaderSystem" :  {"requires" : ["OgreMain"], "libs": ["OgreRTShaderSystem"], "include": [include_prefix, f"{include_prefix}/RTShaderSystem"]},
            "Terrain" :  {"requires" : ["OgreMain"], "libs": ["OgreTerrain"], "include": [include_prefix, f"{include_prefix}/Terrain"]},
            "Volume" :  {"requires" : ["OgreMain"], "libs": ["OgreVolume"], "include": [include_prefix, f"{include_prefix}/Volume"]}
        }

        return components

    def package_info(self):
        version_major = tools.Version(self.version).major
        self.cpp_info.set_property("cmake_file_name", "OGRE")
        self.cpp_info.names["cmake_find_package"] = "OGRE"
        self.cpp_info.names["cmake_find_package_multi"] = "OGRE"
        self.cpp_info.names["cmake_paths"] = "OGRE"

        for comp, values in self._components.items():
            self.cpp_info.components[comp].names["cmake_find_package"] = comp
            self.cpp_info.components[comp].names["cmake_find_package_multi"] = comp
            self.cpp_info.components[comp].names["cmake_paths"] = comp
            self.cpp_info.components[comp].libs = values.get("libs")
            self.cpp_info.components[comp].requires = values.get("requires")
            self.cpp_info.components[comp].set_property("cmake_target_name", f"OGRE::{comp}")
            self.cpp_info.components[comp].includedirs = values.get("include")
            self.cpp_info.components[comp].build_modules["cmake_find_package"] = [self._module_file_rel_path]
            self.cpp_info.components[comp].build_modules["cmake_find_package_multi"] = [self._module_file_rel_path]
            self.cpp_info.components[comp].build_modules["cmake_paths"] = [self._module_file_rel_path]
            self.cpp_info.components[comp].builddirs.append(self._module_file_rel_path)
            if self.settings.os == "Linux":
                self.cpp_info.components[comp].system_libs.append("pthread")

    @property
    def _module_file_rel_path(self):
        return os.path.join("lib", "cmake", f"conan-official-{self.name}-variables.cmake")
