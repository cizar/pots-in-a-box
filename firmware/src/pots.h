/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Cesar Kastli */
/* pots.h — one 1 ms tick of the exchange: hardware inputs ->
 * detection -> logic -> outputs. Pure: main.c wires it to the HAL. */
#ifndef POTS_H
#define POTS_H

#include <stdbool.h>
#include <stdint.h>
#include "call.h"
#include "hook.h"
#include "signals.h"
#include "tones.h"

typedef struct {
    bool loop_closed[2];
    bool dtmf_std[2];    /* StD of each line's MT8870 (TOE tied to StD) */
    uint8_t dtmf_code;   /* shared Q4..Q1 bus */
    country_t country;
} pots_inputs_t;

/* Debug events, one list per tick (printed over the UART by main.c). */
typedef enum {
    POTS_EV_HOOK_OFF = 0,
    POTS_EV_HOOK_ON,
    POTS_EV_PULSE_DIGIT,     /* value: 0-9 */
    POTS_EV_DTMF_DIGIT,      /* value: 0-9, DTMF_STAR, DTMF_HASH */
    POTS_EV_DTMF_COLLISION,  /* both StD high: digit discarded */
    POTS_EV_STATE,           /* value: line_state_t after the tick */
    POTS_EV_COUNTRY          /* value: country_t; at start and on change */
} pots_ev_type_t;

typedef struct {
    uint8_t type, line, value;
} pots_event_t;

#define POTS_MAX_EVENTS 8

typedef struct {
    uint16_t f1[2], f2[2];  /* tone per line; 0,0 = silence */
    bool ring_en[2];
    bool ring_drive;
    bool link;
    bool led_call;
    pots_event_t events[POTS_MAX_EVENTS];
    uint8_t n_events;
} pots_outputs_t;

typedef struct {
    hook_t hook[2];
    call_t call;
    signals_t sig;
    bool ring_on_prev[2];
    bool last_std[2];
    uint8_t last_country; /* 0xFF until the first tick */
} pots_t;

void pots_init(pots_t *p);
void pots_step(pots_t *p, const pots_inputs_t *in, pots_outputs_t *out);

#endif
