# PBX 2 líneas — Firmware y prueba de banco: plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Firmware completo del ATmega328P, con su lógica probada en la PC, y el documento de la prueba de banco de una línea que el usuario arma contra el Commodore Modem 1200.

**Architecture:** La lógica está en módulos C puros, sin `<avr/*>`, que se compilan y prueban en la PC con `make test`. Son la decodificación de descolgado y pulsos, la máquina de llamada, las cadencias, la tabla de tonos y el DDS. Una capa fina (`hal_avr.c` + `main.c`) hace el tick de 1 ms, lee pines y aplica las salidas. El KiCad (esquemático y PCB) queda para un **segundo plan**, después de la prueba de banco, porque sus valores dependen de lo que mida esa prueba (spec §8).

**Tech Stack:** C99, avr-gcc + avr-libc, avrdude (programador por ISP, por defecto `usbasp`), `cc` del sistema y `make` para las pruebas en la PC. Sin Arduino.

**Spec:** `docs/superpowers/specs/2026-11-13-pbx-2-lineas-design.md`

## Global Constraints

- MCU: ATmega328P, cristal externo de 16 MHz (`F_CPU=16000000UL`).
- Los módulos puros (`hook`, `call`, `cadence`, `tones`, `dds`, `signals`, `dtmf`) no incluyen `<avr/*>` y compilan con `cc -std=c99 -Wall -Wextra -Werror`.
- El build AVR también usa `-Wall -Wextra -Werror`, `-Os` y `-mmcu=atmega328p`.
- Identificadores en inglés y comentarios en español.
- Tick lógico de **1 ms**. Todos los tiempos se expresan en ms.
- Las líneas se indexan `0` (L1) y `1` (L2).
- **Cualquier número marcado hace sonar la otra línea** (spec §7.8).
- **Línea llamada descolgada → tono de ocupado.** No hay conexión directa (spec §7.8 paso 5, decisión del usuario).
- Tiempos de la lógica (spec §7.8): fin de número a los **2500 ms** sin dígitos, sin marcar **30000 ms**, ring máxima **60000 ms**.
- Tonos y ring (spec §7.7, a verificar en la Task 2): AR 425 Hz; US 350+440 / 440+480 / 480+620; ring AR 25 Hz 1000/4000, US 20 Hz 2000/4000.
- Los pines ISP (PB3, PB4, PB5) no se usan para otra cosa.

**Mapa de pines** (fijado por este plan, lo usan la Task 7 y el KiCad futuro):

| Pin | Señal | Sentido | Nota |
|---|---|---|---|
| PC0 | `OFFHOOK_L1` | entrada | activo en bajo (opto), pull-up interno |
| PC1 | `OFFHOOK_L2` | entrada | activo en bajo |
| PC2–PC5 | `DTMF_Q1`–`DTMF_Q4` | entrada | salidas del MT8870 |
| PD2 | `DTMF_STD` | entrada | StD del MT8870, alto = dígito válido |
| PD6 | `TONE_L1` | salida | OC0A, PWM → filtro RC → línea 1 |
| PD5 | `TONE_L2` | salida | OC0B, PWM → filtro RC → línea 2 |
| PB0 | `RING_EN_L1` | salida | → ULN2003A → relé de ring L1 |
| PB1 | `RING_EN_L2` | salida | → ULN2003A → relé de ring L2 |
| PB2 | `LINK_EN` | salida | → ULN2003A → relé que une el audio L1–L2 |
| PD7 | `DTMF_SEL` | salida | 0 = MT8870 escucha L1, 1 = escucha L2 |
| PD4 | `RING_DRIVE` | salida | fase del puente H; la complementaria se hace por hardware |
| PD3 | `LED_CALL` | salida | LED de llamada activa |
| PD0 | `COUNTRY_SW` | entrada | pull-up; abierta = AR, a GND = US |
| PD1 | `UART_TX` | salida | depuración, 38400 8N1 |

**Cambio respecto del spec, decisión de este plan:** hay **una salida de tono PWM por línea** (OC0A/OC0B), en vez de una sola salida conmutable. Así una línea puede tener ocupado mientras la otra tiene tono de invitación. El cambio se anota en el spec en la Task 7.

## Review Focus

1. **El módem descuelga durante la ráfaga de ring.** Mientras el relé de ring está activo, el opto no ve el lazo. Se espera que la atención se detecte apenas termina la ráfaga, sin falsos descuelgues por la ring. El test va en la Task 4 (`hook_sample` con `masked`).
2. **El módem marca sin esperar tono (`ATX1`), justo después de descolgar.** Se espera que el dígito se acepte en cualquier momento después del evento de descolgado. El test va en la Task 5.
3. **El audio de los datos del módem parece DTMF durante la llamada.** Se espera que en `CONNECTED` no se escuche el MT8870 (`dtmf_line = -1`) y que los dígitos se ignoren. El test va en la Task 5.
4. **Corte breve del lazo durante la llamada, entre 120 y 500 ms.** Se espera que no corte la llamada ni cuente un dígito. El test va en la Task 4.
5. **Cambio de la llave AR/US con el equipo encendido.** Se espera que el tono que está sonando cambie de frecuencia en el tick siguiente, sin cuelgues. El test va en la Task 6.

