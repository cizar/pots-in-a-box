/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Cesar Kastli */
/* hook.h — off-hook/on-hook detection and pulse-dial decoding.
 * Fed with one loop sample per ms. */
#ifndef HOOK_H
#define HOOK_H

#include <stdbool.h>
#include <stdint.h>

#define HOOK_OFF_MS    50  /* loop closed this long while on-hook -> OFF  */
#define HOOK_ON_MS     500 /* loop open this long while off-hook -> ON    */
#define PULSE_MIN_MS   20  /* a break of 20..120 ms counts as a pulse     */
#define PULSE_MAX_MS   120
#define INTERDIGIT_MS  200 /* loop closed after >=1 pulse -> DIGIT        */
#define MASK_TAIL_MS   150 /* ignored after the mask: relay + coupling-cap recharge */

typedef enum { HOOK_EV_NONE = 0, HOOK_EV_OFF, HOOK_EV_ON, HOOK_EV_DIGIT } hook_ev_type_t;

typedef struct {
    hook_ev_type_t type;
    uint8_t digit; /* 0-9; 10 pulses = 0 */
} hook_ev_t;

typedef struct {
    bool off;
    uint16_t closed_ms, open_ms, mask_tail;
    uint8_t pulses;
} hook_t;

void hook_init(hook_t *h);
/* masked: ignore the sample (ring active) and freeze the state. */
hook_ev_t hook_sample(hook_t *h, bool loop_closed, bool masked);
bool hook_is_off(const hook_t *h);

#endif
