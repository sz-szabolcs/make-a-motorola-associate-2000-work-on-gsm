# Make a Motorola Associate 2000 phone work with GSM
## The main goal was make this phone able to make and accept a call on a GSM network instead of NMT 450 with it's original display, backlight and keypad.

# Credits to:
  - Thomascountz/micropython_i2c_lcd
  - basanovase/sim800 -> modified core.py @ line 9 & 14 (changed pre-defined UART pins to assignable GPIOs)


# Hardware

## External components:
  - ESP32-S3-Zero module - fits inside the CCCN4052A handpiece and has a lots of GPIO's
  - SIM800L module - also fits and works well with the CCCN4052A handpiece's original speaker and mic
  - PCF8574 - used as a serial to parallel port to drive the original display (S-8093A)

## Display:
  For pinout, see 'HeaderPinout_S-8093A' and 'CCCN4052A_modify_data_bus'. The four 10K resistors marked with red dots
  needs to be removed and the 6 pins on the custom controller (also marked) needs to be disconnected. -> This way the 4-bit
  bus of the display is free to use because isolated from the keypad and the custom u. The display module don't need
  to be removed. Works well with a PCF8574, but needs contrast voltages from the custom controller or from the
  main board to show anything! The traces on the board tends to break and-or lift if too much pressure or heat applied.

## Keypad:
  For row and column points see: 'CCCN4052A_pin_functions'. Note: the three 100K resistors marked with a red dot
  needs to be removed because those are pulling the columns up to the main board's 5V - it will be done by the
  ESP32.

## GSM module:
  It wont tolerate 5V, the marked 9.5V and common GND on 'CCCN4052A_pin_functions' are ideal to supply a generic
  7805, I dropped the output with a diode and it works well.

## Keypad, LCD backlight, ON/OFF key are managed from the original system, I did not touch that and the head unit. The head unit powers the system. I re-hydrated the cells of the original lead-acid battery and it also works for a few hours!

![CCCN4052A_working_boot.jpg](https://github.com/sz-szabolcs/make-a-motorola-associate-2000-work-on-gsm/blob/main/IMAGES_FINISHED/CCCN4052A_working_boot.jpg)
