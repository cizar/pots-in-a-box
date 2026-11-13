/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Cesar Kastli */
#include <string.h>
#include "minitest.h"
#include "../src/pots.h"

static pots_t p;
static pots_inputs_t in;
static pots_outputs_t out;

static void reset(void) {
    pots_init(&p);
    memset(&in, 0, sizeof in);
    in.country = COUNTRY_AR;
}
static void step(long ms) { for (long i = 0; i < ms; i++) pots_step(&p, &in, &out); }

/* L0 goes off-hook and dials one DTMF digit (code 5). */
static void l0_dials(void) {
    in.loop_closed[0] = true; step(60);
    in.dtmf_code = 5; in.dtmf_std[0] = true; step(40);
    in.dtmf_std[0] = false;
}

TEST(offhook_gives_dialtone_on_its_pwm) {
    reset(); in.loop_closed[0] = true; step(60);
    CHECK_EQ(out.f1[0], 425); CHECK_EQ(out.f1[1], 0);
}
TEST(dtmf_digit_rings_other_line) {
    reset(); l0_dials(); step(DIGIT_TIMEOUT_MS);
    CHECK(out.ring_en[1]); CHECK(!out.ring_en[0]);
    CHECK_EQ(out.f1[0], 425); /* ringback, first second */
}
TEST(dtmf_held_std_counts_once) {
    /* StD held high for 3 s: if it counted on every tick, the end-of-number
     * timer would keep restarting and the other line would never ring. */
    reset(); in.loop_closed[0] = true; step(60);
    in.dtmf_code = 5; in.dtmf_std[0] = true; step(DIGIT_TIMEOUT_MS + 10);
    CHECK(out.ring_en[1]);
}
TEST(dtmf_abcd_is_ignored) {
    reset(); in.loop_closed[0] = true; step(60);
    in.dtmf_code = 13; in.dtmf_std[0] = true; step(40); in.dtmf_std[0] = false;
    step(DIGIT_TIMEOUT_MS + 100);
    CHECK(!out.ring_en[1]); CHECK_EQ(out.f1[0], 425); /* still dial tone */
}
TEST(dtmf_on_onhook_line_is_ignored) {
    reset(); in.dtmf_code = 5; in.dtmf_std[0] = true; step(40); in.dtmf_std[0] = false;
    in.loop_closed[0] = true; step(60 + DIGIT_TIMEOUT_MS + 100);
    CHECK(!out.ring_en[1]);
}
TEST(ring_does_not_fake_answer) { /* ring looks like a closed loop */
    reset(); l0_dials(); step(DIGIT_TIMEOUT_MS);
    CHECK(out.ring_en[1]);
    in.loop_closed[1] = true;             /* ring seen as a closed loop */
    while (out.ring_en[1]) step(1);       /* until the burst ends */
    in.loop_closed[1] = false; step(300); /* modem still on-hook */
    CHECK(!out.led_call); CHECK(!out.link);
}
TEST(answer_during_burst_connects_after_it) {
    reset(); l0_dials(); step(DIGIT_TIMEOUT_MS);
    in.loop_closed[1] = true;              /* modem answers during the burst */
    while (out.ring_en[1]) step(1);
    CHECK(!out.led_call);
    step(MASK_TAIL_MS + HOOK_OFF_MS + 5);
    CHECK(out.led_call); CHECK(out.link); CHECK(!out.ring_en[1]);
}
TEST(dtmf_on_line2_rings_line1) { /* each line has its own MT8870 */
    reset(); in.loop_closed[1] = true; step(60);
    in.dtmf_code = 7; in.dtmf_std[1] = true; step(40); in.dtmf_std[1] = false;
    step(DIGIT_TIMEOUT_MS);
    CHECK(out.ring_en[0]); CHECK(!out.ring_en[1]);
}
TEST(simultaneous_std_is_discarded) { /* both chips drive the shared Q bus */
    reset(); in.loop_closed[0] = true; in.loop_closed[1] = true; step(60);
    in.dtmf_code = 5; in.dtmf_std[0] = true; in.dtmf_std[1] = true; step(40);
    in.dtmf_std[0] = false; in.dtmf_std[1] = false;
    step(100); /* well before the end-of-number timeout (busy is also 425 Hz) */
    CHECK_EQ(out.f1[0], 425); CHECK_EQ(out.f1[1], 425); /* both still on dial tone */
}
TEST(std_rising_while_other_high_is_discarded) {
    reset(); in.loop_closed[0] = true; in.loop_closed[1] = true; step(60);
    in.dtmf_code = 5; in.dtmf_std[1] = true; step(10);  /* L2 digit accepted */
    in.dtmf_std[0] = true; step(30);                   /* L1 rises while L2 is high */
    in.dtmf_std[0] = false; in.dtmf_std[1] = false; step(100);
    CHECK_EQ(out.f1[0], 425); /* L1 got no digit: still dial tone */
    CHECK_EQ(out.f1[1], 0);   /* L2 is dialing: dial tone stopped */
}
TEST(ring_drive_toggles_while_ringing) {
    reset(); l0_dials(); step(DIGIT_TIMEOUT_MS);
    bool first = out.ring_drive; step(20);
    CHECK(out.ring_drive != first);
}

int main(void) {
    RUN(offhook_gives_dialtone_on_its_pwm); RUN(dtmf_digit_rings_other_line);
    RUN(dtmf_held_std_counts_once); RUN(dtmf_abcd_is_ignored);
    RUN(dtmf_on_onhook_line_is_ignored); RUN(ring_does_not_fake_answer);
    RUN(answer_during_burst_connects_after_it); RUN(dtmf_on_line2_rings_line1); RUN(simultaneous_std_is_discarded);
    RUN(std_rising_while_other_high_is_discarded);
    RUN(ring_drive_toggles_while_ringing);
    MINITEST_MAIN_END("test_pots");
}
