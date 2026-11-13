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
}

void pots_step(pots_t *p, const pots_inputs_t *in, pots_outputs_t *out) {
    /* 1. Hook and pulses; the loop is ignored while the ring was on
     *    (previous tick). */
    for (uint8_t l = 0; l < 2; l++) {
        hook_ev_t e = hook_sample(&p->hook[l], in->loop_closed[l], p->ring_on_prev[l]);
        if (e.type == HOOK_EV_OFF) call_event(&p->call, l, CALL_EV_OFF);
        else if (e.type == HOOK_EV_ON) call_event(&p->call, l, CALL_EV_ON);
        else if (e.type == HOOK_EV_DIGIT) call_event(&p->call, l, CALL_EV_DIGIT);
    }

    /* 2. DTMF: one MT8870 per line on a shared Q bus. A digit counts on the
     *    StD rising edge, unless the other chip is also driving the bus. */
    bool both = in->dtmf_std[0] && in->dtmf_std[1];
    for (uint8_t l = 0; l < 2; l++) {
        if (in->dtmf_std[l] && !p->last_std[l] && !both &&
            dtmf_code_to_digit(in->dtmf_code) >= 0)
            call_event(&p->call, l, CALL_EV_DIGIT);
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
}
