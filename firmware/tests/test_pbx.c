#include <string.h>
#include "minitest.h"
#include "../src/pbx.h"

static pbx_t p;
static pbx_inputs_t in;
static pbx_outputs_t out;

static void reset(void) {
    pbx_init(&p);
    memset(&in, 0, sizeof in);
    in.country = COUNTRY_AR;
}
static void step(long ms) { for (long i = 0; i < ms; i++) pbx_step(&p, &in, &out); }

/* L0 descuelga y marca un dígito DTMF (código 5). */
static void l0_dials(void) {
    in.loop_closed[0] = true; step(60);
    in.dtmf_code = 5; in.dtmf_std = true; step(40);
    in.dtmf_std = false;
}

TEST(offhook_gives_dialtone_on_its_pwm) {
    reset(); in.loop_closed[0] = true; step(60);
    CHECK_EQ(out.f1[0], 425); CHECK_EQ(out.f1[1], 0); CHECK_EQ(out.dtmf_sel, 0);
}
TEST(dtmf_digit_rings_other_line) {
    reset(); l0_dials(); step(DIGIT_TIMEOUT_MS);
    CHECK(out.ring_en[1]); CHECK(!out.ring_en[0]);
    CHECK_EQ(out.f1[0], 425); /* tono de llamada, primer segundo */
}
TEST(dtmf_held_std_counts_once) {
    /* StD alto 3 s: si contara en cada tick, el timer de fin de número
     * se reiniciaría y no sonaría nunca la otra línea. */
    reset(); in.loop_closed[0] = true; step(60);
    in.dtmf_code = 5; in.dtmf_std = true; step(DIGIT_TIMEOUT_MS + 10);
    CHECK(out.ring_en[1]);
}
TEST(dtmf_abcd_is_ignored) {
    reset(); in.loop_closed[0] = true; step(60);
    in.dtmf_code = 13; in.dtmf_std = true; step(40); in.dtmf_std = false;
    step(DIGIT_TIMEOUT_MS + 100);
    CHECK(!out.ring_en[1]); CHECK_EQ(out.f1[0], 425); /* sigue en invitación */
}
TEST(dtmf_without_owner_is_ignored) {
    reset(); in.dtmf_code = 5; in.dtmf_std = true; step(40); in.dtmf_std = false;
    in.loop_closed[0] = true; step(60 + DIGIT_TIMEOUT_MS + 100);
    CHECK(!out.ring_en[1]);
}
TEST(ring_does_not_fake_answer) { /* la ring se ve como lazo cerrado */
    reset(); l0_dials(); step(DIGIT_TIMEOUT_MS);
    CHECK(out.ring_en[1]);
    in.loop_closed[1] = true;             /* ring vista como lazo cerrado */
    while (out.ring_en[1]) step(1);       /* hasta que termina la ráfaga */
    in.loop_closed[1] = false; step(300); /* módem todavía colgado */
    CHECK(!out.led_call); CHECK(!out.link);
}
TEST(answer_during_burst_connects_after_it) {
    reset(); l0_dials(); step(DIGIT_TIMEOUT_MS);
    in.loop_closed[1] = true;              /* el módem atiende durante la ráfaga */
    while (out.ring_en[1]) step(1);
    CHECK(!out.led_call);
    step(MASK_TAIL_MS + HOOK_OFF_MS + 5);
    CHECK(out.led_call); CHECK(out.link); CHECK(!out.ring_en[1]);
}
TEST(dtmf_sel_holds_last_line) {
    reset(); in.loop_closed[1] = true; step(60);
    CHECK_EQ(out.dtmf_sel, 1);
    in.loop_closed[1] = false; step(600);  /* cuelga: dtmf_line = -1 */
    CHECK_EQ(out.dtmf_sel, 1);
}
TEST(ring_drive_toggles_while_ringing) {
    reset(); l0_dials(); step(DIGIT_TIMEOUT_MS);
    bool first = out.ring_drive; step(20);
    CHECK(out.ring_drive != first);
}

int main(void) {
    RUN(offhook_gives_dialtone_on_its_pwm); RUN(dtmf_digit_rings_other_line);
    RUN(dtmf_held_std_counts_once); RUN(dtmf_abcd_is_ignored);
    RUN(dtmf_without_owner_is_ignored); RUN(ring_does_not_fake_answer);
    RUN(answer_during_burst_connects_after_it); RUN(dtmf_sel_holds_last_line);
    RUN(ring_drive_toggles_while_ringing);
    MINITEST_MAIN_END("test_pbx");
}
