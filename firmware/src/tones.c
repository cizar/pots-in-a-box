#include <stddef.h>
#include "tones.h"

/* Argentina: ITU-T E.180, Operational Bulletin annex (status as of 2010-05-01). */
/* USA: Precise Tone Plan. */
static const signal_spec_t TONES[2][3] = {
    [COUNTRY_AR] = {
        { 425, 0, 1, 0 },       /* DIAL     continuous */
        { 425, 0, 1000, 4000 }, /* RINGBACK */
        { 425, 0, 300, 200 },   /* BUSY     */
    },
    [COUNTRY_US] = {
        { 350, 440, 1, 0 },       /* DIAL     continuous */
        { 440, 480, 2000, 4000 }, /* RINGBACK */
        { 480, 620, 500, 500 },   /* BUSY     */
    },
};

static const signal_spec_t RING[2] = {
    [COUNTRY_AR] = { 25, 0, 1000, 4000 }, /* 25 Hz unverified; cadence = E.180 ringback */
    [COUNTRY_US] = { 20, 0, 2000, 4000 },
};

const signal_spec_t *tones_spec(country_t c, tone_id_t t) {
    if (t == TONE_NONE || t > TONE_BUSY || c > COUNTRY_US) return NULL;
    return &TONES[c][t - 1];
}

const signal_spec_t *tones_ring_spec(country_t c) {
    return &RING[c == COUNTRY_US ? COUNTRY_US : COUNTRY_AR];
}
