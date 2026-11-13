/* cadence.h — on/off cadence driven by a 1 ms tick. */
#ifndef CADENCE_H
#define CADENCE_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    uint16_t on_ms, off_ms, pos;
} cadence_t;

void cadence_start(cadence_t *c, uint16_t on_ms, uint16_t off_ms);
/* Returns whether the current ms is "on", then advances.
 * off_ms == 0: always true. on_ms == 0: always false. */
bool cadence_tick(cadence_t *c);

#endif
