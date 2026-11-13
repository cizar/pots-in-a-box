#include "signals.h"

void signals_init(signals_t *s) {
    for (uint8_t l = 0; l < 2; l++) {
        s->tone[l] = TONE_NONE;
        s->ring[l] = false;
        cadence_start(&s->tone_cad[l], 0, 0);
        cadence_start(&s->ring_cad[l], 0, 0);
    }
    s->country = COUNTRY_AR;
    s->phase_ms = 0;
    s->phase = false;
}

void signals_tick(signals_t *s, const call_outputs_t *o, country_t c, signals_out_t *out) {
    const signal_spec_t *rs = tones_ring_spec(c);
    bool country_changed = c != s->country;
    s->country = c;
    bool any_ring = false;

    for (uint8_t l = 0; l < 2; l++) {
        const signal_spec_t *ts = tones_spec(c, o->tone[l]);

        /* La cadencia arranca en "on" cuando cambia el tono o el país. */
        if (o->tone[l] != s->tone[l] || country_changed) {
            s->tone[l] = o->tone[l];
            if (ts) cadence_start(&s->tone_cad[l], ts->on_ms, ts->off_ms);
            else cadence_start(&s->tone_cad[l], 0, 0);
        }
        bool tone_on = cadence_tick(&s->tone_cad[l]);
        out->f1[l] = (ts && tone_on) ? ts->f1_hz : 0;
        out->f2[l] = (ts && tone_on) ? ts->f2_hz : 0;

        if (o->ring[l] != s->ring[l] || country_changed) {
            s->ring[l] = o->ring[l];
            if (o->ring[l]) cadence_start(&s->ring_cad[l], rs->on_ms, rs->off_ms);
            else cadence_start(&s->ring_cad[l], 0, 0);
        }
        out->ring_on[l] = cadence_tick(&s->ring_cad[l]);
        any_ring = any_ring || out->ring_on[l];
    }

    /* Puente H: media onda de 500/f ms mientras haya ring. */
    if (any_ring) {
        uint8_t half = (uint8_t)(500u / rs->f1_hz);
        if (s->phase_ms >= half) {
            s->phase = !s->phase;
            s->phase_ms = 0;
        }
        s->phase_ms++;
    } else {
        s->phase = false;
        s->phase_ms = 0;
    }
    out->ring_phase = s->phase;
}
