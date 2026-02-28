import cv2
import numpy as np
from ultralytics import YOLO
from datetime import datetime
import os
import time

# YOLOv8 for object/weapon detection
model = YOLO("yolov8n.pt")

# Weapon-related COCO classes (knife=43, scissors=76 — closest we get without custom model)
WEAPON_CLASSES = ["knife", "scissors"]
PERSON_CLASS = "person"

# ── Fight tracker ──
person_history = []   # Last N frames of person bounding boxes
HISTORY_LEN = 10

# ── Theft tracker ──
object_history = {}   # track disappearing objects


def detect_crimes(frame, confidence_threshold=0.30):
    """
    Master crime detection function.
    Returns: (crimes_found, crime_details_list, annotated_frame)
    """
    annotated_frame = frame.copy()
    crimes_found = []

    h, w = frame.shape[:2]
    if w < 400:
        frame_resized = cv2.resize(frame, (w * 2, h * 2))
        scale = 2
    else:
        frame_resized = frame.copy()
        scale = 1

    results = model(frame_resized, verbose=False)

    persons = []
    weapons = []
    all_objects = []

    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            label = model.names[cls_id]
            conf = float(box.conf[0])

            if conf < confidence_threshold:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            x1, y1, x2, y2 = x1//scale, y1//scale, x2//scale, y2//scale

            obj = {
                "type": label,
                "confidence": round(conf, 2),
                "bbox": (x1, y1, x2, y2),
                "center": ((x1+x2)//2, (y1+y2)//2),
                "area": (x2-x1)*(y2-y1)
            }

            if label == PERSON_CLASS:
                persons.append(obj)
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (200, 200, 0), 1)
            elif label in WEAPON_CLASSES:
                weapons.append(obj)
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                cv2.putText(annotated_frame, f"WEAPON:{label}",
                           (x1, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            all_objects.append(obj)

    # ── CHECK 1: Weapon Detection ──
    if weapons:
        crimes_found.append({
            "type": "WEAPON_DETECTED",
            "label": "⚔️ Weapon Detected",
            "detail": f"{len(weapons)} weapon(s) visible: {', '.join(w['type'] for w in weapons)}",
            "severity": "CRITICAL",
            "color": (0, 0, 255)
        })

    # ── CHECK 2: Fight / Violence Detection ──
    fight = detect_fight(persons, frame)
    if fight:
        crimes_found.append({
            "type": "FIGHT_DETECTED",
            "label": "👊 Fight/Violence Detected",
            "detail": fight,
            "severity": "HIGH",
            "color": (0, 60, 255)
        })

    # ── CHECK 3: Theft / Robbery (crowd + sudden scatter) ──
    theft = detect_theft_pattern(persons)
    if theft:
        crimes_found.append({
            "type": "THEFT_PATTERN",
            "label": "🚨 Theft/Robbery Pattern",
            "detail": theft,
            "severity": "HIGH",
            "color": (0, 0, 200)
        })

    # Draw crime overlays
    if crimes_found:
        most_severe = crimes_found[0]
        color = most_severe["color"]
        cv2.rectangle(annotated_frame, (0, 0),
                     (annotated_frame.shape[1], annotated_frame.shape[0]), color, 4)

        y_offset = 28
        for crime in crimes_found:
            cv2.putText(annotated_frame, crime["label"],
                       (8, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.65, crime["color"], 2)
            y_offset += 24

    return len(crimes_found) > 0, crimes_found, annotated_frame


# ── Fight Detection ──
person_bbox_history = []

def detect_fight(persons, frame):
    global person_bbox_history

    person_bbox_history.append(persons)
    if len(person_bbox_history) > HISTORY_LEN:
        person_bbox_history.pop(0)

    if len(persons) < 2:
        return None

    # Check 1: Persons very close together (within 40px)
    for i in range(len(persons)):
        for j in range(i+1, len(persons)):
            c1 = persons[i]["center"]
            c2 = persons[j]["center"]
            dist = ((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2)**0.5
            if dist < 40:
                return f"2 persons in close aggressive proximity (dist:{dist:.0f}px)"

    # Check 2: Rapid erratic movement across frames
    if len(person_bbox_history) >= 5:
        total_movement = 0
        for fi in range(1, len(person_bbox_history)):
            curr = person_bbox_history[fi]
            prev = person_bbox_history[fi-1]
            if curr and prev:
                for cp in curr:
                    for pp in prev:
                        dx = cp["center"][0] - pp["center"][0]
                        dy = cp["center"][1] - pp["center"][1]
                        total_movement += (dx**2 + dy**2)**0.5
        avg_movement = total_movement / max(len(persons), 1)
        if avg_movement > 30:
            return f"Erratic high-speed movement detected (score:{avg_movement:.0f})"

    return None


# ── Theft Pattern Detection ──
prev_person_count = []

def detect_theft_pattern(persons):
    global prev_person_count

    prev_person_count.append(len(persons))
    if len(prev_person_count) > 15:
        prev_person_count.pop(0)

    if len(prev_person_count) < 10:
        return None

    # Pattern: crowd gathers (3+ people) then suddenly disperses
    max_recent = max(prev_person_count[-10:])
    current = len(persons)

    if max_recent >= 3 and current <= 1 and max_recent - current >= 3:
        return f"Crowd-then-disperse pattern (was {max_recent} people, now {current})"

    # Pattern: sudden rush toward one area (multiple people converging)
    if len(persons) >= 3:
        centers = [p["center"] for p in persons]
        avg_x = sum(c[0] for c in centers) / len(centers)
        avg_y = sum(c[1] for c in centers) / len(centers)
        spread = sum(((c[0]-avg_x)**2 + (c[1]-avg_y)**2)**0.5 for c in centers) / len(centers)
        if spread < 35:
            return f"Multiple persons converging on single point (spread:{spread:.0f}px)"

    return None


def save_crime_snapshot(frame, crime_type):
    os.makedirs("static/crime_snapshots", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"static/crime_snapshots/{crime_type}_{timestamp}.jpg"
    cv2.imwrite(filename, frame)
    return filename


def run_crime_detection_on_video(video_path, on_crime_callback):
    global person_bbox_history, loiter_tracker, prev_person_count
    # Reset all state
    person_bbox_history = []
    prev_person_count = []

    cap = cv2.VideoCapture(video_path)
    alerted_crimes = set()
    frame_count = 0
    crime_frame_counter = {}

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if frame_count % 3 != 0:
            continue

        crime_found, crimes, annotated = detect_crimes(frame)

        for crime in crimes:
            ctype = crime["type"]
            crime_frame_counter[ctype] = crime_frame_counter.get(ctype, 0) + 1

            # Fire alert only after 2 consecutive frames + not already alerted
            if crime_frame_counter[ctype] >= 2 and ctype not in alerted_crimes:
                snapshot = save_crime_snapshot(annotated, ctype)
                on_crime_callback(annotated, crimes, snapshot)
                alerted_crimes.add(ctype)
        
        # Reset counters for crimes not seen this frame
        seen_types = {c["type"] for c in crimes}
        for ctype in list(crime_frame_counter.keys()):
            if ctype not in seen_types:
                crime_frame_counter[ctype] = max(0, crime_frame_counter[ctype] - 1)

        yield annotated, crime_found, crimes

    cap.release()