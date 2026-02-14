from __future__ import annotations

import os
from typing import List

import dlib
import numpy as np
import numpy.typing as npt

import paths_factory
from recog.backend import FaceRectangle, LandmarkPoint, LandmarkSet, RecognitionBackend


class DlibBackend(RecognitionBackend):
	def __init__(self, use_cnn: bool = False):
		if not os.path.isfile(paths_factory.shape_predictor_5_face_landmarks_path()):
			raise FileNotFoundError("dlib data files not found")

		self._use_cnn = use_cnn
		if use_cnn:
			self._detector = dlib.cnn_face_detection_model_v1(
				paths_factory.mmod_human_face_detector_path())
		else:
			self._detector = dlib.get_frontal_face_detector()

		self._predictor = dlib.shape_predictor(
			paths_factory.shape_predictor_5_face_landmarks_path())
		self._encoder = dlib.face_recognition_model_v1(
			paths_factory.dlib_face_recognition_resnet_model_v1_path())

	def detect_faces(self, frame: npt.NDArray, upsample: int = 1) -> List[FaceRectangle]:
		raw = self._detector(frame, upsample)
		result = []
		for det in raw:
			r = det.rect if self._use_cnn else det
			result.append(FaceRectangle(
				top=r.top(), left=r.left(), right=r.right(), bottom=r.bottom()))
		return result

	def get_landmarks(self, frame: npt.NDArray, rect: FaceRectangle) -> LandmarkSet:
		dlib_rect = dlib.rectangle(rect.left(), rect.top(), rect.right(), rect.bottom())
		raw_landmarks = self._predictor(frame, dlib_rect)
		points = [LandmarkPoint(x=raw_landmarks.part(i).x, y=raw_landmarks.part(i).y)
			for i in range(raw_landmarks.num_parts)]
		return LandmarkSet(points, raw=raw_landmarks)

	def compute_encoding(self, frame: npt.NDArray, landmarks: LandmarkSet, num_jitters: int = 1) -> npt.NDArray:
		return np.array(
			self._encoder.compute_face_descriptor(frame, landmarks._raw, num_jitters))
