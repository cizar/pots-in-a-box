# Prueba de banco: línea discreta contra el Commodore Modem 1200

Esta prueba se hace **antes de diseñar el PCB** (spec §8). Se arma en protoboard o en placa
perforada y responde cuatro preguntas:

1. ¿El descolgado se detecta bien?
2. ¿El Modem 1200 (1670) detecta nuestra ring y atiende solo?
3. ¿El ring trip funciona?
4. ¿Dos módems negocian a 1200 bps a través del acople por capacitor?

Los resultados fijan `V_LINEA`, la tensión de ring y la opción de acople del plan de KiCad.

Para que suene L1 alguien tiene que llamar desde L2, así que en la práctica se arman **las
dos líneas**:
- **L1:** el Modem 1200 con `ATS0=1`, que es el llamado.
- **L2:** el módem de la PC o un teléfono común, que es el que llama.

El firmware es el de `firmware/`, sin cambios. Mapa de pines en `firmware/README.md`.

---

## 1. Circuito de prueba y lista de materiales

Todos los valores son **de partida**: la idea de la prueba es ajustarlos. Todos los
componentes son pasantes.

### 1.1 Alimentación

```
 12 V (fuente de pared) ──┬──► 7805 ──► +5 V (ATmega, MT8870, lógica)
                          ├──► COM del ULN2003A y bobinas de los relés
                          └──► elevador ajustable ──► V_LINEA (24 / 36 / 48 V)
                                                      │
                                                      ├─ 100 kΩ 1/2 W a GND (descarga)
                                                      └─ 100 µF 63 V
```

Para la prueba conviene un **módulo elevador ajustable** comprado armado, cuya salida llegue a
50 V. Hay que verificar en la publicación la tensión máxima de salida, porque muchos módulos
baratos no pasan de 35 V. El elevador propio de la placa final (por ejemplo, un MC34063 con un
MOSFET externo de 100 V) se diseña después, con la `V_LINEA` que salga de acá.

### 1.2 Alimentación de una línea (por cada línea)

```
 V_LINEA ── PTC 100 mA ──┬── colector  Q1 MJE340 (300 V, con disipador chico)
                         │   base Q1 ── 10 kΩ 1/2 W ── V_LINEA
                         │              └─ colector Q2 BC546
                         │   emisor Q1 ── R_SENSE 27 Ω ──┬── base Q2
                         │                               │   emisor Q2 ─┐
                         │                               └──────────────┴──► nodo TIP_FEED
 nodo TIP_FEED ──► NC del relé de ring ──► TIP (RJ11)
 RING (RJ11) ──► NC del relé de ring ──► nodo RING_RET
 nodo RING_RET ── LED del PC817 (ánodo) ── cátodo ──► GND
                  1N4148 en antiparalelo con el LED (protege contra inversión)
 TVS bidireccional P6KE68CA entre TIP y RING, del lado del RJ11
```

- **Limitador de corriente:** Q1 conduce hasta que la caída en R_SENSE llega a unos 0,65 V.
  Con 27 Ω la corriente queda en unos **24 mA**. Para 30 mA usar 22 Ω; para 20 mA, 33 Ω.
- Con la línea en corto, Q1 disipa `V_LINEA × I`, unos 1,2 W a 48 V: **necesita disipador**.
  La resistencia de base disipa unos 0,22 W: tiene que ser de **1/2 W**.
- **El PC817 va en el retorno (RING → GND), no en la alimentación.** Así por el LED pasa
  solamente la corriente que atraviesa el módem. La corriente que recarga el capacitor de
  acople (§1.4) no pasa por el LED, y no aparecen descuelgues falsos al terminar cada ráfaga
  de ring ni pulsos acortados al marcar por pulsos.
- **PC817:** el transistor va con el colector a **PC0** (pull-up interno del ATmega) y el
  emisor a GND. Lazo cerrado = PC0 en bajo, que es lo que espera el firmware.

### 1.3 Ring

En la prueba se usa **el mismo `V_LINEA` como riel de ring**. Un puente H lo aplica a la
línea con polaridad alternada, así que a la línea llega una onda cuadrada de ±V_LINEA, unos
48 V rms a 48 V.

