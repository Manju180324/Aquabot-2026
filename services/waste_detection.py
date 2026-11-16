from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
import streamlit as st


APP_DIR = Path(__file__).resolve().parents[1]
LIVING_CLASSES = {"person", "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe"}
PLASTIC_CLASSES = {
    "backpack", "umbrella", "handbag", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite", "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup", "bowl", "chair", "couch", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone", "toothbrush", "hair drier",
    "plastic bag", "straw", "plastic bottle", "bottle cap", "cup lid", "plastic container", "wrapper", "packaging", "foam", "pen", "pencil", "glove", "mask", "toy", "charger", "plastic tray", "food tray", "plastic wrap", "zip lock bag", "plastic plate", "plastic spoon", "plastic fork", "plastic knife", "plastic cup", "plastic bowl", "plastic lid", "plastic jar", "styrofoam cup", "styrofoam tray", "bubble wrap", "shopping bag", "packet", "blister pack",
}
METALLIC_CLASSES = {
    "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "knife", "spoon", "fork", "microwave", "oven", "toaster", "sink", "refrigerator", "scissors", "clock", "can", "aluminum foil", "cooking pan", "cable", "battery", "phone", "earphones", "fridge", "light bulb", "tool", "hammer", "wrench", "pliers", "screw", "nail", "bolt", "motor", "fan", "remote control", "charger", "glass bottle", "wine bottle", "glass jar", "drinking glass", "mirror", "window glass", "vase",
}


def waste_category(label: str) -> str:
    normalized = label.lower().strip()
    if normalized in PLASTIC_CLASSES:
        return "Plastic"
    if normalized in METALLIC_CLASSES:
        return "Metallic"
    return "Biodegradable"


@st.cache_resource(show_spinner="Loading the selected YOLO model…")
def load_yolo(model_name: str):
    from ultralytics import YOLO

    model_path = APP_DIR / model_name
    if not model_path.is_file():
        raise FileNotFoundError(f"Model weights not found: {model_path.name}")
    return YOLO(str(model_path))


def detect_image(image_bytes: bytes, model_name: str) -> dict[str, Any]:
    """Run the existing YOLO waste-classification workflow on one uploaded frame."""
    import cv2

    start = perf_counter()
    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("The uploaded image could not be decoded.")
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    model = load_yolo(model_name)
    result = model(rgb, conf=0.25, iou=0.5, verbose=False)[0]
    detections = []
    for box in result.boxes:
        class_id = int(box.cls[0])
        label = str(result.names.get(class_id, class_id)).lower()
        if label in LIVING_CLASSES:
            continue
        confidence = float(box.conf[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        center_x = (x1 + x2) / 2
        offset = (center_x - image.shape[1] / 2) / max(image.shape[1] / 2, 1)
        position = "left" if offset < -0.3 else "right" if offset > 0.3 else "center"
        detections.append({"label": label, "waste": waste_category(label), "confidence": confidence, "bbox": [x1, y1, x2, y2], "box_position": position, "offset": offset, "bbox_height": max(0, y2-y1), "frame_height": image.shape[0]})
    best = max(detections, key=lambda item: item["confidence"], default=None)
    annotated = cv2.cvtColor(result.plot(), cv2.COLOR_BGR2RGB)
    return {"annotated": annotated, "best": best, "detections": detections, "elapsed_ms": (perf_counter() - start) * 1000}


def update_autonomous_navigation(box_position: str | None) -> None:
    nav = st.session_state.navigation
    direction, speed = "Straight", 1.0
    if box_position == "left":
        direction, speed = "Left", 0.5
    elif box_position == "right":
        direction, speed = "Right", 0.5
    elif box_position is None:
        direction, speed = "Straight", 0.8
    nav.update(direction=direction, speed=speed)
