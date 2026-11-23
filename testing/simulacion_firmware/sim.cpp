/*
 * sim.cpp — Prueba de software del firmware SCB sin hardware (software-in-the-loop)
 *
 * Compila el MISMO código del firmware contra un Arduino simulado (carpeta
 * mock/) y un "mundo" que imita la bandeja, la balanza, los sensores y la
 * pinza. Sirve para probar la lógica (estados, reintentos, PARO, comandos y
 * formato JSON) antes de tener el robot integrado. NO reemplaza las pruebas
 * físicas del protocolo: no sabe nada de torques, ruido eléctrico ni rozamiento.
 *
 * Uso:
 *   ./sim escenario     -> corre el escenario de prueba y escribe "ms<TAB>json"
 *   ./sim demo          -> residuos al azar en tiempo real por stdin/stdout
 *                          (para probar el gateway y el dashboard sin robot)
 */
#include "Arduino.h"
#include "Servo.h"
#include "HX711.h"
#include "EEPROM.h"
#include "config.h"   // mismos pines que el firmware (no escribirlos a mano aquí)
#include <vector>
#include <functional>
#include <thread>
#include <chrono>
#include <random>
#include <sys/select.h>
#include <unistd.h>

uint64_t sim_us = 0;
SerialSim Serial;
uint8_t sim_eeprom[1024];
EEPROMClass EEPROM;

// --------------------------- Mundo simulado ---------------------------
struct Objeto {
  const char *nombre; float masa; bool metal; bool capDetecta; bool sinEco;
  int fallasAgarre; bool caeEnTraslado; const char *real;
};

// Poses que el escenario calibra con comandos (y que el mundo reconoce)
struct P3 { int b, h, c; };
const P3 BANDEJA = {90, 130, 60};
const int BASE_METAL = 30, BASE_PLASTICO = 60, BASE_DESCARTE = 150;
const int PINZA_CONTACTO = 72;           // ángulo en que los dedos tocan el residuo
const float CUENTAS_POR_G = 400.0;       // factor "real" de la celda simulada
const long OFFSET_REAL = 84210;

bool modoDemo = false;
int ang[16];                             // ángulo por pin
Objeto obj;                              // residuo actual
bool hayObjeto = false, sostenido = false, mano = false;
int fallasRestantes = 0;
float masaCalibracion = 0;
std::mt19937 rng(7);
std::vector<std::string> registroMundo;  // qué pasó físicamente

void mundo(const std::string &s) {
  char b[32]; snprintf(b, sizeof b, "%llu\t", (unsigned long long)(sim_us / 1000));
  registroMundo.push_back(b + s);
  fprintf(stderr, "[mundo %6.1fs] %s\n", sim_us / 1e6, s.c_str());
}

bool brazoEnBandeja() {
  return abs(ang[PIN_SERVO_BASE] - BANDEJA.b) <= 3 && abs(ang[PIN_SERVO_HOMBRO] - BANDEJA.h) <= 3 &&
         abs(ang[PIN_SERVO_CODO] - BANDEJA.c) <= 3;
}

void sim_servo(uint8_t pin, int a) {
  bool estabaEnBandeja = brazoEnBandeja();
  ang[pin] = a;
  // Levantar: el brazo deja la bandeja con la pinza cerrada sobre el residuo
  if ((pin == PIN_SERVO_BASE || pin == PIN_SERVO_HOMBRO || pin == PIN_SERVO_CODO) && hayObjeto && !sostenido &&
      ang[PIN_SERVO_PINZA] <= PINZA_CONTACTO) {
    if (estabaEnBandeja && !brazoEnBandeja()) {
      if (fallasRestantes > 0) { fallasRestantes--; mundo(std::string("se resbalo: ") + obj.nombre + " sigue en la bandeja"); }
      else if (obj.caeEnTraslado) { hayObjeto = false; mundo(std::string("se cayo al levantar: ") + obj.nombre); }
      else { sostenido = true; mundo(std::string("pinza levanta: ") + obj.nombre); }
    }
  }
  // Soltar: la pinza se abre con el residuo tomado
  if (pin == PIN_SERVO_PINZA && sostenido && a > PINZA_CONTACTO + 2) {
    sostenido = false; hayObjeto = false;
    const char *dest = abs(ang[PIN_SERVO_BASE] - BASE_METAL) <= 3 ? "METAL" :
                       abs(ang[PIN_SERVO_BASE] - BASE_PLASTICO) <= 3 ? "PLASTICO" :
                       abs(ang[PIN_SERVO_BASE] - BASE_DESCARTE) <= 3 ? "DESCARTE" : "FUERA";
    mundo(std::string("cae en contenedor ") + dest + ": " + obj.nombre + " (real " + obj.real + ")");
  }
}

