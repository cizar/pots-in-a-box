# PBX de 2 líneas para módems retro — Diseño

Fecha: 2026-11-13
Estado: listo para aprobación

## 1. Intención

Una central telefónica mínima (PBX) de **2 líneas** para que computadoras retro con módem
telefónico se conecten entre sí sin una línea real. Caso típico: una PC corriendo un BBS con
el módem en auto-atención, y otra computadora (por ejemplo una Commodore 64 con su módem, o
una PC vieja) que la llama.

Si el prototipo funciona y el costo es razonable, se quiere **vender** en ferias de
computación retro y en Mercado Libre (Argentina). Eso condiciona seguridad, costo,
disponibilidad local de componentes y facilidad de armado.

## 2. Objetivos

- Dos fichas RJ11 (L1, L2). Cada una se comporta como una línea telefónica para un módem:
  alimentación de línea, tono de invitación a marcar, detección de marcado, ring, tono de
  llamada y de ocupado.
- Una computadora descuelga, marca **cualquier número** y suena la otra línea. Cuando la
  otra atiende, quedan conectadas y los módems negocian.
- Soporta marcado por **tonos (DTMF)** y por **pulsos**.
- Tonos de Argentina o de EE.UU. según una **llave física** AR/US.
- Alimentación única por **jack de 12 V** desde una fuente externa certificada.
- LED de encendido y LED de llamada activa.
- Caja compacta.

### 2.1 Módem de referencia

- **Commodore Modem 1200 (1670) a 1200 bps** es el módem que tiene que funcionar sí o sí, y
  el que se usa en la prueba previa (§8).
- 1200 bps (Bell 212A / V.22) pide un audio limpio pero no exigente. No hace falta
  garantizar velocidades más altas.
- El módem de la PC que corre el BBS no está definido: se prueba con lo que haya.

## 3. No objetivos (por ahora)

- Más de 2 líneas, o modularidad física (placas de línea, backplane). Se exploró y se dejó
  para el futuro (ver §10).
- Conexión a una línea telefónica real.
- Identificador de llamadas, numeración configurable, varias llamadas simultáneas.
- Certificaciones formales.
- Velocidades por encima de 1200 bps como requisito (si andan, mejor).
- Venta como kit (por ahora se vende armado).

## 4. Anti-objetivos (fracaso aunque "funcione")

- Que haya **220 V dentro de la caja**, o alta tensión accesible sin limitar corriente.
- Que los módems no puedan negociar de forma confiable a través de la central.
- Depender de componentes que haya que importar. Excepción: el ATmega328P y el MT8870 se
  consiguen localmente.
- Un armado tan complejo que no se pueda producir en pequeña serie.

## 5. Restricciones

- Entrada: 12 V de continua desde una fuente de pared externa.
- Componentes comunes en Argentina. Sin chips SLIC importados.
- Partes base elegidas por el usuario: **MT8870** (DTMF), **ATmega328P** (lógica) y
  **ULN2003A** (manejo de relés sin transistores ni diodos sueltos).
- El repo contiene las reglas o documentación (`docs/`) y el proyecto de KiCad, versionado
  con git.

## 6. Enfoques considerados

### 6.1 Interfaz de línea: SLIC integrado o discreto

- **SLIC integrado (por ejemplo AG1171, Silvertel):** resuelve alimentación, ring y
  descolgado desde 12 V. Es más seguro y simple, pero cuesta USD 10–15 por línea y hay que
  importarlo. **Descartado** porque hay que importarlo.
- **Discreto (elegido):** elevadores desde 12 V, limitadores de corriente, optoacopladores y
  relés. Es más barato y se consiguen las piezas localmente. La seguridad depende del diseño
  (limitar corriente, separar la alta tensión).
- Criterio que se mantiene: el circuito de línea se diseña con una **interfaz tipo SLIC**
  hacia el micro (descolgado, ring, audio). El MCU solo controla y no maneja tensiones.

### 6.2 Alimentación y audio entre líneas

- **A. Un solo lazo compartido** (un relé une L1 y L2 en un lazo): es lo más simple, pero
  ata eléctricamente las líneas y complica el tono y la detección por línea. Descartado.
- **B. Alimentación por línea con transformador 600:600:** es lo más prolijo y aísla, pero
  agrega costo y tamaño y conseguirlo es incierto.
- **C. Alimentación por línea con acople por capacitor (elegido):** cada línea es
  independiente, con componentes comunes, barata y compacta. No aísla entre líneas, lo cual
  es aceptable porque comparten fuente y masa.
- Decisión: **C, con huella alternativa para transformador** (ver §7.4).

### 6.3 Topología (explorada y postergada)

