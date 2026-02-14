from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

import numpy.typing as npt


class FaceRectangle:
	"""Normalized face bounding box. Method names match dlib.rectangle."""
	def __init__(self, top: int, left: int, right: int, bottom: int):
		self._top = top
		self._left = left
		self._right = right
		self._bottom = bottom

	def top(self) -> int: return self._top
	def left(self) -> int: return self._left
	def right(self) -> int: return self._right
	def bottom(self) -> int: return self._bottom


class LandmarkPoint:
	"""A single landmark point with x/y attributes."""
	def __init__(self, x: int, y: int):
		self.x = x
		self.y = y


class LandmarkSet:
	"""Landmark results. Preserves .part(index).x/y interface used by nod.py."""
	def __init__(self, points: list[LandmarkPoint], raw=None):
		self._points = points
		self._raw = raw  # backend-specific opaque object (e.g. dlib full_object_detection)

	def part(self, index: int) -> LandmarkPoint:
		return self._points[index]


class RecognitionBackend(ABC):
	@abstractmethod
	def detect_faces(self, frame: npt.NDArray, upsample: int = 1) -> List[FaceRectangle]: ...

	@abstractmethod
	def get_landmarks(self, frame: npt.NDArray, rect: FaceRectangle) -> LandmarkSet: ...

	@abstractmethod
	def compute_encoding(self, frame: npt.NDArray, landmarks: LandmarkSet, num_jitters: int = 1) -> npt.NDArray: ...