float masaBandeja() { return masaCalibracion + ((hayObjeto && !sostenido) ? obj.masa : 0); }

int sim_digitalRead(uint8_t pin) {
  bool enBandeja = hayObjeto && !sostenido;
  if (pin == PIN_INDUCTIVO) return (enBandeja && obj.metal) ? LOW : HIGH;
  if (pin == PIN_CAPACITIVO) return (enBandeja && obj.capDetecta) ? LOW : HIGH;
  return HIGH;
}

int sim_analogRead(uint8_t pin) {
  if (pin != PIN_FSR) return 0;
  int ruido = rng() % 6;
  if (sostenido) return 420 + ruido;
  if (hayObjeto && brazoEnBandeja() && ang[PIN_SERVO_PINZA] <= PINZA_CONTACTO) return (fallasRestantes > 0 ? 60 : 420) + ruido;
  return ruido;
}

unsigned long sim_pulseIn(uint8_t, int, unsigned long timeout) {
  float d;
  if (mano) d = 6.0;
  else if (hayObjeto && !sostenido && obj.sinEco) { sim_avanzar(timeout); return 0; }
  else if (hayObjeto && !sostenido) d = 8.5;
  else d = 17.0;
  d += (rng() % 100) / 200.0;            // ±0,25 cm de ruido
  unsigned long us = (unsigned long)(d * 58);
  sim_avanzar(us + 200);
  return us;
}

uint64_t ultHx = 0;
bool sim_hx_listo() { return sim_us - ultHx >= 100000; }       // 10 SPS
long sim_hx_leer() {
  ultHx = sim_us;
  std::normal_distribution<double> n(0, 0.25);                  // 0,25 g de ruido
  return OFFSET_REAL + (long)((masaBandeja() + n(rng)) * CUENTAS_POR_G);
}

// --------------------------- Entrada serie y guion --------------------
std::deque<char> entrada;
struct Paso { uint64_t ms; std::function<void()> f; };
std::vector<Paso> guion;
size_t idxGuion = 0;

void cmd(uint64_t ms, const char *texto) {
  std::string t = std::string(texto) + "\n";
  guion.push_back({ms, [t] { for (char c : t) entrada.push_back(c); fprintf(stderr, "[cmd   %6.1fs] %s", sim_us / 1e6, t.c_str()); }});
}
void poner(uint64_t ms, Objeto o) {
  guion.push_back({ms, [o] { obj = o; hayObjeto = true; sostenido = false; fallasRestantes = o.fallasAgarre;
                             mundo(std::string("operario deja: ") + o.nombre); }});
}
void retirar(uint64_t ms) {
  guion.push_back({ms, [] { if (hayObjeto) mundo(std::string("operario retira: ") + obj.nombre); hayObjeto = false; sostenido = false; }});
}
void evento(uint64_t ms, std::function<void()> f) { guion.push_back({ms, f}); }

int sim_serial_disponible() {
  if (modoDemo) {                        // comandos reales desde stdin (gateway)
    fd_set s; FD_ZERO(&s); FD_SET(0, &s); timeval tv = {0, 0};
    if (select(1, &s, nullptr, nullptr, &tv) > 0) {
      char b[64]; ssize_t n = ::read(0, b, sizeof b);
      for (ssize_t i = 0; i < n; i++) entrada.push_back(b[i]);
    }
  }
  return (int)entrada.size();
}
int sim_serial_leer() { if (entrada.empty()) return -1; char c = entrada.front(); entrada.pop_front(); return c; }

