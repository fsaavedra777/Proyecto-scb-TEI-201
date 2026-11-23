#pragma once
#include "Arduino.h"
extern uint8_t sim_eeprom[1024];
struct EEPROMClass {
  template <class T> T &get(int a, T &t) { memcpy(&t, sim_eeprom + a, sizeof(T)); return t; }
  template <class T> const T &put(int a, const T &t) { memcpy(sim_eeprom + a, &t, sizeof(T)); return t; }
};
extern EEPROMClass EEPROM;
