#pragma once
#include "Arduino.h"
bool sim_hx_listo();
long sim_hx_leer();
class HX711 {
 public:
  void begin(uint8_t, uint8_t) {}
  bool is_ready() { return sim_hx_listo(); }
  long read() { while (!sim_hx_listo()) sim_avanzar(1000); return sim_hx_leer(); }
};
