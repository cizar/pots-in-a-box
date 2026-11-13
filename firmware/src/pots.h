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

typedef struct {
    uint16_t f1[2], f2[2];  /* tone per line; 0,0 = silence */
    bool ring_en[2];
    bool ring_drive;
    bool link;
    bool led_call;
} pots_outputs_t;

typedef struct {
    hook_t hook[2];
    call_t call;
    signals_t sig;
    bool ring_on_prev[2];
    bool last_std[2];
} pots_t;

void pots_init(pots_t *p);
void pots_step(pots_t *p, const pots_inputs_t *in, pots_outputs_t *out);

#endif
