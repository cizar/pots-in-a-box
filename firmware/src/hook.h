/* hook.h — detección de descolgado/colgado y marcado por pulsos.
 * Se alimenta con una muestra del lazo por ms. */
#ifndef HOOK_H
#define HOOK_H

#include <stdbool.h>
#include <stdint.h>

#define HOOK_OFF_MS    50  /* lazo cerrado continuo estando colgado -> OFF   */
#define HOOK_ON_MS     500 /* lazo abierto continuo estando descolgado -> ON */
#define PULSE_MIN_MS   20  /* apertura que cuenta como pulso: 20..120 ms     */
#define PULSE_MAX_MS   120
#define INTERDIGIT_MS  200 /* lazo cerrado tras >=1 pulso -> DIGIT           */
#define MASK_TAIL_MS   150 /* se ignora tras la máscara: relé + recarga del acople */

typedef enum { HOOK_EV_NONE = 0, HOOK_EV_OFF, HOOK_EV_ON, HOOK_EV_DIGIT } hook_ev_type_t;

typedef struct {
    hook_ev_type_t type;
    uint8_t digit; /* 0-9; 10 pulsos = 0 */
} hook_ev_t;

typedef struct {
    bool off;
    uint16_t closed_ms, open_ms, mask_tail;
    uint8_t pulses;
} hook_t;

void hook_init(hook_t *h);
/* masked: ignora la muestra (ring activa) y congela el estado. */
hook_ev_t hook_sample(hook_t *h, bool loop_closed, bool masked);
bool hook_is_off(const hook_t *h);

#endif
