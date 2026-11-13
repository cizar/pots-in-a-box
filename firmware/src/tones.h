/* tones.h — tabla de tonos y ring por país (ITU-T E.180). */
#ifndef TONES_H
#define TONES_H

#include <stdint.h>

typedef enum { COUNTRY_AR = 0, COUNTRY_US = 1 } country_t;
typedef enum { TONE_NONE = 0, TONE_DIAL, TONE_RINGBACK, TONE_BUSY } tone_id_t;

/* f2_hz = 0: un solo tono. off_ms = 0: continuo. */
typedef struct {
    uint16_t f1_hz, f2_hz, on_ms, off_ms;
} signal_spec_t;

/* NULL para TONE_NONE. */
const signal_spec_t *tones_spec(country_t c, tone_id_t t);
/* Frecuencia de ring en f1_hz y su cadencia. */
const signal_spec_t *tones_ring_spec(country_t c);

#endif
