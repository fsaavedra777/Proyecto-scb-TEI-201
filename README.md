# Proyecto SCB
## Sistema de Clasificación de Basura

### 1. Descripción del proyecto

SCB es un sistema automatizado de clasificación de residuos que busca facilitar la separación de basura mediante sensores y mecanismos de movimiento. El dispositivo detecta un residuo, mide su masa, identifica su material y lo deposita en el contenedor correspondiente.

### 2. Integrantes

- Facundo Saavedra
- Matías Jara
- Martín Olivares

### 3. Funcionamiento del sistema

El sistema realiza un ciclo automático compuesto por seis etapas:

1. Recepción del residuo en una bandeja.
2. Detección mediante el sensor ultrasónico HC-SR04.
3. Medición de masa mediante la celda de carga y el módulo HX711.
4. Identificación del material mediante sensores inductivos y capacitivos.
5. Agarre del residuo mediante una pinza con servomotor.
6. Depósito del residuo en el contenedor correspondiente.

### 4. Componentes principales

- Arduino UNO.
- Sensor ultrasónico HC-SR04.
- Celda de carga y módulo HX711.
- Sensor inductivo LJ12A3.
- Sensor capacitivo LJC18A3.
- Sensor de fuerza FSR-402.
- Servomotores SG90 y MG90S.
- Fuente de alimentación de 5 V y 10 A.

### 5. Estructura del repositorio

- `firmware/`: programación del Arduino.
- `hardware/`: esquemáticos, componentes y fotografías.
- `diseno-3d/`: modelos CAD, planos y renders.
- `testing/`: protocolos y resultados de pruebas.
- `docs/`: informes y documentación general.

### 6. Instrucciones de uso

1. Conectar el Arduino UNO al computador.
2. Abrir el código fuente mediante Arduino IDE.
3. Instalar las bibliotecas necesarias.
4. Conectar los sensores y servomotores según el esquemático.
5. Cargar el programa al Arduino.
6. Ejecutar y comprobar el funcionamiento del sistema.

### 7. Documentación

Los archivos de diseño, programación, fabricación y validación se encuentran organizados en las carpetas correspondientes de este repositorio.
