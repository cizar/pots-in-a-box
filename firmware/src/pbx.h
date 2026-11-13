/* pbx.h — one 1 ms tick of the exchange: hardware inputs ->
 * detection -> logic -> outputs. Pure: main.c wires it to the HAL. */
#ifndef PBX_H
#define PBX_H

#include <stdbool.h>
#include <stdint.h>
#include "call.h"
#include "hook.h"
#include "signals.h"
#include "tones.h"

typedef struct {
    bool loop_closed[2];
    bool dtmf_std;
    uint8_t dtmf_code;   /* Q4..Q1 */
    country_t country;
} pbx_inputs_t;

typedef struct {
    uint16_t f1[2], f2[2];  /* tone per line; 0,0 = silence */
    bool ring_en[2];
    bool ring_drive;
    bool link;
    uint8_t dtmf_sel;       /* held when no line is dialing */
    bool led_call;
} pbx_outputs_t;

typedef struct {
    hook_t hook[2];
    call_t call;
    signals_t sig;
    bool ring_on_prev[2];
    bool last_std;
    uint8_t dtmf_sel;
} pbx_t;

void pbx_init(pbx_t *p);
void pbx_step(pbx_t *p, const pbx_inputs_t *in, pbx_outputs_t *out);

#endif