---

### Task 1: Estructura del firmware, framework de pruebas y decodificación DTMF

**Files:**
- Create: `firmware/Makefile`
- Create: `firmware/tests/minitest.h`
- Create: `firmware/src/dtmf.h`, `firmware/src/dtmf.c`
- Create: `firmware/tests/test_dtmf.c`
- Create: `.gitignore` (con `firmware/build/`)

**Interfaces:**
- Produces:
  - `minitest.h`: `TEST(name)`, `CHECK(cond)`, `CHECK_EQ(a, b)` (compara como `long` e imprime archivo, línea y valores), `RUN(name)` y `MINITEST_MAIN_END()` (imprime el resumen y devuelve 1 si hubo fallas).
  - `int8_t dtmf_code_to_digit(uint8_t q)`: `q` son los 4 bits Q4..Q1 del MT8870. Devuelve 1–9 para los códigos 1–9, `0` para el código 10, `DTMF_STAR` (10) para el 11, `DTMF_HASH` (11) para el 12, y `-1` para los códigos 0 y 13–15 (D, A, B, C) o si `q > 15`.
  - `Makefile`:
    - `make test` compila cada `tests/test_*.c` con los `src/*.c` puros (excluye `main.c` y `hal_avr.c`) en `build/host/`, los ejecuta todos y falla si alguno falla.
    - `make` construye `build/pbx.hex` (se completa en la Task 7).
    - `make flash` y `make fuses` usan `PROGRAMMER ?= usbasp`.

- [ ] **Step 1: Escribir `tests/minitest.h` y `tests/test_dtmf.c`**

```c
TEST(maps_digits) {
    CHECK_EQ(dtmf_code_to_digit(1), 1);
    CHECK_EQ(dtmf_code_to_digit(9), 9);
    CHECK_EQ(dtmf_code_to_digit(10), 0);
    CHECK_EQ(dtmf_code_to_digit(11), DTMF_STAR);
    CHECK_EQ(dtmf_code_to_digit(12), DTMF_HASH);
}
TEST(rejects_abcd_and_garbage) {
    CHECK_EQ(dtmf_code_to_digit(0), -1);
    CHECK_EQ(dtmf_code_to_digit(13), -1);
    CHECK_EQ(dtmf_code_to_digit(15), -1);
    CHECK_EQ(dtmf_code_to_digit(16), -1);
}
```

- [ ] **Step 2: Escribir el `Makefile` con el objetivo `test` y verificar que falla**

Run: `make -C firmware test`
Expected: FAIL de compilación o de enlace, porque `dtmf_code_to_digit` no existe.

- [ ] **Step 3: Implementar `dtmf.h` y `dtmf.c`**

- [ ] **Step 4: Verificar que pasa**

Run: `make -C firmware test`
Expected: `test_dtmf: 2 tests, 0 failures` y exit code 0.

- [ ] **Step 5: Commit**

```bash
git add .gitignore firmware/
git commit -m "firmware: estructura, minitest y decodificación DTMF"
```

---

### Task 2: Tabla de tonos y cadencias

**Files:**
- Create: `firmware/src/tones.h`, `firmware/src/tones.c`
- Create: `firmware/src/cadence.h`, `firmware/src/cadence.c`
- Create: `firmware/tests/test_tones.c`, `firmware/tests/test_cadence.c`
- Modify (solo si la verificación lo pide): la tabla del spec §7.7

**Interfaces:**
- Produces:
  - `typedef enum { COUNTRY_AR = 0, COUNTRY_US = 1 } country_t;`
  - `typedef enum { TONE_NONE = 0, TONE_DIAL, TONE_RINGBACK, TONE_BUSY } tone_id_t;`
  - `typedef struct { uint16_t f1_hz, f2_hz, on_ms, off_ms; } signal_spec_t;`
    - `f2_hz = 0` significa un solo tono.
    - `off_ms = 0` significa continuo.
  - `const signal_spec_t *tones_spec(country_t c, tone_id_t t)` devuelve `NULL` para `TONE_NONE`.
  - `const signal_spec_t *tones_ring_spec(country_t c)` devuelve la ring en `f1_hz` (y `f2_hz = 0`).
  - `typedef struct { uint16_t on_ms, off_ms, pos; } cadence_t;`
  - `void cadence_start(cadence_t *c, uint16_t on_ms, uint16_t off_ms)`
  - `bool cadence_tick(cadence_t *c)` devuelve si el ms actual está en "on" y avanza.
    - Después de `start`, las llamadas 1..on_ms devuelven `true` y las siguientes off_ms devuelven `false`, y se repite.
    - `off_ms == 0` siempre devuelve `true`.
    - `on_ms == 0` siempre devuelve `false`.

