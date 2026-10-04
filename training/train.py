"""Trains the lens segmenter and exports it to ONNX for the backend.

Colab/Kaggle: pip install -r requirements.txt, then
  python train.py --data data/ --epochs 40
  -> lens-seg.onnx, copy to backend/models/
"""

import argparse
from pathlib import Path

import segmentation_models_pytorch as smp
import torch
from dataset import SIZE, LensDataset
from torch.utils.data import DataLoader, random_split


def iou(logits: torch.Tensor, target: torch.Tensor) -> float:
    pred = logits > 0
    inter = (pred & (target > 0.5)).sum().item()
    union = (pred | (target > 0.5)).sum().item()
    return inter / union if union else 1.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--out", type=Path, default=Path("lens-seg.onnx"))
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    full = LensDataset(args.data, augment=True)
    n_val = max(1, len(full) // 5)
    train_set, val_idx = random_split(
        range(len(full)), [len(full) - n_val, n_val], generator=torch.Generator().manual_seed(0)
    )
    train = torch.utils.data.Subset(full, list(train_set))
    val = torch.utils.data.Subset(LensDataset(args.data, augment=False), list(val_idx))

    # MobileNetV3 encoder: small enough to run on a free CPU server.
    model = smp.Unet("timm-mobilenetv3_large_100", encoder_weights="imagenet", classes=1).to(device)
    loss_fn = smp.losses.DiceLoss("binary")
    bce = torch.nn.BCEWithLogitsLoss()
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.epochs)

    best = 0.0
    for epoch in range(args.epochs):
        model.train()
        for x, y in DataLoader(train, batch_size=8, shuffle=True, num_workers=2):
            x, y = x.to(device), y.to(device)
            logits = model(x)
            loss = loss_fn(logits, y) + bce(logits, y)
            opt.zero_grad()
            loss.backward()
            opt.step()
        sched.step()

        model.eval()
        with torch.no_grad():
            scores = [iou(model(x.to(device)), y.to(device)) for x, y in DataLoader(val, batch_size=8)]
        score = sum(scores) / len(scores)
        print(f"epoch {epoch + 1}: val IoU {score:.4f}")
        if score > best:
            best = score
            torch.save(model.state_dict(), "best.pt")

    model.load_state_dict(torch.load("best.pt"))
    model.eval().cpu()
    torch.onnx.export(
        model, torch.zeros(1, 3, SIZE, SIZE), args.out, input_names=["image"], output_names=["logits"], opset_version=17
    )
    print(f"Best val IoU {best:.4f}, exported {args.out}")


if __name__ == "__main__":
    main()
