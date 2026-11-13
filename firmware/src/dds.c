/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Cesar Kastli */
#include "dds.h"

#ifdef __AVR__
#include <avr/pgmspace.h>
#define SINE(i) pgm_read_byte(&SINE_TABLE[(i)])
#else
#define PROGMEM
#define SINE(i) (SINE_TABLE[(i)])
#endif

/* round(127.5 + 127.5 * sin(2*pi*i/256)) */
static const uint8_t SINE_TABLE[256] PROGMEM = {
    128, 131, 134, 137, 140, 143, 146, 149, 152, 155, 158, 162, 165, 167, 170, 173,
    176, 179, 182, 185, 188, 190, 193, 196, 198, 201, 203, 206, 208, 211, 213, 215,
    218, 220, 222, 224, 226, 228, 230, 232, 234, 235, 237, 238, 240, 241, 243, 244,
    245, 246, 248, 249, 250, 250, 251, 252, 253, 253, 254, 254, 254, 255, 255, 255,
    255, 255, 255, 255, 254, 254, 254, 253, 253, 252, 251, 250, 250, 249, 248, 246,
    245, 244, 243, 241, 240, 238, 237, 235, 234, 232, 230, 228, 226, 224, 222, 220,
    218, 215, 213, 211, 208, 206, 203, 201, 198, 196, 193, 190, 188, 185, 182, 179,
    176, 173, 170, 167, 165, 162, 158, 155, 152, 149, 146, 143, 140, 137, 134, 131,
    128, 124, 121, 118, 115, 112, 109, 106, 103, 100,  97,  93,  90,  88,  85,  82,
     79,  76,  73,  70,  67,  65,  62,  59,  57,  54,  52,  49,  47,  44,  42,  40,
     37,  35,  33,  31,  29,  27,  25,  23,  21,  20,  18,  17,  15,  14,  12,  11,
     10,   9,   7,   6,   5,   5,   4,   3,   2,   2,   1,   1,   1,   0,   0,   0,
      0,   0,   0,   0,   1,   1,   1,   2,   2,   3,   4,   5,   5,   6,   7,   9,
     10,  11,  12,  14,  15,  17,  18,  20,  21,  23,  25,  27,  29,  31,  33,  35,
     37,  40,  42,  44,  47,  49,  52,  54,  57,  59,  62,  65,  67,  70,  73,  76,
     79,  82,  85,  88,  90,  93,  97, 100, 103, 106, 109, 112, 115, 118, 121, 124
};

uint16_t dds_increment(uint16_t f_hz) {
    return (uint16_t)(((uint32_t)f_hz * 65536u + DDS_SAMPLE_RATE_HZ / 2) / DDS_SAMPLE_RATE_HZ);
}

void dds_set_increments(dds_t *d, uint16_t inc1, uint16_t inc2) {
    d->inc1 = inc1;
    d->inc2 = inc2;
}

void dds_set(dds_t *d, uint16_t f1_hz, uint16_t f2_hz) {
    dds_set_increments(d, dds_increment(f1_hz), dds_increment(f2_hz));
}

uint8_t dds_next(dds_t *d) {
    uint8_t out;
    if (d->inc1 == 0 && d->inc2 == 0) {
        out = 128;
    } else if (d->inc2 == 0) {
        out = SINE(d->phase1 >> 8);
    } else {
        out = (uint8_t)(((uint16_t)SINE(d->phase1 >> 8) + SINE(d->phase2 >> 8)) >> 1);
    }
    d->phase1 += d->inc1;
    d->phase2 += d->inc2;
    return out;
}