- [ ] **Step 1: Verificar los valores contra ITU-T E.180 (suplemento de "Various tones used in national networks")**

Buscar las entradas de Argentina y de EE.UU. para invitación a marcar, llamada (ringback) y ocupado, más la frecuencia y la cadencia de la ring.
- Si difieren de la tabla de abajo, usar los valores de E.180, actualizar la tabla del spec §7.7 y anotar la fuente en el commit.
- Si no se encuentra una fuente para algún valor, dejar el de la tabla y marcarlo `// sin verificar` en `tones.c`.

| | AR | US |
|---|---|---|
| DIAL | 425 / 0, continuo | 350 / 440, continuo |
| RINGBACK | 425 / 0, 1000 / 4000 | 440 / 480, 2000 / 4000 |
| BUSY | 425 / 0, 300 / 200 | 480 / 620, 500 / 500 |
| RING | 25 Hz, 1000 / 4000 | 20 Hz, 2000 / 4000 |

- [ ] **Step 2: Escribir los tests**

```c
// test_tones.c
TEST(ar_dial_is_425_continuous) {
    const signal_spec_t *s = tones_spec(COUNTRY_AR, TONE_DIAL);
    CHECK_EQ(s->f1_hz, 425); CHECK_EQ(s->f2_hz, 0); CHECK_EQ(s->off_ms, 0);
}
TEST(us_busy) {
    const signal_spec_t *s = tones_spec(COUNTRY_US, TONE_BUSY);
    CHECK_EQ(s->f1_hz, 480); CHECK_EQ(s->f2_hz, 620);
    CHECK_EQ(s->on_ms, 500); CHECK_EQ(s->off_ms, 500);
}
TEST(none_is_null) { CHECK(tones_spec(COUNTRY_AR, TONE_NONE) == NULL); }
TEST(ring_specs) {
    CHECK_EQ(tones_ring_spec(COUNTRY_AR)->f1_hz, 25);
    CHECK_EQ(tones_ring_spec(COUNTRY_US)->f1_hz, 20);
    CHECK_EQ(tones_ring_spec(COUNTRY_US)->on_ms, 2000);
}
// test_cadence.c
TEST(on_off_boundaries) {
    cadence_t c; cadence_start(&c, 1000, 4000);
    for (int i = 1; i <= 1000; i++) CHECK(cadence_tick(&c));
    for (int i = 1; i <= 4000; i++) CHECK(!cadence_tick(&c));
    CHECK(cadence_tick(&c));            // llamada 5001: arranca otro período
}
TEST(continuous) { cadence_t c; cadence_start(&c, 1, 0);
    for (int i = 0; i < 10000; i++) CHECK(cadence_tick(&c)); }
TEST(never) { cadence_t c; cadence_start(&c, 0, 500);
    for (int i = 0; i < 2000; i++) CHECK(!cadence_tick(&c)); }
```

Si el Step 1 cambió algún valor, ajustar los tests con los valores verificados.

- [ ] **Step 3: Verificar que fallan**

Run: `make -C firmware test`
Expected: FAIL, porque faltan `tones_spec` y `cadence_start`.

- [ ] **Step 4: Implementar `tones.c` (tablas `static const`) y `cadence.c`**

- [ ] **Step 5: Verificar que pasan**

Run: `make -C firmware test`
Expected: todos los tests pasan y exit code 0.

- [ ] **Step 6: Commit**

```bash
git add firmware/ docs/
git commit -m "firmware: tabla de tonos AR/US y cadencias"
```

---

### Task 3: Generador de tonos DDS

**Files:**
- Create: `firmware/src/dds.h`, `firmware/src/dds.c`
- Create: `firmware/tests/test_dds.c`

**Interfaces:**
- Produces:
  - `#define DDS_SAMPLE_RATE_HZ 31250u`. Timer0 hace PWM rápido de 8 bits a 62500 Hz, y la muestra se actualiza cada 2 desbordes.
  - `typedef struct { uint16_t phase1, phase2, inc1, inc2; } dds_t;`
  - `void dds_set(dds_t *d, uint16_t f1_hz, uint16_t f2_hz)`:
    - `inc = round(f * 65536 / DDS_SAMPLE_RATE_HZ)`.
    - `f1 = f2 = 0` es silencio.
    - No resetea la fase si la frecuencia no cambió.
  - `uint8_t dds_next(dds_t *d)`:
    - Con un tono (`f2 = 0`) devuelve la muestra de seno de amplitud completa, 0–255 centrada en 128.
    - Con dos tonos devuelve `(s1 + s2) / 2`.
    - En silencio devuelve 128.
    - Avanza las fases.
  - Tabla de seno de 256 entradas `uint8_t` en `dds.c`, indexada con el byte alto de la fase. En AVR va en `PROGMEM` con `#ifdef __AVR__`; en la PC es un arreglo `const` normal.