```
 V_LINEA ── R_BRIDGE 470 Ω 5 W ──┬──────────────┬──      (limita corto y conducción cruzada)
                                 P1 IRF9540     P2 IRF9540
                                 │              │
                       salida A ─┤              ├─ salida B ──► NO del relé (lado TIP)
                                 N1 IRF540      N2 IRF540     salida A ──► NO del relé (lado RING)
                                 │              │
 GND ────────────────────────────┴──────────────┴──
 RING_DRIVE (PD4) ── 10 kΩ a GND (fija el nivel en reset y durante ISP)
   PD4 ──► excita P1 y N2;  inversor BC547 (12 V) ──► excita P2 y N1
 Gates de los P (una red por cada P):
   desplazador con BC546 (65 V) o MPSA42: colector ── 22 kΩ ── V_LINEA,
   zener de 12 V entre gate y fuente (Vgs < 20 V)
 Gates de los N: 10 kΩ entre gate y fuente (pull-down)
 Todas las gates: 220 Ω en serie con un 1N4148 en paralelo, cátodo hacia el driver
   (carga lenta y descarga rápida: el MOSFET apaga antes de que prenda el otro)
```

- **Relé de ring:** DPDT con bobina de 12 V (por ejemplo, de la serie HK19F). Lo maneja una
  entrada del ULN2003A desde **PB0** (L1) o **PB1** (L2). El pin COM del ULN2003A va a 12 V
  y ya trae los diodos de protección.
  - En reposo (NC), la línea queda en la alimentación de §1.2.
  - Activado (NO), la línea queda en el puente H.
- **R_BRIDGE está entre `V_LINEA` y el lado alto del puente.** Así limita la corriente tanto
  si la línea está en corto como si P y N de la misma rama conducen a la vez (unos 100 mA
  como máximo a 48 V). Por eso no puede ir solo en la salida.
- **Verificar con el osciloscopio**, sin línea conectada: medir la tensión sobre R_BRIDGE en
  cada cambio de fase. Si aparecen picos de conducción cruzada de más de unos microsegundos,
  aumentar la resistencia de 220 Ω de las gates.
- Si a 48 V el Modem 1200 no detecta la ring, ver el plan B en §1.6.

### 1.4 Audio, tonos y DTMF (acople por capacitor)

```
 nodo TIP_FEED (lado NC del relé: nunca ve la ring)
   └── 1 µF 250 V film ── nodo de audio de la línea (lado línea)
                              │
                              ├── relé de unión L1–L2 (ULN2003A desde PB2) ── nodo de audio de la otra línea
                              │
                              └── 1 kΩ ──┬── 1N4148 a +5 V (cátodo a +5 V)
                                         ├── 1N4148 a GND (ánodo a GND)
                                         └── nodo de audio protegido (lado lógica, 0–5 V)

 PD6 (L1) o PD5 (L2) ── 1 kΩ ─┬─ 1 kΩ ─┬─ 4,7 kΩ fijo ── trimmer 47 kΩ ──► nodo protegido
                            47 nF     47 nF
                              GND      GND            (filtro RC de 2 polos, ~3 kHz)

 nodo protegido L1 ─┐
                    ├── DTMF_SEL: relé chico de 12 V (ULN2003A desde PD7) ── 100 nF ── 100 kΩ ── IN- del MT8870
 nodo protegido L2 ─┘                               (circuito de entrada de una sola terminal de la hoja de datos)
```

- **El capacitor de acople va del lado NC del relé de ring.** Así nunca le llega la ring y
  mantiene su carga.
- **Del lado de la lógica, todo queda protegido por la resistencia de 1 kΩ y los dos diodos
  a +5 V y GND.** Así los escalones de continua de cada descuelgue, cuelgue y pulso (unos
  ±40 V) no llegan al MT8870 ni a los pines del ATmega.
- **El DTMF_SEL es un relé, no un CD4066,** y la resistencia fija de 4,7 kΩ en serie con el
  trimmer protege a PD5 y PD6 aunque el trimmer se ponga en cero.
- La unión L1–L2 va del lado línea, antes de la protección, para que el audio de los módems
  pase sin atenuación.
- El nivel del tono se ajusta con el trimmer. Hay que empezar alto, en unos 47 kΩ, y bajarlo
  hasta que el módem detecte el tono de invitación, para no saturar la línea.
- **MT8870:** usar el circuito de entrada de una sola terminal y el cristal de 3,579545 MHz
  de la hoja de datos. Las salidas Q1–Q4 van a PC2–PC5 y StD a PD2.
