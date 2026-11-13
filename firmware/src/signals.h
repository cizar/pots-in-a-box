/* signals.h — de la salida lógica de la llamada a frecuencias y ring
 * con la cadencia del país. Tick de 1 ms. */
#ifndef SIGNALS_H
#define SIGNALS_H

#include <stdbool.h>
#include <stdint.h>
#include "cadence.h"
#include "call.h"
#include "tones.h"

typedef struct {
    uint16_t f1[2], f2[2]; /* 0,0 = silencio */
    bool ring_on[2];
    bool ring_phase;       /* polaridad del puente H */
} signals_out_t;

typedef struct {
    tone_id_t tone[2];
    bool ring[2];
    country_t country;
    cadence_t tone_cad[2], ring_cad[2];
    uint8_t phase_ms;
    bool phase;
} signals_t;

void signals_init(signals_t *s);
void signals_tick(signals_t *s, const call_outputs_t *o, country_t c, signals_out_t *out);

#endif
