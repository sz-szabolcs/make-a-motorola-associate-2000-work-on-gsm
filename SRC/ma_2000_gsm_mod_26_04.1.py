""" Credits to:
        - Thomascountz/micropython_i2c_lcd
        - basanovase/sim800 -> modified core.py @ line 9 & 14 (changed pre-defined UART pins to assignable GPIOs)

A simple program to make a modified Motorola Associate 2000 work again (with GSM instead of NMT 450).
HW modify: see R&D_IMAGES, readme. [SoC: ESP32S3] It can accept or make a call, shows and call back a missed call.

Accept an incoming call: HF key
Hang up an incoming or outgoing call: CL
Open Menu: M/R
    Step Menu Items: UP arrow
        Enter: A
            Call a typed in number (*-key will be the +): A
Exit: CL in Sub-Menu or Main Menu->Abort->A
In case of a missed call, a 'Missed: Contact name' or 'Missed: number' will appear on the display. Pressing A will call
it back.

V2026.4.1

- This display module 'S-8093A' uses a HD44780 with a MSM5839C so it deals with the segments in a unique way. However,
  it looks like a 2 line, 8 char setup, it actually a one line, 16 char display (?) so HD44780 object should init with
  num_lines=1, num_columns=16. It also solves the faded contrast issue somehow.

* Issues:
- For some reason, SIM800's number appears as an unknown caller during an outgoing call, different power sources
  including a Li-Ion battery will not help.
- Catch a missed incoming call sometimes is not working. This code implemented in about 1.5 days along HW testings, feel
  free to make it better. 2026-04-19
"""


from micropython import const
from time import sleep_ms, time
from machine import Pin, I2C
from pcf8574 import PCF8574
from hd44780 import HD44780
from lcd import LCD
from associate_2k_keypad import Associate2KKeypad
from sim800 import SIM800
from sim800 import utils
from my_contacts import ma_2000_gsm_mod_contacts


# --------  PIN MAP  --------
# this I2C bus drives the 4 bit mode parallel HD44780 display module through a PCF8574:
I2C_BUS0_PCF8574_SCL = const(9)
I2C_BUS0_PCF8574_SDA = const(8)

KEYP_COL_1 = const(7)   # 1, 4, 7, *, CL
KEYP_COL_2 = const(10)  # 2, 5, 8, 0, A, MR
KEYP_COL_3 = const(11)  # 3, 6, 9, #, HF, UP
KEYP_ROW_1 = const(12)  # 1, 2, 3
KEYP_ROW_2 = const(13)  # 4, 5, 6
KEYP_ROW_3 = const(6)   # 7, 8, 9
KEYP_ROW_4 = const(5)   # *, 0, #
KEYP_ROW_5 = const(4)   # CL, A, HF
KEYP_ROW_6 = const(3)   # MR, UP

SIM800_RX = const(2)
SIM800_TX = const(1)
SIM800_RING = const(17)  # pulled to LOW when there is an incoming phone call or sms
# --------  PIN MAP END  --------


# --------  CONTROL VARS  --------
DEBUG = False
mainloop_cycle_time = 200  # milliseconds
menu_loop_cycle_time = 100
is_in_active_call = False
menu_pointer = 0
current_pressed_key = ""
current_caller_id_linked_name = ""
contact_to_show_on_incoming_call = ""
timer_to_show = ""
mins, secs = "", ""
start_time = time()
gsm_current_caller_number = "NAN"
gsm_last_caller_number = "NAN"
tmp_is_missed_call = False
incoming_call_response_status = "not_rang_not_responded"  # not_rang_not_responded, rang_not_responded, rang_responded
missed_call_active = False
# --------  CONTROL VARS END  --------


# --------  INIT DISPLAY  --------
i2c_0 = I2C(0, sda=Pin(I2C_BUS0_PCF8574_SDA), scl=Pin(I2C_BUS0_PCF8574_SCL), freq=400000)

