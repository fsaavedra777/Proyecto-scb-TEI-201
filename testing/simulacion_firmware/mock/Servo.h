#pragma once
#include "Arduino.h"
void sim_servo(uint8_t pin, int ang);
class Servo {
  uint8_t pin = 255; int ang = 90;
 public:
  void attach(uint8_t p) { pin = p; sim_servo(pin, ang); }
  void write(int a) { ang = a; if (pin != 255) sim_servo(pin, ang); }
  int read() { return ang; }
};
