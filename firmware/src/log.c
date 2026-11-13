/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Cesar Kastli */
#include "log.h"
#include "dtmf.h"

static const char *const STATE_NAMES[] = {
    "IDLE", "DIALTONE", "DIALING", "RINGBACK", "RINGING", "CONNECTED", "BUSY",
};

typedef struct {
    char *buf;
    uint8_t size, len;
} sink_t;

static void put(sink_t *s, char c) {
    if (s->len + 1 < s->size) s->buf[s->len++] = c;
}
static void puts_(sink_t *s, const char *str) {
    while (*str) put(s, *str++);
}
static void line(sink_t *s, uint8_t l) {
    put(s, 'L');
    put(s, (char)('1' + l));
    put(s, ' ');
}
static void digit(sink_t *s, uint8_t d) {
    if (d == DTMF_STAR) put(s, '*');
    else if (d == DTMF_HASH) put(s, '#');
    else put(s, (char)('0' + (d % 10)));
}

uint8_t log_format(const pots_event_t *e, char *buf, uint8_t size) {
    sink_t s = { buf, size, 0 };
    if (size == 0) return 0;
    switch (e->type) {
    case POTS_EV_HOOK_OFF: line(&s, e->line); puts_(&s, "off-hook"); break;
    case POTS_EV_HOOK_ON: line(&s, e->line); puts_(&s, "on-hook"); break;
    case POTS_EV_PULSE_DIGIT:
        line(&s, e->line); puts_(&s, "digit "); digit(&s, e->value); puts_(&s, " (pulse)");
        break;
    case POTS_EV_DTMF_DIGIT:
        line(&s, e->line); puts_(&s, "digit "); digit(&s, e->value); puts_(&s, " (dtmf)");
        break;
    case POTS_EV_DTMF_COLLISION: puts_(&s, "dtmf collision, digit discarded"); break;
    case POTS_EV_STATE:
        line(&s, e->line); puts_(&s, "-> ");
        puts_(&s, e->value < sizeof STATE_NAMES / sizeof STATE_NAMES[0] ? STATE_NAMES[e->value] : "?");
        break;
    case POTS_EV_COUNTRY: puts_(&s, e->value == COUNTRY_US ? "country US" : "country AR"); break;
    default: puts_(&s, "?"); break;
    }
    puts_(&s, "\r\n");
    buf[s.len] = '\0';
    return s.len;
}
