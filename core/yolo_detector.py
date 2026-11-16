from ultralytics import YOLO
import cv2

model = YOLO("yolov8n.pt")

PLASTIC = ["bottle","cup","fork","spoon","knife","bowl","wine glass", "pen", "phone"]
METAL = ["fork","knife","spoon","scissors"]
BIO = ["banana","apple","orange","leaf","paper","cardboard"]

def detect_waste(frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = model([rgb])
    annotated = results[0].plot()

    waste_type = "None"
    confidence = 0.0

    for box in results[0].boxes:
        label = results[0].names[int(box.cls[0])].lower()
        confidence = float(box.conf[0])

        if label in PLASTIC:
            waste_type = "Plastic"
            break
        elif label in METAL:
            waste_type = "Metal"
            break
        elif label in BIO:
            waste_type = "Biodegradable"
            break

    return annotated, waste_type, confidence