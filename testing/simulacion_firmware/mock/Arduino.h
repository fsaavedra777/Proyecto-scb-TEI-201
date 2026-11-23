// Arduino.h simulado: corre el firmware en un PC, con tiempo virtual.
#pragma once
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <cctype>
#include <cmath>
#include <string>
#include <deque>
using std::isnan; using std::isinf;

typedef uint8_t byte;
typedef bool boolean;
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define A0 14
#define A1 15
#define A2 16
#define DEC 10

class __FlashStringHelper;
#define F(s) (reinterpret_cast<const __FlashStringHelper *>(s))
#define PSTR(s) (s)
#define strcmp_P strcmp

template <class T, class L, class H> T constrain(T x, L lo, H hi) { return x < lo ? (T)lo : (x > hi ? (T)hi : x); }
template <class A, class B> auto max(A a, B b) -> decltype(a + b) { return a > b ? a : b; }
template <class A, class B> auto min(A a, B b) -> decltype(a + b) { return a < b ? a : b; }

// ---- Hooks implementados por el "mundo" (sim.cpp) ----
extern uint64_t sim_us;                       // tiempo virtual en microsegundos
void sim_avanzar(uint64_t us);
int  sim_digitalRead(uint8_t pin);
int  sim_analogRead(uint8_t pin);
unsigned long sim_pulseIn(uint8_t pin, int state, unsigned long timeout);
void sim_salida(const std::string &s);
int  sim_serial_disponible();
int  sim_serial_leer();

inline unsigned long millis() { sim_avanzar(20); return (unsigned long)(sim_us / 1000); }
inline unsigned long micros() { sim_avanzar(5); return (unsigned long)sim_us; }
inline void delay(unsigned long ms) { sim_avanzar((uint64_t)ms * 1000); }
inline void delayMicroseconds(unsigned int us) { sim_avanzar(us); }
inline void pinMode(uint8_t, uint8_t) {}
inline void digitalWrite(uint8_t, uint8_t) { sim_avanzar(4); }
inline int digitalRead(uint8_t p) { sim_avanzar(4); return sim_digitalRead(p); }
inline int analogRead(uint8_t p) { sim_avanzar(110); return sim_analogRead(p); }
inline unsigned long pulseIn(uint8_t p, int s, unsigned long t) { return sim_pulseIn(p, s, t); }

class SerialSim {
  std::string buf;
  void out(const std::string &s) {
    sim_avanzar((uint64_t)s.size() * 87);      // 115200 baudios ~ 87 us por byte
    for (char c : s) { if (c == '\n') { sim_salida(buf); buf.clear(); } else if (c != '\r') buf += c; }
  }
 public:
  void begin(long) {}
  int available() { return sim_serial_disponible(); }
  int read() { return sim_serial_leer(); }
  void print(const __FlashStringHelper *s) { out((const char *)s); }
  void print(const char *s) { out(s); }
  void print(char c) { out(std::string(1, c)); }
  void print(int v) { out(std::to_string(v)); }
  void print(unsigned int v) { out(std::to_string(v)); }
  void print(long v) { out(std::to_string(v)); }
  void print(unsigned long v) { out(std::to_string(v)); }
  void print(unsigned char v) { out(std::to_string((int)v)); }
  void print(bool v) { out(std::to_string((int)v)); }
  void print(double v, int d = 2) {
    if (std::isnan(v)) { out("nan"); return; }
    char b[48]; snprintf(b, sizeof b, "%.*f", d, v); out(b);
  }
  template <class T> void println(T v) { print(v); out("\n"); }
  void println() { out("\n"); }
};
extern SerialSim Serial;
