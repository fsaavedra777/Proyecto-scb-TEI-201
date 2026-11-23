/*
 * =============================================================================
 *  PROYECTO SCB — Sistema Clasificador de Basura (Avance 3: prototipo IoT)
 *  TEI201 Taller de Diseño en Ingeniería · Universidad Adolfo Ibáñez
 *  Equipo: Facundo Saavedra, Matías Jara, Martín Olivares
 * =============================================================================
 *
 *  CICLO DE DATOS
 *    1. Captura: el HC-SR04 (10 Hz) y la celda de carga detectan un residuo.
 *    2. Análisis: se pesa (HX711) y se muestrea el inductivo y el capacitivo.
 *    3. Decisión: METAL si lo ve el inductivo; PLÁSTICO si lo ve el capacitivo
 *       y pesa poco; si no, DESCARTE.
 *    4. Acción: la garra lo toma (el FSR y la balanza confirman el agarre) y
 *       lo deja en su contenedor.
 *    5. Comunicación: cada 500 ms se envía una línea JSON de telemetría y, al
 *       terminar cada ciclo, una línea JSON con el evento. El programa
 *       gateway/gateway.py las guarda en una base SQLite y el dashboard las
 *       convierte en indicadores y alertas.
 *
 *  ARCHIVOS (pestañas del IDE)
 *    config.h          pines, umbrales y tiempos
 *    prototipos.h      índice de funciones por pestaña
 *    garra_scb_iot     variables globales, setup() y la máquina de estados
 *    brazo.ino         movimiento suave de servos y agarre con FSR
 *    comunicacion.ino  JSON de salida y comandos de entrada
 *    memoria.ino       configuración en EEPROM (poses y calibración)
 *    sensores.ino      ultrasónico, balanza, inductivo, capacitivo y FSR
 *
 *  Librerías: Servo (Arduino) y HX711 de Bogdan Necula (Gestor de librerías).
 *  Monitor Serie / gateway: 115200 baudios. Escriban AYUDA para ver comandos.
 * =============================================================================
 */

#include <Servo.h>
#include <EEPROM.h>
#include "HX711.h"
#include "config.h"
#include "prototipos.h"

// ---------------------------- Hardware ----------------------------
HX711 balanza;
Servo servos[4];                       // 0 base, 1 hombro, 2 codo, 3 pinza
const uint8_t PIN_SERVOS[4] = {PIN_SERVO_BASE, PIN_SERVO_HOMBRO, PIN_SERVO_CODO, PIN_SERVO_PINZA};
uint8_t angulo[4] = {90, 90, 90, 90};  // ángulo actual de cada servo

// ---------------------------- Configuración -----------------------
Config cfg;                            // se carga de la EEPROM en setup()
long offsetBalanza = 0;                // tara (se hace al encender)

// ---------------------------- Estado del sistema ------------------
Estado estado = INICIANDO;
bool pausaPedida = false;              // PAUSA llegó en medio de un ciclo
bool paro = false;                     // PARO de emergencia
bool ocupado = false;                  // hay un movimiento en curso

// ---------------------------- Últimas lecturas --------------------
float distanciaCm = -1;                // -1 = sin eco
float pesoG = 0;                       // promedio móvil corto
float pesoCrudoG = 0;                  // última lectura individual
uint16_t lecturasBalanza = 0;          // contador de lecturas nuevas
bool inductivoAhora = false;
bool capacitivoAhora = false;
int fsrAhora = 0;

// ---------------------------- Datos del ciclo en curso ------------
struct Ciclo {
  uint16_t numero;                     // correlativo desde el encendido
  unsigned long tDeteccion;            // millis() al confirmar la llegada
  unsigned long latenciaMs;            // detección -> material decidido
  float peso;
  uint8_t pctInductivo, pctCapacitivo;
  int fsrMax;
  uint8_t intentos;
  Material material;
  char via;                            // 'U' ultrasónico, 'P' por masa
} ciclo;

uint8_t confirmacionesUS = 0;
uint8_t confirmacionesPeso = 0;
unsigned long tUltUltrasonico = 0;

// =============================================================================
void setup() {
  Serial.begin(115200);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  pinMode(PIN_INDUCTIVO, INPUT_PULLUP);    // el diodo solo deja tirar a LOW
  pinMode(PIN_CAPACITIVO, INPUT_PULLUP);
  pinMode(PIN_LED, OUTPUT);

  cargarConfig();
  iniciarServos();                         // parten en REPOSO (o 90° si no hay poses)

  balanza.begin(PIN_HX_DT, PIN_HX_SCK);
  logMsg(F("Iniciando. La bandeja debe estar VACIA para la tara."));
  esperar(1500);                           // deja estabilizar la celda
  hacerTara();

  enviarConfig();
  if (cfg.guardadas == TODO_GUARDADO) {
    cambiarEstado(ESPERANDO);
    logMsg(F("Listo. Esperando residuo."));
  } else {
    cambiarEstado(SIN_CALIBRAR);
    logMsg(F("Faltan poses por calibrar. Escriba AYUDA."));
  }
}

