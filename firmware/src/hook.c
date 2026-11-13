/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Cesar Kastli */
#include "hook.h"

void hook_init(hook_t *h) {
    h->off = false;
    h->closed_ms = h->open_ms = h->mask_tail = 0;
    h->pulses = 0;
}

bool hook_is_off(const hook_t *h) { return h->off; }

static hook_ev_t ev(hook_ev_type_t t, uint8_t d) {
    hook_ev_t e = { t, d };
    return e;
}

hook_ev_t hook_sample(hook_t *h, bool closed, bool masked) {
    if (masked) {
        h->mask_tail = MASK_TAIL_MS;
        return ev(HOOK_EV_NONE, 0);
    }
    if (h->mask_tail) {
        h->mask_tail--;
        return ev(HOOK_EV_NONE, 0);
    }

    if (!h->off) {
        /* On-hook: wait for a stable closed loop. */
        if (!closed) {
            h->closed_ms = 0;
            return ev(HOOK_EV_NONE, 0);
        }
        if (++h->closed_ms >= HOOK_OFF_MS) {
            h->off = true;
            h->closed_ms = h->open_ms = 0;
            h->pulses = 0;
            return ev(HOOK_EV_OFF, 0);
        }
        return ev(HOOK_EV_NONE, 0);
    }

    /* Off-hook. */
    if (!closed) {
        h->closed_ms = 0;
        if (h->open_ms < UINT16_MAX) h->open_ms++;
        if (h->open_ms == HOOK_ON_MS) {
            h->off = false;
            h->open_ms = 0;
            h->pulses = 0;
            return ev(HOOK_EV_ON, 0);
        }
        return ev(HOOK_EV_NONE, 0);
    }

    if (h->open_ms) {
        /* Loop closed again: was it a pulse? Other breaks are ignored. */
        if (h->open_ms >= PULSE_MIN_MS && h->open_ms <= PULSE_MAX_MS) h->pulses++;
        h->open_ms = 0;
    }
    if (h->closed_ms < UINT16_MAX) h->closed_ms++;
    if (h->pulses && h->closed_ms == INTERDIGIT_MS) {
        uint8_t d = (uint8_t)(h->pulses % 10);
        h->pulses = 0;
        return ev(HOOK_EV_DIGIT, d);
    }
    return ev(HOOK_EV_NONE, 0);
}
