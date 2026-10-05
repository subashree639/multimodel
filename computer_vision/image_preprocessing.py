"""
Image preprocessing utilities for computer vision pipeline.
"""

import logging
import numpy as np
from PIL import Image
from typing import List, Tuple, Optional, Union
from pathlib import Path

try:
    import cv2  # type: ignore
    _HAS_CV2 = True
except ImportError:  # pragma: no cover - optional heavy dep
    cv2 = None  # type: ignore
    _HAS_CV2 = False

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Handles image preprocessing for the recommendation system."""

    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
    MAX_SIZE = 256

    def __init__(self, target_size: int = 256):
        """
        Initialize the image preprocessor.

        Args:
            target_size: Target size for image resizing
        """
        self.target_size = target_size
        self.mean = np.array([0.485, 0.456, 0.406])
        self.std = np.array([0.229, 0.224, 0.225])

    def load_image(self, image_path: Union[str, Path]) -> Optional[np.ndarray]:
        """
        Load an image from a file path.

        Args:
            image_path: Path to the image file

        Returns:
            Image as numpy array (BGR format), or None if loading fails
        """
        try:
            if not _HAS_CV2:
                raise ImportError(
                    "opencv-python is not installed. "
                    "Install it with: pip install opencv-python"
                )
            image = cv2.imread(str(image_path))
            if image is None:
                logger.error(f"Failed to load image: {image_path}")
                return None
            logger.info(f"Loaded image: {image_path}, shape: {image.shape}")
            return image
        except Exception as e:
            logger.error(f"Error loading image {image_path}: {e}")
            return None

    def load_image_pil(self, image_path: Union[str, Path]) -> Optional[Image.Image]:
        """
        Load an image using PIL.

        Args:
            image_path: Path to the image file

        Returns:
            PIL Image object, or None if loading fails
        """
        try:
            return Image.open(image_path).convert('RGB')
        except Exception as e:
            logger.error(f"Error loading image with PIL {image_path}: {e}")
            return None

    def validate_image(self, file_path: Union[str, Path]) -> bool:
        """
        Validate if file is an allowed image type.

        Args:
            file_path: Path to the file

        Returns:
            True if valid, False otherwise
        """
        path = Path(file_path)
        if path.suffix.lower() not in self.ALLOWED_EXTENSIONS:
            logger.warning(f"Invalid file type: {path.suffix}")
            return False

        # Try to open as image
        try:
            img = Image.open(path)
            img.verify()
            return True
        except Exception:
            return False

    def resize_image(self, image: np.ndarray, size: Optional[int] = None) -> np.ndarray:
        """
        Resize image maintaining aspect ratio with padding.

        Args:
            image: Input image array (BGR)
            size: Target size (square), defaults to self.target_size

        Returns:
            Resized and padded image
        """
        if size is None:
            size = self.target_size

        if not _HAS_CV2:
            raise ImportError(
                "opencv-python is not installed. "
                "Install it with: pip install opencv-python"
            )

        h, w = image.shape[:2]
        scale = size / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)

        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Pad to square
        pad_h = (size - new_h) // 2
        pad_w = (size - new_w) // 2

        if len(image.shape) == 3:
            padded = cv2.copyMakeBorder(
                resized, pad_h, size - new_h - pad_h,
                pad_w, size - new_w - pad_w,
                cv2.BORDER_CONSTANT, value=(0, 0, 0)
            )
        else:
            padded = cv2.copyMakeBorder(
                resized, pad_h, size - new_h - pad_h,
                pad_w, size - new_w - pad_w,
                cv2.BORDER_CONSTANT, value=0
            )

        return padded

    def normalize_image(self, image: np.ndarray) -> np.ndarray:
        """
        Normalize image for ResNet50 input.

        Args:
            image: Image in RGB format, range [0, 255]

        Returns:
            Normalized image as float32 array
        """
        image = image.astype(np.float32) / 255.0
        image = (image - self.mean) / self.std
        return image

    def preprocess_pipeline(self, image: Union[str, Path, np.ndarray, Image.Image]) -> Optional[np.ndarray]:
        """
        Complete preprocessing pipeline.

        Args:
            image: Input image (path, array, or PIL Image)

        Returns:
            Preprocessed image ready for model input, or None on failure
        """
        # Load image
        if isinstance(image, (str, Path)):
            img = self.load_image(image)
            if img is None:
                return None
        elif isinstance(image, Image.Image):
            img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        else:
            img = image.copy()

        # Resize
        img = self.resize_image(img)

        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Normalize
        img_normalized = self.normalize_image(img_rgb)

        return img_normalized

    def augment_image(
        self,
        image: np.ndarray,
        augmentations: List[str] = None
    ) -> List[np.ndarray]:
        """
        Apply data augmentation augmentations.

        Args:
            image: Input image
            augmentations: List of augmentation types to apply

        Returns:
            List of augmented images
        """
        if augmentations is None:
            augmentations = ['flip_h', 'flip_v', 'rotate', 'brightness']

        augmented_images = [image]
        h, w = image.shape[:2]
        center = (w // 2, h // 2)

        for aug in augmentations:
            if aug == 'flip_h':
                augmented_images.append(cv2.flip(image, 1))
            elif aug == 'flip_v':
                augmented_images.append(cv2.flip(image, 0))
            elif aug == 'rotate':
                M = cv2.getRotationMatrix2D(center, 15, 1.0)
                augmented_images.append(cv2.warpAffine(image, M, (w, h)))
            elif aug == 'brightness':
                augmented = cv2.convertScaleAbs(image, alpha=1.2, beta=10)
                augmented_images.append(augmented)

        return augmented_images

    def extract_object_region(
        self,
        image: np.ndarray,
        bbox: Tuple[int, int, int, int]
    ) -> np.ndarray:
        """
        Crop image to a bounding box region.

        Args:
            image: Input image
            bbox: Bounding box (x, y, width, height)

        Returns:
            Cropped region
        """
        x, y, w, h = bbox
        return image[y:y+h, x:x+w]

    def save_image(self, image: np.ndarray, output_path: Union[str, Path]) -> bool:
        """
        Save image to file.

        Args:
            image: Image array
            output_path: Output file path

        Returns:
            True if successful
        """
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            # Convert from normalized to uint8 if needed
            if image.dtype == np.float32 or image.dtype == np.float64:
                image = (image * 255).astype(np.uint8)
            if len(image.shape) == 3 and image.shape[2] == 3:
                image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                cv2.imwrite(str(output_path), image_bgr)
            else:
                cv2.imwrite(str(output_path), image)
            return True
        except Exception as e:
            logger.error(f"Error saving image: {e}")
            return False


def detect_duplicate_image(img1_path: str, img2_path: str, threshold: float = 0.95) -> bool:
    """
    Detect if two images are near-duplicates.

    Args:
        img1_path: Path to first image
        img2_path: Path to second image
        threshold: Similarity threshold

    Returns:
        True if images are duplicates
    """
    preprocessor = ImagePreprocessor()
    img1 = preprocessor.preprocess_pipeline(img1_path)
    img2 = preprocessor.preprocess_pipeline(img2_path)

    if img1 is None or img2 is None:
        return False

    if img1.shape != img2.shape:
        return False

    similarity = np.mean(img1 == img2)
    return similarity > threshold
