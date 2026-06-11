# Swim Pose Project

竞技游泳姿态视觉评分系统的 MMPose 工程骨架。

## Local Environment

This project uses a local conda environment inside the workspace:

```bash
conda activate /Users/tuian/Documents/大学/竞赛/大创/游泳/swim/.conda/swim-pose
```

Do not install dependencies into the global/base environment.

Validated core versions:

```text
Python 3.10.20
PyTorch 2.12.0
NumPy 1.26.4
OpenCV 4.11.0
MMEngine 0.10.7
MMCV Lite 2.1.0
MMDetection 3.3.0
MMPose 1.3.2
```

Note: this Mac environment uses `mmcv-lite` for local development and pipeline
checks. For full GPU training on Windows + NVIDIA, install the full `mmcv`
wheel that matches that machine's CUDA and PyTorch versions.

## Data Layout

Put CVAT COCO exports here:

```text
data/swim_coco/annotations/train.json
data/swim_coco/annotations/val.json
data/swim_coco/images/train/
data/swim_coco/images/val/
```

For the first overfitting test, using the same tiny dataset for train and val is acceptable.

## Your Checklist

1. Export COCO Keypoints annotations from CVAT.
2. Put training images in `data/swim_coco/images/train/`.
3. Put validation images in `data/swim_coco/images/val/`.
4. Put annotations in:
   - `data/swim_coco/annotations/train.json`
   - `data/swim_coco/annotations/val.json`
5. Make sure each JSON `file_name` matches the image path under its folder.
6. Put pretrained or fine-tuned model weights in `weights/`.
7. Put test videos wherever convenient, then save output videos under `outputs/`.
8. Before running commands, activate the local environment:

```bash
conda activate /Users/tuian/Documents/大学/竞赛/大创/游泳/swim/.conda/swim-pose
```

