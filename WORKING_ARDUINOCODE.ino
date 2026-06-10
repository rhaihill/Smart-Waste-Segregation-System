/*
  Smart Bin Integrated System
  Stepper Motor + Servo Holding Compartment
*/

#include <Servo.h>

// =========================
// STEPPER MOTOR PINS
// =========================
const int INA1 = 7;
const int INB1 = 8;
const int PWM1 = 5;

const int INA2 = 4;
const int INB2 = 9;
const int PWM2 = 6;

// =========================
// SERVO MOTOR
// =========================
Servo gateServo;

const int SERVO_PIN = 3;

// Adjust these based on your actual gate alignment
const int SERVO_CLOSED = 25;
const int SERVO_OPEN = 115;

// =========================
// MOTOR SETTINGS
// =========================
const int STEP_DELAY_MS = 25;
const int PWM_MOVE = 220;

// Calibrated angles
const int STEPS_BIO = 100;        // about 120 degrees
const int STEPS_RESIDUAL = 300;   // about 240 degrees

// Timing
const int HOLD_OPEN_TIME_MS = 3000;
const int WAIT_NEXT_WASTE_MS = 3000;

int currentHalfStep = 0;

// Half-step sequence
const int halfStepSeq[8][4] = {
  {HIGH, LOW,  HIGH, LOW },
  {HIGH, LOW,  LOW,  LOW },
  {HIGH, LOW,  LOW,  HIGH},
  {LOW,  LOW,  LOW,  HIGH},
  {LOW,  HIGH, LOW,  HIGH},
  {LOW,  HIGH, LOW,  LOW },
  {LOW,  HIGH, HIGH, LOW },
  {LOW,  LOW,  HIGH, LOW }
};

void setup() {
  Serial.begin(9600);

  pinMode(INA1, OUTPUT);
  pinMode(INB1, OUTPUT);
  pinMode(PWM1, OUTPUT);

  pinMode(INA2, OUTPUT);
  pinMode(INB2, OUTPUT);
  pinMode(PWM2, OUTPUT);

  gateServo.attach(SERVO_PIN);
  gateServo.write(SERVO_CLOSED);

  stopMotor();

  Serial.println("Smart Bin Arduino Ready");
  Serial.println("Waiting for command: R, B, or X");

  delay(2000);
}

// =========================
// STEPPER FUNCTIONS
// =========================

void applyHalfStep(int stepIndex) {
  int s = ((stepIndex % 8) + 8) % 8;

  digitalWrite(INA1, halfStepSeq[s][0]);
  digitalWrite(INB1, halfStepSeq[s][1]);
  digitalWrite(INA2, halfStepSeq[s][2]);
  digitalWrite(INB2, halfStepSeq[s][3]);
}

void stepMotor(int steps, bool clockwise) {
  analogWrite(PWM1, PWM_MOVE);
  analogWrite(PWM2, PWM_MOVE);

  for (int i = 0; i < steps; i++) {
    if (clockwise) {
      currentHalfStep++;
      if (currentHalfStep > 7) currentHalfStep = 0;
    } else {
      currentHalfStep--;
      if (currentHalfStep < 0) currentHalfStep = 7;
    }

    applyHalfStep(currentHalfStep);
    delay(STEP_DELAY_MS);
  }
}

void stopMotor() {
  digitalWrite(INA1, LOW);
  digitalWrite(INB1, LOW);
  digitalWrite(INA2, LOW);
  digitalWrite(INB2, LOW);
}

// =========================
// SERVO FUNCTIONS
// =========================

void openHoldingCompartment() {
  Serial.println("Holding compartment OPEN");
  gateServo.write(SERVO_OPEN);
  delay(HOLD_OPEN_TIME_MS);
}

void closeHoldingCompartment() {
  Serial.println("Holding compartment CLOSED");
  gateServo.write(SERVO_CLOSED);
  delay(700);
}

// =========================
// SORTING FUNCTIONS
// =========================

void goRecyclable() {
  Serial.println("RECYCLABLE selected");
  Serial.println("No stepper rotation needed");

  openHoldingCompartment();
  closeHoldingCompartment();

  delay(WAIT_NEXT_WASTE_MS);

  Serial.println("DONE");
}

void goBiodegradable() {
  Serial.println("BIODEGRADABLE selected");

  Serial.println("Rotating to BIO position");
  stepMotor(STEPS_BIO, true);
  stopMotor();

  Serial.println("BIO reached");

  openHoldingCompartment();
  closeHoldingCompartment();

  Serial.println("Returning HOME");
  stepMotor(STEPS_BIO, false);
  stopMotor();

  delay(WAIT_NEXT_WASTE_MS);

  Serial.println("DONE");
}

void goResidual() {
  Serial.println("RESIDUAL selected");

  Serial.println("Rotating to RESIDUAL position");
  stepMotor(STEPS_RESIDUAL, true);
  stopMotor();

  Serial.println("RESIDUAL reached");

  openHoldingCompartment();
  closeHoldingCompartment();

  Serial.println("Returning HOME");
  stepMotor(STEPS_RESIDUAL, false);
  stopMotor();

  delay(WAIT_NEXT_WASTE_MS);

  Serial.println("DONE");
}

// =========================
// MAIN LOOP
// =========================

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();

    Serial.print("Received command: ");
    Serial.println(command);

    if (command == 'R') {
      goRecyclable();
    } 
    else if (command == 'B') {
      goBiodegradable();
    } 
    else if (command == 'X') {
      goResidual();
    } 
    else {
      Serial.println("Unknown command");
    }
  }
}