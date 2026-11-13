# Firmware PBX 2 líneas

ATmega328P con cristal de 16 MHz, en C99 con avr-gcc. Sin Arduino.

## Comandos

```sh
make test     # pruebas de la lógica en la PC (cc)
make          # build/pbx.hex
make size     # uso de flash y RAM
make fuses    # una sola vez por chip: cristal externo 16 MHz (lfuse FF, hfuse D9, efuse FF)
make flash    # graba por ISP
```

El programador por defecto es `usbasp`. Se cambia con `make flash PROGRAMMER=avrisp PORT=/dev/tty...`.

## Estructura

| Archivo | Qué hace |
|---|---|
| `src/hook.c` | descolgado, colgado y marcado por pulsos (muestras de 1 ms) |
| `src/dtmf.c` | código de 4 bits del MT8870 → dígito |
| `src/call.c` | máquina de llamada de 2 líneas |
| `src/tones.c` | tonos y ring de AR (ITU-T E.180) y de EE.UU. |
| `src/cadence.c` | cadencias on/off |
| `src/signals.c` | estado de llamada → frecuencias y ring con cadencia |
| `src/dds.c` | síntesis de 1 o 2 senos para PWM |
| `src/hal_avr.c`, `src/main.c` | hardware y bucle principal (solo AVR) |

Los módulos puros no incluyen `<avr/*>` y se prueban con `make test`.

## Mapa de pines

| Pin | Señal | Sentido | Nota |
|---|---|---|---|
| PC0 | `OFFHOOK_L1` | entrada | activo en bajo (opto), pull-up interno |
| PC1 | `OFFHOOK_L2` | entrada | activo en bajo |
| PC2–PC5 | `DTMF_Q1`–`DTMF_Q4` | entrada | salidas del MT8870 |
| PD2 | `DTMF_STD` | entrada | StD del MT8870, alto = dígito válido |
| PD6 | `TONE_L1` | salida | OC0A, PWM 62,5 kHz → filtro RC → línea 1 |
| PD5 | `TONE_L2` | salida | OC0B, PWM → filtro RC → línea 2 |
| PB0 | `RING_EN_L1` | salida | → ULN2003A → relé de ring L1 |
| PB1 | `RING_EN_L2` | salida | → ULN2003A → relé de ring L2 |
| PB2 | `LINK_EN` | salida | → ULN2003A → relé que une el audio L1–L2 |
| PD7 | `DTMF_SEL` | salida | 0 = MT8870 escucha L1, 1 = L2 |
| PD4 | `RING_DRIVE` | salida | fase del puente H (la complementaria por hardware) |
| PD3 | `LED_CALL` | salida | LED de llamada activa |
| PD0 | `COUNTRY_SW` | entrada | pull-up; abierta = AR, a GND = US |
| PD1 | `UART_TX` | — | reservado para depuración (todavía sin usar) |
| PB3–PB5 | ISP | — | no se usan para otra cosa |

## Prueba de humo

Después de `make fuses flash`, conectar un parlante o un osciloscopio en PD6 a través de un RC (1 kΩ + 100 nF). Poner PC0 a GND:

- a los 50 ms suena el tono de invitación de 425 Hz;
- con PD0 a GND pasa a 350 + 440 Hz;
- PC0 abierto más de 500 ms lo corta.
