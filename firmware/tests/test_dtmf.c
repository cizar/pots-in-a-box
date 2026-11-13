#include "minitest.h"
#include "../src/dtmf.h"

TEST(maps_digits) {
    CHECK_EQ(dtmf_code_to_digit(1), 1);
    CHECK_EQ(dtmf_code_to_digit(9), 9);
    CHECK_EQ(dtmf_code_to_digit(10), 0);
    CHECK_EQ(dtmf_code_to_digit(11), DTMF_STAR);
    CHECK_EQ(dtmf_code_to_digit(12), DTMF_HASH);
}

TEST(rejects_abcd_and_garbage) {
    CHECK_EQ(dtmf_code_to_digit(0), -1);
    CHECK_EQ(dtmf_code_to_digit(13), -1);
    CHECK_EQ(dtmf_code_to_digit(15), -1);
    CHECK_EQ(dtmf_code_to_digit(16), -1);
}

int main(void) {
    RUN(maps_digits);
    RUN(rejects_abcd_and_garbage);
    MINITEST_MAIN_END("test_dtmf");
}
