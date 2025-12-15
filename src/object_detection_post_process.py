import cv2
import numpy as np
from utils.toolbox import id_to_color
from speed_estimation import SpeedEstimationManager
import time
from collections import defaultdict


class LoiteringDetectionManager:
    """
    Manager for detecting loitering objects based on how long they've been present
    """
    def __init__(self, loitering_threshold=10.0, fps=30.0):
        """
        Initialize loitering detection manager

        Args:
            loitering_threshold (float): Time threshold in seconds for loitering detection
            fps (float): Frames per second of the video stream
        """
        self.loitering_threshold = loitering_threshold  # seconds
        self.frame_threshold = loitering_threshold * fps  # convert to frames
        self.track_start_frames = defaultdict(int)  # track_id -> start frame number
        self.current_frame = 0

    def update_frame_count(self):
        """Increment the current frame number"""
        self.current_frame += 1

    def update_track(self, track_id):
        """
        Update the start frame for a track ID if it's not already being tracked

        Args:
            track_id: Unique identifier for the tracked object
        """
        if track_id not in self.track_start_frames:
            self.track_start_frames[track_id] = self.current_frame

    def is_loitering(self, track_id):
        """
        Check if a track ID is considered loitering

        Args:
            track_id: Unique identifier for the tracked object

        Returns:
            bool: True if the object has been present for longer than the threshold
        """
        if track_id not in self.track_start_frames:
            return False

        frames_present = self.current_frame - self.track_start_frames[track_id]
        return frames_present > self.frame_threshold

    def cleanup_missing_tracks(self, current_track_ids):
        """
        Remove tracks that are no longer present

        Args:
            current_track_ids: Set of currently active track IDs
        """
        # Remove tracks that are no longer present
        ids_to_remove = []
        for track_id in self.track_start_frames:
            if track_id not in current_track_ids:
                ids_to_remove.append(track_id)

        for track_id in ids_to_remove:
            del self.track_start_frames[track_id]


def inference_result_handler(original_frame, infer_results, labels, config_data,
                            tracker=None, camera_width=640, camera_height=480,
                            pixel_distance=0.01, speed_estimation=False, speed_manager=None,
                            target_labels=None, loitering_detection=False,
                            loitering_manager=None, loitering_threshold=10.0,
                            enable_person_only=False):
    """
    Processes inference results and draw detections (with optional tracking).

    Args:
        infer_results (list): Raw output from the model.
        original_frame (np.ndarray): Original image frame.
        labels (list): List of class labels.
        enable_tracking (bool): Whether tracking is enabled.
        tracker (BYTETracker, optional): ByteTrack tracker instance.
        camera_width (int): Camera resolution width in pixels.
        camera_height (int): Camera resolution height in pixels.
        pixel_distance (float): Real-world distance per pixel in meters.
        speed_estimation (bool): Whether to enable speed estimation.

    Returns:
        np.ndarray: Frame with detections or tracks drawn.
    """
    # Use the passed speed manager or create a new one if needed (fallback)
    if speed_estimation and speed_manager is None and tracker is not None:
        # Fallback: create a temporary speed manager if not passed
        estimated_fps = 30.0  # Default FPS
        speed_manager = SpeedEstimationManager(pixel_distance=pixel_distance, fps=estimated_fps)

    # Set default target labels to person and car if none provided
    if target_labels is None:
        target_labels = ["person", "car"]

    # Check if person detection is required for loitering
    person_class_index = -1
    if enable_person_only or loitering_detection:
        for idx, label in enumerate(labels):
            if label == "person":
                person_class_index = idx
                break

        # If person detection is required but not found in labels, disable loitering
        if enable_person_only and person_class_index == -1:
            loitering_detection = False

    detections = extract_detections(original_frame, infer_results, config_data, labels, target_labels)  #should return dict with boxes, classes, scores
    frame_with_detections = draw_detections(detections, original_frame, labels,
                                          tracker=tracker, speed_manager=speed_manager,
                                          target_labels=target_labels,
                                          loitering_detection=loitering_detection,
                                          loitering_manager=loitering_manager,
                                          loitering_threshold=loitering_threshold,
                                          enable_person_only=enable_person_only,
                                          person_class_index=person_class_index)
    return frame_with_detections


