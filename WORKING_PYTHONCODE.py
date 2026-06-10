import pathlib
pathlib.PosixPath = pathlib.WindowsPath

import cv2
import serial
import time
from collections import Counter
from ultralytics import YOLO

# ============================================
# ARDUINO SERIAL PORT
# ============================================

arduino = serial.Serial('COM10', 9600, timeout=1)

time.sleep(2)

# ============================================
# LOAD YOLO MODEL
# ============================================

model = YOLO(r"bestv2.pt")

# ============================================
# CAMERA
# ============================================

cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

print("====================================")
print("SMART BIN SYSTEM STARTED")
print("Press Q to quit")
print("====================================")

# ============================================
# SYSTEM STATES
# ============================================

STATE_WAITING = "WAITING"
STATE_DETECTING = "DETECTING"
STATE_SORTING = "SORTING"

current_state = STATE_WAITING

# ============================================
# DETECTION SETTINGS
# ============================================

DETECTION_WINDOW = 5

detection_start = None

detections_list = []

MIN_CONFIDENCE = 0.6

# ============================================
# SORTING TIMERS
# ============================================

RECYCLABLE_TOTAL_TIME = 7
BIO_TOTAL_TIME = 12
RESIDUAL_TOTAL_TIME = 22

sort_start = None
sort_duration = 0

current_command = None
target_angle = 0

# ============================================
# SEND COMMAND TO ARDUINO
# ============================================

def send_command(command):

    arduino.write(command.encode())

    arduino.flush()

    print(f"\nSent to Arduino: {command}")

# ============================================
# ESTIMATED STEPPER ANGLE
# ============================================

def get_estimated_angle(command, elapsed):

    if command == 'B':

        target = 120

        rotate_time = 2.5
        hold_time = 3
        return_time = 2.5

    elif command == 'X':

        target = 240

        rotate_time = 7.5
        hold_time = 3
        return_time = 7.5

    else:

        return 0

    # ROTATING TO TARGET
    if elapsed <= rotate_time:

        angle = (elapsed / rotate_time) * target

    # HOLDING POSITION
    elif elapsed <= rotate_time + hold_time:

        angle = target

    # RETURNING HOME
    elif elapsed <= rotate_time + hold_time + return_time:

        return_elapsed = elapsed - rotate_time - hold_time

        angle = target - (
            (return_elapsed / return_time) * target
        )

    else:

        angle = 0

    return max(0, min(target, angle))

# ============================================
# SORTING PHASE DISPLAY
# ============================================

def get_sorting_phase(command, elapsed):

    if command == 'R':

        if elapsed <= 3:
            return "Holding compartment OPEN"

        elif elapsed <= 7:
            return "Waiting before next detection"

        else:
            return "Done"

    elif command == 'B':

        if elapsed <= 2.5:
            return "Rotating to BIO"

        elif elapsed <= 5.5:
            return "Holding compartment OPEN"

        elif elapsed <= 8:
            return "Returning HOME"

        elif elapsed <= 12:
            return "Waiting before next detection"

        else:
            return "Done"

    elif command == 'X':

        if elapsed <= 7.5:
            return "Rotating to RESIDUAL"

        elif elapsed <= 10.5:
            return "Holding compartment OPEN"

        elif elapsed <= 18:
            return "Returning HOME"

        elif elapsed <= 22:
            return "Waiting before next detection"

        else:
            return "Done"

    return "Unknown"

# ============================================
# MAIN LOOP
# ============================================

