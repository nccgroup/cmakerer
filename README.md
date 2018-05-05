# CMakerer

This script generates `CMakeLists.txt` from arbitrary C/C++ codebases. It is
not intended to produce "buildable" cmake configurations, but instead enable
CLion to load and index the code.

# Installation

```bash
pip3 install --user cmakerer
```

```bash
python3 setup.py sdist bdist_wheel
pip3 install --user dist/cmakerer-*.whl
```

# Usage

```bash
cmakerer -o ~/path/to/cpp/code -x src/windows -! tests -z ~/path/to/cpp/code
```

# Features

* Detects both standard and system include paths.
* Handles "multi-encoding" C/C++ files
* Exclude directory paths with `-x`
* Exclude (sub)directory segments with `-!`
* Exclude cmake directories with `-z`
