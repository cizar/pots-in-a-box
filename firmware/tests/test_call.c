/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Cesar Kastli */
#include "minitest.h"
#include "../src/call.h"

static void ticks(call_t *c, long ms) { for (long i = 0; i < ms; i++) call_tick(c); }

/* L0 calls L1, L1 is ringing. */
static void to_ringing(call_t *c) {
    call_init(c);
    call_event(c, 0, CALL_EV_OFF);
    call_event(c, 0, CALL_EV_DIGIT);
    ticks(c, DIGIT_TIMEOUT_MS);
}
static void to_connected(call_t *c) { to_ringing(c); call_event(c, 1, CALL_EV_OFF); }

TEST(idle_outputs) {
    call_t c; call_init(&c); call_outputs_t o = call_outputs(&c);
    CHECK_EQ(o.tone[0], TONE_NONE); CHECK_EQ(o.tone[1], TONE_NONE);
    CHECK(!o.ring[0]); CHECK(!o.ring[1]); CHECK(!o.link); CHECK(!o.led_call);
}
TEST(offhook_gives_dialtone) {
    call_t c; call_init(&c); call_event(&c, 0, CALL_EV_OFF);
    call_outputs_t o = call_outputs(&c);
    CHECK_EQ(o.tone[0], TONE_DIAL);
    CHECK_EQ(call_line_state(&c, 0), LINE_DIALTONE);
}
TEST(digit_timeout_boundary) {
    call_t c; call_init(&c);
    call_event(&c, 0, CALL_EV_OFF); call_event(&c, 0, CALL_EV_DIGIT);
    ticks(&c, 2499);
    CHECK_EQ(call_line_state(&c, 0), LINE_DIALING);
    CHECK_EQ(call_outputs(&c).tone[0], TONE_NONE);
    ticks(&c, 1);
    call_outputs_t o = call_outputs(&c);
    CHECK_EQ(o.tone[0], TONE_RINGBACK); CHECK(o.ring[1]); CHECK(!o.ring[0]);
    CHECK_EQ(call_line_state(&c, 1), LINE_RINGING);
}
TEST(each_digit_restarts_timer) {
    call_t c; call_init(&c);
    call_event(&c, 0, CALL_EV_OFF); call_event(&c, 0, CALL_EV_DIGIT);
    ticks(&c, 2000); call_event(&c, 0, CALL_EV_DIGIT); ticks(&c, 2000);
    CHECK_EQ(call_line_state(&c, 0), LINE_DIALING);
}
TEST(answer_connects) {
    call_t c; to_connected(&c); call_outputs_t o = call_outputs(&c);
    CHECK(o.link); CHECK(o.led_call);
    CHECK_EQ(o.tone[0], TONE_NONE); CHECK_EQ(o.tone[1], TONE_NONE);
    CHECK(!o.ring[0]); CHECK(!o.ring[1]);
    CHECK_EQ(call_line_state(&c, 0), LINE_CONNECTED);
    CHECK_EQ(call_line_state(&c, 1), LINE_CONNECTED);
}
TEST(hangup_in_call_gives_busy_to_other) {
    call_t c; to_connected(&c); call_event(&c, 1, CALL_EV_ON);
    call_outputs_t o = call_outputs(&c);
    CHECK_EQ(o.tone[0], TONE_BUSY); CHECK(!o.link); CHECK(!o.led_call);
    CHECK_EQ(call_line_state(&c, 1), LINE_IDLE);
}
TEST(called_offhook_gives_busy) {
    call_t c; call_init(&c);
    call_event(&c, 1, CALL_EV_OFF);
    call_event(&c, 0, CALL_EV_OFF); call_event(&c, 0, CALL_EV_DIGIT);
    ticks(&c, DIGIT_TIMEOUT_MS);
    call_outputs_t o = call_outputs(&c);
    CHECK_EQ(o.tone[0], TONE_BUSY); CHECK_EQ(o.tone[1], TONE_DIAL);
    CHECK(!o.ring[1]);
}
TEST(no_dial_timeout) {
    call_t c; call_init(&c); call_event(&c, 0, CALL_EV_OFF);
    ticks(&c, 29999); CHECK_EQ(call_outputs(&c).tone[0], TONE_DIAL);
    ticks(&c, 1);     CHECK_EQ(call_outputs(&c).tone[0], TONE_BUSY);
}
TEST(ring_timeout) {
    call_t c; to_ringing(&c);
    ticks(&c, 59999); CHECK(call_outputs(&c).ring[1]);
    ticks(&c, 1);
    call_outputs_t o = call_outputs(&c);
    CHECK_EQ(o.tone[0], TONE_BUSY); CHECK(!o.ring[1]);
    CHECK_EQ(call_line_state(&c, 1), LINE_IDLE);
}
TEST(caller_abandons) {
    call_t c; to_ringing(&c); call_event(&c, 0, CALL_EV_ON);
    call_outputs_t o = call_outputs(&c);
    CHECK(!o.ring[1]); CHECK_EQ(o.tone[0], TONE_NONE);
    CHECK_EQ(call_line_state(&c, 0), LINE_IDLE);
    CHECK_EQ(call_line_state(&c, 1), LINE_IDLE);
}
TEST(both_lines_dial_independently) { /* one MT8870 per line */
    call_t c; call_init(&c);
    call_event(&c, 1, CALL_EV_OFF); call_event(&c, 0, CALL_EV_OFF);
    call_event(&c, 0, CALL_EV_DIGIT); call_event(&c, 1, CALL_EV_DIGIT);
    CHECK_EQ(call_line_state(&c, 0), LINE_DIALING);
    CHECK_EQ(call_line_state(&c, 1), LINE_DIALING);
}
TEST(blind_dial_digit_right_after_offhook) { /* Review Focus 2 */
    call_t c; call_init(&c);
    call_event(&c, 0, CALL_EV_OFF); call_event(&c, 0, CALL_EV_DIGIT);
    CHECK_EQ(call_line_state(&c, 0), LINE_DIALING);
}
TEST(digits_ignored_when_connected) { /* Review Focus 3 */
    call_t c; to_connected(&c);
    call_event(&c, 0, CALL_EV_DIGIT); call_event(&c, 1, CALL_EV_DIGIT);
    ticks(&c, 5000);
    call_outputs_t o = call_outputs(&c);
    CHECK_EQ(call_line_state(&c, 0), LINE_CONNECTED); CHECK(o.link);
}
TEST(pulse_digit_in_call_is_ignored) { /* a 20-120 ms break during the call */
    call_t c; to_connected(&c);
    call_event(&c, 1, CALL_EV_DIGIT);
    ticks(&c, DIGIT_TIMEOUT_MS * 2);
    CHECK_EQ(call_line_state(&c, 1), LINE_CONNECTED); CHECK(call_outputs(&c).link);
}
TEST(busy_then_hangup_is_idle) {
    call_t c; call_init(&c); call_event(&c, 0, CALL_EV_OFF);
    ticks(&c, NO_DIAL_TIMEOUT_MS);
    CHECK_EQ(call_line_state(&c, 0), LINE_BUSY);
    call_event(&c, 0, CALL_EV_ON);
    CHECK_EQ(call_line_state(&c, 0), LINE_IDLE);
}
TEST(call_back_after_hangup) {
    call_t c; to_connected(&c);
    call_event(&c, 0, CALL_EV_ON); call_event(&c, 1, CALL_EV_ON);
    call_event(&c, 1, CALL_EV_OFF); call_event(&c, 1, CALL_EV_DIGIT);
    ticks(&c, DIGIT_TIMEOUT_MS);
    CHECK(call_outputs(&c).ring[0]);
    CHECK_EQ(call_outputs(&c).tone[1], TONE_RINGBACK);
}

int main(void) {
    RUN(idle_outputs); RUN(offhook_gives_dialtone); RUN(digit_timeout_boundary);
    RUN(each_digit_restarts_timer); RUN(answer_connects);
    RUN(hangup_in_call_gives_busy_to_other); RUN(called_offhook_gives_busy);
    RUN(no_dial_timeout); RUN(ring_timeout); RUN(caller_abandons);
    RUN(both_lines_dial_independently); RUN(blind_dial_digit_right_after_offhook);
    RUN(digits_ignored_when_connected); RUN(pulse_digit_in_call_is_ignored); RUN(busy_then_hangup_is_idle);
    RUN(call_back_after_hangup);
    MINITEST_MAIN_END("test_call");
}