while True:

    ret, frame = cap.read()

    if not ret:

        print("Failed to grab frame")

        break

    results = model(frame, stream=True)

    detected_label = None
    highest_conf = 0

    annotated_frame = frame.copy()

    # ========================================
    # YOLO DETECTION
    # ========================================

    for r in results:

        annotated_frame = r.plot()

        for box in r.boxes:

            conf = float(box.conf[0])

            class_id = int(box.cls[0])

            label = model.names[class_id].lower()

            if conf > highest_conf and conf > MIN_CONFIDENCE:

                highest_conf = conf
                detected_label = label

    # ========================================
    # WAITING STATE
    # ========================================

    if current_state == STATE_WAITING:

        cv2.putText(
            annotated_frame,
            "STATUS: WAITING FOR WASTE",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        cv2.putText(
            annotated_frame,
            "Stepper Angle: 0 deg",
            (10, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        if detected_label:

            print("\nWaste detected.")
            print("Starting 5 second assessment...")

            current_state = STATE_DETECTING

            detection_start = time.time()

            detections_list = []

    # ========================================
    # DETECTING STATE
    # ========================================

    elif current_state == STATE_DETECTING:

        elapsed = time.time() - detection_start

        remaining = DETECTION_WINDOW - elapsed

        if detected_label:

            detections_list.append(detected_label)

        cv2.putText(
            annotated_frame,
            "STATUS: DETECTING WASTE",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2
        )

        cv2.putText(
            annotated_frame,
            f"Detection Timer: {max(0, remaining):.1f}s",
            (10, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        if detected_label:

            cv2.putText(
                annotated_frame,
                f"Seeing: {detected_label} ({highest_conf:.0%})",
                (10, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 0),
                2
            )

        # ====================================
        # END OF DETECTION WINDOW
        # ====================================

        if elapsed >= DETECTION_WINDOW:

            if detections_list:

                vote_counts = Counter(detections_list)

                final_label = vote_counts.most_common(1)[0][0]

                total_votes = sum(vote_counts.values())

                print("\nVoting Results:")
                print(dict(vote_counts))

                print(
                    f"Final Decision: {final_label} "
                    f"({vote_counts[final_label]}/{total_votes} votes)"
                )

                # ====================================
                # CLASSIFICATION DECISION
                # ====================================

                if 'recyclable' in final_label:

                    current_command = 'R'

                    sort_duration = RECYCLABLE_TOTAL_TIME

                    target_angle = 0

                elif (
                    'biodegradable' in final_label
                    or
                    'bio' in final_label
                ):

                    current_command = 'B'

                    sort_duration = BIO_TOTAL_TIME

                    target_angle = 120

                elif 'residual' in final_label:

                    current_command = 'X'

                    sort_duration = RESIDUAL_TOTAL_TIME

                    target_angle = 240

                else:

                    current_command = None

                # ====================================
                # SEND COMMAND
                # ====================================

                if current_command:

                    send_command(current_command)

                    sort_start = time.time()

                    current_state = STATE_SORTING

                else:

                    print("Unknown waste class.")

                    current_state = STATE_WAITING

            else:

                print("No confident detection.")

                current_state = STATE_WAITING

    # ========================================
    # SORTING STATE
    # ========================================

    elif current_state == STATE_SORTING:

        elapsed_sort = time.time() - sort_start

        remaining_sort = sort_duration - elapsed_sort

        estimated_angle = get_estimated_angle(
            current_command,
            elapsed_sort
        )

        phase = get_sorting_phase(
            current_command,
            elapsed_sort
        )

        cv2.putText(
            annotated_frame,
            "STATUS: SORTING WASTE",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )

        cv2.putText(
            annotated_frame,
            f"Phase: {phase}",
            (10, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        cv2.putText(
            annotated_frame,
            f"Target Angle: {target_angle} deg",
            (10, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        cv2.putText(
            annotated_frame,
            f"Current Angle: {estimated_angle:.1f} deg",
            (10, 135),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        cv2.putText(
            annotated_frame,
            f"Time Left: {max(0, remaining_sort):.1f}s",
            (10, 170),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        if elapsed_sort >= sort_duration:

            print("\nSorting complete.")
            print("Ready for next waste.")

            current_state = STATE_WAITING

            sort_start = None

            current_command = None

            sort_duration = 0

            target_angle = 0

    # ========================================
    # SHOW CAMERA WINDOW
    # ========================================

    cv2.putText(
        annotated_frame,
        f"System State: {current_state}",
        (10, frame.shape[0] - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )

    cv2.imshow("Smart Bin", annotated_frame)

    # ========================================
    # QUIT
    # ========================================

    if cv2.waitKey(1) & 0xFF == ord('q'):

        break

# ============================================
# CLEANUP
# ============================================

cap.release()

cv2.destroyAllWindows()

arduino.close()