def draw_detection(image: np.ndarray, box: list, labels: list, score: float, color: tuple, track=False, speed=None):
    """
    Draw box and label for one detection.

    Args:
        image (np.ndarray): Image to draw on.
        box (list): Bounding box coordinates.
        labels (list): List of labels (1 or 2 elements).
        score (float): Detection score.
        color (tuple): Color for the bounding box.
        track (bool): Whether to include tracking info.
        speed (float): Speed in km/h, if available.
    """
    ymin, xmin, ymax, xmax = map(int, box)
    cv2.rectangle(image, (xmin, ymin), (xmax, ymax), color, 2)
    font = cv2.FONT_HERSHEY_SIMPLEX

    # Compose texts
    # Include speed in the top text if available
    if speed is not None:
        top_text = f"{labels[0]}: {score:.1f}% {speed:.1f}km/h" if not track or len(labels) == 2 else f"{score:.1f}% {speed:.1f}km/h"
    else:
        top_text = f"{labels[0]}: {score:.1f}%" if not track or len(labels) == 2 else f"{score:.1f}%"

    bottom_text = None

    if track:
        if len(labels) == 2:
            bottom_text = labels[1]
        else:
            bottom_text = labels[0]

    # Set colors
    text_color = (255, 255, 255)  # white
    border_color = (0, 0, 0)      # black

    # Draw top text with black border first
    cv2.putText(image, top_text, (xmin + 4, ymin + 20), font, 0.5, border_color, 2, cv2.LINE_AA)
    cv2.putText(image, top_text, (xmin + 4, ymin + 20), font, 0.5, text_color, 1, cv2.LINE_AA)

    # Draw bottom text if exists
    if bottom_text:
        pos = (xmax - 50, ymax - 6)
        cv2.putText(image, bottom_text, pos, font, 0.5, border_color, 2, cv2.LINE_AA)
        cv2.putText(image, bottom_text, pos, font, 0.5, text_color, 1, cv2.LINE_AA)


def denormalize_and_rm_pad(box: list, size: int, padding_length: int, input_height: int, input_width: int) -> list:
    """
    Denormalize bounding box coordinates and remove padding.

    Args:
        box (list): Normalized bounding box coordinates.
        size (int): Size to scale the coordinates.
        padding_length (int): Length of padding to remove.
        input_height (int): Height of the input image.
        input_width (int): Width of the input image.

    Returns:
        list: Denormalized bounding box coordinates with padding removed.
    """
    for i, x in enumerate(box):
        box[i] = int(x * size)
        if (input_width != size) and (i % 2 != 0):
            box[i] -= padding_length
        if (input_height != size) and (i % 2 == 0):
            box[i] -= padding_length

    return box