// --------------------------- Demo con residuos al azar ----------------
const Objeto CATALOGO[] = {
  {"lata de aluminio", 14.5, true,  true,  false, 0, false, "METAL"},
  {"lata de conserva", 52.0, true,  true,  false, 0, false, "METAL"},
  {"tapa metalica",     6.0, true,  true,  false, 0, false, "METAL"},
  {"botella PET",      23.0, false, true,  false, 0, false, "PLASTICO"},
  {"vaso plastico",     7.5, false, true,  false, 0, false, "PLASTICO"},
  {"envase de yogur",   9.0, false, true,  false, 1, false, "PLASTICO"},
  {"papel arrugado",    6.5, false, false, true,  0, false, "DESCARTE"},
  {"carton",           18.0, false, false, false, 0, false, "DESCARTE"},
  {"bolsa plastica",    4.0, false, false, true,  0, false, "PLASTICO"},   // caso difícil
  {"trozo de madera",  35.0, false, true,  false, 0, false, "DESCARTE"},   // el capacitivo se confunde
};
uint64_t proximaLlegada = 8000, tieneDesde = 0;
void demoMundo() {
  uint64_t ms = sim_us / 1000;
  if (hayObjeto && !sostenido) {
    if (!tieneDesde) tieneDesde = ms;
    if (ms - tieneDesde > 25000) { mundo("operario retira lo que quedo en la bandeja"); hayObjeto = false; }
  } else tieneDesde = 0;
  if (!hayObjeto && ms >= proximaLlegada) {
    Objeto o = CATALOGO[rng() % (sizeof CATALOGO / sizeof CATALOGO[0])];
    if (rng() % 25 == 0) o.masa = 180;   // de vez en cuando algo pesado
    obj = o; hayObjeto = true; fallasRestantes = o.fallasAgarre;
    mundo(std::string("operario deja: ") + o.nombre);
    proximaLlegada = ms + 14000 + rng() % 12000;
  }
}

// --------------------------- Reloj virtual ----------------------------
bool tiempoReal = false;
uint64_t inicioReal = 0;
void sim_avanzar(uint64_t us) {
  sim_us += us;
  while (idxGuion < guion.size() && guion[idxGuion].ms * 1000 <= sim_us) guion[idxGuion++].f();
  if (modoDemo) demoMundo();
  if (tiempoReal && (sim_us & 0x3FFF) < us) {   // cada ~16 ms sincroniza con el reloj
    using namespace std::chrono;
    uint64_t real = duration_cast<microseconds>(steady_clock::now().time_since_epoch()).count() - inicioReal;
    if (sim_us > real) std::this_thread::sleep_for(microseconds(sim_us - real));
  }
}

void sim_salida(const std::string &s) {
  if (modoDemo) { printf("%s\n", s.c_str()); fflush(stdout); }
  else printf("%llu\t%s\n", (unsigned long long)(sim_us / 1000), s.c_str());
}

// --------------------------- Firmware ---------------------------------
#include "garra_scb_iot.ino.cpp"   // lo genera compilar.sh