- [ ] **Step 1: Escribir los tests**

En el test hay que escribir un helper `double goertzel(dds_t *d, double f, int n)` que genere `n` muestras con `dds_next` (centradas en 0) y devuelva la potencia en `f`.

```c
TEST(single_425_crossings) {
    dds_t d = {0}; dds_set(&d, 425, 0);
    int up = 0; uint8_t prev = dds_next(&d);
    for (int i = 1; i < (int)DDS_SAMPLE_RATE_HZ; i++) {   // 1 segundo
        uint8_t s = dds_next(&d);
        if (prev < 128 && s >= 128) up++;
        prev = s;
    }
    CHECK(up >= 424 && up <= 426);
}
TEST(dual_350_440_has_both_and_not_400) {
    dds_t d = {0}; dds_set(&d, 350, 440);
    double p350 = goertzel(&d, 350, 3125), p440 = goertzel(&d, 440, 3125);
    double p400 = goertzel(&d, 400, 3125);
    CHECK(p350 > 20 * p400); CHECK(p440 > 20 * p400);
}
TEST(silence_is_midscale) {
    dds_t d = {0}; dds_set(&d, 0, 0);
    for (int i = 0; i < 100; i++) CHECK_EQ(dds_next(&d), 128);
}
TEST(single_tone_full_scale) {
    dds_t d = {0}; dds_set(&d, 425, 0); uint8_t lo = 255, hi = 0;
    for (int i = 0; i < 1000; i++) { uint8_t s = dds_next(&d); if (s<lo) lo=s; if (s>hi) hi=s; }
    CHECK(lo <= 2); CHECK(hi >= 253);
}
```

- [ ] **Step 2: Verificar que fallan**

Run: `make -C firmware test`
Expected: FAIL, porque falta `dds_set`.

- [ ] **Step 3: Implementar `dds.c`**

Generar la tabla con un script de una sola vez, `round(127.5 + 127.5*sin(2πi/256))`, y pegarla en el código. No se calcula en tiempo de ejecución en el AVR.

- [ ] **Step 4: Verificar que pasan**

Run: `make -C firmware test`
Expected: todos los tests pasan.

- [ ] **Step 5: Commit**

```bash
git add firmware/
git commit -m "firmware: generador de tonos DDS de 1 y 2 frecuencias"
```

---

### Task 4: Detección de descolgado y de marcado por pulsos

**Files:**
- Create: `firmware/src/hook.h`, `firmware/src/hook.c`
- Create: `firmware/tests/test_hook.c`

**Interfaces:**
- Produces:
  - `typedef enum { HOOK_EV_NONE = 0, HOOK_EV_OFF, HOOK_EV_ON, HOOK_EV_DIGIT } hook_ev_type_t;`
  - `typedef struct { hook_ev_type_t type; uint8_t digit; } hook_ev_t;` (`digit` vale 0–9, y 10 pulsos dan `0`)
  - `void hook_init(hook_t *h)`. Arranca colgado.
  - `hook_ev_t hook_sample(hook_t *h, bool loop_closed, bool masked)`. Se llama cada 1 ms.
  - `bool hook_is_off(const hook_t *h)`
  - Constantes en `hook.h`:
    - `HOOK_OFF_MS 50`: lazo cerrado continuo estando colgado da `OFF`.
    - `HOOK_ON_MS 500`: lazo abierto continuo estando descolgado da `ON`.
    - `PULSE_MIN_MS 20` y `PULSE_MAX_MS 120`: una apertura de esa duración que se vuelve a cerrar cuenta como un pulso.
    - `INTERDIGIT_MS 200`: lazo cerrado ese tiempo después de 1 o más pulsos da `DIGIT`.
    - `MASK_TAIL_MS 50`.
  - Las aperturas de menos de 20 ms o de entre 120 y 500 ms no generan nada.
  - **Máscara:** mientras `masked` es `true`, la muestra se ignora y el estado y los contadores quedan congelados. Durante `MASK_TAIL_MS` después de que `masked` pasa a `false` se sigue ignorando, para que se asiente el relé de ring. Después, la detección sigue normal.

- [ ] **Step 1: Escribir los tests**

En el test hay que escribir un helper `feed(hook_t*, bool closed, int ms, bool masked, hook_ev_t out[], int *n)` que llame a `hook_sample` `ms` veces y junte los eventos distintos de `NONE`.

