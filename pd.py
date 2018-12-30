"""This file is part of the libsigrokdecode project.

Copyright (C) 2018 Libor Gabaj <libor.gabaj@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see <http://www.gnu.org/licenses/>.

"""

import sigrokdecode as srd
from common.srdhelper import bcd2int

weekdays = (
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
    "Saturday", "Sunday"
)

rates = {
    0b00: 1,
    0b01: 4096,
    0b10: 8192,
    0b11: 32768,
}

bits = {
    # Time keeping regiters
    "CH": 0x07,
    "MODE": 0x06,
    "AMPM": 0x05,
    # Control register
    "OUT": 0x07,
    "SQWE": 0x04,
    "RS1": 0x01,
    "RS0": 0x00,
}


class AnnRegs:
    """Enumeration of annotations for registers."""

    (
        SECOND, MINUTE, HOUR, WEEKDAY, DAY, MONTH, YEAR,
        CONTROL, NVRAM
    ) = range(0, 9)


class AnnBitsCtlr:
    """Enumeration of annotations for control bits."""

    (
        RESERVED,
        CH, MODE, AMPM,     # From time keeping registers
        OUT, SQWE, RATE     # From control registers
    ) = range(AnnRegs.NVRAM + 1, 16)


class AnnBitsTime:
    """Enumeration of annotations for time keeping bits."""

    (
        SECOND, MINUTE, HOUR,       # From time registers
        WEEKDAY, DAY, MONTH, YEAR,  # From date registers
        NVRAM
    ) = range(AnnBitsCtlr.RATE + 1, 24)


class AnnStrings:
    """Enumeration of annotations for formatted strings."""

    (
        DTREAD, DTWRITE,    # Datetime formatting
        REGREAD, REDWRITE,  # Data formatting
        WARN
    ) = range(AnnBitsTime.NVRAM + 1, 29)


