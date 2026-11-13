# Firmware de POTS in a box (central telefónica de 2 líneas)

ATmega328P con cristal de 16 MHz, en C99 con avr-gcc. Sin Arduino.

## Comandos

```sh
make test     # pruebas de la lógica en la PC (cc)
make          # build/pots.hex
make size     # uso de flash y RAM
make fuses    # una sola vez por chip: cristal 16 MHz full swing, BOD 4,3 V (lfuse F7, hfuse D9, efuse FC)
make flash    # graba por ISP
```

El programador por defecto es `usbasp`. Se cambia con `make flash PROGRAMMER=avrisp PORT=/dev/tty...`.

### Con un Arduino Uno

El mismo firmware corre en un Arduino Uno, sin cambios. Se graba por USB, a través del
bootloader del Uno:

```sh
make flash PROGRAMMER=arduino PORT=/dev/cu.usbmodemXXXX   # ls /dev/cu.usbmodem* para ver el puerto
```

- **No ejecutar `make fuses` en el Uno:** desactivaría su bootloader. El `Makefile` lo
  impide cuando `PROGRAMMER=arduino`. Los fusibles de fábrica del Uno sirven para la prueba.
- El Uno usa un resonador cerámico de 16 MHz (±0,5 %), no un cristal. Alcanza para los
  tonos (425 Hz ± 2 Hz) y para la UART.
- **Al abrir el monitor serie, el Uno se reinicia.** Es normal: lo hace el chip USB del Uno.

## Monitor serie (depuración)

El firmware escribe cada evento por la UART (PD1, 38400 8N1):

```
country AR
L2 off-hook
L2 -> DIALTONE
L2 digit 1 (dtmf)
L2 -> DIALING
L2 -> RINGBACK
L1 -> RINGING
L1 off-hook
L1 -> CONNECTED
L2 -> CONNECTED
```

- **En el Uno:** sale por el mismo cable USB. Se ve con `screen /dev/cu.usbmodemXXXX 38400`
  (para salir: Ctrl-A, K) o con el monitor serie del IDE de Arduino a 38400.
- **En el ATmega solo:** un adaptador USB-serie de 5 V (FTDI, CH340 o CP2102) con su RX al
  pin PD1 y masa común.

## Estructura

| Archivo | Qué hace |
|---|---|
| `src/hook.c` | descolgado, colgado y marcado por pulsos (muestras de 1 ms) |
| `src/dtmf.c` | código de 4 bits del MT8870 → dígito (hay un MT8870 por línea) |
| `src/call.c` | máquina de llamada de 2 líneas |
| `src/tones.c` | tonos y ring de AR (ITU-T E.180) y de EE.UU. |
| `src/cadence.c` | cadencias on/off |
| `src/signals.c` | estado de llamada → frecuencias y ring con cadencia |
| `src/dds.c` | síntesis de 1 o 2 senos para PWM |
| `src/pots.c` | un tick de 1 ms: entradas → detección → lógica → salidas y eventos (probado en la PC) |
| `src/log.c`, `src/txq.c` | texto de los eventos y cola de transmisión de la UART |
| `src/hal_avr.c`, `src/main.c` | hardware, watchdog y bucle principal (solo AVR) |

Los módulos puros no incluyen `<avr/*>` y se prueban con `make test`.

**Idioma:** el código (identificadores, comentarios, Makefile, mensajes de los tests y nombres de señales como `V_LINE`) va en inglés. La documentación va en español.

## Mapa de pines

| Pin ATmega | Pin Uno | Señal | Sentido | Nota |
|---|---|---|---|---|
| PC0 | A0 | `OFFHOOK_L1` | entrada | activo en bajo (opto), pull-up interno |
| PC1 | A1 | `OFFHOOK_L2` | entrada | activo en bajo |
| PC2–PC5 | A2–A5 | `DTMF_Q1`–`DTMF_Q4` | entrada | bus compartido de los dos MT8870 (1 kΩ en serie) |
| PD0 | D0 | `UART_RX` | — | libre (en el Uno va al chip USB) |
| PD1 | D1 | `UART_TX` | salida | log de depuración, 38400 8N1 (en el Uno sale por USB) |
| PD2 | D2 | `DTMF_STD_L1` | entrada | StD del MT8870 de L1, alto = dígito válido (también va a su TOE) |
| PD3 | D3 | `LED_CALL` | salida | LED de llamada activa |
| PD4 | D4 | `RING_DRIVE` | salida | fase del puente H (la complementaria por hardware) |
| PD5 | D5 | `TONE_L2` | salida | OC0B, PWM → filtro RC → línea 2 |
| PD6 | D6 | `TONE_L1` | salida | OC0A, PWM 62,5 kHz → filtro RC → línea 1 |
| PD7 | D7 | `DTMF_STD_L2` | entrada | StD del MT8870 de L2 (también va a su TOE) |
| PB0 | D8 | `RING_EN_L1` | salida | → ULN2003A → relé de ring L1 |
| PB1 | D9 | `RING_EN_L2` | salida | → ULN2003A → relé de ring L2 |
| PB2 | D10 | `LINK_EN` | salida | → ULN2003A → relé que une el audio L1–L2 |
| PB3 | D11 | ISP (MOSI) | — | no se usa para otra cosa |
| PB4 | D12 | `COUNTRY_SW` | entrada | pull-up; llave a GND **a través de 1 kΩ**; abierta = AR, cerrada = US |
| PB5 | D13 | ISP (SCK) | — | no se usa (en el Uno tiene el LED "L") |

**Por qué la llave AR/US va en PB4 con 1 kΩ:** PB4 es la pata MISO del ISP. Mientras se graba,
el ATmega la maneja como salida, y la resistencia de 1 kΩ hace que la llave cerrada solo le
pida unos 5 mA: la grabación funciona en cualquier posición de la llave. En PD0 chocaría con
el USB del Uno (las grabaciones por USB fallarían con la llave en US).

## Prueba de humo

Después de `make fuses flash` (o `make flash PROGRAMMER=arduino ...` en un Uno), conectar un parlante o un osciloscopio en PD6 a través de un RC (1 kΩ + 100 nF). Poner PC0 a GND:

- a los 50 ms suena el tono de invitación de 425 Hz;
- con PB4 a GND a través de 1 kΩ (D12 en el Uno) pasa a 350 + 440 Hz;
- en el monitor serie aparecen `country AR`, `L1 off-hook` y `L1 -> DIALTONE`;
- PC0 abierto más de 500 ms lo corta.