```c
TEST(offhook_after_50ms) {           // también cubre el arranque con la línea ya descolgada
    hook_t h; hook_init(&h); hook_ev_t e[8]; int n = 0;
    feed(&h, true, 49, false, e, &n); CHECK_EQ(n, 0);
    feed(&h, true, 1, false, e, &n);  CHECK_EQ(n, 1); CHECK_EQ(e[0].type, HOOK_EV_OFF);
}
TEST(short_glitch_is_not_offhook) { /* 10 ms cerrado, después 1000 ms abierto → n == 0 */ }
TEST(pulse_digit_3) {   // 10 pps: 60 ms abierto / 40 ms cerrado
    // descolgar (60 ms cerrado), 3 × (60 abierto + 40 cerrado), después 200 cerrado
    // → eventos: OFF, DIGIT(3); ningún ON
}
TEST(ten_pulses_is_zero) { /* igual, con 10 pulsos → DIGIT(0) */ }
TEST(hangup_after_500ms_open) { /* descolgado, 600 abierto → ON exactamente al ms 500, sin DIGIT */ }
TEST(open_200ms_during_call_does_nothing) {   // Review Focus 4
    /* descolgado, 200 abierto, 1000 cerrado → sin ON y sin DIGIT, hook_is_off sigue en true */
}
TEST(open_15ms_not_counted) { /* descolgado, 15 abierto, 300 cerrado → sin DIGIT */ }
TEST(masked_ring_then_answer) {               // Review Focus 1
    /* colgado; 1000 ms con masked=true y la muestra alternando abierto/cerrado cada 20 ms → n == 0;
       después cerrado con masked=false: sin OFF durante los primeros 50+49 ms, OFF en el ms 100 */
}
```

- [ ] **Step 2: Verificar que fallan**

Run: `make -C firmware test`
Expected: FAIL, porque falta `hook_init`.

- [ ] **Step 3: Implementar `hook.c`**

Es una máquina de estados con dos estados (colgado y descolgado) y contadores de ms del nivel actual, de pulsos acumulados y de la cola de máscara.

- [ ] **Step 4: Verificar que pasan**

Run: `make -C firmware test`
Expected: todos los tests pasan.

- [ ] **Step 5: Commit**

```bash
git add firmware/
git commit -m "firmware: detección de descolgado y marcado por pulsos"
```

---

### Task 5: Máquina de llamada

**Files:**
- Create: `firmware/src/call.h`, `firmware/src/call.c`
- Create: `firmware/tests/test_call.c`

**Interfaces:**
- Consumes: `tone_id_t` (Task 2).
- Produces:
  - `typedef enum { CALL_EV_OFF, CALL_EV_ON, CALL_EV_DIGIT } call_ev_t;`
  - Estados por línea: `LINE_IDLE, LINE_DIALTONE, LINE_DIALING, LINE_RINGBACK, LINE_RINGING, LINE_CONNECTED, LINE_BUSY`, expuestos como `line_state_t call_line_state(const call_t*, uint8_t line)` para los tests.
  - `void call_init(call_t *c)`
  - `void call_event(call_t *c, uint8_t line, call_ev_t ev)`
  - `void call_tick(call_t *c)`. Se llama cada 1 ms.
  - `typedef struct { tone_id_t tone[2]; bool ring[2]; bool link; int8_t dtmf_line; bool led_call; } call_outputs_t;`
    - `ring` es lógico, sin cadencia.
    - `dtmf_line` vale `-1` cuando no hay ninguna línea escuchando.
  - `call_outputs_t call_outputs(const call_t *c)`
  - Constantes: `DIGIT_TIMEOUT_MS 2500`, `NO_DIAL_TIMEOUT_MS 30000`, `RING_TIMEOUT_MS 60000`.

**Reglas** (spec §7.8). "Otra" es `1 - línea`.

- `IDLE` + `OFF` → `DIALTONE`, con tono `DIAL`.
- `DIALTONE` + `DIGIT` → `DIALING`, sin tono. Cada dígito en `DIALING` reinicia el temporizador de fin de número.
- `DIALTONE` durante `NO_DIAL_TIMEOUT_MS` → `BUSY`.
- `DIALING` durante `DIGIT_TIMEOUT_MS` sin dígitos:
  - Si la otra no está en `IDLE` → `BUSY`.
  - Si no → la línea pasa a `RINGBACK` (tono `RINGBACK`) y la otra a `RINGING` (`ring = true`).
