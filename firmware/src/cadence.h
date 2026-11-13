/* cadence.h — cadencia on/off con tick de 1 ms. */
#ifndef CADENCE_H
#define CADENCE_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    uint16_t on_ms, off_ms, pos;
} cadence_t;

void cadence_start(cadence_t *c, uint16_t on_ms, uint16_t off_ms);
/* Devuelve si el ms actual está en "on" y avanza.
 * off_ms == 0: siempre true. on_ms == 0: siempre false. */
bool cadence_tick(cadence_t *c);

#endif
