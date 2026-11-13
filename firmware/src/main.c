/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Cesar Kastli */
/* main.c — wires pots_step (pure logic, tested on the host) to the HAL.
 * 1 ms tick. The watchdog resets the chip if the loop hangs. */
#include <avr/wdt.h>
#include <stdbool.h>
#include <stdint.h>
#include "hal.h"
#include "pots.h"

int main(void) {
    pots_t pots;
    pots_inputs_t in;
    pots_outputs_t out;
    uint16_t last_f1[2] = { 0, 0 }, last_f2[2] = { 0, 0 };

    /* The watchdog stays enabled after a watchdog reset: turn it off first. */
    MCUSR = 0;
    wdt_disable();

    pots_init(&pots);
    hal_init();
    wdt_enable(WDTO_250MS);

    for (;;) {
        if (!hal_tick_pending()) continue;
        hal_tick_clear();
        wdt_reset();

        in.loop_closed[0] = hal_loop_closed(0);
        in.loop_closed[1] = hal_loop_closed(1);
        in.dtmf_std = hal_dtmf_std();
        in.dtmf_code = hal_dtmf_code();
        in.country = hal_country();

        pots_step(&pots, &in, &out);

        for (uint8_t l = 0; l < 2; l++) {
            if (out.f1[l] != last_f1[l] || out.f2[l] != last_f2[l]) {
                hal_set_tones(l, out.f1[l], out.f2[l]);
                last_f1[l] = out.f1[l];
                last_f2[l] = out.f2[l];
            }
            hal_set_ring_en(l, out.ring_en[l]);
        }
        hal_set_ring_drive(out.ring_drive);
        hal_set_link(out.link);
        hal_set_dtmf_sel(out.dtmf_sel);
        hal_set_led_call(out.led_call);
    }
}
