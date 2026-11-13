/* hal_avr.c — ATmega328P @ 16 MHz.
 *
 * Timer0: PWM rápido 8 bits sin prescaler (62500 Hz) en OC0A (PD6, L1) y
 *         OC0B (PD5, L2). La ISR de desborde alterna canales: L1 en los
 *         desbordes impares y L2 en los pares, así cada canal se actualiza a
 *         DDS_SAMPLE_RATE_HZ = 31250 y ninguna ISR calcula dos muestras.
 * Timer1: CTC a 1 kHz para el tick lógico.
 */
#include <avr/interrupt.h>
#include <avr/io.h>
#include "dds.h"
#include "hal.h"

static dds_t dds[2];
static volatile bool tick_flag;

ISR(TIMER0_OVF_vect) {
    static uint8_t odd;
    odd ^= 1;
    if (odd) OCR0A = dds_next(&dds[0]);
    else OCR0B = dds_next(&dds[1]);
}

ISR(TIMER1_COMPA_vect) { tick_flag = true; }

void hal_init(void) {
    /* Salidas: PB0 RING_EN_L1, PB1 RING_EN_L2, PB2 LINK_EN. */
    DDRB |= _BV(PB0) | _BV(PB1) | _BV(PB2);
    PORTB &= ~(_BV(PB0) | _BV(PB1) | _BV(PB2));

    /* Salidas: PD3 LED_CALL, PD4 RING_DRIVE, PD5/PD6 tonos, PD7 DTMF_SEL.
     * Entradas: PD0 COUNTRY_SW (pull-up), PD2 DTMF_STD. PD1 reservado UART TX. */
    DDRD |= _BV(PD3) | _BV(PD4) | _BV(PD5) | _BV(PD6) | _BV(PD7);
    DDRD &= ~(_BV(PD0) | _BV(PD2));
    PORTD = (PORTD & ~(_BV(PD3) | _BV(PD4) | _BV(PD7))) | _BV(PD0);

    /* Entradas: PC0/PC1 OFFHOOK (pull-up), PC2-PC5 Q1-Q4 del MT8870. */
    DDRC &= ~0x3F;
    PORTC = (PORTC & ~0x3C) | 0x03;

    dds_set(&dds[0], 0, 0);
    dds_set(&dds[1], 0, 0);
    OCR0A = OCR0B = 128;
    TCCR0A = _BV(COM0A1) | _BV(COM0B1) | _BV(WGM01) | _BV(WGM00);
    TCCR0B = _BV(CS00);
    TIMSK0 = _BV(TOIE0);

    TCCR1A = 0;
    TCCR1B = _BV(WGM12) | _BV(CS11);  /* CTC, prescaler 8 */
    OCR1A = (F_CPU / 8 / 1000) - 1;   /* 1 ms */
    TIMSK1 = _BV(OCIE1A);

    sei();
}

bool hal_loop_closed(uint8_t line) { return !(PINC & _BV(line ? PC1 : PC0)); }
bool hal_dtmf_std(void) { return (PIND & _BV(PD2)) != 0; }
uint8_t hal_dtmf_code(void) { return (uint8_t)((PINC >> PC2) & 0x0F); }
country_t hal_country(void) { return (PIND & _BV(PD0)) ? COUNTRY_AR : COUNTRY_US; }

static void pin(volatile uint8_t *port, uint8_t bit, bool on) {
    if (on) *port |= _BV(bit);
    else *port &= ~_BV(bit);
}

void hal_set_ring_en(uint8_t line, bool on) { pin(&PORTB, line ? PB1 : PB0, on); }
void hal_set_ring_drive(bool phase) { pin(&PORTD, PD4, phase); }
void hal_set_link(bool on) { pin(&PORTB, PB2, on); }
void hal_set_dtmf_sel(uint8_t line) { pin(&PORTD, PD7, line != 0); }
void hal_set_led_call(bool on) { pin(&PORTD, PD3, on); }

void hal_set_tones(uint8_t line, uint16_t f1_hz, uint16_t f2_hz) {
    /* Las divisiones van fuera de la sección crítica. */
    uint16_t inc1 = dds_increment(f1_hz), inc2 = dds_increment(f2_hz);
    uint8_t sreg = SREG;
    cli();
    dds_set_increments(&dds[line & 1], inc1, inc2);
    SREG = sreg;
}

bool hal_tick_pending(void) { return tick_flag; }
void hal_tick_clear(void) { tick_flag = false; }
