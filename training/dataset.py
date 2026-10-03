"""Dataset of rectified lens-window crops and their masks.

Preprocessing MUST match backend OnnxSegmenter: resize to SIZE x SIZE (no aspect ratio kept), RGB, /255,
ImageNet mean/std, NCHW. Images come from the API with OPTIFRAME_DATASET_DIR set (auto-labeled backlit
shots) and from your own harder shots whose masks were transferred from a backlit twin.
"""
from pathlib import Path

import albumentations as A
import cv2
import numpy as np
import torch
from torch.utils.data import Dataset

SIZE = 512
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def augmentations() -> A.Compose:
    """Reflections, shadows, blur and lighting changes the backlit shots do not have."""
    return A.Compose([
        A.HorizontalFlip(),
        A.VerticalFlip(),
        A.Affine(rotate=(-20, 20), scale=(0.9, 1.1), p=0.7),
        A.RandomBrightnessContrast(0.3, 0.3),
        A.RandomShadow(p=0.3),
        A.RandomSunFlare(src_radius=120, p=0.2),
        A.GaussianBlur(p=0.2),
        A.ImageCompression(quality_range=(60, 95), p=0.3),
    ])


def to_tensor(rgb: np.ndarray) -> torch.Tensor:
    x = cv2.resize(rgb, (SIZE, SIZE), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    return torch.from_numpy(((x - MEAN) / STD).transpose(2, 0, 1))


class LensDataset(Dataset):
    def __init__(self, root: Path, augment: bool):
        self.images = sorted((root / "images").glob("*.png"))
        self.root = root
        self.aug = augmentations() if augment else None

    def __len__(self) -> int:
        return len(self.images)

    def __getitem__(self, i: int):
        path = self.images[i]
        rgb = cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2RGB)
        mask = cv2.imread(str(self.root / "masks" / path.name), cv2.IMREAD_GRAYSCALE)
        if self.aug:
            out = self.aug(image=rgb, mask=mask)
            rgb, mask = out["image"], out["mask"]
        m = cv2.resize(mask, (SIZE, SIZE), interpolation=cv2.INTER_NEAREST)
        return to_tensor(rgb), torch.from_numpy((m > 127).astype(np.float32))[None]
