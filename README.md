### How an application is manipulated

- Pywinauto - open apps

- Airtest - find a template on the desktop

- PyAutoGUI - mouse/keyboard action onto found coordinates<br>

### Override timeouts and tools specific configurations
- Use `pyproject.toml` file in the project root for project configuration

- Use `\_pyproject.toml` for local project configuration

- By default configuration is:

```
[project-configuration.retry-ms]
  retry = 500
[project-configuration.timeout-ms]
  instant = 500
  short = 1500
  mid = 30000
  long = 60000
[pywinauto-configuration]
  after_sendkeys_key_wait = 0.15
  after_clickinput_wait = 0.5
  window_find_timeout = 30
  window_find_retry = 0.5
[airtest-configuration]
  find_timeout = 30
  threshold = 0.8
  cvstrategy = ["tpl"]
```

If some property will not be overrided in the project or local project files - the property from the lib configuration file (default) will be selected.