- `RINGING` + `OFF` → las dos pasan a `CONNECTED`: `link` y `led_call` en `true`, sin tonos, sin ring.
- `RINGBACK` + `ON` → las dos pasan a `IDLE`.
- `RINGBACK` durante `RING_TIMEOUT_MS` → el llamador pasa a `BUSY` y el llamado a `IDLE`.
- `CONNECTED` + `ON` de una → esa pasa a `IDLE` y la otra a `BUSY`.
- `BUSY` + `ON` → `IDLE`.
- Cualquier estado + `ON` → `IDLE`, y si estaba en llamada se aplica la regla anterior para la otra.
- `DIGIT` en cualquier estado que no sea `DIALTONE` o `DIALING` se ignora.
- `dtmf_line`:
  - Es la línea en `DIALTONE` o `DIALING` que entró primero a ese estado.
  - Si deja de estarlo, pasa a la otra si está en `DIALTONE` o `DIALING`.
  - Si no hay ninguna, vale `-1`.

- [ ] **Step 1: Escribir los tests**

En el test hay que escribir un helper `ticks(call_t*, int ms)`.

```c
TEST(idle_outputs) { call_t c; call_init(&c); call_outputs_t o = call_outputs(&c);
    CHECK_EQ(o.tone[0], TONE_NONE); CHECK(!o.ring[1]); CHECK(!o.link); CHECK_EQ(o.dtmf_line, -1); }
TEST(offhook_gives_dialtone) { /* OFF L0 → tone[0]==TONE_DIAL, dtmf_line==0 */ }
TEST(digit_timeout_boundary) {
    /* OFF L0, DIGIT L0; ticks 2499 → estado DIALING, tone[0]==NONE;
       1 tick más → tone[0]==TONE_RINGBACK, ring[1]==true, ring[0]==false */
}
TEST(each_digit_restarts_timer) { /* DIGIT, 2000 ms, DIGIT, 2000 ms → sigue DIALING */ }
TEST(answer_connects) { /* ... llega a RINGING; OFF L1 → link, led_call, sin tonos, sin ring, dtmf_line==-1 */ }
TEST(hangup_in_call_gives_busy_to_other) { /* CONNECTED; ON L1 → tone[0]==TONE_BUSY, !link, !led_call */ }
TEST(called_offhook_gives_busy) {
    /* OFF L1 (DIALTONE); OFF L0, DIGIT L0, 2500 ms → tone[0]==BUSY, tone[1]==DIAL, dtmf_line==1 */
}
TEST(no_dial_timeout) { /* OFF L0, 29999 → DIAL; +1 → BUSY */ }
TEST(ring_timeout) { /* RINGBACK; 60000 ms → tone[0]==BUSY, !ring[1], L1 IDLE */ }
TEST(caller_abandons) { /* RINGBACK; ON L0 → todo IDLE, !ring[1] */ }
TEST(first_offhook_owns_dtmf) { /* OFF L1, OFF L0 → dtmf_line==1 */ }
TEST(blind_dial_digit_right_after_offhook) {   // Review Focus 2
    /* OFF L0 e inmediatamente DIGIT L0, sin ticks → DIALING */
}
TEST(digits_ignored_when_connected) {          // Review Focus 3
    /* CONNECTED; DIGIT L0 y DIGIT L1, 5000 ms → sigue CONNECTED, link true, dtmf_line == -1 */
}
TEST(busy_then_hangup_is_idle) { /* BUSY L0; ON L0 → IDLE */ }
```

- [ ] **Step 2: Verificar que fallan**

Run: `make -C firmware test`
Expected: FAIL, porque falta `call_init`.

- [ ] **Step 3: Implementar `call.c`**

- [ ] **Step 4: Verificar que pasan**

Run: `make -C firmware test`
Expected: todos los tests pasan.

- [ ] **Step 5: Commit**

```bash
git add firmware/
git commit -m "firmware: máquina de llamada de 2 líneas"
```

---

### Task 6: Señales (de la salida lógica a tonos y ring con cadencia)

**Files:**
- Create: `firmware/src/signals.h`, `firmware/src/signals.c`
- Create: `firmware/tests/test_signals.c`

**Interfaces:**
- Consumes: `call_outputs_t` (Task 5), `tones_spec`, `tones_ring_spec` y `cadence_*` (Task 2).
- Produces:
  - `typedef struct { uint16_t f1[2], f2[2]; bool ring_on[2]; bool ring_phase; } signals_out_t;`
    - `f1 = f2 = 0` es silencio.
    - `ring_phase` es la polaridad del puente H.
  - `void signals_init(signals_t *s)`
  - `void signals_tick(signals_t *s, const call_outputs_t *o, country_t c, signals_out_t *out)`. Se llama cada 1 ms.
  - Comportamiento:
    - La cadencia de cada línea se reinicia en "on" cuando cambia su `tone` o su `ring`.
    - Las frecuencias salen de la tabla del país `c` **en cada tick**, así que la llave AR/US actúa en el momento.
    - Mientras hay algún `ring_on`, `ring_phase` se invierte cada `500 / f_ring` ms: 20 ms en AR, 25 ms en US.
    - Si no hay ring, `ring_phase` queda en `false`.

