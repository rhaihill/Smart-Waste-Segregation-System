import cv2
from ultralytics import YOLO

model = YOLO(r"C:\Users\Clarisse\OneDrive\Documents\COLLEGE (UPD)\4th Year\197\YOLO-Garbage-Detection-main\bestv2.pt")

cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    results = model(frame, stream=True)

    for r in results:
        annotated_frame = r.plot()

    cv2.imshow("YOLO Webcam Inference", annotated_frame)

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

