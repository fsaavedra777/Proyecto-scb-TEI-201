/*
 * memoria.ino — Configuración persistente en la EEPROM del Arduino
 *
 * Guarda el factor de la balanza, las 6 poses del brazo, la apertura y el
 * cierre de la pinza y el umbral del FSR. Así, si se cambia un servo o se
 * reinicia el equipo en terreno, se recalibra por comandos sin reprogramar.
 */

void configPorDefecto() {
  cfg.magic = CONFIG_MAGIC;
  cfg.factor = 420.0;                 // valor típico de una celda de 1 kg; calibrar con CAL
  for (uint8_t i = 0; i < N_POSES; i++) cfg.poses[i] = {90, 90, 90};
  cfg.pinzaAbierta = 90;
  cfg.pinzaCerrada = 60;
  cfg.guardadas = 0;                  // nada calibrado todavía
  cfg.umbralFsr = UMBRAL_FSR_DEFECTO;
}

void cargarConfig() {
  EEPROM.get(0, cfg);
  if (cfg.magic != CONFIG_MAGIC || isnan(cfg.factor) || cfg.factor == 0) {
    configPorDefecto();
    guardarConfig();
  }
}

void guardarConfig() {
  EEPROM.put(0, cfg);                 // put() solo reescribe los bytes que cambian
}