def extract_detections(image: np.ndarray, detections: list, config_data, labels, target_labels=None) -> dict:
    """
    Extract detections from the input data.

    Args:
        image (np.ndarray): Image to draw on.
        detections (list): Raw detections from the model.
        config_data (Dict): Loaded JSON config containing post-processing metadata.
        labels (list): List of class labels.
        target_labels (list): List of class names to detect.

    Returns:
        dict: Filtered detection results containing 'detection_boxes', 'detection_classes', 'detection_scores', and 'num_detections'.
    """

    # Set default target labels to person and car if none provided
    if target_labels is None:
        target_labels = ["person", "car"]

    # Define target class indices based on provided target labels
    target_classes = set(target_labels)
    target_class_indices = set()
    for idx, label in enumerate(labels):
        if label in target_classes:
            target_class_indices.add(idx)

    visualization_params = config_data["visualization_params"]
    score_threshold = visualization_params.get("score_thres", 0.5)
    max_boxes = visualization_params.get("max_boxes_to_draw", 50)


    #values used for scaling coords and removing padding
    img_height, img_width = image.shape[:2]
    size = max(img_height, img_width)
    padding_length = int(abs(img_height - img_width) / 2)

    all_detections = []

    for class_id, detection in enumerate(detections):
        # Only process target class detections (pedestrians and cars)
        if class_id in target_class_indices:
            for det in detection:
                bbox, score = det[:4], det[4]
                if score >= score_threshold:
                    denorm_bbox = denormalize_and_rm_pad(bbox, size, padding_length, img_height, img_width)
                    all_detections.append((score, class_id, denorm_bbox))

    #sort all detections by score descending
    all_detections.sort(reverse=True, key=lambda x: x[0])

    #take top max_boxes (for pedestrians and cars only)
    top_detections = all_detections[:max_boxes]

    scores, class_ids, boxes = zip(*top_detections) if top_detections else ([], [], [])

    return {
        'detection_boxes': list(boxes),
        'detection_classes': list(class_ids),
        'detection_scores': list(scores),
        'num_detections': len(top_detections)
    }


def draw_detections(detections: dict, img_out: np.ndarray, labels, tracker=None, speed_manager=None, target_labels=None,
                    loitering_detection=False, loitering_manager=None, loitering_threshold=10.0, enable_person_only=False, person_class_index=-1):
    """
    Draw detections or tracking results on the image.

    Args:
        detections (dict): Raw detection outputs.
        img_out (np.ndarray): Image to draw on.
        labels (list): List of class labels.
        enable_tracking (bool): Whether to use tracker output (ByteTrack).
        tracker (BYTETracker, optional): ByteTrack tracker instance.
        speed_manager (SpeedEstimationManager, optional): Speed estimation manager for speed calculation.
        target_labels (list): List of class names to detect.

    Returns:
        np.ndarray: Annotated image.
    """

    # Set default target labels to person and car if none provided
    if target_labels is None:
        target_labels = ["person", "car"]

    # Define target class indices based on provided target labels
    target_classes_set = set(target_labels)
    target_class_indices = set()
    for idx, label in enumerate(labels):
        if label in target_classes_set:
            target_class_indices.add(idx)

    #extract detection data from the dictionary
    boxes = detections["detection_boxes"]  # List of [xmin,ymin,xmaxm, ymax] boxes
    scores = detections["detection_scores"]  # List of detection confidences
    num_detections = detections["num_detections"]  # Total number of valid detections
    classes = detections["detection_classes"]  # List of class indices per detection

    # Filter to only include pedestrian and car detections
    target_boxes = []
    target_scores = []
    target_classes_filtered = []

    for i in range(num_detections):
        if classes[i] in target_class_indices:
            target_boxes.append(boxes[i])
            target_scores.append(scores[i])
            target_classes_filtered.append(classes[i])

    # Update the values to only include pedestrians and cars
    boxes = target_boxes
    scores = target_scores
    classes = target_classes_filtered
    num_detections = len(target_boxes)

    if tracker:
        dets_for_tracker = []

        #Convert detection format to [xmin,ymin,xmaxm ymax,score] for tracker
        for idx in range(num_detections):
            box = boxes[idx]  #[x, y, w, h]
            score = scores[idx]
            dets_for_tracker.append([*box, score])

        #skip tracking if no detections passed
        if not dets_for_tracker:
            return img_out

        #run BYTETracker and get active tracks
        online_targets = tracker.update(np.array(dets_for_tracker))

        # Update loitering manager with the current frame count
        if loitering_manager:
            loitering_manager.update_frame_count()

        #draw tracked bounding boxes with ID labels
        current_track_ids = set()
        for track in online_targets:
            track_id = track.track_id  #unique tracker ID
            x1, y1, x2, y2 = track.tlbr  #bounding box (top-left, bottom-right)
            xmin, ymin, xmax, ymax = map(int, [x1, y1, x2, y2])
            best_idx = find_best_matching_detection_index(track.tlbr, boxes)
            if best_idx is not None:  # Only process if we found a matching detection
                current_track_ids.add(track_id)

                # Get original color based on class
                color = tuple(id_to_color(classes[best_idx]).tolist())  # color based on class

                # Check for loitering if enabled and person is detected (if required)
                is_loitering = False
                if loitering_detection:
                    # Check if person detection is required and if this is a person
                    is_person = (person_class_index != -1 and classes[best_idx] == person_class_index)
                    is_relevant = (not enable_person_only or is_person)

                    if is_relevant and loitering_manager:
                        # Update the loitering manager with this track
                        loitering_manager.update_track(track_id)
                        is_loitering = loitering_manager.is_loitering(track_id)

                        # Change color to red if loitering
                        if is_loitering:
                            color = (0, 0, 255)  # Red color for loitering detection

                # Calculate and display speed if speed estimation is enabled
                speed = None
                if speed_manager is not None:
                    bbox = [xmin, ymin, xmax, ymax]
                    speed = speed_manager.estimate_speed(track_id, bbox)

                # Get smoothed speed for display
                display_speed = None
                if speed_manager is not None and speed is not None:
                    smoothed_speed = speed_manager.get_smoothed_speed(track_id)
                    if smoothed_speed is not None:
                        display_speed = smoothed_speed

                # Only draw pedestrian detections with tracking info and speed
                draw_detection(img_out, [xmin, ymin, xmax, ymax], [labels[classes[best_idx]], f"ID {track_id}"],
                               track.score * 100.0, color, track=True, speed=display_speed)

        # Clean up the loitering manager with tracks that are no longer present
        if loitering_manager:
            loitering_manager.cleanup_missing_tracks(current_track_ids)


    else:
        #No tracking — draw raw model detections (only pedestrians and cars)
        for idx in range(num_detections):
            color = tuple(id_to_color(classes[idx]).tolist())  #color based on class
            draw_detection(img_out, boxes[idx], [labels[classes[idx]]], scores[idx] * 100.0, color)

    return img_out


