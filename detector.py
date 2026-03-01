import cv2
import numpy as np
from ultralytics import YOLO
from datetime import datetime
import os

model = YOLO("yolov8n.pt")

# ONLY these count as accident-relevant vehicles — NO persons
VEHICLE_CLASSES = ["car", "truck", "bus", "motorcycle", "bicycle"]

# Track previous frame data for motion analysis
prev_frame_gray = None
vehicle_history = []  # Last N frames of vehicle positions
HISTORY_LEN = 8


def detect_accident(frame, confidence_threshold=0.25):
    global prev_frame_gray, vehicle_history

    annotated_frame = frame.copy()
    accident_detected = False
    accident_reason = ""

    # Upscale small CCTV frame
    h, w = frame.shape[:2]
    if w < 400:
        frame_resized = cv2.resize(frame, (w * 2, h * 2))
    else:
        frame_resized = frame.copy()

    # Run YOLO
    results = model(frame_resized, verbose=False)
    vehicles_detected = []

    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            label = model.names[cls_id]
            conf = float(box.conf[0])

            # ✅ STRICTLY only vehicles — ignore persons completely
            if label in VEHICLE_CLASSES and conf >= confidence_threshold:
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                # Scale back to original frame size
                if w < 400:
                    x1, y1, x2, y2 = x1//2, y1//2, x2//2, y2//2

                vehicles_detected.append({
                    "type": label,
                    "confidence": round(conf, 2),
                    "bbox": (x1, y1, x2, y2),
                    "center": ((x1+x2)//2, (y1+y2)//2),
                    "area": (x2-x1) * (y2-y1)
                })

                # Draw vehicle boxes in GREEN (normal state)
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 200, 0), 2)
                cv2.putText(annotated_frame, f"{label} {conf:.2f}",
                           (x1, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

    # ── DETECTION LAYER 1: Sudden abnormal motion (impact) ──
    # Always convert from the ORIGINAL frame (not resized) to keep consistent size
    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    if prev_frame_gray is not None:
        # ✅ FIX: if sizes differ (e.g. variable resolution video), resize prev to match
        if prev_frame_gray.shape != frame_gray.shape:
            prev_frame_gray = cv2.resize(prev_frame_gray, (frame_gray.shape[1], frame_gray.shape[0]))

        motion_score = detect_sudden_motion(prev_frame_gray, frame_gray)
        if motion_score > 18 and len(vehicles_detected) >= 1:
            accident_detected = True
            accident_reason = f"Sudden Impact Motion (score:{motion_score:.1f})"

    prev_frame_gray = frame_gray

    # ── DETECTION LAYER 2: Vehicle-only overlap (tight threshold) ──
    if not accident_detected and len(vehicles_detected) >= 2:
        overlap, pair = check_vehicle_overlap(vehicles_detected)
        if overlap:
            accident_detected = True
            accident_reason = f"Vehicle Collision: {pair[0]} + {pair[1]}"

    # ── DETECTION LAYER 3: Sudden vehicle direction change ──
    vehicle_history.append(vehicles_detected)
    if len(vehicle_history) > HISTORY_LEN:
        vehicle_history.pop(0)

    if not accident_detected and len(vehicle_history) >= 4:
        if detect_sudden_direction_change(vehicle_history):
            accident_detected = True
            accident_reason = "Sudden Direction Change Detected"

    # Draw accident overlay
    if accident_detected:
        cv2.rectangle(annotated_frame, (0, 0),
                     (annotated_frame.shape[1], annotated_frame.shape[0]),
                     (0, 0, 255), 5)
        cv2.putText(annotated_frame, "ACCIDENT DETECTED",
                   (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
        cv2.putText(annotated_frame, accident_reason,
                   (10, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 100, 255), 1)

    return accident_detected, vehicles_detected, annotated_frame


def detect_sudden_motion(prev_gray, curr_gray):
    """
    Detects sudden large motion = impact moment.
    Returns a motion score. High score = sudden crash motion.
    """
    diff = cv2.absdiff(prev_gray, curr_gray)
    # Only count HIGH intensity pixel changes (ignore small movements)
    _, thresh = cv2.threshold(diff, 40, 255, cv2.THRESH_BINARY)
    motion_score = np.sum(thresh) / (thresh.shape[0] * thresh.shape[1] * 255) * 100
    return motion_score


def check_vehicle_overlap(vehicles):
    """
    Only triggers if VEHICLE bounding boxes actually overlap.
    No persons involved. Uses tight overlap — not proximity.
    """
    for i in range(len(vehicles)):
        for j in range(i + 1, len(vehicles)):
            b1 = vehicles[i]["bbox"]
            b2 = vehicles[j]["bbox"]

            # Strict overlap — boxes must actually intersect
            overlap_x = min(b1[2], b2[2]) - max(b1[0], b2[0])
            overlap_y = min(b1[3], b2[3]) - max(b1[1], b2[1])

            if overlap_x > 10 and overlap_y > 10:
                # Extra check: overlap area must be significant
                overlap_area = overlap_x * overlap_y
                area1 = (b1[2]-b1[0]) * (b1[3]-b1[1])
                area2 = (b2[2]-b2[0]) * (b2[3]-b2[1])
                min_area = min(area1, area2)

                # Overlap must be at least 15% of smaller vehicle
                if min_area > 0 and (overlap_area / min_area) > 0.15:
                    return True, (vehicles[i]["type"], vehicles[j]["type"])

    return False, None


def detect_sudden_direction_change(history):
    """
    Tracks vehicle centers across frames.
    A sudden large jump in position = vehicle thrown by impact.
    """
    if len(history) < 4:
        return False

    for frame_idx in range(2, len(history)):
        curr_vehicles = history[frame_idx]
        prev_vehicles = history[frame_idx - 2]

        for curr_v in curr_vehicles:
            for prev_v in prev_vehicles:
                if curr_v["type"] == prev_v["type"]:
                    cx, cy = curr_v["center"]
                    px, py = prev_v["center"]
                    displacement = ((cx-px)**2 + (cy-py)**2) ** 0.5

                    # Sudden jump > 45px in 2 frames = abnormal
                    if displacement > 45:
                        return True
    return False


def save_snapshot(frame):
    os.makedirs("static/snapshots", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"static/snapshots/accident_{timestamp}.jpg"
    cv2.imwrite(filename, frame)
    return filename


def run_on_video(video_path, on_accident_callback):
    global prev_frame_gray, vehicle_history
    # Reset state for new video
    prev_frame_gray = None
    vehicle_history = []

    cap = cv2.VideoCapture(video_path)
    alert_sent = False
    frame_count = 0

    accident_frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if frame_count % 3 != 0:
            continue

        accident, vehicles, annotated = detect_accident(frame)

        # Cooldown logic — only trigger once per accident event
        if accident:
            accident_frame_count += 1
        else:
            accident_frame_count = max(0, accident_frame_count - 1)

        # Only fire alert if accident sustained for 2+ frames (not a flicker)
        if accident_frame_count >= 2 and not alert_sent:
            snapshot_path = save_snapshot(annotated)
            on_accident_callback(annotated, vehicles, snapshot_path)
            alert_sent = True

        yield annotated, accident, vehicles

    cap.release()