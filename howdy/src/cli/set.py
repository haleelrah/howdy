# Set a config value
from __future__ import annotations

import builtins
import configparser

# Import required modules
import sys

import paths_factory
from i18n import _

# Get the absolute filepath
config_path = paths_factory.config_file_path()

# Read config from disk
config = configparser.ConfigParser()
config.read(config_path)

# Check if enough arguments have been passed
if len(builtins.howdy_args.arguments) < 2:
	print(_("Please add a setting you would like to change and the value to set it to"))
	print(_("For example:"))
	print("\n\thowdy set certainty 3\n")
	sys.exit(1)

# Get the name and value from the cli
set_name = builtins.howdy_args.arguments[0]
set_value = builtins.howdy_args.arguments[1]

# Search for the option across all sections
found_section = None
for section in config.sections():
	if config.has_option(section, set_name):
		found_section = section
		break

# If we don't have the option it is not in the config file
if not found_section:
	print(_('Could not find a "{}" config option to set').format(set_name))
	sys.exit(1)

# Update the config value and write it back
config.set(found_section, set_name, set_value)
with open(config_path, "w") as f:
	config.write(f)

print(_("Config option updated"))
