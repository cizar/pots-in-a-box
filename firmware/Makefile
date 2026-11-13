# Firmware for the 2-line PBX (ATmega328P @ 16 MHz)
#
#   make test    run the logic tests on the host
#   make         build/pbx.hex
#   make size    firmware size
#   make fuses   write fuses: 16 MHz full-swing crystal, BOD 4.3 V
#   make flash   flash the firmware over ISP

MCU        = atmega328p
F_CPU      = 16000000UL
PROGRAMMER ?= usbasp
PORT       ?= usb

BUILD   = build
SRC     = src
TESTS   = tests

# Pure modules: no <avr/*>, tested on the host
PURE_SRCS = $(filter-out $(SRC)/main.c $(SRC)/hal_avr.c,$(wildcard $(SRC)/*.c))
AVR_SRCS  = $(wildcard $(SRC)/*.c)

HOST_CC     = cc
HOST_CFLAGS = -std=c99 -Wall -Wextra -Werror -O1 -g
HOST_LIBS   = -lm

AVR_CC      = avr-gcc
AVR_CFLAGS  = -std=c99 -Wall -Wextra -Werror -Os -mmcu=$(MCU) -DF_CPU=$(F_CPU) \
              -ffunction-sections -fdata-sections
AVR_LDFLAGS = -mmcu=$(MCU) -Wl,--gc-sections

TEST_SRCS = $(wildcard $(TESTS)/test_*.c)
TEST_BINS = $(patsubst $(TESTS)/%.c,$(BUILD)/host/%,$(TEST_SRCS))

.PHONY: all test size fuses flash clean

all: $(BUILD)/pbx.hex

test: $(TEST_BINS)
	@fail=0; for t in $(TEST_BINS); do ./$$t || fail=1; done; exit $$fail

$(BUILD)/host/%: $(TESTS)/%.c $(PURE_SRCS) $(wildcard $(SRC)/*.h) $(TESTS)/minitest.h
	@mkdir -p $(dir $@)
	$(HOST_CC) $(HOST_CFLAGS) -o $@ $< $(PURE_SRCS) $(HOST_LIBS)

$(BUILD)/pbx.elf: $(AVR_SRCS) $(wildcard $(SRC)/*.h)
	@mkdir -p $(dir $@)
	$(AVR_CC) $(AVR_CFLAGS) $(AVR_LDFLAGS) -o $@ $(AVR_SRCS)

$(BUILD)/pbx.hex: $(BUILD)/pbx.elf
	avr-objcopy -O ihex -R .eeprom $< $@

size: $(BUILD)/pbx.elf
	avr-size --format=avr --mcu=$(MCU) $< 2>/dev/null || avr-size $<

fuses:
	avrdude -c $(PROGRAMMER) -P $(PORT) -p m328p \
	  -U lfuse:w:0xF7:m -U hfuse:w:0xD9:m -U efuse:w:0xFC:m

flash: $(BUILD)/pbx.hex
	avrdude -c $(PROGRAMMER) -P $(PORT) -p m328p -U flash:w:$<:i

clean:
	rm -rf $(BUILD)
