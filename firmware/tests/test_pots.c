#include <string.h>
#include "minitest.h"
#include "../src/pots.h"

static pots_t p;
static pots_inputs_t in;
static pots_outputs_t out;

static void reset(void) {
    pots_init(&p);
    memset(&in, 0, sizeof in);
    in.country = COUNTRY_AR;
}
static void step(long ms) { for (long i = 0; i < ms; i++) pots_step(&p, &in, &out); }

/* L0 goes off-hook and dials one DTMF digit (code 5). */
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
    CHECK_EQ(out.f1[0], 425); /* ringback, first second */
}
TEST(dtmf_held_std_counts_once) {
    /* StD held high for 3 s: if it counted on every tick, the end-of-number
     * timer would keep restarting and the other line would never ring. */
    reset(); in.loop_closed[0] = true; step(60);
    in.dtmf_code = 5; in.dtmf_std = true; step(DIGIT_TIMEOUT_MS + 10);
    CHECK(out.ring_en[1]);
}
TEST(dtmf_abcd_is_ignored) {
    reset(); in.loop_closed[0] = true; step(60);
    in.dtmf_code = 13; in.dtmf_std = true; step(40); in.dtmf_std = false;
    step(DIGIT_TIMEOUT_MS + 100);
    CHECK(!out.ring_en[1]); CHECK_EQ(out.f1[0], 425); /* still dial tone */
}
TEST(dtmf_without_owner_is_ignored) {
    reset(); in.dtmf_code = 5; in.dtmf_std = true; step(40); in.dtmf_std = false;
    in.loop_closed[0] = true; step(60 + DIGIT_TIMEOUT_MS + 100);
    CHECK(!out.ring_en[1]);
}
TEST(ring_does_not_fake_answer) { /* ring looks like a closed loop */
    reset(); l0_dials(); step(DIGIT_TIMEOUT_MS);
    CHECK(out.ring_en[1]);
    in.loop_closed[1] = true;             /* ring seen as a closed loop */
    while (out.ring_en[1]) step(1);       /* until the burst ends */
    in.loop_closed[1] = false; step(300); /* modem still on-hook */
    CHECK(!out.led_call); CHECK(!out.link);
}
TEST(answer_during_burst_connects_after_it) {
    reset(); l0_dials(); step(DIGIT_TIMEOUT_MS);
    in.loop_closed[1] = true;              /* modem answers during the burst */
    while (out.ring_en[1]) step(1);
    CHECK(!out.led_call);
    step(MASK_TAIL_MS + HOOK_OFF_MS + 5);
    CHECK(out.led_call); CHECK(out.link); CHECK(!out.ring_en[1]);
}
TEST(dtmf_sel_holds_last_line) {
    reset(); in.loop_closed[1] = true; step(60);
    CHECK_EQ(out.dtmf_sel, 1);
    in.loop_closed[1] = false; step(600);  /* hangs up: dtmf_line = -1 */
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
    MINITEST_MAIN_END("test_pots");
}
