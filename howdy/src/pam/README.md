# Howdy PAM module

## Requirements

This module depends on `INIReader` and `libevdev`.
They can be installed with these packages:

```
Arch Linux - libinih libevdev
Debian     - libinih-dev libevdev-dev
Fedora     - inih-devel libevdev-devel
OpenSUSE   - inih libevdev-devel
```

If your distribution doesn't provide `INIReader`,
it will be automatically pulled from git at the subproject's pinned version.

## Build

``` sh
meson setup build
ninja -C build # or meson compile -C build
```

## Install

``` sh
meson install -C build
```

Add the following line to your PAM configuration (/etc/pam.d/your-service):

``` pam
auth  sufficient  pam_howdy.so
```

## SELinux Compatibility

On SELinux-enforcing systems (Fedora, RHEL, CentOS), the PAM module may be
denied access to resources it needs. Common issues and fixes:

**Symptoms:** Authentication silently falls back to password. `journalctl`
shows `pam_howdy` logging "Compare script not accessible" or the compare
process fails with permission errors.

**Check audit log:**

``` sh
sudo ausearch -m avc -ts recent | grep howdy
```

**Common denials and solutions:**

1. **Reading config/model files:** The PAM module reads
   `/etc/howdy/config.ini` and user model files. The compare script needs
   `read` access to `/usr/lib/howdy/` (or wherever installed).

2. **Executing Python:** `posix_spawnp` launches Python to run `compare.py`.
   SELinux may block `pam_t` from executing `bin_t` Python binaries.

3. **Camera device access:** The compare script opens `/dev/video*` devices.
   A policy needs to allow this for the PAM execution context.

4. **uinput access:** The "input" workaround writes to `/dev/uinput`. This
   requires `write` permission on `uinput_device_t`.

**Quick permissive workaround** (for testing only):

``` sh
sudo semanage permissive -a pam_t
```

**Proper fix:** Generate a local policy module from collected denials:

``` sh
sudo ausearch -m avc -ts recent | audit2allow -M howdy_pam
sudo semodule -i howdy_pam.pp
```

**Important:** The PAM module returns `PAM_AUTHINFO_UNAVAIL` (not
`PAM_AUTH_ERR`) when it cannot access its own files, so authentication
will fall through to the next PAM module (typically password) rather
than blocking login.
