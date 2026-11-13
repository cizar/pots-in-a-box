#include <stddef.h>
#include "minitest.h"
#include "../src/tones.h"

TEST(ar_dial_is_425_continuous) {
    const signal_spec_t *s = tones_spec(COUNTRY_AR, TONE_DIAL);
    CHECK_EQ(s->f1_hz, 425); CHECK_EQ(s->f2_hz, 0); CHECK_EQ(s->off_ms, 0);
}
TEST(ar_busy_and_ringback) {
    const signal_spec_t *b = tones_spec(COUNTRY_AR, TONE_BUSY);
    CHECK_EQ(b->f1_hz, 425); CHECK_EQ(b->on_ms, 300); CHECK_EQ(b->off_ms, 200);
    const signal_spec_t *r = tones_spec(COUNTRY_AR, TONE_RINGBACK);
    CHECK_EQ(r->f1_hz, 425); CHECK_EQ(r->on_ms, 1000); CHECK_EQ(r->off_ms, 4000);
}
TEST(us_busy) {
    const signal_spec_t *s = tones_spec(COUNTRY_US, TONE_BUSY);
    CHECK_EQ(s->f1_hz, 480); CHECK_EQ(s->f2_hz, 620);
    CHECK_EQ(s->on_ms, 500); CHECK_EQ(s->off_ms, 500);
}
TEST(us_dial_and_ringback) {
    const signal_spec_t *d = tones_spec(COUNTRY_US, TONE_DIAL);
    CHECK_EQ(d->f1_hz, 350); CHECK_EQ(d->f2_hz, 440); CHECK_EQ(d->off_ms, 0);
    const signal_spec_t *r = tones_spec(COUNTRY_US, TONE_RINGBACK);
    CHECK_EQ(r->f1_hz, 440); CHECK_EQ(r->f2_hz, 480);
    CHECK_EQ(r->on_ms, 2000); CHECK_EQ(r->off_ms, 4000);
}
TEST(none_is_null) { CHECK(tones_spec(COUNTRY_AR, TONE_NONE) == NULL); }
TEST(ring_specs) {
    CHECK_EQ(tones_ring_spec(COUNTRY_AR)->f1_hz, 25);
    CHECK_EQ(tones_ring_spec(COUNTRY_AR)->on_ms, 1000);
    CHECK_EQ(tones_ring_spec(COUNTRY_AR)->off_ms, 4000);
    CHECK_EQ(tones_ring_spec(COUNTRY_US)->f1_hz, 20);
    CHECK_EQ(tones_ring_spec(COUNTRY_US)->on_ms, 2000);
    CHECK_EQ(tones_ring_spec(COUNTRY_US)->off_ms, 4000);
}

int main(void) {
    RUN(ar_dial_is_425_continuous); RUN(ar_busy_and_ringback); RUN(us_busy);
    RUN(us_dial_and_ringback); RUN(none_is_null); RUN(ring_specs);
    MINITEST_MAIN_END("test_tones");
}
