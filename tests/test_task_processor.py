import re
from pathlib import Path
from unittest.mock import patch

import pytest
from _pytest.capture import CaptureFixture

from cmstp.core.logger import Logger
from cmstp.core.task_processor import TaskProcessor
from cmstp.utils.common import (
    PACKAGE_CONFIG_PATH,
    PACKAGE_TESTS_PATH,
    generate_random_path,
)


def get_empty_yaml_file() -> str:
    """Create and return a path to an empty temporary YAML file"""
    return str(generate_random_path(suffix=".yaml", create=True))


def get_missing_yaml_file() -> str:
    """Generate and return a path to a non-existent YAML file"""
    return str(generate_random_path(suffix=".yaml", create=False))


#################################################################################################################
################################################ Package Configs ################################################
#################################################################################################################


def test_package_configs():
    """See if the package default and custom configs are valid"""
    dummy_logger = Logger(parser=None)
    dummy_path = Path()
    TaskProcessor(
        logger=dummy_logger,
        config_file=PACKAGE_CONFIG_PATH / "enabled.yaml",
        config_dir=dummy_path,
    )


#################################################################################################################
############################################# Default Config Checks #############################################
#################################################################################################################


class TestDefaultConfig:
    """Group default config tests in a class for better organization"""

    def setup_method(self):
        """Setup that runs before each test method"""
        self.config_dir: Path = (
            PACKAGE_TESTS_PATH / "config" / "test_task_processor" / "default"
        )
        self.fields_message = (
            "Some tasks have extra or missing fields, or use incorrect types"
        )

    def _check_config(
        self, capsys: CaptureFixture, config_file: str, expected_err: str
    ) -> None:
        with patch.object(
            TaskProcessor, "default_config", self.config_dir / config_file
        ):
            with pytest.raises(SystemExit) as exc_info:
                TaskProcessor(
                    logger=Logger(parser=None),  # Dummy logger
                    config_file=self.config_dir / ".." / "valid_custom.yaml",
                    config_dir=Path(),  # Dummy path
                )

        captured_err = capsys.readouterr().err
        captured_err_clean = re.sub(r"\s+", " ", captured_err).strip()

        assert exc_info.value.code == 1
        assert expected_err in captured_err_clean

    def test_missing_config(self, capsys: CaptureFixture):
        """See if a missing default config is handled correctly"""
        self._check_config(
            capsys, get_missing_yaml_file(), "File does not exist"
        )

    def test_empty_config(self, capsys: CaptureFixture):
        """See if an empty default config is handled correctly"""
        self._check_config(capsys, get_empty_yaml_file(), "File is empty")

    def test_duplicate_task(self, capsys: CaptureFixture):
        """See if a default config with duplicate tasks is handled correctly"""
        self._check_config(
            capsys,
            "test_duplicate_task.yaml",
            "Duplicate (script, function) pair",
        )

    ### Properties ####

    def test_missing_task_property(self, capsys: CaptureFixture):
        self._check_config(
            capsys, "test_missing_task_property.yaml", self.fields_message
        )

    def test_extra_task_property(self, capsys: CaptureFixture):
        self._check_config(
            capsys, "test_extra_task_property.yaml", self.fields_message
        )

    def test_wrong_task_property_type(self, capsys: CaptureFixture):
        self._check_config(
            capsys, "test_wrong_task_property_type.yaml", self.fields_message
        )

    def test_missing_script(self, capsys: CaptureFixture):
        self._check_config(
            capsys, "test_missing_script.yaml", "script does not exist"
        )

    def test_script_with_nonexistent_package(self, capsys: CaptureFixture):
        self._check_config(
            capsys,
            "test_script_with_nonexistent_package.yaml",
            "Script is either null or uses a package that can't be found",
        )

    def test_nonexistent_function(self, capsys: CaptureFixture):
        self._check_config(
            capsys,
            "test_nonexistent_function.yaml",
            "function not found in script",
        )

    def test_wrong_function_definition(self, capsys: CaptureFixture):
        self._check_config(
            capsys,
            "test_wrong_function_definition.yaml",
            "must ONLY capture '*args' as an argument",
        )

    def test_missing_dependency(self, capsys: CaptureFixture):
        self._check_config(
            capsys,
            "test_missing_dependency.yaml",
            "dependency task does not exist",
        )

    def test_cyclic_dependency(self, capsys: CaptureFixture):
        self._check_config(
            capsys,
            "test_cyclic_dependency.yaml",
            "Dependency graph has cycles between",
        )

    def test_wrong_args_type(self, capsys: CaptureFixture):
        self._check_config(
            capsys, "test_wrong_args_type.yaml", self.fields_message
        )

    ### Args ####

    def test_missing_task_arg(self, capsys: CaptureFixture):
        self._check_config(
            capsys, "test_missing_task_arg.yaml", self.fields_message
        )

    def test_extra_task_arg(self, capsys: CaptureFixture):
        self._check_config(
            capsys, "test_extra_task_arg.yaml", self.fields_message
        )

    def test_wrong_task_arg_type(self, capsys: CaptureFixture):
        self._check_config(
            capsys, "test_wrong_task_arg_type.yaml", self.fields_message
        )

    def test_unallowed_arg(self, capsys: CaptureFixture):
        self._check_config(
            capsys, "test_unallowed_arg.yaml", "not in allowed args"
        )