// =============================================================================
void loop() {
  servicio();   // telemetría, comandos y balanza: siempre corriendo

  switch (estado) {
    case ESPERANDO:     estadoEsperando();   break;
    case ANALIZANDO:    estadoAnalizando();  break;
    case RECOGIENDO:    estadoRecogiendo();  break;
    case DEPOSITANDO:   estadoDepositando(); break;
    case RETIRO_MANUAL: estadoRetiro();      break;
    default: break;     // SIN_CALIBRAR, PAUSADO y PARADO solo atienden comandos
  }
}

// -----------------------------------------------------------------------------
// ESPERANDO: vigila la bandeja con el ultrasónico (y la masa como respaldo)
// -----------------------------------------------------------------------------
void estadoEsperando() {
  if (pausaPedida) { pausaPedida = false; cambiarEstado(PAUSADO); return; }
  if (millis() - tUltUltrasonico < PERIODO_ULTRASONICO_MS) return;
  tUltUltrasonico = millis();

  distanciaCm = medirDistanciaCm();
  bool cerca = (distanciaCm > 0 && distanciaCm < DIST_OBJETO_CM);
  confirmacionesUS   = cerca ? confirmacionesUS + 1 : 0;
  // Respaldo por masa: bolsas o papel arrugado a veces no devuelven eco
  confirmacionesPeso = (pesoG > PESO_MIN_G) ? confirmacionesPeso + 1 : 0;

  if (confirmacionesUS >= LECTURAS_CONFIRMACION || confirmacionesPeso >= LECTURAS_CONFIRMACION_PESO) {
    memset(&ciclo, 0, sizeof(ciclo));
    static uint16_t contadorCiclos = 0;
    ciclo.numero = ++contadorCiclos;
    ciclo.tDeteccion = millis();
    ciclo.via = (confirmacionesUS >= LECTURAS_CONFIRMACION) ? 'U' : 'P';
    ciclo.material = NINGUNO;
    confirmacionesUS = confirmacionesPeso = 0;
    cambiarEstado(ANALIZANDO);
  }
}

// -----------------------------------------------------------------------------
// ANALIZANDO: pesa, muestrea los sensores de material y decide
// -----------------------------------------------------------------------------
void estadoAnalizando() {
  if (!esperar(300)) return;                  // que el objeto deje de moverse
  ciclo.peso = pesoEstable(LECTURAS_PESO_ESTABLE);

  if (ciclo.peso < PESO_MIN_G) {              // era una mano o ruido
    enviarEvento(F("FALSA_DETECCION"));
    esperarBandejaLibre();
    cambiarEstado(ESPERANDO);
    return;
  }
  if (ciclo.peso > PESO_MAX_G) {
    enviarEvento(F("SOBREPESO"));
    logMsg(F("Residuo demasiado pesado. Retirelo a mano."));
    cambiarEstado(RETIRO_MANUAL);
    return;
  }

  muestrearMaterial(ciclo.pctInductivo, ciclo.pctCapacitivo);
  ciclo.material = decidirMaterial(ciclo.pctInductivo, ciclo.pctCapacitivo, ciclo.peso);
  ciclo.latenciaMs = millis() - ciclo.tDeteccion;
  cambiarEstado(RECOGIENDO);
}

// Regla de decisión. El inductivo manda: el capacitivo también "ve" el metal.
Material decidirMaterial(uint8_t pctInd, uint8_t pctCap, float peso) {
  if (pctInd >= PORCENTAJE_DETECCION) return METAL;
  if (USAR_CAPACITIVO) {
    if (pctCap >= PORCENTAJE_DETECCION && peso <= PESO_MAX_PLASTICO_G) return PLASTICO;
    return DESCARTE;
  }
  return (peso <= PESO_MAX_PLASTICO_G) ? PLASTICO : DESCARTE;   // sin capacitivo
}

