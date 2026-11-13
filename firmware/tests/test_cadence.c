#include "minitest.h"
#include "../src/cadence.h"

TEST(on_off_boundaries) {
    cadence_t c; cadence_start(&c, 1000, 4000);
    for (int i = 1; i <= 1000; i++) CHECK(cadence_tick(&c));
    for (int i = 1; i <= 4000; i++) CHECK(!cadence_tick(&c));
    CHECK(cadence_tick(&c)); /* llamada 5001: arranca otro período */
}
TEST(continuous) {
    cadence_t c; cadence_start(&c, 1, 0);
    for (int i = 0; i < 10000; i++) CHECK(cadence_tick(&c));
}
TEST(never) {
    cadence_t c; cadence_start(&c, 0, 500);
    for (int i = 0; i < 2000; i++) CHECK(!cadence_tick(&c));
}

int main(void) {
    RUN(on_off_boundaries); RUN(continuous); RUN(never);
    MINITEST_MAIN_END("test_cadence");
}
