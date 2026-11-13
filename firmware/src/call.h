/* call.h — máquina de llamada de 2 líneas (spec §7.8). Tick de 1 ms. */
#ifndef CALL_H
#define CALL_H

#include <stdbool.h>
#include <stdint.h>
#include "tones.h"

#define DIGIT_TIMEOUT_MS   2500u  /* sin dígitos nuevos -> fin de número */
#define NO_DIAL_TIMEOUT_MS 30000u /* descolgado sin marcar -> ocupado    */
#define RING_TIMEOUT_MS    60000u /* nadie atiende -> ocupado            */

typedef enum { CALL_EV_OFF, CALL_EV_ON, CALL_EV_DIGIT } call_ev_t;

typedef enum {
    LINE_IDLE = 0,
    LINE_DIALTONE,
    LINE_DIALING,
    LINE_RINGBACK,  /* llamador escuchando tono de llamada */
    LINE_RINGING,   /* llamado, colgado, sonando           */
    LINE_CONNECTED,
    LINE_BUSY
} line_state_t;

typedef struct {
    line_state_t state[2];
    uint16_t timer[2];   /* ms en el estado actual */
    int8_t dtmf_owner;   /* línea que escucha el MT8870, o -1 */
} call_t;

typedef struct {
    tone_id_t tone[2];
    bool ring[2];        /* lógico, sin cadencia */
    bool link;
    int8_t dtmf_line;    /* -1: ninguna */
    bool led_call;
} call_outputs_t;

void call_init(call_t *c);
void call_event(call_t *c, uint8_t line, call_ev_t ev);
void call_tick(call_t *c);
call_outputs_t call_outputs(const call_t *c);
line_state_t call_line_state(const call_t *c, uint8_t line);

#endif
