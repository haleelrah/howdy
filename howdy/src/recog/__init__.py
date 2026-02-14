from recog.backend import FaceRectangle, LandmarkPoint, LandmarkSet, RecognitionBackend

__all__ = ["FaceRectangle", "LandmarkPoint", "LandmarkSet", "RecognitionBackend", "create_backend"]


def create_backend(use_cnn: bool = False) -> RecognitionBackend:
	from recog.dlib_backend import DlibBackend
	return DlibBackend(use_cnn=use_cnn)
