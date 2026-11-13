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
                         │   base Q1 ── 10 kΩ ── V_LINEA
                         │              └─ colector Q2 BC546
                         │   emisor Q1 ── R_SENSE 27 Ω ──┬── base Q2
                         │                               │   emisor Q2 ─┐
                         │                               └──────────────┴──► nodo A
 nodo A ── LED del PC817 (ánodo) ── cátodo ──► NC del relé de ring ──► TIP (RJ11)
           1N4148 en antiparalelo con el LED (protege contra inversión y ring)
 RING (RJ11) ──► NC del relé de ring ──► GND
 TVS bidireccional P6KE68CA entre TIP y RING, del lado del RJ11
```

- **Limitador de corriente:** Q1 conduce hasta que la caída en R_SENSE llega a unos 0,65 V.
  Con 27 Ω la corriente queda en unos **24 mA**. Para 30 mA usar 22 Ω; para 20 mA, 33 Ω.
- Con la línea en corto, Q1 disipa `V_LINEA × I`, unos 1,2 W a 48 V: **necesita disipador**.
- **PC817:** el transistor va con el colector a **PC0** (pull-up interno del ATmega) y el
  emisor a GND. Lazo cerrado = PC0 en bajo, que es lo que espera el firmware.

### 1.3 Ring

En la prueba se usa **el mismo `V_LINEA` como riel de ring**. Un puente H lo aplica a la
línea con polaridad alternada, así que a la línea llega una onda cuadrada de ±V_LINEA, unos
48 V rms a 48 V.

```
 V_LINEA ──┬───────────────┬──
           P1 IRF9540      P2 IRF9540
           │               │
 salida A ─┤               ├─ salida B ── 470 Ω 5 W ── NO del relé (lado TIP)
           N1 IRF540       N2 IRF540                  salida A ── NO del relé (lado RING)
           │               │
 GND ──────┴───────────────┴──
 RING_DRIVE (PD4) ──► excita P1/N2;  inversor (BC547 o 74HC04) ──► excita P2/N1
 Gates de los P: desplazador de nivel con BC547 + 10 kΩ / 4,7 kΩ a V_LINEA
                 (Vgs del IRF9540 limitado a menos de 20 V con un zener de 12 V)
 Gates de los N: 100 Ω desde la lógica (o desde el colector de un BC547 a 12 V)
```

- **Relé de ring:** DPDT con bobina de 12 V (por ejemplo, de la serie HK19F). Lo maneja una
  entrada del ULN2003A desde **PB0** (L1) o **PB1** (L2). El pin COM del ULN2003A va a 12 V
  y ya trae los diodos de protección.
  - En reposo (NC), la línea queda en la alimentación de §1.2.
  - Activado (NO), la línea queda en el puente H, a través de la resistencia de 470 Ω.
- La resistencia de 470 Ω limita la corriente de ring a unos 100 mA en cortocircuito.
- **Tiempo muerto:** el firmware cambia la fase cada 20 ms (AR) o 25 ms (US). Para evitar que
  conduzcan a la vez el P y el N de la misma rama, poner una red RC en las gates (10 kΩ +
  10 nF) y verificar con el osciloscopio que no haya conducción cruzada.
- Si a 48 V el Modem 1200 no detecta la ring, el plan B es un **segundo elevador solo para la
  ring** de unos 70–90 V, con el mismo puente H y MOSFETs de 100 V o más.

### 1.4 Audio, tonos y DTMF (acople por capacitor)

```
 TIP (después del relé) ── 1 µF 250 V film ──┬── nodo de audio de la línea
                                              │
 PD6 (L1) o PD5 (L2) ── 1 kΩ ─┬─ 1 kΩ ─┬─ trimmer 47 kΩ ─┘   (inyección de tono)
                            47 nF     47 nF
                              GND      GND                 (filtro RC de 2 polos, ~3 kHz)

 nodo de audio L1 ─┐
                   ├── DTMF_SEL (PD7) elige ── 100 nF ── 100 kΩ ── IN- del MT8870
 nodo de audio L2 ─┘   (relé chico o CD4066)          (circuito de entrada de una
                                                       sola terminal de la hoja de datos)
 Unión de audio L1–L2: relé (vía ULN2003A desde PB2) entre los dos nodos de audio
```

- El nivel del tono se ajusta con el trimmer. Hay que empezar alto, en unos 47 kΩ, y bajarlo
  hasta que el módem detecte el tono de invitación, para no saturar la línea.
- **MT8870:** usar el circuito de entrada de una sola terminal y el cristal de 3,579545 MHz
  de la hoja de datos. Las salidas Q1–Q4 van a PC2–PC5 y StD a PD2.
- Para la alternativa con **transformador 600:600**: reemplazar el capacitor de 1 µF por el
  bobinado de línea del transformador, en serie con un capacitor de 1 µF 250 V para que no
  pase la continua. El otro bobinado va al nodo de audio.

### 1.5 Lista de materiales (por línea, salvo indicación)

| Cant. | Componente | Nota |
|---|---|---|
| 1 | Módulo elevador ajustable de 12 V a ≥ 50 V | compartido; solo para la prueba |
| 1 | 7805 + capacitores de 100 nF y 10 µF | compartido |
| 1 | ATmega328P DIP-28 + cristal de 16 MHz + 2 × 22 pF | compartido |
| 1 | MT8870 DIP-18 + cristal de 3,579545 MHz | compartido |
| 1 | ULN2003A DIP-16 | compartido |
| 1 | MJE340 + disipador chico | |
| 1 | BC546 | |
| 1 | resistencia de 27 Ω (y 22 Ω y 33 Ω para probar) | |
| 1 | resistencia de 10 kΩ | |
| 1 | PTC de 100 mA y 60 V o más | |
| 1 | TVS P6KE68CA | |
| 1 | PC817 + 1N4148 | |
| 1 | relé DPDT con bobina de 12 V | |
| 1 | capacitor de film de 1 µF 250 V | |
| 1 | trimmer de 47 kΩ + 2 × 1 kΩ + 2 × 47 nF | filtro de tono |
| 1 | RJ11 hembra pasante | |
| 2 | IRF540 + 2 × IRF9540 + 3 × BC547 + zener de 12 V | compartido (puente H) |
| 1 | resistencia de 470 Ω 5 W | compartido |
| 1 | relé chico de 12 V para la unión L1–L2 | compartido |
| 1 | resistencia de 100 kΩ 1/2 W + capacitor de 100 µF 63 V | compartido |
| 1 | transformador 600:600 (opcional) | solo si falla la validación 4 |

---

## 2. Seguridad

- **Nodos con tensión peligrosa:**
  - el riel `V_LINEA`;
  - las salidas del puente H y la resistencia de 470 Ω;
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
5 de 5 llamadas. Registrar los V rms de ring medidos. Si no atiende, pasar al plan B de §1.3.

### Validación 3: ring trip

1. Igual que la validación 2.
2. Observar qué pasa cuando el Modem 1200 atiende.

**Criterio de éxito:** en 5 de 5 llamadas se cumplen las tres cosas:
- la ring se corta antes de que empiece la ráfaga siguiente (no hay una segunda ráfaga
  después de atender);
- se enciende el LED de llamada activa (PD3);
- se cierra el relé de unión.

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
