def read_conf(
    inifile_path: Union[str, pathlib.Path],
    section: str,
    prop: str,
    *,
    keep_orig_val=False,
) -> str:
    """
    Read value from a property configured in .ini files or from the env system variable.

    - To use local version of .ini file without it being pushed into the remote repository use "_" prefix before .ini file
    - To use property value from env sys variable: Setup env variable that have pattern like this {section name}_{prop name}. For e.g. DEFAULT_slackPath=C:/...

    - Value gained from env sys env variable would be prioritized
    """
    conf = configparser.ConfigParser()

    # Check if search ini by absolute path
    ini = pathlib.Path(inifile_path)
    if not ini.is_absolute():
        ini = PROJECT_ROOT.joinpath("resources", "config", inifile_path)

    conf.read(ini)

    # Check if local ini exists
    local_conf = None
    local_ini = ini.with_name("_" + ini.name)
    if local_ini.exists():
        local_conf = configparser.ConfigParser()
        local_conf.read(local_ini)

    def val(conf):
        nonlocal section, prop, keep_orig_val

        if not conf:
            return None
        try:
            sect = conf[section]  # No such section
        except KeyError:
            return None

        try:
            val = sect[prop]  # No such property
        except KeyError:
            return None

        if not keep_orig_val:
            # Check if there is an env that much a required config property
            val = os.getenv(f"{sect.name}_{prop}") or val
        return val

    # Check if need to override properties with local ini
    local_v = val(local_conf)
    # If not found local property - use from the main ini
    v = val(conf) if local_v is None else local_v
    assert (
        v is not None
    ), f"No property={prop} found in the section={section} from the ini config file={ini}"

    # Common pattern to insert a PC user
    v = v.replace("<user>", os.getlogin())
    return v
