#include "cadence.h"

void cadence_start(cadence_t *c, uint16_t on_ms, uint16_t off_ms) {
    c->on_ms = on_ms;
    c->off_ms = off_ms;
    c->pos = 0;
}

bool cadence_tick(cadence_t *c) {
    if (c->on_ms == 0) return false;
    if (c->off_ms == 0) return true;
    bool on = c->pos < c->on_ms;
    c->pos++;
    if ((uint32_t)c->pos >= (uint32_t)c->on_ms + c->off_ms) c->pos = 0;
    return on;
}