class Decoder(srd.Decoder):
    """Protocol decoder for real time clock chip  ``DS1307``."""

    api_version = 3
    id = "ds1307"
    name = "DS1307"
    longname = "Dallas DS1307 RTC chip"
    desc = "Realtime clock module protocol."
    license = "gplv2+"
    inputs = ["i2c"]
    outputs = ["ds1307"]

    options = (
        {"id": "start_weekday", "desc": "The first day of the week",
            "default": "Monday", "values": weekdays},
        {"id": "date_format", "desc": "Date format",
            "default": "European", "values": ("European", "American", "ANSI")}
    )

    annotations = (
        # Registers
        ("reg-seconds", "Seconds register"),            # 0
        ("reg-minutes", "Minutes register"),            # 1
        ("reg-hours", "Hours register"),                # 2
        ("reg-weekdays", "Weekdays register"),          # 3
        ("reg-days", "Days register"),                  # 4
        ("reg-months", "Months register"),              # 5
        ("reg-years", "Years register"),                # 6
        ("reg-control", "Control register"),            # 7
        ("reg-nvram", "Non-volatile memory register"),  # 8
        # Control bits
        ("bit-reserved", "Reserved bit"),               # 9
        ("bit-ch", "Clock halt bit"),                   # 10
        ("bit-mode", "12/24 hours mode bit"),           # 11
        ("bit-ampm", "AM/PM bit"),                      # 12
        ("bit-out", "OUT bit"),                         # 13
        ("bit-sqwe", "SQWE bit"),                       # 14
        ("bit-rate", "Rate select bits"),               # 15
        # Time keeping and NVRAM bits
        ("bit-second", "Second bits"),                  # 16
        ("bit-minute", "Minute bits"),                  # 17
        ("bit-hour", "Hour bits"),                      # 18
        ("bit-weekday", "Weekday bits"),                # 19
        ("bit-date", "Date bits"),                      # 20
        ("bit-month", "Month bits"),                    # 21
        ("bit-year", "Year bits"),                      # 22
        ("bit-nvram", "Non-volatile memory bits"),      # 23
        # Strings
        ("read-datetime", "Read datetime"),             # 24
        ("write-datetime", "Write datetime"),           # 25
        ("reg-read", "Register read"),                  # 26
        ("reg-write", "Register write"),                # 27
        ("warnings", "Warnings"),                       # 28
    )

    annotation_rows = (
        ("bits", "Bits", tuple(range(9, 24))),
        ("regs", "Registers", tuple(range(AnnRegs.SECOND, AnnRegs.NVRAM + 1))),
        ("datetime", "Date/time", tuple(range(AnnStrings.DTREAD,
                                              AnnStrings.WARN))),
        ("warnings", "Warnings", (AnnStrings.WARN,))
    )

    ADDRESS = 0x68
    """str: Expected I2C address of the slave DS1307."""

    NVRAM_MIN = 0x08
    """str: Minimal position of the internal non-volatile memory of DS1307."""

    NVRAM_MAX = 0x3f
    """str: Maximal position of the internal non-volatile memory of DS1307."""

    def __init__(self):
        """Initialize decoder."""
        self.reset()

    def reset(self):
        """Reset decoder and initialize instance variables."""
        # Common parameters for I2C sampling
        self.ss = 0         # Start sample
        self.es = 0         # End sample
        self.ssb = 0        # Start sample of a formatted string block
        self.bits = []
        self.state = "IDLE"
        # Specific parameters for a device
        self.reg = -1                       # Processed slave register
        self.second = -1
        self.minute = -1
        self.hour = -1
        self.weekday = -1
        self.day = -1
        self.month = -1
        self.year = -1

    def start(self):
        """Actions before the beginning of the decoding."""
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def check_chip(self, addr_slave):
        """Check correct slave address of the chip."""
        if self.ADDRESS == addr_slave:
            return True
        self.put(self.ssb, self.es, self.out_ann,
                 [AnnStrings.WARN,
                  ["Unknown slave address ({:#04x})"
                   .format(addr_slave)]])
        return False

    def output_datetime(self, ann_index, rw_prefix):
        """Format datetime string and prefix it by recent r/w operation.

        - Applied decoder options for the starting weekday and date format.
        - Datetime parts are numbered in the format string equally to numbering
          of time keeping registers.
        """
        if self.options["date_format"] == "European":
            format_datetime =\
                "{3:s} {4:02d}.{5:02d}.{6:04d} {2:02d}:{1:02d}:{0:02d}"
        elif self.options["date_format"] == "American":
            format_datetime =\
                "{3:s}, {5:02d}/{4:02d}/{6:04d} {2:02d}:{1:02d}:{0:02d}"
        elif self.options["date_format"] == "ANSI":
            format_datetime =\
                "{6:04d}-{4:02d}-{5:02d}T{2:02d}:{1:02d}:{0:02d}"
        else:
            format_datetime = "Unknown format"
        dt_str = format_datetime.format(
            self.second, self.minute, self.hour,
            weekdays[self.weekday], self.day, self.month, self.year,
        )
        self.put(self.ssb, self.es, self.out_ann,
                 [ann_index, ["{} datetime: {}".format(rw_prefix, dt_str)]])

    def put_data(self, bit_start, bit_stop, data):
        """Span data output across bit range.

        - Output is an annotation block from the start sample of the first bit
          to the end sample of the last bit.
        """
        self.put(self.bits[bit_start][1], self.bits[bit_stop][2],
                 self.out_ann, data)

    def put_reserved(self, bit_reserved):
        """Span output under reserved bit.

        - Output is an annotation block from the start  to the end sample
          of a reserved bit.
        """
        self.put(self.bits[bit_reserved][1], self.bits[bit_reserved][2],
                 self.out_ann,
                 [AnnBitsCtlr.RESERVED,
                  [self.annotations[AnnBitsCtlr.RESERVED][1],
                   "Reserved", "Rsvd", "R"]])

    def handle_reg(self, databyte):
        """Create name and call corresponding slave registers handler.

        - Honor address auto-increment feature of the DS1307. When the
          address reaches maximal nvram position, it will wrap around
          to address 0.
        """
        reg = self.reg if self.reg < self.NVRAM_MIN else self.NVRAM_MAX
        fn = getattr(self, "handle_reg_{:#04x}".format(reg))
        fn(databyte)
        self.reg += 1
        if self.reg > self.NVRAM_MAX:
            self.reg = 0

    def handle_reg_0x00(self, databyte):
        """Process seconds (0-59) and Clock halt bit."""
        # Registers row
        self.put_data(7, 0, [AnnRegs.SECOND,
                             [self.annotations[AnnRegs.SECOND][1],
                              "Seconds", "Sec", "S"]])
        # Bits row - Clock Halt bit
        ch = 1 if (databyte & (1 << bits["CH"])) else 0
        annots = [self.annotations[AnnBitsCtlr.CH][1], "Clock halt", "Clk hlt",
                  "CH", "CH", "C"]
        for i in range(0, len(annots) - 2):
            annots[i] += ": {}".format(ch)
        self.put_data(bits["CH"], bits["CH"], [AnnBitsCtlr.CH, annots])
        # Bits row - Second bits
        self.second = bcd2int(databyte & 0x7f)
        annots = [self.annotations[AnnBitsTime.SECOND][1], "Second", "Sec",
                  "S", "S"]
        for i in range(0, len(annots) - 1):
            annots[i] += ": {}".format(self.second)
        self.put_data(6, 0, [AnnBitsTime.SECOND, annots])

    def handle_reg_0x01(self, databyte):
        """Process minutes (0-59)."""
        # Registers row
        self.put_data(7, 0, [AnnRegs.MINUTE,
                             [self.annotations[AnnRegs.MINUTE][1],
                              "Minutes", "Min", "M"]])
        # Bits row
        self.put_reserved(7)
        self.minute = bcd2int(databyte & 0x7f)
        annots = [self.annotations[AnnBitsTime.MINUTE][1], "Minute", "Min",
                  "M", "M"]
        for i in range(0, len(annots) - 1):
            annots[i] += ": {}".format(self.minute)
        self.put_data(6, 0, [AnnBitsTime.MINUTE, annots])

    def handle_reg_0x02(self, databyte):
        """Process hours (1-12+AM/PM or 0-23) and 12/24 hours mode.

        - In case of 12 hours mode convert hours to 24 hours mode to instance
          variable for formatting.
        """
        # Registers row
        self.put_data(7, 0, [AnnRegs.HOUR,
                             [self.annotations[AnnRegs.HOUR][1],
                              "Hours", "Hrs", "Hr", "H"]])
        # Bits row
        self.put_reserved(7)
        mode12h = True if (databyte & (1 << bits["MODE"])) else False
        if mode12h:
            # Bits row - 12h mode
            annots = ["12 hours mode", "12h mode", "12h", "12"]
            self.put_data(bits["MODE"], bits["MODE"],
                          [AnnBitsCtlr.MODE, annots])
            # Bits row - AM/PM mode
            am = "PM" if (databyte & (1 << bits["AMPM"])) else "AM"
            annots = [am, am[0]]
            self.put_data(bits["AMPM"], bits["AMPM"],
                          [AnnBitsCtlr.AMPM, annots])
            # Bits row - hours
            self.hour = bcd2int(databyte & 0x1f)
            annots = [self.annotations[AnnBitsTime.HOUR][1], "Hour", "Hr",
                      "H", "H"]
            for i in range(0, len(annots) - 1):
                annots[i] += ": {}".format(self.hour)
            self.put_data(4, 0, [AnnBitsTime.HOUR, annots])
            # Convert to 24h expression
            self.hour %= 12
            if am == "PM":
                self.hour += 12
        else:
            # Bits row - 24h mode
            annots = ["24 hours mode", "24h mode", "24h", "24"]
            self.put_data(6, 6, [AnnBitsCtlr.MODE, annots])
            self.hour = bcd2int(databyte & 0x3f)
            annots = [self.annotations[AnnBitsTime.HOUR][1], "Hour", "Hr",
                      "H", "H"]
            for i in range(0, len(annots) - 1):
                annots[i] += ": {}".format(self.hour)
            self.put_data(5, 0, [AnnBitsTime.HOUR, annots])

    def handle_reg_0x03(self, databyte):
        """Process weekday (1-7).

        - Recalculate weekday in respect to starting weekday option to instance
          variable for formatting.
        """
        # Registers row
        self.put_data(7, 0, [AnnRegs.WEEKDAY,
                             [self.annotations[AnnRegs.WEEKDAY][1],
                              "Weekdays", "Wday", "WD", "W"]])
        # Bits row
        for i in range(7, 2, -1):
            self.put_reserved(i)
        self.weekday = bcd2int(databyte & 0x07)
        start_weekday_index = 0
        for i, weekday in enumerate(weekdays):
            if weekday == self.options["start_weekday"]:
                start_weekday_index = i
                break
        start_weekday_index += self.weekday - 1
        start_weekday_index %= 7
        weekday = weekdays[start_weekday_index]
        annots = [self.annotations[AnnBitsTime.WEEKDAY][1], "Weekday", "WD",
                  "WD", "W"]
        for i in range(0, len(annots) - 2):
            annots[i] += ": {}".format(weekday)
        self.put_data(2, 0, [AnnBitsTime.WEEKDAY, annots])
        self.weekday = start_weekday_index

    def handle_reg_0x04(self, databyte):
        """Process day (1-31)."""
        # Registers row
        self.put_data(7, 0, [AnnRegs.DAY,
                             [self.annotations[AnnRegs.DAY][1],
                              "Days", "Day", "D"]])
        # Bits row
        for i in (7, 6):
            self.put_reserved(i)
        self.day = bcd2int(databyte & 0x3f)
        annots = [self.annotations[AnnBitsTime.DAY][1], "Day", "D", "D"]
        for i in range(0, len(annots) - 1):
            annots[i] += ": {}".format(self.day)
        self.put_data(5, 0, [AnnBitsTime.DAY, annots])

    def handle_reg_0x05(self, databyte):
        """Process month (1-12)."""
        # Registers row
        self.put_data(7, 0, [AnnRegs.MONTH,
                             [self.annotations[AnnRegs.MONTH][1],
                              "Months", "Month", "Mon", "M"]])
        # Bits row
        for i in range(7, 4, -1):
            self.put_reserved(i)
        self.month = bcd2int(databyte & 0x1f)
        annots = [self.annotations[AnnBitsTime.MONTH][1], "Month", "Mon",
                  "M", "M"]
        for i in range(0, len(annots) - 1):
            annots[i] += ": {}".format(self.month)
        self.put_data(4, 0, [AnnBitsTime.MONTH, annots])

    def handle_reg_0x06(self, databyte):
        """Process year (0-99).

        - Add 2000 to double digit year number (expect 21st century)
          to instance variable for formatting.
        """
        # Registers row
        self.put_data(7, 0, [AnnRegs.YEAR,
                             [self.annotations[AnnRegs.YEAR][1],
                              "Years", "Year", "Yr", "Y"]])
        # Bits row
        self.year = bcd2int(databyte & 0xff)
        annots = [self.annotations[AnnBitsTime.YEAR][1], "Year", "Yr",
                  "Y", "Y"]
        for i in range(0, len(annots) - 1):
            annots[i] += ": {}".format(self.year)
        self.put_data(7, 0, [AnnBitsTime.YEAR, annots])
        self.year += 2000

    def handle_reg_0x07(self, databyte):
        """Control Register."""
        # Registers row
        self.put_data(7, 0, [AnnRegs.CONTROL,
                             [self.annotations[AnnRegs.CONTROL][1],
                              "Control", "Ctrl", "C"]])
        # Bits row
        for i in (6, 5, 3, 2):
            self.put_reserved(i)
        # Bits row - OUT bit
        out = 1 if (databyte & (1 << bits["OUT"])) else 0
        annots = [self.annotations[AnnBitsCtlr.OUT][1], "OUT", "O", "O"]
        for i in range(0, len(annots) - 1):
            annots[i] += ": {}".format(out)
        self.put_data(bits["OUT"], bits["OUT"], [AnnBitsCtlr.OUT, annots])
        # Bits row - SQWE bit
        sqwe = 1 if (databyte & (1 << bits["SQWE"])) else 0
        sqwe_txt = ("en" if (sqwe) else "dis") + "abled"
        annots = [self.annotations[AnnBitsCtlr.SQWE][1], "SQWE"]
        for i in range(0, len(annots)):
            annots[i] += ": {}".format(sqwe_txt)
        annots_alt = ["SQWE", "SW", "S", "S"]
        for i in range(0, len(annots_alt) - 1):
            annots_alt[i] += ": {}".format(sqwe)
        annots.extend(annots_alt)
        self.put_data(bits["SQWE"], bits["SQWE"], [AnnBitsCtlr.SQWE, annots])
        # Bits row - RS bits
        rate = rates[databyte & 0x03]
        annots = [self.annotations[AnnBitsCtlr.RATE][1],
                  "Square wave rate", "SQW rate"]
        for i in range(0, len(annots)):
            annots[i] += ": {} Hz".format(rate)
        annots_alt = [self.annotations[AnnBitsCtlr.RATE][1],
                      "Square wave rate", "SQW rate", "Rate", "RS"]
        rate //= 1000
        for i in range(0, len(annots_alt)):
            annots_alt[i] += ": {} kHz".format(rate)
        annots.extend(annots_alt)
        annots_alt = ["SQW rate", "Rate", "RS", "RS", "R"]
        for i in range(0, len(annots_alt) - 2):
            annots_alt[i] += ": {}".format(rate)
        annots.extend(annots_alt)
        self.put_data(bits["RS1"], bits["RS0"], [AnnBitsCtlr.RATE, annots])

    def handle_reg_0x3f(self, databyte):
        """Process NVRAM."""
        # Registers row
        self.put_data(7, 0, [AnnRegs.NVRAM,
                             [self.annotations[AnnRegs.NVRAM][1],
                              "NVRAM", "RAM", "R"]])
        # Bits row
        annots = [self.annotations[AnnBitsTime.NVRAM][1], "NVRAM", "RAM",
                  "R", "R"]
        for i in range(0, len(annots) - 1):
            annots[i] += ": {:#04x}".format(databyte)
        self.put_data(7, 0, [AnnBitsTime.NVRAM, annots])

    def decode(self, startsample, endsample, data):
        """Decode samples in infinite wait loop."""
        cmd, databyte = data
        self.ss, self.es = startsample, endsample

        if cmd == "BITS":
            """Collect packet of bits that belongs to the following command.
            - Packet is in the form of list of bit lists:
                ["BITS", [[bit, startsample, endsample], ...]
            - Samples are counted for aquisition sampling frequency.
            - Parent decoder ``i2c``stores individual bits in the list from
              the least significant bit (LSB) to the most significant bit
              (MSB) as it is at representing numbers in computers, although I2C
              bus transmits data in oposite order with MSB first.
            """
            self.bits = databyte
            return

        # State machine
        if self.state == "IDLE":
            """Wait for an I2C START condition.
            - By start condition a new transmission begins.
            """
            if cmd != "START":
                return
            self.state = "ADDRESS SLAVE"
            self.ssb = self.ss

        elif self.state == "ADDRESS SLAVE":
            """Wait for a slave address write operation.
            - Every transmission starts with writing a register pointer
              to the chip, so that the slave address should be always
              followed by the write bit.
            """
            if cmd != "ADDRESS WRITE":
                return
            if not self.check_chip(databyte):
                self.state = "IDLE"  # Start waiting for expected transmission
                return
            self.state = "ADDRESS REGISTER"

        elif self.state == "ADDRESS REGISTER":
            """Wait for a data write.
            - Master selects the slave register.
            """
            if cmd != "DATA WRITE":
                return
            self.reg = databyte
            self.state = "REGISTER WRITE"

        elif self.state == "REGISTER WRITE":
            """Analyze situation after selecting slave register.
            - Repeated Start condition signals, that reading sequence follows.
            - Subsequent writes signals writing to the slave.
            - Otherwise Stop condition is expected.
            """
            if cmd == "START REPEAT":
                self.state = "REGISTER READ"
                return
            elif cmd == "DATA WRITE":
                """Contiuous writing to subsequent registers."""
                self.handle_reg(databyte)
            elif cmd == "STOP":
                """Output formatted string with written data.
                - This is and of a I2C transmission. Start waiting for another
                  one.
                """
                self.output_datetime(AnnStrings.DTWRITE, "Written")
                self.state = "IDLE"  # Start waiting for another transmission

        elif self.state == "REGISTER READ":
            """Wait for a slave address read operation.
            - This is start of reading sequence with preceeding slave address.
            """
            if cmd != "ADDRESS READ":
                return
            if not self.check_chip(databyte):
                self.state = "IDLE"  # Start waiting for expected transmission
                return
            self.state = "SUBSEQUENT READ"
        elif self.state == "SUBSEQUENT READ":
            if cmd == "DATA READ":
                self.handle_reg(databyte)
            elif cmd == "STOP":
                self.output_datetime(AnnStrings.DTREAD, "Read")
                self.state = "IDLE"  # Start waiting for another transmission