Se exploró hasta 8 líneas: un MT8870 por línea, buses de audio con CD4051, registros de
desplazamiento, `CS` por ranura, backplane con edge connector 2×13 y placas de 2 líneas. Se
**posterga**. La versión actual es una placa única de 2 líneas con un solo MT8870.

## 7. Diseño

### 7.1 Diagrama general

```
 12 V ─► [protección / regulador 5 V] ─► lógica
      └► [elevador 12 V → V_LINEA (24–48 V)] ─► alimentación de línea ×2
      └► [generador de ring compartido] ─► relé ring L1 / relé ring L2

 RJ11 L1 ─┬─ limitador de corriente ─ opto descolgado ─► ATmega
          ├─ relé de ring (ULN2003A) ◄─ ATmega
          └─ acople de audio (C o transformador) ─► nodo de audio L1

 RJ11 L2 ─  (igual)                                   ─► nodo de audio L2

 nodo L1 ──[relé o llave de conexión]── nodo L2
 nodo L1/L2 ─► selector ─► MT8870 ─► ATmega   (escucha a la línea que marca)
 ATmega PWM ×2 (OC0A→L1, OC0B→L2) ─► filtro RC ×2 ─► inyección de tono por línea
 llave AR/US ─► ATmega        LED PWR, LED LÍNEA ◄─ ATmega
```

### 7.2 Interfaz de línea "tipo SLIC" (hoja jerárquica de KiCad, usada ×2)

Cada instancia expone hacia el resto de la placa:

| Señal | Sentido | Descripción |
|---|---|---|
| `OFFHOOK` | sale | lógica: la línea está descolgada (y los pulsos de marcado) |
| `RING_EN` | entra | activa el relé de ring de esa línea (vía ULN2003A) |
| `AUDIO` | bidireccional | nodo de audio después del acople |
| `V_LINEA`, `RING_A/B`, `GND`, `+5V` | alimentación | |

Contenido: RJ11, limitador de corriente de lazo, optoacoplador de descolgado, relé de ring,
acople de audio, protección (por ejemplo TVS o varistor y fusible PTC en la línea).

Objetivo: que en el futuro una placa con SLIC integrado pueda reemplazar esta hoja con la
misma interfaz.

### 7.3 Alimentación de línea

- Tensión de lazo abierta: **24–48 V**. El valor final se decide en la prueba de protoboard
  (§8), con 48 V como referencia y 24 V si alcanza para todos los módems.
- Corriente de lazo limitada a unos **20–30 mA** por línea.

### 7.4 Acople de audio

- Por defecto: **2 capacitores de film de 250 V** por línea (tienen que aguantar V_LINEA más
  la ring).
- Alternativa en el mismo PCB: **huella de transformador 600:600** con puentes. Se arma una
  u otra opción. Hay que reservar unos 25×25 mm por línea y respetar la separación del caso
  transformador, alejado de la bobina del elevador.

### 7.5 Generador de ring

- **Compartido.** Suena una sola línea a la vez.
- Se genera desde 12 V: elevador más puente H que conmuta el ATmega a la frecuencia del país.
- Objetivo: que la detecten los módems en auto-atención (`ATS0=1`). Referencia: unos
  **45–60 V rms** sobre 1–2 REN. A confirmar en la prueba.
- Corriente limitada por diseño (seguridad).
- **Detección de atención durante la ring (ring trip):** el ATmega tiene que darse cuenta de
  que la línea llamada descolgó mientras suena, para cortar la ring. Es un punto
  delicado del diseño discreto. Hay que validarlo en la prueba.
  En el diseño discreto actual, mientras el relé de ring está activo el detector no ve el
  lazo, así que la atención se detecta **al terminar la ráfaga** (hasta 1 s en AR y 2 s en
  US), más unos 200 ms de asentamiento. Es aceptable para módems. Un detector de ring trip
  dedicado queda como mejora si la prueba muestra problemas.

### 7.6 Marcado

- **DTMF:** un solo MT8870 compartido, que escucha el nodo de audio de la línea que está
  marcando a través de un selector (relé o CD4066). Con 2 líneas hay una sola llamada
  posible, así que alcanza.
- **Pulsos:** el ATmega decodifica las aperturas del lazo leyendo `OFFHOOK`, a unos 10 pps.

### 7.7 Tonos

- Los genera el ATmega por **PWM + tabla de seno (DDS)**, con filtro RC y nivel ajustado
  para inyectar en la línea.
- La llave AR/US elige el juego de tonos y la cadencia de ring. Valores de referencia, a
  verificar contra ITU-T E.180 antes de fijarlos en el firmware:

| | Argentina | EE.UU. |
|---|---|---|
| Invitación a marcar | 425 Hz continuo | 350 + 440 Hz continuo |
| Llamada (ringback) | 425 Hz, 1 s on / 4 s off | 440 + 480 Hz, 2 s on / 4 s off |
| Ocupado | 425 Hz, cadencia corta (≈0,3/0,2 s) | 480 + 620 Hz, 0,5/0,5 s |
| Ring (frecuencia / cadencia) | 25 Hz, 1 s / 4 s | 20 Hz, 2 s / 4 s |

### 7.8 Lógica de llamada (firmware)

1. **Reposo:** las dos líneas colgadas, LED LÍNEA apagado.
2. **Descuelgue de A** (con antirrebote): A recibe tono de invitación. El MT8870 y el
   decodificador de pulsos escuchan A.
3. **Primer dígito:** se corta el tono de invitación. Se siguen aceptando dígitos.
4. **Fin del número:** cuando pasa un tiempo sin dígitos nuevos (propuesta: unos 2–3 s), se
   llama a la otra línea. **Cualquier número sirve**, para que funcionen los directorios de
   los programas de terminal tal como están.
5. **Si B está descolgada:** A recibe tono de ocupado. Es una decisión del usuario: se
   mantiene la lógica de una central de varias líneas aunque haya solo 2. Una línea
   descolgada que no está en llamada recibe tono de invitación, no queda "esperando". La
   atención manual sigue funcionando si se hace mientras suena: `ATA` en el módem llamado
   equivale a descolgar (paso 7).
6. **Si B está colgada:** B recibe ring con cadencia y A recibe tono de llamada.
7. **B atiende** (ring trip): se corta la ring y el tono, se cierra la conexión de audio
   A–B y se enciende el LED LÍNEA.
8. **Corte:** si cualquiera de las dos cuelga, se abre la conexión. La que quedó descolgada
   recibe tono de ocupado hasta que cuelgue.
9. **Tiempos de espera:** si A descuelga y no marca, o si B no atiende, después de un tiempo
   razonable (propuesta: unos 30 s sin marcar y unos 60 s de ring) A pasa a ocupado.
10. Si las dos líneas descuelgan a la vez, las dos reciben tono de invitación. La que marca
    recibe ocupado (paso 5), porque la otra está descolgada.

### 7.9 Placa y caja

- **Se vende armado, con componentes pasantes** (decisión del usuario): facilita el armado a
  mano en pequeña serie y las reparaciones. Sin componentes de montaje superficial salvo que
  alguna pieza no exista en versión pasante.
- **Caja:** una caja plástica estándar que se consiga en Argentina. El modelo lo elige el
  constructor y la placa se dimensiona para esa caja (decisión de Claude, el usuario no
  definió una caja).
- Una sola placa. Panel con 2 RJ11, jack de 12 V, LED PWR, LED LÍNEA y llave AR/US.
- Separación física de la zona de alta tensión (elevadores, ring y lado de línea) respecto
  de la lógica.
- Conector ISP de 6 pines para programar el ATmega.
- Hay que pensar en la producción en pequeña serie: componentes que se consigan y armado
  posible a mano.

### 7.10 Organización del repo

```
docs/                  reglas y decisiones (este documento y los que sigan)
docs/superpowers/specs diseños
hardware/              proyecto KiCad
firmware/              código del ATmega328P
```

## 8. Prueba previa (antes del PCB)

Prueba en protoboard de **una línea** más el generador de ring, contra el módem más
exigente (probablemente el de la C64). Tiene que validar:

1. El descolgado se detecta de forma confiable con el V_LINEA elegido.
2. El módem en auto-atención detecta la ring generada.
3. El ring trip funciona.
4. Con las dos líneas improvisadas y el acople por capacitor, dos módems negocian sin
   problemas de ruido o zumbido. Si falla, se prueba con transformador.

Lo que salga de la prueba ajusta V_LINEA, la tensión de ring y la opción de acople.

## 9. Decisiones que quedan para el constructor

- El circuito concreto de cada bloque (topología de los elevadores, del limitador de
  corriente, del puente H y de la protección) y los valores de los componentes.
- Cómo conmutar el MT8870 y la inyección de tono entre líneas (relé o CD4066).
- Cristal y frecuencia del ATmega. Sugerencia: 16 MHz, para que los tonos tengan buena
  precisión.
- Cadena de herramientas del firmware. Sugerencia: avr-gcc con Makefile, como en el otro
  proyecto retro del usuario.
- La versión de KiCad y las librerías de símbolos y huellas.
- Los tiempos exactos de antirrebote, fin de número y espera.

## 10. Futuro

- Llegar a 8 líneas con la topología explorada en §6.3, reutilizando la hoja de línea tipo
  SLIC.
- Opcionalmente, una placa de línea con SLIC integrado si se consigue.
