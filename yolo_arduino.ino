/* Sweep
 by BARRAGAN <http://barraganstudio.com>
 This example code is in the public domain.

 modified 8 Nov 2013
 by Scott Fitzgerald
 https://www.arduino.cc/en/Tutorial/LibraryExamples/Sweep
*/

#include <Servo.h>

Servo myservo;  // create Servo object to control a servo
// twelve Servo objects can be created on most boards

int pos = 90;  // variable to store the servo position
int status = 1;
int finalpos[3] = {35, 60, 95};

void setup() {
  Serial.begin(9600);
  myservo.attach(9);  // attaches the servo on pin 9 to the Servo object
}

void loop() {
  
  if (Serial.available() > 0) {
    char incomingByte = Serial.read();
    Serial.print("Received: ");
    Serial.println(incomingByte);
    if ((incomingByte - '0') >= 0 && (incomingByte - '0') <= 2) {
      status = incomingByte - '0';
      Serial.println(status);
    }
  }

  if (pos != finalpos[status]) {
    if (status != 1) {
      pos += status - 1;
    }
    else {
      if (pos < finalpos[1]) {
        pos += 1;
      }
      else if (pos > finalpos[1]) {
        pos -= 1;
      }
    }
    myservo.write(pos);
    delay(15);
  }

}
