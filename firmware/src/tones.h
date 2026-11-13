/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Cesar Kastli */
/* tones.h — per-country tone and ring table (ITU-T E.180). */
#ifndef TONES_H
#define TONES_H

#include <stdint.h>

typedef enum { COUNTRY_AR = 0, COUNTRY_US = 1 } country_t;
typedef enum { TONE_NONE = 0, TONE_DIAL, TONE_RINGBACK, TONE_BUSY } tone_id_t;

/* f2_hz = 0: single tone. off_ms = 0: continuous. */
typedef struct {
    uint16_t f1_hz, f2_hz, on_ms, off_ms;
} signal_spec_t;

/* NULL for TONE_NONE. */
const signal_spec_t *tones_spec(country_t c, tone_id_t t);
/* Ring frequency in f1_hz, plus its cadence. */
const signal_spec_t *tones_ring_spec(country_t c);

#endif