// -----------------------------------------------------------------------------
// RECOGIENDO: hasta MAX_INTENTOS. Agarre confirmado = FSR siente + bandeja vacía
// -----------------------------------------------------------------------------
void estadoRecogiendo() {
  for (uint8_t intento = 1; intento <= MAX_INTENTOS; intento++) {
    ciclo.intentos = intento;
    if (!moverBrazo(cfg.poses[P_SOBRE], MS_POR_GRADO_BRAZO)) return;
    if (!moverPinza(cfg.pinzaAbierta, MS_POR_GRADO_PINZA)) return;
    if (!moverBrazo(cfg.poses[P_BANDEJA], MS_POR_GRADO_BRAZO)) return;
    int fsr = 0;
    if (!cerrarPinzaSintiendo(fsr)) return;
    if (fsr > ciclo.fsrMax) ciclo.fsrMax = fsr;
    if (!moverBrazo(cfg.poses[P_SOBRE], MS_POR_GRADO_BRAZO)) return;
    if (!esperar(500)) return;

    float pesoBandeja = pesoEstable(5);
    bool sostiene = !USAR_FSR || leerFsr() >= (int)(cfg.umbralFsr / 2);
    bool bandejaVacia = pesoBandeja < PESO_MIN_G;

    if (bandejaVacia && sostiene) { cambiarEstado(DEPOSITANDO); return; }

    if (bandejaVacia && !sostiene) {          // se cayó fuera de la bandeja
      enviarEvento(F("FALLA_AGARRE"));
      logMsg(F("El residuo se solto durante el traslado."));
      moverPinza(cfg.pinzaAbierta, MS_POR_GRADO_PINZA);
      moverBrazo(cfg.poses[P_REPOSO], MS_POR_GRADO_BRAZO);
      cambiarEstado(ESPERANDO);
      return;
    }
    logMsg(F("No lo tomo. Reintentando."));
    if (!moverPinza(cfg.pinzaAbierta, MS_POR_GRADO_PINZA)) return;
  }
  // Agotó los intentos con el residuo todavía en la bandeja
  enviarEvento(F("FALLA_AGARRE"));
  moverBrazo(cfg.poses[P_REPOSO], MS_POR_GRADO_BRAZO);
  logMsg(F("No se pudo tomar el residuo. Retirelo a mano."));
  cambiarEstado(RETIRO_MANUAL);
}

// -----------------------------------------------------------------------------
// DEPOSITANDO: lo lleva a su contenedor, suelta y vuelve a reposo
// -----------------------------------------------------------------------------
void estadoDepositando() {
  PoseId destino = (ciclo.material == METAL) ? P_METAL :
                   (ciclo.material == PLASTICO) ? P_PLASTICO : P_DESCARTE;
  if (!moverBrazo(cfg.poses[destino], MS_POR_GRADO_BRAZO)) return;
  if (!moverPinza(cfg.pinzaAbierta, MS_POR_GRADO_PINZA)) return;
  if (!esperar(400)) return;
  if (!moverBrazo(cfg.poses[P_REPOSO], MS_POR_GRADO_BRAZO)) return;
  enviarEvento(F("OK"));
  cambiarEstado(ESPERANDO);
}

// -----------------------------------------------------------------------------
// RETIRO_MANUAL: espera a que el operario saque el residuo
// -----------------------------------------------------------------------------
void estadoRetiro() {
  if (pesoG < PESO_MIN_G) {
    if (!esperar(1500)) return;               // que alcance a sacar la mano
    logMsg(F("Bandeja libre. Esperando residuo."));
    cambiarEstado(pausaPedida ? PAUSADO : ESPERANDO);
    pausaPedida = false;
  }
}

// Tras una falsa detección: no reaccionar de nuevo mientras siga la mano encima
void esperarBandejaLibre() {
  unsigned long t0 = millis();
  while (millis() - t0 < 3000) {
    if (!esperar(100)) return;
    distanciaCm = medirDistanciaCm();
    if (distanciaCm < 0 || distanciaCm > DIST_OBJETO_CM) break;
  }
}

// -----------------------------------------------------------------------------
void cambiarEstado(Estado nuevo) {
  if (nuevo == estado) return;
  if (paro && nuevo != PARADO) return;   // tras un PARO solo SEGUIR saca de PARADO
  estado = nuevo;
  enviarCambioEstado();
}

// Servicio de fondo: se llama en loop() y dentro de toda espera o movimiento,
// así la telemetría nunca se corta aunque el brazo esté moviéndose.
void servicio() {
  actualizarBalanza();
  leerComandos();
  actualizarLed();
  static unsigned long tUltTelemetria = 0;
  if (millis() - tUltTelemetria >= PERIODO_TELEMETRIA_MS) {
    tUltTelemetria = millis();
    enviarTelemetria();
  }
}

// Espera atendiendo el servicio. Devuelve false si llegó un PARO.
bool esperar(unsigned long ms) {
  unsigned long t0 = millis();
  while (millis() - t0 < ms) {
    servicio();
    if (paro) { atenderParo(); return false; }
  }
  return true;
}

// PARO de emergencia: congela el brazo donde está y registra el evento
void atenderParo() {
  if (estado == PARADO) return;
  bool enCiclo = (estado == ANALIZANDO || estado == RECOGIENDO || estado == DEPOSITANDO);
  if (enCiclo) enviarEvento(F("PARO"));
  cambiarEstado(PARADO);
  logMsg(F("PARO. Retire el residuo de la pinza y envie SEGUIR."));
}

void actualizarLed() {
  unsigned long periodo;
  switch (estado) {
    case ESPERANDO:     digitalWrite(PIN_LED, LOW);  return;
    case ANALIZANDO: case RECOGIENDO: case DEPOSITANDO:
                        digitalWrite(PIN_LED, HIGH); return;
    case PARADO: case RETIRO_MANUAL: periodo = 150; break;  // parpadeo rápido
    default:            periodo = 600; break;               // pausado / sin calibrar
  }
  digitalWrite(PIN_LED, (millis() / periodo) % 2);
}
