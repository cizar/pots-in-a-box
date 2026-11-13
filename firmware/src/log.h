/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Cesar Kastli */
/* log.h — human-readable debug lines for pots events (UART on PD1). */
#ifndef LOG_H
#define LOG_H

#include <stdint.h>
#include "pots.h"

#define LOG_LINE_MAX 40

/* Writes a NUL-terminated line ending in "\r\n" (truncated to size - 1).
 * Returns the number of characters written, without the NUL. */
uint8_t log_format(const pots_event_t *e, char *buf, uint8_t size);

#endif
