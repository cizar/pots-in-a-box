#include "minitest.h"
#include "../src/hook.h"

/* Llama a hook_sample `ms` veces; junta eventos y el ms (1-based, dentro
 * de esta llamada) en que ocurrió el último. */
static hook_ev_t ev[32];
static int nev;
static int last_at;

static void feed(hook_t *h, bool closed, int ms, bool masked) {
    for (int i = 1; i <= ms; i++) {
        hook_ev_t e = hook_sample(h, closed, masked);
        if (e.type != HOOK_EV_NONE && nev < 32) { ev[nev++] = e; last_at = i; }
    }
}
static void reset(hook_t *h) { hook_init(h); nev = 0; last_at = 0; }
static void offhook(hook_t *h) { reset(h); feed(h, true, 60, false); nev = 0; }
static void pulses(hook_t *h, int n) {
    for (int i = 0; i < n; i++) { feed(h, false, 60, false); feed(h, true, 40, false); }
}

TEST(offhook_after_50ms) { /* también cubre arrancar con la línea ya descolgada */
    hook_t h; reset(&h);
    feed(&h, true, 49, false); CHECK_EQ(nev, 0); CHECK(!hook_is_off(&h));
    feed(&h, true, 1, false);
    CHECK_EQ(nev, 1); CHECK_EQ(ev[0].type, HOOK_EV_OFF); CHECK(hook_is_off(&h));
}
TEST(short_glitch_is_not_offhook) {
    hook_t h; reset(&h);
    feed(&h, true, 10, false); feed(&h, false, 1000, false);
    CHECK_EQ(nev, 0);
}
TEST(pulse_digit_3) {
    hook_t h; reset(&h);
    feed(&h, true, 60, false);
    pulses(&h, 3);
    feed(&h, true, 200, false);
    CHECK_EQ(nev, 2);
    CHECK_EQ(ev[0].type, HOOK_EV_OFF);
    CHECK_EQ(ev[1].type, HOOK_EV_DIGIT); CHECK_EQ(ev[1].digit, 3);
}
TEST(ten_pulses_is_zero) {
    hook_t h; offhook(&h);
    pulses(&h, 10); feed(&h, true, 200, false);
    CHECK_EQ(nev, 1); CHECK_EQ(ev[0].type, HOOK_EV_DIGIT); CHECK_EQ(ev[0].digit, 0);
}
TEST(two_digits) {
    hook_t h; offhook(&h);
    pulses(&h, 2); feed(&h, true, 300, false);
    pulses(&h, 5); feed(&h, true, 300, false);
    CHECK_EQ(nev, 2); CHECK_EQ(ev[0].digit, 2); CHECK_EQ(ev[1].digit, 5);
}
TEST(hangup_after_500ms_open) {
    hook_t h; offhook(&h);
    feed(&h, false, 600, false);
    CHECK_EQ(nev, 1); CHECK_EQ(ev[0].type, HOOK_EV_ON); CHECK_EQ(last_at, 500);
    CHECK(!hook_is_off(&h));
}
TEST(open_200ms_during_call_does_nothing) { /* Review Focus 4 */
    hook_t h; offhook(&h);
    feed(&h, false, 200, false); feed(&h, true, 1000, false);
    CHECK_EQ(nev, 0); CHECK(hook_is_off(&h));
}
TEST(open_15ms_not_counted) {
    hook_t h; offhook(&h);
    feed(&h, false, 15, false); feed(&h, true, 300, false);
    CHECK_EQ(nev, 0);
}
TEST(masked_ring_then_answer) { /* Review Focus 1 */
    hook_t h; reset(&h);
    for (int i = 0; i < 50; i++) feed(&h, (i & 1) != 0, 20, true);
    CHECK_EQ(nev, 0); CHECK(!hook_is_off(&h));
    feed(&h, true, 99, false); CHECK_EQ(nev, 0);
    feed(&h, true, 1, false);
    CHECK_EQ(nev, 1); CHECK_EQ(ev[0].type, HOOK_EV_OFF);
}
TEST(masked_while_offhook_keeps_state) {
    hook_t h; offhook(&h);
    feed(&h, false, 1000, true); feed(&h, true, 100, false);
    CHECK_EQ(nev, 0); CHECK(hook_is_off(&h));
}

int main(void) {
    RUN(offhook_after_50ms); RUN(short_glitch_is_not_offhook); RUN(pulse_digit_3);
    RUN(ten_pulses_is_zero); RUN(two_digits); RUN(hangup_after_500ms_open);
    RUN(open_200ms_during_call_does_nothing); RUN(open_15ms_not_counted);
    RUN(masked_ring_then_answer); RUN(masked_while_offhook_keeps_state);
    MINITEST_MAIN_END("test_hook");
}
