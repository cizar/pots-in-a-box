/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Cesar Kastli */
/* hal.h — ATmega328P hardware access. Used by main.c only.
 * Pin map: see firmware/README.md. */
#ifndef HAL_H
#define HAL_H

#include <stdbool.h>
#include <stdint.h>
#include "tones.h"

void hal_init(void);

bool hal_loop_closed(uint8_t line);  /* OFFHOOK_L1/L2, active low */
bool hal_dtmf_std(void);
uint8_t hal_dtmf_code(void);         /* Q4..Q1 */
country_t hal_country(void);

void hal_set_ring_en(uint8_t line, bool on);
void hal_set_ring_drive(bool phase);
void hal_set_link(bool on);
void hal_set_dtmf_sel(uint8_t line);
void hal_set_led_call(bool on);
void hal_set_tones(uint8_t line, uint16_t f1_hz, uint16_t f2_hz);

bool hal_tick_pending(void);
void hal_tick_clear(void);

#endif
