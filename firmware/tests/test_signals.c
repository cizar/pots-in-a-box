#include <string.h>
#include "minitest.h"
#include "../src/signals.h"

static call_outputs_t none(void) {
    call_outputs_t o; memset(&o, 0, sizeof o); o.dtmf_line = -1; return o;
}

TEST(ar_ringback_cadence) {
    signals_t s; signals_init(&s); signals_out_t out;
    call_outputs_t o = none(); o.tone[0] = TONE_RINGBACK;
    for (int t = 1; t <= 1000; t++) { signals_tick(&s, &o, COUNTRY_AR, &out); CHECK_EQ(out.f1[0], 425); }
    for (int t = 1001; t <= 5000; t++) { signals_tick(&s, &o, COUNTRY_AR, &out); CHECK_EQ(out.f1[0], 0); }
    signals_tick(&s, &o, COUNTRY_AR, &out); CHECK_EQ(out.f1[0], 425);
    CHECK_EQ(out.f1[1], 0);
}
TEST(us_busy_dual) {
    signals_t s; signals_init(&s); signals_out_t out;
    call_outputs_t o = none(); o.tone[0] = TONE_BUSY;
    signals_tick(&s, &o, COUNTRY_US, &out);
    CHECK_EQ(out.f1[0], 480); CHECK_EQ(out.f2[0], 620);
    for (int t = 2; t <= 501; t++) signals_tick(&s, &o, COUNTRY_US, &out);
    CHECK_EQ(out.f1[0], 0); CHECK_EQ(out.f2[0], 0);
    for (int t = 502; t <= 1001; t++) signals_tick(&s, &o, COUNTRY_US, &out);
    CHECK_EQ(out.f1[0], 480);
}
TEST(dial_continuous) {
    signals_t s; signals_init(&s); signals_out_t out;
    call_outputs_t o = none(); o.tone[1] = TONE_DIAL;
    for (int t = 0; t < 10000; t++) { signals_tick(&s, &o, COUNTRY_AR, &out); CHECK_EQ(out.f1[1], 425); }
}
TEST(ar_ring_cadence_and_phase) {
    signals_t s; signals_init(&s); signals_out_t out;
    call_outputs_t o = none(); o.ring[1] = true;
    for (int t = 1; t <= 1000; t++) {
        signals_tick(&s, &o, COUNTRY_AR, &out);
        CHECK(out.ring_on[1]); CHECK(!out.ring_on[0]);
        CHECK_EQ(out.ring_phase, ((t - 1) / 20) % 2); /* cambia en 21, 41, 61… */
    }
    for (int t = 1001; t <= 5000; t++) {
        signals_tick(&s, &o, COUNTRY_AR, &out);
        CHECK(!out.ring_on[1]); CHECK(!out.ring_phase);
    }
    signals_tick(&s, &o, COUNTRY_AR, &out); CHECK(out.ring_on[1]);
}
TEST(us_ring_phase_25ms) {
    signals_t s; signals_init(&s); signals_out_t out;
    call_outputs_t o = none(); o.ring[0] = true;
    for (int t = 1; t <= 2000; t++) {
        signals_tick(&s, &o, COUNTRY_US, &out);
        CHECK(out.ring_on[0]);
        CHECK_EQ(out.ring_phase, ((t - 1) / 25) % 2);
    }
    signals_tick(&s, &o, COUNTRY_US, &out); CHECK(!out.ring_on[0]);
}
TEST(cadence_restarts_on_change) {
    signals_t s; signals_init(&s); signals_out_t out;
    call_outputs_t o = none(); o.tone[0] = TONE_RINGBACK;
    for (int t = 0; t < 1500; t++) signals_tick(&s, &o, COUNTRY_AR, &out);
    CHECK_EQ(out.f1[0], 0);
    o.tone[0] = TONE_BUSY;
    signals_tick(&s, &o, COUNTRY_AR, &out); CHECK_EQ(out.f1[0], 425);
}
TEST(country_switch_mid_tone) { /* Review Focus 5 */
    signals_t s; signals_init(&s); signals_out_t out;
    call_outputs_t o = none(); o.tone[0] = TONE_DIAL;
    for (int t = 0; t < 100; t++) signals_tick(&s, &o, COUNTRY_AR, &out);
    CHECK_EQ(out.f1[0], 425);
    signals_tick(&s, &o, COUNTRY_US, &out);
    CHECK_EQ(out.f1[0], 350); CHECK_EQ(out.f2[0], 440);
}
TEST(silence_when_none) {
    signals_t s; signals_init(&s); signals_out_t out;
    call_outputs_t o = none();
    signals_tick(&s, &o, COUNTRY_AR, &out);
    CHECK_EQ(out.f1[0], 0); CHECK_EQ(out.f2[1], 0); CHECK(!out.ring_on[0]); CHECK(!out.ring_phase);
}

int main(void) {
    RUN(ar_ringback_cadence); RUN(us_busy_dual); RUN(dial_continuous);
    RUN(ar_ring_cadence_and_phase); RUN(us_ring_phase_25ms);
    RUN(cadence_restarts_on_change); RUN(country_switch_mid_tone); RUN(silence_when_none);
    MINITEST_MAIN_END("test_signals");
}
