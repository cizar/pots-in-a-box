/* call.h — 2-line call state machine (spec §7.8). 1 ms tick. */
#ifndef CALL_H
#define CALL_H

#include <stdbool.h>
#include <stdint.h>
#include "tones.h"

#define DIGIT_TIMEOUT_MS   2500u  /* no new digits -> number complete   */
#define NO_DIAL_TIMEOUT_MS 30000u /* off-hook without dialing -> busy   */
#define RING_TIMEOUT_MS    60000u /* nobody answers -> busy             */

typedef enum { CALL_EV_OFF, CALL_EV_ON, CALL_EV_DIGIT } call_ev_t;

typedef enum {
    LINE_IDLE = 0,
    LINE_DIALTONE,
    LINE_DIALING,
    LINE_RINGBACK,  /* caller hearing ringback tone */
    LINE_RINGING,   /* called line, on-hook, ringing */
    LINE_CONNECTED,
    LINE_BUSY
} line_state_t;

typedef struct {
    line_state_t state[2];
    uint16_t timer[2];   /* ms in the current state */
    int8_t dtmf_owner;   /* line the MT8870 listens to, or -1 */
} call_t;

typedef struct {
    tone_id_t tone[2];
    bool ring[2];        /* logical, without cadence */
    bool link;
    int8_t dtmf_line;    /* -1: none */
    bool led_call;
} call_outputs_t;

void call_init(call_t *c);
void call_event(call_t *c, uint8_t line, call_ev_t ev);
void call_tick(call_t *c);
call_outputs_t call_outputs(const call_t *c);
line_state_t call_line_state(const call_t *c, uint8_t line);

#endif