def find_best_matching_detection_index(track_box, detection_boxes):
    """
    Finds the index of the detection box with the highest IoU relative to the given tracking box.

    Args:
        track_box (list or tuple): The tracking box in [x_min, y_min, x_max, y_max] format.
        detection_boxes (list): List of detection boxes in [x_min, y_min, x_max, y_max] format.

    Returns:
        int or None: Index of the best matching detection, or None if no match is found.
    """
    best_iou = 0
    best_idx = -1

    for i, det_box in enumerate(detection_boxes):
        iou = compute_iou(track_box, det_box)
        if iou > best_iou:
            best_iou = iou
            best_idx = i

    return best_idx if best_idx != -1 else None


def compute_iou(boxA, boxB):
    """
    Compute Intersection over Union (IoU) between two bounding boxes.

    IoU measures the overlap between two boxes:
        IoU = (area of intersection) / (area of union)
    Values range from 0 (no overlap) to 1 (perfect overlap).

    Args:
        boxA (list or tuple): [x_min, y_min, x_max, y_max]
        boxB (list or tuple): [x_min, y_min, x_max, y_max]

    Returns:
        float: IoU value between 0 and 1.
    """
    xA, yA = max(boxA[0], boxB[0]), max(boxA[1], boxB[1])
    xB, yB = min(boxA[2], boxB[2]), min(boxA[3], boxB[3])
    inter = max(0, xB - xA) * max(0, yB - yA)
    areaA = max(1e-5, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    areaB = max(1e-5, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))
    return inter / (areaA + areaB - inter + 1e-5)
