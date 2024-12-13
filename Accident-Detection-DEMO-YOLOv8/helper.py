import cv2
import os
import uuid
from datetime import datetime
from ultralytics import YOLO
import numpy as np
import streamlit as st
from tinydb import TinyDB, Query
from pathlib import Path

class AccidentDetectionHelper:
    def __init__(self, settings):
        self.settings = settings
        self.db = TinyDB('database/data.json') 

    def generate_video_id(self):
        return str(uuid.uuid4())

    def process_video(self, video_path, st_frame, model):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            st.error(f"Error opening video file {video_path}")
            return False, False

        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0:
            fps = 20.0  # default FPS if not detected

        # Prepare for processed video saving
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        processed_videos_dir = self.settings.snapshots_dir.parent / 'processed_videos'
        processed_videos_dir.mkdir(parents=True, exist_ok=True)
        output_path = processed_videos_dir / f"processed_{Path(video_path).stem}.mp4"
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (frame_width, frame_height))

        accident_detected = False
        severe_accident_detected = False
        video_id = self.generate_video_id()
        snapshots_folder = self.settings.snapshots_dir / video_id
        snapshots_folder.mkdir(parents=True, exist_ok=True)

        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            detected_classes = []

            results = model.predict(frame, conf=self.settings.confidence_threshold)

            # Extract bounding boxes, confidences, and class IDs
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    conf = box.conf[0].item()
                    cls_id = int(box.cls[0].item())

                    # Only process if class_id is in [0,1]
                    if cls_id not in self.settings.class_ids:
                        continue

                    detected_classes.append(cls_id)

                    # Assign box color based on class
                    if cls_id == 1:
                        box_color = (0, 0, 255)  # Red for "vazna nehoda"
                        severe_accident_detected = True
                        accident_detected = True 
                    elif cls_id == 0:
                        box_color = (0, 165, 255)  # Orange for "nehoda"
                        accident_detected = True

                    # Draw bounding box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

            # Determine border color based on detection
            if severe_accident_detected:
                border_color = (0, 0, 255)  # Red
            elif accident_detected:
                border_color = (0, 165, 255)  # Orange
            else:
                border_color = (128, 128, 128)  # Gray

            # Add border to frame
            frame = cv2.copyMakeBorder(
                frame, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=border_color
            )

            # Convert frame to RGB for Streamlit
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Display frame
            st_frame.image(frame_rgb, channels="RGB", use_container_width=True)
            out.write(frame)
            frame_count += 1

            # Save snapshot if accident detected in this frame
            if detected_classes:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                snapshot_path = snapshots_folder / f"snapshot_{timestamp}.png"
                cv2.imwrite(str(snapshot_path), frame)

                # Save to database
                self.db.insert({
                    'video_id': video_id,
                    'timestamp': timestamp,
                    'snapshot_path': str(snapshot_path),
                    'class_detected': [cls_id for cls_id in detected_classes],
                })

        cap.release()
        out.release()

        return accident_detected, severe_accident_detected
