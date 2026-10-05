"""
Feature extraction using ResNet50 for visual product similarity.
"""

import logging
import numpy as np
from typing import List, Optional, Tuple, Union
from pathlib import Path
from PIL import Image
import os

try:
    import torch  # type: ignore
    import torch.nn as nn  # type: ignore
    _HAS_TORCH_CORE = True
except ImportError:  # pragma: no cover - optional heavy dep
    torch = None  # type: ignore
    nn = None  # type: ignore
    _HAS_TORCH_CORE = False

try:
    from torchvision import models, transforms  # type: ignore
    _HAS_VISION = True
except ImportError:  # pragma: no cover - optional heavy dep
    models = None  # type: ignore
    transforms = None  # type: ignore
    _HAS_VISION = False

_HAS_TORCH = _HAS_TORCH_CORE and _HAS_VISION

try:
    import cv2  # type: ignore
    _HAS_CV2 = True
except ImportError:  # pragma: no cover - optional heavy dep
    cv2 = None  # type: ignore
    _HAS_CV2 = False

from .image_preprocessing import ImagePreprocessor

logger = logging.getLogger(__name__)


class ResNet50FeatureExtractor:
    """Extract features from images using ResNet50 pre-trained model."""

    def __init__(self, device: Optional[str] = None, model_path: Optional[str] = None):
        """
        Initialize the ResNet50 feature extractor.

        Args:
            device: Device to run on ('cuda', 'cpu', or None for auto-detect)
            model_path: Optional path to fine-tuned model weights
        """
        if not _HAS_TORCH:
            raise ImportError(
                "torchvision is required for ResNet50 visual search "
                "(pip install torchvision)."
            )
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Using device: {self.device}")

        self.feature_dim = 2048  # ResNet50 output dimension

        # Load pre-trained ResNet50
        self.model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V1)

        # Remove the final classification layer to get features
        self.model = nn.Sequential(*list(self.model.children())[:-1])

        # Load fine-tuned weights if provided
        if model_path and os.path.exists(model_path):
            state_dict = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(state_dict)
            logger.info(f"Loaded fine-tuned weights from {model_path}")

        self.model = self.model.to(self.device)
        self.model.eval()

        # Preprocessor
        self.preprocessor = ImagePreprocessor()

        # ImageNet normalization
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def extract_features(self, image: Union[str, Path, np.ndarray, Image.Image]) -> Optional[np.ndarray]:
        """
        Extract features from a single image.

        Args:
            image: Input image (path, numpy array, or PIL Image)

        Returns:
            Feature vector of shape (2048,), or None on failure
        """
        try:
            # Preprocess
            if isinstance(image, (str, Path)):
                pil_img = Image.open(image).convert('RGB')
            elif isinstance(image, np.ndarray):
                pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            elif isinstance(image, Image.Image):
                pil_img = image.convert('RGB')
            else:
                logger.error(f"Unsupported image type: {type(image)}")
                return None

            # Resize and normalize
            pil_img = pil_img.resize((224, 224), Image.Resampling.LANCZOS)
            img_tensor = self.transform(pil_img).unsqueeze(0).to(self.device)

            # Extract features
            with torch.no_grad():
                features = self.model(img_tensor)

            # Flatten and normalize
            features = features.squeeze().cpu().numpy()
            features = features / (np.linalg.norm(features) + 1e-8)  # L2 normalization

            return features.astype(np.float32)

        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return None

    def extract_batch_features(self, images: List[Union[str, Path, np.ndarray]]) -> List[Optional[np.ndarray]]:
        """
        Extract features from a batch of images.

        Args:
            images: List of input images

        Returns:
            List of feature vectors
        """
        batch_tensors = []
        valid_indices = []

        for i, img in enumerate(images):
            try:
                if isinstance(img, (str, Path)):
                    pil_img = Image.open(img).convert('RGB')
                elif isinstance(img, np.ndarray):
                    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                elif isinstance(img, Image.Image):
                    pil_img = img.convert('RGB')
                else:
                    continue

                pil_img = pil_img.resize((224, 224), Image.Resampling.LANCZOS)
                batch_tensors.append(self.transform(pil_img))
                valid_indices.append(i)

            except Exception as e:
                logger.error(f"Error processing image {i}: {e}")
                continue

        if not batch_tensors:
            return [None] * len(images)

        batch_tensor = torch.stack(batch_tensors).to(self.device)

        with torch.no_grad():
            features = self.model(batch_tensor)

        features = features.squeeze().cpu().numpy()
        if features.ndim == 1:
            features = features.reshape(1, -1)

        # L2 normalize
        norms = np.linalg.norm(features, axis=1, keepdims=True)
        features = features / (norms + 1e-8)

        results = [None] * len(images)
        for i, idx in enumerate(valid_indices):
            results[idx] = features[i].astype(np.float32)

        return results

    def get_feature_dimension(self) -> int:
        """Return the dimension of the feature vectors."""
        return self.feature_dim
