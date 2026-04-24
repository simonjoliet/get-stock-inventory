# Changelog

All notable changes to this project will be documented in this file.

## v1.2 - 2026-04-24

- Moved login logic into the standalone `stock-logins.py` file
- Added support for setting inventory names on both Adobe and Shutterstock
- Added single-asset and CSV-based inventory update workflows
- Moved additional runtime settings into the config file

## v1.1 - 2026-04-24

- Renamed `credentials.ini` to `config.ini`
- Renamed `default_credentials.ini` to `default-config.ini`
- Renamed `stock_logins.py` to `stock-logins.py`
- Moved runtime configuration values out of Python code and into INI files
- Updated the README to document the new configuration layout and current usage
