import sys
import os
import configparser
from pathlib import Path
from typing import MutableMapping, Optional as Opt, Union

if sys.version_info < (3, 11):
    import toml as tomllib
else:
    import tomllib

_PROJECT_ROOT = Path(os.getcwd())
_TOML_NAME = "pyproject.toml"
_CONFIG_TOML_NAME = "config.toml"


def _getval(conf: Opt[MutableMapping], section: str, prop: str):
    if not conf:
        return None
    try:
        if "." in section:
            sect_names = section.split(".")
            sect_data = conf[sect_names[0]]  # Get base section data
            for inner_sect_name in sect_names[1:]:
                sect_data = sect_data[inner_sect_name]
        else:
            sect_data = conf[section]  # conf.get would not work here
    except KeyError:
        return None
    return sect_data.get(prop)


def _get_toml_val(conf, section, prop):
    if not conf.exists():
        return None
    with open(conf, "r") as f:
        local_conf = tomllib.load(f)
    return _getval(local_conf, section, prop)


def read_toml(section: str, prop: str):
    """
    Grab the value of the property from pyproject.toml configuration file checking the scope of the file:
    1 priority - local version _pyproject.toml in the project root
    2 priority - pyproject.toml in the project root
    3 priority - pyproject.toml in the deskapptest lib root
    """
    lib_toml = Path(__file__).parent.parent.joinpath(_CONFIG_TOML_NAME).resolve()
    assert lib_toml, "testapptest lib does not include pyproject.toml"
    project_toml = _PROJECT_ROOT.joinpath(_TOML_NAME)
    local_project_toml = project_toml.with_name("_" + project_toml.name)
    lib_v = _get_toml_val(lib_toml, section, prop)
    v = _get_toml_val(project_toml, section, prop)
    local_v = _get_toml_val(local_project_toml, section, prop)

    if local_v:
        return local_v
    elif v:
        return v
    else:
        assert lib_v, "testapptest lib configs are not set"
        return lib_v


def read_ini(
    inifile_path: Union[str, Path],
    section: str,
    prop: str,
) -> str:
    """
    Read value from a property configured in .ini files or from the env system variable.

    - To use local version of .ini file without it being pushed into the remote repository use "_" prefix before .ini file
    - To use property value from env sys variable: Setup env variable that have pattern like this {section name}_{prop name}. For e.g. DEFAULT_slackPath=C:/...

    - Value gained from env sys env variable would be prioritized
    """
    conf = configparser.ConfigParser()

    # Check if search ini by absolute path
    ini = Path(inifile_path)
    if not ini.is_absolute():
        ini = _PROJECT_ROOT.joinpath("resources", "config", inifile_path)

    conf.read(ini)

    # Check if local ini exists
    local_conf = None
    local_ini = ini.with_name("_" + ini.name)
    if local_ini.exists():
        local_conf = configparser.ConfigParser()
        local_conf.read(local_ini)

    # Check if need to override properties with local ini
    local_v = _getval(local_conf, section, prop)
    # If not found local property - use from the main ini
    val = _getval(conf, section, prop) if local_v is None else local_v
    assert (
        val is not None
    ), f"No property={prop} found in the section={section} from the ini config file={ini}"

    # Common pattern to insert a PC user
    val = val.replace("<user>", os.getlogin())
    return val
