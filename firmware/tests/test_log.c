/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Cesar Kastli */
#include <string.h>
#include "minitest.h"
#include "../src/log.h"

static const char *fmt(uint8_t type, uint8_t line, uint8_t value) {
    static char buf[LOG_LINE_MAX];
    pots_event_t e = { type, line, value };
    uint8_t n = log_format(&e, buf, sizeof buf);
    CHECK_EQ(n, strlen(buf));
    return buf;
}

TEST(formats_events) {
    CHECK(strcmp(fmt(POTS_EV_HOOK_OFF, 0, 0), "L1 off-hook\r\n") == 0);
    CHECK(strcmp(fmt(POTS_EV_HOOK_ON, 1, 0), "L2 on-hook\r\n") == 0);
    CHECK(strcmp(fmt(POTS_EV_PULSE_DIGIT, 0, 7), "L1 digit 7 (pulse)\r\n") == 0);
    CHECK(strcmp(fmt(POTS_EV_DTMF_DIGIT, 1, 10), "L2 digit * (dtmf)\r\n") == 0);
    CHECK(strcmp(fmt(POTS_EV_DTMF_DIGIT, 1, 11), "L2 digit # (dtmf)\r\n") == 0);
    CHECK(strcmp(fmt(POTS_EV_DTMF_COLLISION, 0, 0), "dtmf collision, digit discarded\r\n") == 0);
    CHECK(strcmp(fmt(POTS_EV_STATE, 1, LINE_RINGING), "L2 -> RINGING\r\n") == 0);
    CHECK(strcmp(fmt(POTS_EV_COUNTRY, 0, COUNTRY_US), "country US\r\n") == 0);
}
TEST(truncates_safely) {
    char buf[6];
    pots_event_t e = { POTS_EV_HOOK_OFF, 0, 0 };
    uint8_t n = log_format(&e, buf, sizeof buf);
    CHECK_EQ(n, 5); CHECK_EQ(buf[5], '\0');
}

int main(void) {
    RUN(formats_events); RUN(truncates_safely);
    MINITEST_MAIN_END("test_log");
}
