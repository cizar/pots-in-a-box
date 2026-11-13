/* main.c — bucle principal de la PBX de 2 líneas. Tick de 1 ms. */
#include <stdbool.h>
#include <stdint.h>
#include "call.h"
#include "dtmf.h"
#include "hal.h"
#include "hook.h"
#include "signals.h"

int main(void) {
    hook_t hook[2];
    call_t call;
    signals_t sig;
    signals_out_t out = { { 0, 0 }, { 0, 0 }, { false, false }, false };
    uint16_t last_f1[2] = { 0, 0 }, last_f2[2] = { 0, 0 };
    bool last_std = false;

    hook_init(&hook[0]);
    hook_init(&hook[1]);
    call_init(&call);
    signals_init(&sig);
    hal_init();

    for (;;) {
        if (!hal_tick_pending()) continue;
        hal_tick_clear();

        /* 1. Descolgado y pulsos; se ignora el lazo mientras suena la ring. */
        for (uint8_t l = 0; l < 2; l++) {
            hook_ev_t e = hook_sample(&hook[l], hal_loop_closed(l), out.ring_on[l]);
            if (e.type == HOOK_EV_OFF) call_event(&call, l, CALL_EV_OFF);
            else if (e.type == HOOK_EV_ON) call_event(&call, l, CALL_EV_ON);
            else if (e.type == HOOK_EV_DIGIT) call_event(&call, l, CALL_EV_DIGIT);
        }

        /* 2. DTMF: flanco de subida de StD. */
        bool std = hal_dtmf_std();
        if (std && !last_std) {
            int8_t line = call_outputs(&call).dtmf_line;
            if (line >= 0 && dtmf_code_to_digit(hal_dtmf_code()) >= 0)
                call_event(&call, (uint8_t)line, CALL_EV_DIGIT);
        }
        last_std = std;

        /* 3. Lógica. */
        call_tick(&call);
        call_outputs_t o = call_outputs(&call);
        signals_tick(&sig, &o, hal_country(), &out);

        /* 4. Salidas. */
        for (uint8_t l = 0; l < 2; l++) {
            if (out.f1[l] != last_f1[l] || out.f2[l] != last_f2[l]) {
                hal_set_tones(l, out.f1[l], out.f2[l]);
                last_f1[l] = out.f1[l];
                last_f2[l] = out.f2[l];
            }
            hal_set_ring_en(l, out.ring_on[l]);
        }
        hal_set_ring_drive(out.ring_phase);
        hal_set_link(o.link);
        if (o.dtmf_line >= 0) hal_set_dtmf_sel((uint8_t)o.dtmf_line);
        hal_set_led_call(o.led_call);
    }
}
