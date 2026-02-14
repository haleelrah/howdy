# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

Howdy provides Windows Hello™ style facial authentication for Linux using PAM (Pluggable Authentication Modules). It uses IR cameras and dlib-based face recognition to authenticate users at login, lock screen, sudo, su, etc.

## Build Commands

```bash
# Configure and build
meson setup build
meson compile -C build

# Install to system (requires sudo)
sudo meson install -C build

# Run clang-tidy linting
ninja clang-tidy -C build
```

### Build Dependencies

- Python 3.6+, pip, setuptools, wheel
- meson (>= 0.64), ninja
- libpam, libinih (INIReader), libevdev
- OpenCV (with Python bindings)
- dlib (for face recognition models)

## Architecture

### Two Main Components

**howdy/** - Core module containing:
- `src/pam/` - C++ PAM module (`pam_howdy.so`) that integrates with Linux authentication
- `src/compare.py` - Python face recognition engine using dlib
- `src/cli.py` - CLI entry point for the `howdy` command
- `src/cli/` - Subcommands: add, clear, config, disable, list, remove, set, snap, test
- `src/recorders/` - Video capture backends (opencv, ffmpeg, pyv4l2)
- `src/rubberstamps/` - Optional post-recognition verification stamps (nod detection, hotkey)

**howdy-gtk/** - GTK user interface for:
- Authentication feedback overlay during login
- Configuration management
- Onboarding flow

### Authentication Flow

1. PAM module (`main.cc`) receives authentication request
2. Checks if Howdy is enabled (SSH detection, lid state, user has face model)
3. Spawns Python subprocess running `compare.py` with username
4. `compare.py` loads user's face encodings from `{models_dir}/{user}.dat`
5. Captures frames from IR camera via `VideoCapture` class
6. Uses dlib to detect faces and compute face descriptors
7. Compares against stored encodings using numpy vector distance
8. Returns exit code to PAM module (0 = success, others = various failures)
9. If rubberstamps enabled, runs additional verification

### Exit Codes (from compare.py)

- 0: Success
- 10: No face model
- 11: Timeout reached
- 12: Abort/missing username
- 13: Image too dark
- 14: Invalid camera device
- 15: Rubberstamp failed

### Configuration

Main config: `/etc/howdy/config.ini` (default location)

Key sections:
- `[core]` - Enable/disable, CNN mode, SSH detection, workaround mode
- `[video]` - Camera settings (device_path, certainty, timeout, dark_threshold)
- `[rubberstamps]` - Additional verification rules
- `[debug]` - Diagnostic output options

### Path Configuration (meson.options)

- `pam_dir` - PAM module install location
- `config_dir` - Config directory (default: `/etc/howdy`)
- `dlib_data_dir` - dlib model files location
- `user_models_dir` - User face model storage
- `python_path` - Python interpreter path

## Code Style

- C++ code follows Google style with clang-tidy checks (see `.clang-tidy`)
- Python code uses tabs for indentation
- Internationalization via gettext (`i18n.py` provides `_()` function)

## Testing Locally

After building, test face recognition:
```bash
sudo howdy test      # Test camera and recognition
sudo howdy add       # Add your face model
sudo howdy list      # List stored face models
sudo howdy config    # Edit configuration
```
