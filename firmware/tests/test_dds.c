/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Cesar Kastli */
#include <math.h>
#include "minitest.h"
#include "../src/dds.h"

/* Power at f over n samples of dds_next (centred on 0). */
static double goertzel(dds_t *d, double f, int n) {
    double w = 2.0 * M_PI * f / DDS_SAMPLE_RATE_HZ, k = 2.0 * cos(w);
    double s1 = 0, s2 = 0;
    for (int i = 0; i < n; i++) {
        double s = (double)dds_next(d) - 128.0 + k * s1 - s2;
        s2 = s1; s1 = s;
    }
    return s1 * s1 + s2 * s2 - k * s1 * s2;
}

TEST(single_425_crossings) {
    dds_t d = {0}; dds_set(&d, 425, 0);
    int up = 0; uint8_t prev = dds_next(&d);
    for (int i = 1; i < (int)DDS_SAMPLE_RATE_HZ; i++) { /* 1 second */
        uint8_t s = dds_next(&d);
        if (prev < 128 && s >= 128) up++;
        prev = s;
    }
    CHECK(up >= 424 && up <= 426);
}
TEST(dual_350_440_has_both_and_not_400) {
    dds_t a = {0}, b = {0}, c = {0};
    dds_set(&a, 350, 440); dds_set(&b, 350, 440); dds_set(&c, 350, 440);
    double p350 = goertzel(&a, 350, 3125), p440 = goertzel(&b, 440, 3125);
    double p400 = goertzel(&c, 400, 3125);
    CHECK(p350 > 20 * p400); CHECK(p440 > 20 * p400);
}
TEST(silence_is_midscale) {
    dds_t d = {0}; dds_set(&d, 0, 0);
    for (int i = 0; i < 100; i++) CHECK_EQ(dds_next(&d), 128);
}
TEST(single_tone_full_scale) {
    dds_t d = {0}; dds_set(&d, 425, 0); uint8_t lo = 255, hi = 0;
    for (int i = 0; i < 1000; i++) {
        uint8_t s = dds_next(&d);
        if (s < lo) lo = s;
        if (s > hi) hi = s;
    }
    CHECK(lo <= 2); CHECK(hi >= 253);
}
TEST(same_freq_keeps_phase) {
    dds_t d = {0}; dds_set(&d, 425, 0);
    for (int i = 0; i < 37; i++) dds_next(&d);
    uint16_t ph = d.phase1;
    dds_set(&d, 425, 0);
    CHECK_EQ(d.phase1, ph);
}

TEST(increment_is_rounded) { /* final review #6: computed outside cli */
    CHECK_EQ(dds_increment(425), 891);
    CHECK_EQ(dds_increment(0), 0);
    dds_t d = {0}; dds_set_increments(&d, 891, 0); CHECK_EQ(d.inc1, 891);
}

int main(void) {
    RUN(increment_is_rounded);
    RUN(single_425_crossings); RUN(dual_350_440_has_both_and_not_400);
    RUN(silence_is_midscale); RUN(single_tone_full_scale); RUN(same_freq_keeps_phase);
    MINITEST_MAIN_END("test_dds");
}
