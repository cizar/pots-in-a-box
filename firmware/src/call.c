#include "call.h"

#define OTHER(l) ((uint8_t)(1u - (l)))

static bool is_dialing(line_state_t s) { return s == LINE_DIALTONE || s == LINE_DIALING; }

/* Changes a line's state and keeps track of which line owns the MT8870. */
static void set_state(call_t *c, uint8_t l, line_state_t s) {
    bool was = is_dialing(c->state[l]);
    c->state[l] = s;
    c->timer[l] = 0;
    bool now = is_dialing(s);
    if (now && c->dtmf_owner < 0) {
        c->dtmf_owner = (int8_t)l;
    } else if (was && !now && c->dtmf_owner == (int8_t)l) {
        c->dtmf_owner = is_dialing(c->state[OTHER(l)]) ? (int8_t)OTHER(l) : -1;
    }
}

void call_init(call_t *c) {
    c->state[0] = c->state[1] = LINE_IDLE;
    c->timer[0] = c->timer[1] = 0;
    c->dtmf_owner = -1;
}

void call_event(call_t *c, uint8_t l, call_ev_t ev) {
    if (l > 1) return;
    uint8_t o = OTHER(l);
    line_state_t s = c->state[l];

    switch (ev) {
    case CALL_EV_OFF:
        if (s == LINE_IDLE) {
            set_state(c, l, LINE_DIALTONE);
        } else if (s == LINE_RINGING) {
            set_state(c, l, LINE_CONNECTED);
            set_state(c, o, LINE_CONNECTED);
        }
        break;

    case CALL_EV_ON:
        if (s == LINE_RINGING || s == LINE_IDLE) break; /* already on-hook */
        set_state(c, l, LINE_IDLE);
        if (s == LINE_CONNECTED) set_state(c, o, LINE_BUSY);
        else if (s == LINE_RINGBACK) set_state(c, o, LINE_IDLE);
        break;

    case CALL_EV_DIGIT:
        if (is_dialing(s)) set_state(c, l, LINE_DIALING); /* restarts the timer */
        break;
    }
}

void call_tick(call_t *c) {
    for (uint8_t l = 0; l < 2; l++) {
        if (c->timer[l] < UINT16_MAX) c->timer[l]++;
        uint8_t o = OTHER(l);
        switch (c->state[l]) {
        case LINE_DIALTONE:
            if (c->timer[l] >= NO_DIAL_TIMEOUT_MS) set_state(c, l, LINE_BUSY);
            break;
        case LINE_DIALING:
            if (c->timer[l] >= DIGIT_TIMEOUT_MS) {
                /* Any number rings the other line. */
                if (c->state[o] != LINE_IDLE) {
                    set_state(c, l, LINE_BUSY);
                } else {
                    set_state(c, l, LINE_RINGBACK);
                    set_state(c, o, LINE_RINGING);
                }
            }
            break;
        case LINE_RINGBACK:
            if (c->timer[l] >= RING_TIMEOUT_MS) {
                set_state(c, l, LINE_BUSY);
                set_state(c, o, LINE_IDLE);
            }
            break;
        default:
            break;
        }
    }
}

call_outputs_t call_outputs(const call_t *c) {
    call_outputs_t out;
    for (uint8_t l = 0; l < 2; l++) {
        switch (c->state[l]) {
        case LINE_DIALTONE: out.tone[l] = TONE_DIAL; break;
        case LINE_RINGBACK: out.tone[l] = TONE_RINGBACK; break;
        case LINE_BUSY:     out.tone[l] = TONE_BUSY; break;
        default:            out.tone[l] = TONE_NONE; break;
        }
        out.ring[l] = c->state[l] == LINE_RINGING;
    }
    out.link = c->state[0] == LINE_CONNECTED && c->state[1] == LINE_CONNECTED;
    out.led_call = out.link;
    out.dtmf_line = c->dtmf_owner;
    return out;
}

line_state_t call_line_state(const call_t *c, uint8_t l) { return c->state[l & 1]; }