if DEBUG:
    print(f'I2C slave(s): {i2c_0.scan()}')

pcf8574 = PCF8574(i2c_0, address=0x20)  # NXP chip, A0, A1, A2 are grounded
hd44780 = HD44780(pcf8574, num_lines=1, num_columns=16)
display = LCD(hd44780, pcf8574)

# show a nice, high-tech welcome screen while stuff boots:
display.display_on()
display.clear()
display.cursor_on()
display.blink_on()
display.write_line("MOTOROLA", 0)


# display methods:
# display_on()
# display_off()
# backlight_on() - [i] - backlight is not connected in this HW setup, Motorola deals with it with factory FW
# backlight_off()
# clear()
# cursor_on()
# cursor_off()
# reset_cursor(num_pos)
# blink_on()
# blink_off()
# write_line("01234567", line_num_at_0_or_1)
# scroll_content_off_screen("left", time_num_seconds)
# scroll_content_off_screen("right", time_num_seconds)
# marquee_text("test", line_num, time_num_seconds)
# write_lines("First line\nSecond line")
# --------  INIT DISPLAY END  --------


# --------  INIT KEYPAD  --------
keypad = Associate2KKeypad(KEYP_COL_1, KEYP_COL_2, KEYP_COL_3, KEYP_ROW_1,
                           KEYP_ROW_2, KEYP_ROW_3, KEYP_ROW_4, KEYP_ROW_5, KEYP_ROW_6)
# --------  INIT KEYPAD END  --------


# --------  INIT GMS MODULE  --------
gsm = SIM800(uart_device_rx_pin=SIM800_RX, uart_device_tx_pin=SIM800_TX)
is_incoming_call_detected = Pin(SIM800_RING, Pin.IN, Pin.PULL_UP)  # while module is ringing, it pulled to LOW

# enabling caller ID notification:
enable_caller_id_notification = utils.SIM800Utils.send_command(uart=gsm.uart, command="AT+CLIP=1", wait_for="OK", timeout=2000)
sleep_ms(500)
if DEBUG:
    print(f'GSM response for enable caller id notification: {enable_caller_id_notification}')

# sim800 methods:
# make and end a call
# dial_number('phonenumber')
# hang_up()

# answer an incoming call:
# from sim800 import utils
# utils.SIM800Utils.send_command(uart=gsm.uart, command="ATA", wait_for="OK", timeout=2000)

# get GPRS:
# from sim800 import SIM800GPRS
# sim800 = SIM800GPRS(uart_device_rx_pin=SIM800_RX, uart_device_tx_pin=SIM800_TX)
# location_info = sim800.get_gsm_location()
# print("GSM Location Info:", location_info)

# send SMS:
# from sim800 import SIM800SMS
# sim800 = SIM800SMS(uart_device_rx_pin=SIM800_RX, uart_device_tx_pin=SIM800_TX)
# sim800.send_sms('phonenumber', 'Hello World')

# read data from module while an incoming call is active and get the caller's number as a string:
# gsm_runtime_response = gsm.read_response()
# gsm_current_caller_number = str(gsm_runtime_response)[26:38]
# --------  INIT GMS MODULE END  --------


def menu_phonebook(cyc_time):
    global current_pressed_key
    temp_phonebook_contacts = []  # [['name', 'number'], ['name2', 'number']]
    display.clear()

    for key, value in ma_2000_gsm_mod_contacts.items():
        temp_phonebook_contacts.append([value, key])

    temp_phonebook_contacts_len = len(temp_phonebook_contacts) - 1
    contact_pointer = 0

    while 1:
        current_pressed_key = keypad.scan_keypad()

        if current_pressed_key == "UP":
            if contact_pointer < temp_phonebook_contacts_len:
                contact_pointer += 1
            elif contact_pointer == temp_phonebook_contacts_len:
                if current_pressed_key == "UP":
                    contact_pointer = 0

        current_contact_to_show = f'{temp_phonebook_contacts[contact_pointer][0]}{temp_phonebook_contacts[contact_pointer][1]}'
        display.write_line(current_contact_to_show, 0)

        if current_pressed_key == "A":
            display.clear()
            display.write_line(f'Calling-{temp_phonebook_contacts[contact_pointer][0]}', 0)
            gsm.dial_number(temp_phonebook_contacts[contact_pointer][1])
        if current_pressed_key == "CL":
            gsm.hang_up()
            mainloop(mainloop_cycle_time)
            break

        sleep_ms(cyc_time)


