import os
import tempfile

from ruamel.yaml import YAML

from cmstp.utils.tasks import HARDWARE_SPECIFIC_TASKS

# from cmstp.main import main


def test_hardware_specific():
    """Test enabling only the hardware-specific tasks in a temporary YAML file"""

    # Enable all hardware-specific tasks in a temporary YAML file
    data = {task: {"enabled": True} for task in HARDWARE_SPECIFIC_TASKS}

    # Create the temporary YAML file
    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.default_flow_style = False
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as tmpfile:
        yaml.dump(data, tmpfile)
        temp_yaml = tmpfile.name

    # # Run main() with this temporary YAML file
    # main(["--config-file", temp_yaml])

    # Delete the temporary file
    os.remove(temp_yaml)