- Para la alternativa con **transformador 600:600**: reemplazar el capacitor de 1 µF por el
  bobinado de línea del transformador, en serie con un capacitor de 1 µF 250 V para que no
  pase la continua. El otro bobinado va al nodo de audio. La protección de 1 kΩ y los
  diodos se mantiene.

### 1.5 Lista de materiales

Los componentes "por línea" se multiplican por 2. Los "compartidos" van una sola vez.

| Cant. | Componente | Uso |
|---|---|---|
| 1 | Módulo elevador ajustable de 12 V a ≥ 50 V | compartido; solo para la prueba |
| 1 | 7805 + capacitores de 100 nF y 10 µF | compartido |
| 1 | ATmega328P DIP-28 + cristal de 16 MHz + 2 × 22 pF | compartido |
| 1 | MT8870 DIP-18 + cristal de 3,579545 MHz + componentes de entrada de la hoja de datos | compartido |
| 1 | ULN2003A DIP-16 | compartido (ring L1, ring L2, unión, DTMF_SEL) |
| 1 | MJE340 + disipador chico | por línea |
| 1 | BC546 | por línea (limitador) |
| 1 | resistencia de 27 Ω (y 22 Ω y 33 Ω para probar) | por línea |
| 1 | resistencia de 10 kΩ 1/2 W | por línea |
| 1 | PTC de 100 mA y 60 V o más | por línea |
| 1 | TVS P6KE68CA | por línea |
| 1 | PC817 + 1N4148 | por línea |
| 1 | relé DPDT con bobina de 12 V | por línea (ring) |
| 1 | capacitor de film de 1 µF 250 V | por línea |
| 1 | resistencia de 1 kΩ + 2 × 1N4148 | por línea (protección del audio) |
| 1 | trimmer de 47 kΩ + 4,7 kΩ + 2 × 1 kΩ + 2 × 47 nF | por línea (filtro y nivel de tono) |
| 1 | RJ11 hembra pasante | por línea |
| 2 | IRF540 | compartido (puente H) |
| 2 | IRF9540 | compartido (puente H) |
| 2 | BC546 o MPSA42 + 2 × 22 kΩ + 2 × zener de 12 V | compartido (gates de los P) |
| 1 | BC547 + 10 kΩ + 1 kΩ | compartido (inversor de fase) |
| 4 | resistencia de 220 Ω + 1N4148 | compartido (una por gate) |
| 3 | resistencia de 10 kΩ | compartido (pull-down de PD4 y de las gates de los N) |
| 1 | resistencia de 470 Ω 5 W | compartido (R_BRIDGE) |
| 2 | relé chico con bobina de 12 V | compartido (unión L1–L2 y DTMF_SEL) |
| 1 | resistencia de 100 kΩ 1/2 W + capacitor de 100 µF 63 V | compartido (riel V_LINEA) |
| 1 | LED + resistencia de 470 Ω | compartido (LED_CALL en PD3) |
| 1 | transformador 600:600 (opcional) | solo si falla la validación 4 |

### 1.6 Plan B: riel de ring aparte de 70–90 V

Usarlo solo si la validación 2 falla a 48 V. **Supera la tensión de seguridad extra-baja**
(unos 60 V de continua), así que todo lo de §2 se aplica con más cuidado todavía.

Hay que cambiar estos componentes:

| Componente | Prueba a 48 V | Plan B a 90 V |
|---|---|---|
| Elevador | compartido con V_LINEA | segundo elevador solo para la ring, de 70–90 V |
| MOSFETs del puente | IRF540 / IRF9540 (100 V) | IRF640 / IRF9640 (200 V) |
| Desplazadores de gate | BC546 / MPSA42, 22 kΩ | MPSA42 (300 V), 47 kΩ 1 W |
| R_BRIDGE | 470 Ω 5 W | 1 kΩ 10 W (unos 8 W en corto a 90 V) |
| TVS de línea | P6KE68CA | P6KE120CA (la de 68 V conduciría con la ring y se quemaría) |
| Capacitor de acople | 250 V | 250 V (alcanza) |
| Capacitor del riel | 63 V | 160 V o más |

---

## 2. Seguridad

- **Nodos con tensión peligrosa:**
  - el riel `V_LINEA`;
  - las salidas del puente H y R_BRIDGE;
  - los contactos NO de los relés de ring;
  - los RJ11;
  - los capacitores de acople de 250 V.