def menu_dial_number(cyc_time):
    global current_pressed_key
    temp_typed_in_num = ""
    display.clear()
    display.write_line("Dial...:", 0)

    while 1:
        current_pressed_key = keypad.scan_keypad()
        if current_pressed_key:
            if current_pressed_key == "*":  # no '+' on keypad
                current_pressed_key = "+"
            if len(temp_typed_in_num) <= 11:
                temp_typed_in_num += current_pressed_key
            display.write_line(temp_typed_in_num, 0)
        if current_pressed_key == "A":
            gsm.dial_number(temp_typed_in_num)
            display.write_line(f'{temp_typed_in_num}->', 0)
        if current_pressed_key == "CL":
            gsm.hang_up()
            mainloop(mainloop_cycle_time)
            break

        sleep_ms(cyc_time)


def open_menu(cyc_time):
    global menu_pointer, current_pressed_key
    display.clear()
    display.write_line("  MENU  (UP)", 0)

    while 1:
        current_pressed_key = keypad.scan_keypad()
        if menu_pointer >= 5:
            menu_pointer = 0
        if current_pressed_key == "UP":
            menu_pointer += 1

        if menu_pointer == 1:
            display.write_line("Contacts", 0)
            if current_pressed_key == "A":
                menu_phonebook(menu_loop_cycle_time)
                break
        elif menu_pointer == 2:
            display.write_line("Dial a number", 0)
            if current_pressed_key == "A":
                menu_dial_number(menu_loop_cycle_time)
                break
        elif menu_pointer == 3:
            display.write_line("Abort", 0)
            if current_pressed_key == "A":
                mainloop(mainloop_cycle_time)
                break
        elif menu_pointer == 4:  # break loop and exit can help to connect to the device through serial
            display.write_line("#DEBUG_MODE#", 0)
            if current_pressed_key == "A":
                break
        else:
            pass

        sleep_ms(cyc_time)


# --------  MAIN PROGRAM  --------
# the other part of the welcome screen indicates a successful boot:
display.clear()
display.write_line("Keep W140 Alive!", 0)
display.scroll_content_off_screen("left", 0.5)
display.clear()
display.write_line(" Ready.", 0)


