#!/bin/bash

python tests/test_demo_ocfl_root_script.py > docs/demo_ocfl_root_script.md
python tests/test_demo_ocfl_object_script.py > docs/demo_ocfl_object_script.md
python tests/test_demo_ocfl_validate_script.py > docs/demo_ocfl_validate_script.md
python tests/test_demo_using_bagit_bags.py > docs/demo_using_bagit_bags.md
python tests/test_demo_ocfl_sidecar_script.py > docs/demo_ocfl_sidecar_script.md
python tests/test_demo_build_spec_v1_0_examples.py > docs/demo_build_v1_0_spec_examples.md
python tests/test_demo_build_spec_v1_1_examples.py > docs/demo_build_v1_1_spec_examples.md