- [ ] **Step 1: Escribir los tests**

```c
TEST(ar_ringback_cadence) {
    /* tone[0]=RINGBACK, AR: los ticks 1..1000 dan f1[0]==425; 1001..5000 dan f1[0]==0; el 5001 da 425 */
}
TEST(us_busy_dual) { /* tone[0]=BUSY, US: tick 1 → f1 480, f2 620; tick 501 → 0,0; tick 1001 → 480 */ }
TEST(dial_continuous) { /* tone[1]=DIAL, AR: 10000 ticks con f1[1]==425 */ }
TEST(ar_ring_cadence_and_phase) {
    /* ring[1]=true, AR: ring_on[1] en 1..1000 y false en 1001..5000;
       ring_phase cambia en los ticks 21, 41, 61… durante el "on" */
}
TEST(us_ring_phase_25ms) { /* US: ring_phase cambia en los ticks 26, 51… y ring_on dura 2000 */ }
TEST(cadence_restarts_on_change) {
    /* RINGBACK durante 1500 ticks (en "off"), después BUSY → el primer tick de BUSY suena */
}
TEST(country_switch_mid_tone) {                 // Review Focus 5
    /* DIAL con AR durante 100 ticks (f1 425), 1 tick con US → f1 350, f2 440 */
}
```

- [ ] **Step 2: Verificar que fallan**

Run: `make -C firmware test`
Expected: FAIL, porque falta `signals_init`.

- [ ] **Step 3: Implementar `signals.c`**

- [ ] **Step 4: Verificar que pasan**

Run: `make -C firmware test`
Expected: todos los tests pasan.

- [ ] **Step 5: Commit**

```bash
git add firmware/
git commit -m "firmware: cadencias de tonos y ring por país"
```

---

### Task 7: HAL del AVR, `main.c` y build del `.hex`

**Files:**
- Create: `firmware/src/hal.h`, `firmware/src/hal_avr.c`, `firmware/src/main.c`
- Modify: `firmware/Makefile` (objetivos `all`, `flash`, `fuses` y `size`)
- Modify: `docs/superpowers/specs/2026-11-13-pbx-2-lineas-design.md` §7.1: la línea `ATmega PWM ─► filtro RC ─► inyección de tono en L1 / L2 (conmutable)` pasa a ser `ATmega PWM ×2 (OC0A→L1, OC0B→L2) ─► filtro RC ×2 ─► inyección de tono por línea`.
- Create: `firmware/README.md` (cómo compilar, probar, grabar los fusibles y flashear; mapa de pines)

**Interfaces:**
- Consumes: todo lo anterior.
- Produces, en `hal.h`, usado solo por `main.c`:
  - `void hal_init(void)`
  - `bool hal_loop_closed(uint8_t line)`
  - `bool hal_dtmf_std(void)`
  - `uint8_t hal_dtmf_code(void)`
  - `void hal_set_ring_en(uint8_t line, bool on)`
  - `void hal_set_ring_drive(bool phase)`
  - `void hal_set_link(bool on)`
  - `void hal_set_dtmf_sel(uint8_t line)`
  - `void hal_set_led_call(bool on)`
  - `country_t hal_country(void)`
  - `void hal_set_tones(uint8_t line, uint16_t f1, uint16_t f2)`. Actualiza el `dds_t` de esa línea con las interrupciones bloqueadas.
  - `volatile` bandera de tick de 1 ms, `hal_tick_pending()` / `hal_tick_clear()`.
  - Todo según el **mapa de pines** de Global Constraints.

**Comportamiento de `main.c`**, un bucle en cada tick de 1 ms:

1. Por línea: `hook_sample(&hook[l], hal_loop_closed(l), masked = ring_on[l] del tick anterior)`. Los eventos `OFF`, `ON` y `DIGIT` se pasan a `call_event`.
2. Flanco de subida de `hal_dtmf_std()`: si `call_outputs().dtmf_line >= 0` y `dtmf_code_to_digit(hal_dtmf_code()) >= 0`, se manda `call_event(dtmf_line, CALL_EV_DIGIT)`.
3. `call_tick`, después `signals_tick(..., hal_country(), &out)`.
4. Se aplican las salidas: `hal_set_tones` por línea (solo si cambió), `hal_set_ring_en(l, out.ring_on[l])`, `hal_set_ring_drive(out.ring_phase)`, `hal_set_link`, `hal_set_dtmf_sel` (si `dtmf_line` vale `-1`, se mantiene el último valor) y `hal_set_led_call`.