- **Nunca se toca nada con la ring activa,** cuando el LED de la línea titila o el relé está
  cerrado. ±48 V en cuadrada no mata, pero duele.
- **Los capacitores quedan cargados.** El de 100 µF del riel se descarga solo por la
  resistencia de 100 kΩ en unos 30 s. Los de 1 µF de acople hay que descargarlos con una
  resistencia de 1 kΩ antes de tocarlos.
- **Siempre con la fuente de pared de 12 V.** Nada se conecta a 220 V.
- **Primero sin módems:** medir con el téster que `V_LINEA` y la corriente de corto sean las
  esperadas. Recién después se conectan las computadoras.
- **Disipador en el MJE340** antes de probar con la línea en corto.

---

## 3. Procedimiento

Antes de empezar:
- Grabar el firmware con `make -C firmware fuses flash`.
- Llave AR/US en **AR** (PD0 abierto).
- Configurar el Modem 1200 desde la terminal de la C64.

### Validación 1: descolgado

1. Con `V_LINEA = 24 V`, conectar el Modem 1200 a L1.
2. Desde la terminal, enviar `ATH1` (descolgar) y después `ATH0` (colgar). Repetir 10 veces.
3. Medir con el osciloscopio en PC0, o escuchar en la línea: con `ATH1` aparece el tono de
   invitación de 425 Hz, y con `ATH0` desaparece.
4. Repetir con 36 V y con 48 V.

**Criterio de éxito:** 10 de 10 descuelgues y 10 de 10 cuelgues detectados para cada
`V_LINEA`. Registrar además la corriente de lazo medida con el módem descolgado.

### Validación 2: ring

1. Modem 1200 en L1 con `ATS0=1`.
2. Desde L2 (el módem de la PC con `ATDT1`, o un teléfono), marcar cualquier número.
3. A los 2,5 s del último dígito, L1 tiene que sonar con cadencia de 1 s on y 4 s off.
4. Medir la tensión de ring en el RJ11 de L1 con el téster en alterna (V rms) mientras suena.

**Criterio de éxito:** el Modem 1200 atiende (va a línea y emite el tono de respuesta) en
5 de 5 llamadas. Registrar los V rms de ring medidos. Si no atiende, pasar al plan B de §1.6.
5. Repetir una vez marcando por pulsos desde la PC (`ATDP1`) para verificar el marcado por pulsos.

### Validación 3: ring trip

1. Igual que la validación 2.
2. Observar qué pasa cuando el Modem 1200 atiende.

**Criterio de éxito:** en 5 de 5 llamadas se cumplen las tres cosas:
- la ring se corta antes de que empiece la ráfaga siguiente (no hay una segunda ráfaga
  después de atender);
- se enciende el LED de llamada activa (PD3);
- se cierra el relé de unión.

Además, en el osciloscopio, PC0 de L1 no tiene que bajar durante los 200 ms siguientes a
cada ráfaga cuando el módem todavía no atendió (si baja, hay un descuelgue falso).

### Validación 4: negociación a 1200 bps

1. Modem 1200 en L1 con `ATS0=1`, y módem de la PC en L2.
2. Desde la PC: `ATDT1`.
3. Esperar `CONNECT 1200` en las dos terminales.
4. Escribir o pegar texto en las dos direcciones durante 10 minutos.

**Criterio de éxito:** `CONNECT 1200` en 5 de 5 intentos, y 10 minutos de texto sin
caracteres basura visibles. Si falla, se arma la alternativa con transformador 600:600
(§1.4), se repite la validación y se registra el resultado.

---

## 4. Resultados

Una fila por corrida. Se commitea completa en el repo.

| Fecha | V_LINEA (V) | I lazo (mA) | Ring (V rms) | V1 descolgado (x/10) | V2 ring (x/5) | V3 ring trip (x/5) | V4 negociación (x/5) | Acople | Observaciones |
|---|---|---|---|---|---|---|---|---|---|
| | 24 | | | | | | | capacitor | |
| | 36 | | | | | | | capacitor | |
| | 48 | | | | | | | capacitor | |
| | | | | | | | | transformador | (solo si falla V4) |

**Decisiones para el plan de KiCad**, a completar con la tabla de arriba:

- `V_LINEA` elegido:
- Riel de ring: compartido con `V_LINEA` o con elevador aparte, y de cuántos voltios:
- Acople: capacitor o transformador:
- R_SENSE (corriente de lazo):
- Nivel del tono (valor del trimmer):
