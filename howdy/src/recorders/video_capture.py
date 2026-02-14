# Top level class for a video capture providing simplified API's for common
# functions
from __future__ import annotations

# Import required modules
import configparser
import os
import sys
from typing import Any

import cv2

from i18n import _

# Class to provide boilerplate code to build a video recorder with the
# correct settings from the config file.
#
# The internal recorder can be accessed with 'video_capture.internal'


class VideoCapture:
	def __init__(self, config: configparser.ConfigParser | str) -> None:
		"""
		Creates a new VideoCapture instance depending on the settings in the
		provided config file.

		Config can either be a string to the path, or a pre-setup configparser.
		"""

		# Parse config from string if needed
		if isinstance(config, str):
			self.config = configparser.ConfigParser()
			self.config.read(config)
		else:
			self.config = config

		# Check device path
		device_path = self.config.get("video", "device_path")
		if not os.path.exists(device_path):
			if self.config.getboolean("video", "warn_no_device", fallback=True):
				print(_("Howdy could not find a camera device at: {}").format(device_path))
				# Lazy import to avoid overhead on the success path
				from recorders.device_discovery import detect_camera_environment, discover_devices
				env = detect_camera_environment()
				available = discover_devices()
				if available:
					print(_("Available camera devices on this system:"))
					for dev in available:
						print("  {}  ({})".format(dev["path"], dev["name"]))
				else:
					print(_("No camera devices were detected on this system."))
				if env["pipewire_running"]:
					print(_("Note: PipeWire is running. Try setting device_backend = gstreamer in the config."))
				print(_("Please edit the 'device_path' config value by running:"))
				print("\n\tsudo howdy config\n")
			sys.exit(14)

		# Create reader
		# The internal video recorder
		self.internal = None
		# The frame width
		self.fw = None
		# The frame height
		self.fh = None
		self._create_reader()

		# Request a frame to wake the camera up
		self.internal.grab()

	def __del__(self) -> None:
		"""
		Frees resources when destroyed
		"""
		try:
			self.internal.release()
		except AttributeError:
			pass

	def release(self) -> None:
		"""
		Release cameras
		"""
		self.internal.release()

	def read_frame(self) -> tuple[Any, Any]:
		"""
		Reads a frame, returns the frame and an attempted grayscale conversion of
		the frame in a tuple:

		(frame, grayscale_frame)

		If the grayscale conversion fails, both items in the tuple are identical.
		"""

		# Grab a single frame of video
		# Don't remove ret, it doesn't work without it
		ret, frame = self.internal.read()
		if not ret:
			device_path = self.config.get("video", "device_path")
			backend_name = self.config.get("video", "device_backend", fallback="v4l2")
			print(_("Failed to read frame from camera at: {} (backend: {})").format(
				device_path, backend_name))
			print(_("Possible causes: camera in use, driver issue, or wrong device_path."))
			print(_("Run 'sudo howdy test' to diagnose camera issues."))
			sys.exit(14)

		try:
			# Convert from color to grayscale
			# First processing of frame, so frame errors show up here
			gsframe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		except RuntimeError:
			gsframe = frame
		except cv2.error:
			print("\nAn error occurred in OpenCV\n")
			raise
		return frame, gsframe

	def _create_reader(self) -> None:
		"""
		Sets up the video reader instance
		"""
		recording_plugin = self.config.get("video", "recording_plugin", fallback="opencv")

		if recording_plugin == "ffmpeg":
			# Set the capture source for ffmpeg
			from recorders.ffmpeg_reader import ffmpeg_reader
			self.internal = ffmpeg_reader(
				self.config.get("video", "device_path"),
				self.config.get("video", "device_format", fallback="v4l2")
			)

		elif recording_plugin == "pyv4l2":
			# Set the capture source for pyv4l2
			from recorders.pyv4l2_reader import pyv4l2_reader
			self.internal = pyv4l2_reader(
				self.config.get("video", "device_path"),
				self.config.get("video", "device_format", fallback="v4l2")
			)

		else:
			# Start video capture on the IR camera through OpenCV
			# Read the configured OpenCV backend
			backend_name = self.config.get("video", "device_backend", fallback="v4l2")
			backend_map = {
				"v4l2": cv2.CAP_V4L2,
				"gstreamer": cv2.CAP_GSTREAMER,
				"any": cv2.CAP_ANY,
			}
			cap_backend = backend_map.get(backend_name, cv2.CAP_V4L2)

			self.internal = cv2.VideoCapture(
				self.config.get("video", "device_path"),
				cap_backend
			)

			# If V4L2 failed to open, try GStreamer as fallback
			if not self.internal.isOpened() and cap_backend == cv2.CAP_V4L2:
				if hasattr(cv2, "CAP_GSTREAMER"):
					self.internal = cv2.VideoCapture(
						self.config.get("video", "device_path"),
						cv2.CAP_GSTREAMER
					)

			# Set the capture frame rate
			# Without this the first detected (and possibly lower) frame rate is used, -1 seems to select the highest
			# Use 0 as a fallback to avoid breaking an existing setup, new installs should default to -1
			self.fps = self.config.getint("video", "device_fps", fallback=0)
			if self.fps != 0:
				self.internal.set(cv2.CAP_PROP_FPS, self.fps)

		# Force MJPEG decoding if true
		if self.config.getboolean("video", "force_mjpeg", fallback=False):
			self.internal.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

		# Set the frame width and height if requested
		self.fw = self.config.getint("video", "frame_width", fallback=-1)
		self.fh = self.config.getint("video", "frame_height", fallback=-1)
		if self.fw != -1:
			self.internal.set(cv2.CAP_PROP_FRAME_WIDTH, self.fw)
		if self.fh != -1:
			self.internal.set(cv2.CAP_PROP_FRAME_HEIGHT, self.fh)