Los timers:
- **Timer0:** PWM rápido de 8 bits sin prescaler en OC0A y OC0B. La ISR de desborde, cada 2 llamadas, escribe `OCR0A = dds_next(&dds[0])` y `OCR0B = dds_next(&dds[1])`.
- **Timer1:** CTC a 1 kHz para el tick.

Fusibles: `lfuse 0xFF`, `hfuse 0xD9`, `efuse 0xFF` (cristal externo de 16 MHz, sin CKDIV8).

- [ ] **Step 1: Escribir `hal.h`, `hal_avr.c` y `main.c`, y completar el `Makefile`**

- [ ] **Step 2: Compilar para el AVR**

Run: `make -C firmware clean all size`
Expected:
- se genera `firmware/build/pbx.hex` sin warnings;
- `avr-size` muestra Program menor a 32256 bytes y Data menor a 2048 bytes;
- la ISR de Timer0 no tiene operaciones de punto flotante (`avr-objdump -d build/pbx.elf | grep -c __fp` da 0).

- [ ] **Step 3: Verificar que las pruebas en la PC siguen pasando**

Run: `make -C firmware test`
Expected: todos los tests pasan.

- [ ] **Step 4: Commit**

```bash
git add firmware/ docs/
git commit -m "firmware: HAL ATmega328P, bucle principal y build"
```

- [ ] **Step 5 (usuario, con hardware): prueba de humo en un ATmega en protoboard**

Grabar los fusibles y el firmware con `make fuses flash`. Con un parlante o un osciloscopio a través de un RC (1 kΩ + 100 nF) en PD6, poner PC0 a GND:
- a los 50 ms se escucha el tono de invitación de 425 Hz;
- con PD0 a GND pasa a 350+440 Hz;
- PC0 abierto más de 500 ms lo corta.

---

### Task 8: Documento de la prueba de banco (una línea contra el Modem 1200)

**Files:**
- Create: `docs/prueba-banco.md`

**Interfaces:**
- Consumes: el mapa de pines (Global Constraints) y el firmware de la Task 7.
- Produces: el procedimiento y la tabla de resultados que el **segundo plan** (KiCad) usa para fijar `V_LINE`, la tensión de ring y la opción de acople.

**Contenido obligatorio del documento** (spec §7.3–7.5 y §8):

1. **Circuito de prueba propuesto**, con esquema en texto y valores de partida. Todos los componentes tienen que ser pasantes y fáciles de conseguir en Argentina, y deben figurar en una lista de materiales:
   - un elevador de 12 V a `V_LINE` ajustable entre 24 y 48 V;
   - un limitador de corriente de lazo de 20–30 mA;
   - un optoacoplador de descolgado hacia PC0;
   - un generador de ring (elevador más puente H manejado por `RING_DRIVE`), con corriente limitada;
   - un relé de ring por ULN2003A desde PB0;
   - el acople por capacitor de film de 250 V hacia el filtro RC de PD6 y hacia el MT8870.
2. **Advertencias de seguridad:** qué nodos llevan alta tensión, que hay que descargar los capacitores, y que no se toca nada con la ring activa.
3. **Procedimiento** de las 4 validaciones del spec §8, cada una con criterio de éxito medible:
   1. Descolgado: el firmware ve `OFF` en 10 de 10 descuelgues con el Modem 1200 (`ATH1`) y `ON` con `ATH0`, para cada `V_LINE` probado (24, 36 y 48 V).
   2. Ring: con `ATS0=1`, el módem atiende en 5 de 5 llamadas. Se registra la tensión de ring medida en V rms.
   3. Ring trip: después de atender, la ring se corta antes de que termine la ráfaga siguiente y el LED LÍNEA se enciende.
   4. Negociación: con dos líneas improvisadas (Modem 1200 contra el módem de la PC), hay `CONNECT 1200` en 5 de 5 intentos, y se pasan 10 minutos de texto sin errores visibles. Si falla, se repite con un transformador 600:600 y se registra el resultado.
4. **Tabla de resultados** para completar: fecha, `V_LINE`, corriente de lazo, V rms de ring, resultados de cada validación, opción de acople elegida y observaciones.

- [ ] **Step 1: Escribir `docs/prueba-banco.md` con los 4 contenidos de arriba**

- [ ] **Step 2: Verificar que el documento está completo**

Run: `grep -c "^## " docs/prueba-banco.md`
Expected: 4 o más, con secciones para circuito y materiales, seguridad, procedimiento y resultados. Además:
- cada validación tiene un criterio "N de N" o un valor medible;
- la lista de materiales no tiene componentes SMD.

- [ ] **Step 3: Commit**

```bash
git add docs/prueba-banco.md
git commit -m "docs: procedimiento de la prueba de banco de una línea"
```

- [ ] **Step 4 (usuario):** armar la prueba, completar la tabla de resultados y commitearla. Con esos resultados se escribe el plan 2: esquemático y PCB en KiCad.
