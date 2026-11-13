/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Cesar Kastli */
#include "txq.h"

void txq_init(txq_t *q) { q->head = q->tail = 0; }

static uint8_t used(const txq_t *q) {
    return (uint8_t)((q->head + TXQ_SIZE - q->tail) % TXQ_SIZE);
}

bool txq_push(txq_t *q, const uint8_t *data, uint8_t n) {
    if (n > (TXQ_SIZE - 1) - used(q)) return false;
    for (uint8_t i = 0; i < n; i++) {
        q->buf[q->head] = data[i];
        q->head = (uint8_t)((q->head + 1) % TXQ_SIZE);
    }
    return true;
}

bool txq_pop(txq_t *q, uint8_t *b) {
    if (q->head == q->tail) return false;
    *b = q->buf[q->tail];
    q->tail = (uint8_t)((q->tail + 1) % TXQ_SIZE);
    return true;
}