// --------------------------- Escenario de prueba ----------------------
void armarEscenario() {
  uint64_t t = 4000;
  auto c = [&](const char *s) { cmd(t, s); t += 2500; };
  // 1) Calibración por comandos (sistema SIN_CALIBRAR al primer encendido)
  c("AYUDA");
  c("SEGUIR");                           // debe rechazarse: faltan poses
  c("MOVER H 100"); c("MOVER C 80"); c("GUARDAR REPOSO");
  c("MOVER H 110"); c("MOVER C 70"); c("GUARDAR SOBRE");
  c("MOVER H 130"); c("MOVER C 60"); c("GUARDAR BANDEJA");
  c("MOVER P 100"); c("GUARDAR ABIERTA");
  c("MOVER P 50");  c("GUARDAR CERRADA");
  c("MOVER P 100");
  c("MOVER H 110"); c("MOVER C 80"); c("MOVER B 30"); c("GUARDAR METAL");
  c("MOVER B 60");  c("GUARDAR PLASTICO");
  c("MOVER B 150"); c("GUARDAR DESCARTE");
  c("IR REPOSO");
  // 2) Calibración de la balanza con una masa patrón de 100 g
  c("TARA");
  evento(t, [] { masaCalibracion = 100; mundo("operario pone masa patron de 100 g"); }); t += 2000;
  c("CAL 100");
  evento(t, [] { masaCalibracion = 0; mundo("operario retira masa patron"); }); t += 3000;
  c("SEGUIR");
  c("ESTADO");
  c("XYZ");                              // comando desconocido
  t += 3000;

  // 3) Residuos
  poner(t, {"lata de aluminio", 14.5, true, true, false, 0, false, "METAL"});         t += 25000;
  poner(t, {"botella PET", 23.0, false, true, false, 0, false, "PLASTICO"});          t += 25000;
  poner(t, {"papel arrugado", 6.5, false, false, true, 0, false, "DESCARTE"});         t += 25000;
  poner(t, {"envase resbaloso", 9.0, false, true, false, 1, false, "PLASTICO"});       t += 32000;
  poner(t, {"frasco pesado", 250.0, false, true, false, 0, false, "DESCARTE"});        t += 8000;
  retirar(t);                                                                         t += 8000;
  evento(t, [] { mano = true; mundo("mano pasa sobre la bandeja"); });                t += 1000;
  evento(t, [] { mano = false; });                                                    t += 8000;
  poner(t, {"objeto imposible", 20.0, false, false, false, 99, false, "DESCARTE"});    t += 35000;
  retirar(t);                                                                         t += 8000;
  poner(t, {"tapa que se cae", 6.0, true, true, false, 0, true, "METAL"});             t += 25000;
  // 4) PARO en medio de un ciclo y recuperación
  poner(t, {"lata para paro", 14.0, true, true, false, 0, false, "METAL"});            t += 5500;
  cmd(t, "PARO");                                                                     t += 4000;
  cmd(t, "TARA");                        // debe rechazarse: está PARADO
  t += 3000;
  evento(t, [] { if (hayObjeto) mundo("operario saca el residuo de la pinza"); hayObjeto = false; sostenido = false; });
  t += 2000;
  cmd(t, "SEGUIR");                                                                   t += 12000;
  // 5) PAUSA pedida durante un ciclo: se pausa al terminar
  poner(t, {"vaso plastico", 7.5, false, true, false, 0, false, "PLASTICO"});          t += 4000;
  cmd(t, "PAUSA");                                                                    t += 20000;
  poner(t, {"carton", 18.0, false, false, false, 0, false, "DESCARTE"});               t += 8000;  // no debe moverse
  retirar(t);                                                                         t += 2000;
  cmd(t, "SEGUIR");                                                                   t += 5000;
  guion.push_back({t, [] {}});
}

int main(int argc, char **argv) {
  std::string modo = argc > 1 ? argv[1] : "escenario";
  memset(sim_eeprom, 0xFF, sizeof sim_eeprom);
  for (int &a : ang) a = 90;
  if (modo == "demo") {
    modoDemo = tiempoReal = true;
    rng.seed((unsigned)time(nullptr));
    // EEPROM ya calibrada: parte directo en ESPERANDO
    Config c; c.magic = CONFIG_MAGIC; c.factor = CUENTAS_POR_G;
    c.poses[P_REPOSO] = {90, 100, 80}; c.poses[P_SOBRE] = {90, 110, 70}; c.poses[P_BANDEJA] = {90, 130, 60};
    c.poses[P_METAL] = {30, 110, 80}; c.poses[P_PLASTICO] = {60, 110, 80}; c.poses[P_DESCARTE] = {150, 110, 80};
    c.pinzaAbierta = 100; c.pinzaCerrada = 50; c.guardadas = 0xFF; c.umbralFsr = 150;
    memcpy(sim_eeprom, &c, sizeof c);
    using namespace std::chrono;
    inicioReal = duration_cast<microseconds>(steady_clock::now().time_since_epoch()).count();
  } else {
    armarEscenario();
  }
  uint64_t fin = modoDemo ? UINT64_MAX : guion.back().ms * 1000;
  setup();
  while (sim_us < fin) loop();
  if (!modoDemo) {
    FILE *f = fopen("registro_mundo.tsv", "w");
    for (auto &l : registroMundo) fprintf(f, "%s\n", l.c_str());
    fclose(f);
  }
  return 0;
}
