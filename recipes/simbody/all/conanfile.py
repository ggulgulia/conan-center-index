from conan import ConanFile, tools
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.errors import ConanInvalidConfiguration
from conan.tools.scm import Version
import os
import textwrap


class SimbodyConan(ConanFile):
    name = "simbody"
    description = "High-performance, open-source toolkit for science- and engineering-quality simulation"
    license = "Apache-2.0"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/simbody/simbody"
    topics = ("high-performance", "science", "simulation")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "CMakeLists.txt", "patches/**"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    _cmake = None

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    @property
    def _module_file_rel_path(self):
        return os.path.join("lib", "cmake", f"conan-official-{self.name}-variables.cmake")

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    def source(self):
        tools.files.get(self, **self.conan_data["sources"][self.version],  
                    destination=self._source_subfolder, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        tools.files.save(self, os.path.join(self.package_folder, "licenses", "LICENSE"), self._extract_license())
        self.copy("LICENSE", dst="licenses", src=self._source_subfolder)
        cmake = self._configure_cmake()
        cmake.install()
        tools.files.rmdir(os.path.join(self.package_folder, "lib", "pkgconfig"))
        

    @staticmethod
    def _create_cmake_module_variables(module_file, version):
        content = textwrap.dedent("""\
            set(simbody_VERSION_MAJOR {major})
            set(simbody_VERSION_MINOR {minor})
            set(simbody_VERSION_PATCH {patch})
            set(simbody_VERSION_STRING "{major}.{minor}.{patch}")
        """.format(major=version.major, minor=version.minor, patch=version.patch))
        tools.save(module_file, content)

    def package_info(self):
        version_major = tools.Version(self.version).major
        simbody_cmake_component = f"simbody{version_major}"
        base_module_path = os.path.join(self.package_folder, "lib", "cmake", simbody_cmake_component)
        
        self.cpp_info.names["cmake_find_package"] = simbody_cmake_component
        self.cpp_info.names["cmake_find_package_multi"] = simbody_cmake_component

        self.cpp_info.components[simbody_cmake_component].names["cmake_find_package"] = simbody_cmake_component
        self.cpp_info.components[simbody_cmake_component].names["cmake_find_package_multi"] = simbody_cmake_component
        self.cpp_info.components[simbody_cmake_component].builddirs.append(os.path.join(base_module_path, f"cmake{version_major}"))
