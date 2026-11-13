/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Cesar Kastli */
#include "pots.h"
#include "dtmf.h"

void pots_init(pots_t *p) {
    hook_init(&p->hook[0]);
    hook_init(&p->hook[1]);
    call_init(&p->call);
    signals_init(&p->sig);
    p->ring_on_prev[0] = p->ring_on_prev[1] = false;
    p->last_std[0] = p->last_std[1] = false;
    p->last_country = 0xFF;
}

static void emit(pots_outputs_t *out, uint8_t type, uint8_t line, uint8_t value) {
    if (out->n_events >= POTS_MAX_EVENTS) return;
    pots_event_t e = { type, line, value };
    out->events[out->n_events++] = e;
}

void pots_step(pots_t *p, const pots_inputs_t *in, pots_outputs_t *out) {
    out->n_events = 0;
    if (in->country != p->last_country) {
        emit(out, POTS_EV_COUNTRY, 0, (uint8_t)in->country);
        p->last_country = (uint8_t)in->country;
    }
    line_state_t before[2] = { call_line_state(&p->call, 0), call_line_state(&p->call, 1) };

    /* 1. Hook and pulses; the loop is ignored while the ring was on
     *    (previous tick). */
    for (uint8_t l = 0; l < 2; l++) {
        hook_ev_t e = hook_sample(&p->hook[l], in->loop_closed[l], p->ring_on_prev[l]);
        if (e.type == HOOK_EV_OFF) {
            emit(out, POTS_EV_HOOK_OFF, l, 0);
            call_event(&p->call, l, CALL_EV_OFF);
        } else if (e.type == HOOK_EV_ON) {
            emit(out, POTS_EV_HOOK_ON, l, 0);
            call_event(&p->call, l, CALL_EV_ON);
        } else if (e.type == HOOK_EV_DIGIT) {
            emit(out, POTS_EV_PULSE_DIGIT, l, e.digit);
            call_event(&p->call, l, CALL_EV_DIGIT);
        }
    }

    /* 2. DTMF: one MT8870 per line on a shared Q bus. A digit counts on the
     *    StD rising edge, unless the other chip is also driving the bus. */
    bool both = in->dtmf_std[0] && in->dtmf_std[1];
    for (uint8_t l = 0; l < 2; l++) {
        if (in->dtmf_std[l] && !p->last_std[l]) {
            int8_t digit = dtmf_code_to_digit(in->dtmf_code);
            if (both) {
                emit(out, POTS_EV_DTMF_COLLISION, l, 0);
            } else if (digit >= 0) {
                emit(out, POTS_EV_DTMF_DIGIT, l, (uint8_t)digit);
                call_event(&p->call, l, CALL_EV_DIGIT);
            }
        }
        p->last_std[l] = in->dtmf_std[l];
    }

    /* 3. Logic. */
    call_tick(&p->call);
    call_outputs_t o = call_outputs(&p->call);
    signals_out_t s;
    signals_tick(&p->sig, &o, in->country, &s);

    /* 4. Outputs. */
    for (uint8_t l = 0; l < 2; l++) {
        out->f1[l] = s.f1[l];
        out->f2[l] = s.f2[l];
        out->ring_en[l] = s.ring_on[l];
        p->ring_on_prev[l] = s.ring_on[l];
    }
    out->ring_drive = s.ring_phase;
    out->link = o.link;
    out->led_call = o.led_call;
    for (uint8_t l = 0; l < 2; l++) {
        line_state_t now = call_line_state(&p->call, l);
        if (now != before[l]) emit(out, POTS_EV_STATE, l, (uint8_t)now);
    }
}
