# Device discovery and camera environment detection utilities
from __future__ import annotations

import glob
import os
import re
import subprocess

import cv2


def detect_camera_environment() -> dict:
	"""Detect the available camera environment on the system.

	Returns a dict with keys:
		v4l2_available: bool - whether V4L2 device directories exist
		pipewire_running: bool - whether PipeWire is currently running
		gstreamer_available: bool - whether OpenCV has GStreamer backend
		devices_by_path: list - devices listed in /dev/v4l/by-path
		devices_by_id: list - devices listed in /dev/v4l/by-id
	"""
	devices_by_path: list[str] = []
	devices_by_id: list[str] = []

	try:
		devices_by_path = os.listdir("/dev/v4l/by-path")
	except OSError:
		pass

	try:
		devices_by_id = os.listdir("/dev/v4l/by-id")
	except OSError:
		pass

	pipewire_running = False
	try:
		result = subprocess.run(
			["pgrep", "-x", "pipewire"],
			stdout=subprocess.DEVNULL,
			stderr=subprocess.DEVNULL,
			timeout=5,
		)
		pipewire_running = result.returncode == 0
	except (FileNotFoundError, subprocess.TimeoutExpired):
		pass

	gstreamer_available = hasattr(cv2, "CAP_GSTREAMER")

	return {
		"v4l2_available": len(devices_by_path) > 0 or len(devices_by_id) > 0,
		"pipewire_running": pipewire_running,
		"gstreamer_available": gstreamer_available,
		"devices_by_path": devices_by_path,
		"devices_by_id": devices_by_id,
	}


def discover_devices() -> list[dict]:
	"""Discover available camera devices on the system.

	Returns a list of dicts with keys: path, name, source.
	Uses three methods in priority order:
	1. /dev/v4l/by-path/
	2. /dev/v4l/by-id/ (deduplicating by resolved real path)
	3. /dev/video* glob fallback (deduplicating by real path)
	"""
	devices: list[dict] = []
	seen_paths: set[str] = set()

	_scan_v4l_dir("/dev/v4l/by-path", devices, seen_paths, "by-path")
	_scan_v4l_dir("/dev/v4l/by-id", devices, seen_paths, "by-id")

	# Fallback: glob /dev/video*
	for dev_path in sorted(glob.glob("/dev/video*")):
		real_path = os.path.realpath(dev_path)
		if real_path in seen_paths:
			continue
		seen_paths.add(real_path)
		devices.append({
			"path": dev_path,
			"name": _get_device_name(dev_path),
			"source": "video-glob",
		})

	return devices


def test_device_open(device_path: str, backend: int | None = None) -> dict:
	"""Test whether a device can be opened and read a frame.

	Returns a dict with keys: success, is_gray, error.
	"""
	if backend is None:
		backend = cv2.CAP_V4L2

	try:
		cap = cv2.VideoCapture(device_path, backend)
		if not cap.isOpened():
			return {"success": False, "is_gray": False, "error": "Camera could not be opened"}

		ret, frame = cap.read()
		cap.release()

		if not ret or frame is None:
			return {"success": False, "is_gray": False, "error": "Failed to read a frame"}

		return {"success": True, "is_gray": _is_gray_frame(frame), "error": None}
	except Exception as e:
		return {"success": False, "is_gray": False, "error": str(e)}


def _get_device_name(path: str) -> str:
	"""Get a human-readable name for a device using udevadm.

	Falls back to os.path.basename(path) if udevadm is unavailable or fails.
	"""
	try:
		udevadm = subprocess.check_output(
			["udevadm", "info", "-r", "--query=all", "-n", path],
			timeout=5,
		).decode("utf-8")
		for line in udevadm.split("\n"):
			re_name = re.search(r'product.*=(.*)$', line, re.IGNORECASE)
			if re_name:
				return re_name.group(1)
	except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
		pass
	return os.path.basename(path)


def _scan_v4l_dir(dir_path: str, devices: list[dict], seen_paths: set[str], source: str) -> None:
	"""Scan a /dev/v4l/ subdirectory and append discovered devices."""
	try:
		entries = os.listdir(dir_path)
	except OSError:
		return

	for entry in sorted(entries):
		full_path = os.path.join(dir_path, entry)
		real_path = os.path.realpath(full_path)
		if real_path in seen_paths:
			continue
		seen_paths.add(real_path)
		devices.append({
			"path": real_path,
			"name": _get_device_name(real_path),
			"source": source,
		})


def _is_gray_frame(frame) -> bool:
	"""Check if a frame is grayscale by sampling pixels.

	Checks every 10th row and column for performance on large frames.
	"""
	if len(frame.shape) < 3:
		return True

	for row_idx in range(0, frame.shape[0], 10):
		for col_idx in range(0, frame.shape[1], 10):
			pixel = frame[row_idx, col_idx]
			if not (pixel[0] == pixel[1] == pixel[2]):
				return False
	return True