#################################################################################################################
############################################# Custom Config Checks ##############################################
#################################################################################################################


class TestCustomConfig:
    """Group custom config tests in a class for better organization"""

    def setup_method(self):
        """Setup that runs before each test method"""
        self.config_dir: Path = (
            PACKAGE_TESTS_PATH / "config" / "test_task_processor" / "custom"
        )
        self.fields_message = "Some tasks that have extra fields or are trying to override default fields are disabled"

    def _check_config_error(
        self, capsys: CaptureFixture, config_file: str, expected_err: str
    ) -> None:
        with patch.object(
            TaskProcessor,
            "default_config",
            self.config_dir / ".." / "valid_default.yaml",
        ):
            with pytest.raises(SystemExit) as exc_info:
                # Use dummy config paths, as they are not used in the TaskProcessor when checking the default config
                TaskProcessor(
                    logger=Logger(parser=None),  # Dummy logger
                    config_file=self.config_dir / config_file,
                    config_dir=Path(),  # Dummy path
                )

        captured_err = capsys.readouterr().err
        captured_err_clean = re.sub(r"\s+", " ", captured_err).strip()

        assert exc_info.value.code == 1
        assert expected_err in captured_err_clean

    def _check_config_warning(
        self, capsys: CaptureFixture, config_file: str, expected_warn: str
    ) -> None:
        with patch.object(
            TaskProcessor,
            "default_config",
            self.config_dir / ".." / "valid_default.yaml",
        ):
            task_processor = TaskProcessor(
                logger=Logger(parser=None),  # Dummy logger
                config_file=self.config_dir / config_file,
                config_dir=Path(),  # Dummy path
            )

        captured_warn = capsys.readouterr().out
        captured_warn_clean = re.sub(r"\s+", " ", captured_warn).strip()

        assert expected_warn in captured_warn_clean

    def test_missing_config(self, capsys: CaptureFixture):
        """See if a missing default config is handled correctly"""
        self._check_config_error(
            capsys, get_missing_yaml_file(), "File does not exist"
        )

    def test_empty_config(self, capsys: CaptureFixture):
        """See if an empty default config is handled correctly"""
        self._check_config_error(
            capsys, get_empty_yaml_file(), "File is empty"
        )

    def test_wrong_task_type(self, capsys: CaptureFixture):
        """See if a wrong file structure (not a dict) is handled correctly"""
        self._check_config_error(
            capsys, "test_wrong_task_type.yaml", "File does not define a dict"
        )

    def test_eventual_empty_config(self, capsys: CaptureFixture):
        """See if a custom config that results in an empty config (after tasks are disabled) is handled correctly"""
        self._check_config_error(
            capsys, "test_eventual_empty_config.yaml", "No valid tasks defined"
        )

    def test_nonexistent_task(self, capsys: CaptureFixture):
        """See if a task that does not exist in the default config is handled correctly"""
        self._check_config_warning(
            capsys,
            "test_nonexistent_task.yaml",
            "disabled because it is not defined in the default config",
        )

    def test_disabled_dependency(self, capsys: CaptureFixture):
        self._check_config_warning(
            capsys,
            "test_disabled_dependency.yaml",
            "disabled because it depends on disabled tasks",
        )

    ### Properties ####

    def test_extra_task_property(self, capsys: CaptureFixture):
        self._check_config_warning(
            capsys, "test_extra_task_property.yaml", self.fields_message
        )

    def test_wrong_task_property_type(self, capsys: CaptureFixture):
        self._check_config_warning(
            capsys, "test_wrong_task_property_type.yaml", self.fields_message
        )

    def test_wrong_args_type(self, capsys: CaptureFixture):
        self._check_config_warning(
            capsys,
            "test_wrong_args_type.yaml",
            "because 'args' field is not a dict",
        )

    ### Args ####

    def test_extra_task_arg(self, capsys: CaptureFixture):
        self._check_config_warning(
            capsys, "test_extra_task_arg.yaml", self.fields_message
        )

    def test_wrong_task_arg_type(self, capsys: CaptureFixture):
        self._check_config_warning(
            capsys, "test_wrong_task_arg_type.yaml", self.fields_message
        )

    def test_unallowed_arg(self, capsys: CaptureFixture):
        self._check_config_warning(
            capsys,
            "test_unallowed_arg.yaml",
            "disabled because it uses unallowed args",
        )
