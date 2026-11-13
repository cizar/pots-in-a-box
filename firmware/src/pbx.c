#include "pbx.h"
#include "dtmf.h"

void pbx_init(pbx_t *p) {
    hook_init(&p->hook[0]);
    hook_init(&p->hook[1]);
    call_init(&p->call);
    signals_init(&p->sig);
    p->ring_on_prev[0] = p->ring_on_prev[1] = false;
    p->last_std = false;
    p->dtmf_sel = 0;
}

void pbx_step(pbx_t *p, const pbx_inputs_t *in, pbx_outputs_t *out) {
    /* 1. Descolgado y pulsos; mientras suena la ring (tick anterior) el
     *    lazo no se mira. */
    for (uint8_t l = 0; l < 2; l++) {
        hook_ev_t e = hook_sample(&p->hook[l], in->loop_closed[l], p->ring_on_prev[l]);
        if (e.type == HOOK_EV_OFF) call_event(&p->call, l, CALL_EV_OFF);
        else if (e.type == HOOK_EV_ON) call_event(&p->call, l, CALL_EV_ON);
        else if (e.type == HOOK_EV_DIGIT) call_event(&p->call, l, CALL_EV_DIGIT);
    }

    /* 2. DTMF: un dígito por flanco de subida de StD, para la línea dueña. */
    if (in->dtmf_std && !p->last_std) {
        int8_t line = call_outputs(&p->call).dtmf_line;
        if (line >= 0 && dtmf_code_to_digit(in->dtmf_code) >= 0)
            call_event(&p->call, (uint8_t)line, CALL_EV_DIGIT);
    }
    p->last_std = in->dtmf_std;

    /* 3. Lógica. */
    call_tick(&p->call);
    call_outputs_t o = call_outputs(&p->call);
    signals_out_t s;
    signals_tick(&p->sig, &o, in->country, &s);

    /* 4. Salidas. */
    for (uint8_t l = 0; l < 2; l++) {
        out->f1[l] = s.f1[l];
        out->f2[l] = s.f2[l];
        out->ring_en[l] = s.ring_on[l];
        p->ring_on_prev[l] = s.ring_on[l];
    }
    out->ring_drive = s.ring_phase;
    out->link = o.link;
    if (o.dtmf_line >= 0) p->dtmf_sel = (uint8_t)o.dtmf_line;
    out->dtmf_sel = p->dtmf_sel;
    out->led_call = o.led_call;
}