# main loop:
def mainloop(cyc_time):
    global current_pressed_key, current_caller_id_linked_name, contact_to_show_on_incoming_call, timer_to_show, \
        mins, secs, start_time, is_in_active_call, tmp_is_missed_call, incoming_call_response_status, \
        missed_call_active, gsm_current_caller_number, gsm_last_caller_number

    display.cursor_off()
    display.blink_off()

    while 1:
        current_pressed_key = keypad.scan_keypad()  # always scan keypad

        if current_pressed_key == "CL":  # hang up an answered call by pressing CL key
            gsm.hang_up()
            is_in_active_call = False
            display.write_line("->Call Ended", 0)
            sleep_ms(500)
            display.clear()

        if is_in_active_call:  # show elapsed time during an answered incoming call
            elapsed = int(time() - start_time)
            mins, secs = divmod(elapsed, 60)
            timer_to_show = f"{mins:02d}:{secs:02d}"
            display.write_line(contact_to_show_on_incoming_call[0:11] + timer_to_show, 0)

        if current_pressed_key == "MR":
            open_menu(menu_loop_cycle_time)
            break

        # always check RING pin:
        if not is_incoming_call_detected.value():  # if we have an incoming call
            gsm_runtime_response = gsm.read_response()  # get the caller's number as a string
            try:
                gsm_current_caller_number = str(gsm_runtime_response)[26:38]  # number should be always on this index
                if "+" in gsm_current_caller_number:
                    gsm_last_caller_number = gsm_current_caller_number
            except ValueError as error1:
                gsm_last_caller_number = "NAN"

            if gsm_last_caller_number in ma_2000_gsm_mod_contacts:  # if the number is in our 'phonebook'
                current_caller_id_linked_name = ma_2000_gsm_mod_contacts[gsm_last_caller_number]
                contact_to_show_on_incoming_call = f'{current_caller_id_linked_name}Calling!'
                display.clear()
                display.write_line(contact_to_show_on_incoming_call, 0)  # display that a contact is calling
            else:  # else the number displayed without a name
                contact_to_show_on_incoming_call = f'{gsm_last_caller_number}<-'
                display.clear()
                display.write_line(contact_to_show_on_incoming_call, 0)

            if current_pressed_key == "HF":  # incoming call can be answered by pressing HF key
                utils.SIM800Utils.send_command(uart=gsm.uart, command="ATA", wait_for="OK", timeout=2000)
                is_in_active_call = True
                start_time = time()  # reset timer
                display.clear()
                incoming_call_response_status = "rang_responded"
            elif current_pressed_key == "CL":  # hang up an active incoming call by pressing CL key
                gsm.hang_up()
                is_in_active_call = False
                display.write_line("->Call Ended", 0)
                sleep_ms(500)
                display.clear()
                incoming_call_response_status = "rang_responded"
            else:
                incoming_call_response_status = "rang_not_responded"

        else:
            if is_incoming_call_detected.value():
                if not missed_call_active:  # only return to idle state if we do not have an active incoming or missed call
                    if not is_in_active_call:
                        display.write_line(" Ready.", 0)

            # dealing with a missed call:
            if incoming_call_response_status == "rang_not_responded" and is_incoming_call_detected.value():  # only try to fetch if there was a call but nobody touched the keypad
                gsm_runtime_response = gsm.read_response()  # get the 'NO CARRIER' status from SIM800 if there was a missed call
                try:
                    tmp_is_missed_call = str(gsm_runtime_response)[6:16]  # b'\r\nNO CARRIER\r\n'
                except ValueError as error2:
                    tmp_is_missed_call = False
                if tmp_is_missed_call == "NO CARRIER":
                    missed_call_active = True

                if gsm_last_caller_number in ma_2000_gsm_mod_contacts:
                    current_caller_id_linked_name = ma_2000_gsm_mod_contacts[gsm_last_caller_number]
                    contact_to_show_on_incoming_call = f'Missed:{current_caller_id_linked_name}'
                    if missed_call_active:
                        display.clear()
                        display.write_line(contact_to_show_on_incoming_call, 0)
                else:
                    contact_to_show_on_incoming_call = f'Missed:{gsm_last_caller_number}'
                    if missed_call_active:
                        display.clear()
                        display.write_line(contact_to_show_on_incoming_call, 0)

                if current_pressed_key == "A":
                    display.clear()
                    display.write_line("Calling Back!", 0)
                    gsm.dial_number(gsm_last_caller_number)
                    incoming_call_response_status = "not_rang_not_responded"
                    missed_call_active = False

        if DEBUG:
            print(f'gsm_last_caller_number: {gsm_last_caller_number}')
            print(f'is_in_active_call: {is_in_active_call}')
            print(f'tmp_is_missed_call: {tmp_is_missed_call}')
            print(f'incoming_call_response_status: {incoming_call_response_status}')
            print(f'missed_call_active: {missed_call_active}')
            print(f'contact_to_show_on_incoming_call: {contact_to_show_on_incoming_call}')

        sleep_ms(cyc_time)


mainloop(mainloop_cycle_time)
# --------  MAIN PROGRAM END  --------
