/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Cesar Kastli */
/* txq.h — byte FIFO for the debug UART. A message that does not fit is
 * dropped whole, so lines are never cut in the middle. */
#ifndef TXQ_H
#define TXQ_H

#include <stdbool.h>
#include <stdint.h>

#define TXQ_SIZE 128u /* capacity is TXQ_SIZE - 1 bytes */

typedef struct {
    uint8_t buf[TXQ_SIZE];
    uint8_t head, tail;
} txq_t;

void txq_init(txq_t *q);
bool txq_push(txq_t *q, const uint8_t *data, uint8_t n);
bool txq_pop(txq_t *q, uint8_t *b);

#endif
