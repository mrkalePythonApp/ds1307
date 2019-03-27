# -*- coding: utf-8 -*-
"""This file is part of the libsigrokdecode project.

Copyright (C) 2018-2019 Libor Gabaj <libor.gabaj@gmail.com>

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
import common.srdhelper as hlp


###############################################################################
# Enumeration classes for device parameters
###############################################################################
class Address:
    """Enumeration of possible slave addresses."""

    (SLAVE,) = (0x68,)


class Register:
    """Enumeration of possible slave register addresses."""

    (
        SECOND, MINUTE, HOUR, WEEKDAY, DAY, MONTH, YEAR,
        CONTROL, NVRAM
    ) = range(9)


class ControlBits:
    """Enumeration of bits in the control register."""

    (RS0, RS1, SQWE, OUT) = (0, 1, 4, 7)


class TimeBits:
    """Enumeration of bits in the time keeping registers."""

    (AMPM, MODE, CH) = (5, 6, 7)


class NvRAM:
    """Internal non-volatile memory address range of DS1307.

    - Minimal and maximal position.
    """

    (MIN, MAX) = (0x08, 0x3f)


class Params:
    """Specific parameters."""

    (UNIT_HZ, UNIT_KHZ) = ("Hz", "kHz")


###############################################################################
# Enumeration classes for annotations
###############################################################################
class AnnAddrs:
    """Enumeration of annotations for addresses."""

    (SLAVE,) = (0,)


class AnnRegs:
    """Enumeration of annotations for registers."""

    (
        POINTER,
        SECOND, MINUTE, HOUR, WEEKDAY, DAY, MONTH, YEAR,
        CONTROL, NVRAM
    ) = range(AnnAddrs.SLAVE + 1, (AnnAddrs.SLAVE + 1) + 10)


class AnnBits:
    """Enumeration of annotations for configuration bits."""

    (
        RESERVED, DATA,         # General bits
        RS0, RS1, SQWE, OUT,    # From control register
        AMPM, MODE, CH,         # From time keeping registers
        SECOND, MINUTE, HOUR,
        WEEKDAY, DAY, MONTH, YEAR,
        NVRAM,
    ) = range(AnnRegs.NVRAM + 1, (AnnRegs.NVRAM + 1) + 17)


class AnnInfo:
    """Enumeration of annotations for formatted info."""

    (
        WARN, BADADD, CHECK, WRITE, READ,
        DATETIME, NVRAM,
    ) = range(AnnBits.NVRAM + 1, (AnnBits.NVRAM + 1) + 7)


###############################################################################
# Parameters mapping
###############################################################################
weekdays = (
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
    "Saturday", "Sunday"
)

months = (
    "Unknown",
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
)

rates = {
    0b00: 1,
    0b01: 4096,
    0b10: 8192,
    0b11: 32768,
}


###############################################################################
# Parameters anotations definitions
###############################################################################
addresses = {
    AnnAddrs.SLAVE: ["Device address", "Address", "Add", "A"],
}

registers = {
    AnnRegs.POINTER: ["Register pointer", "Pointer", "Ptr", "P"],
    AnnRegs.SECOND: ["Seconds register", "Seconds", "Secs", "S"],
    AnnRegs.MINUTE: ["Minutes register", "Minutes", "Mins", "M"],
    AnnRegs.HOUR: ["Hours register", "Hours", "Hrs", "H"],
    AnnRegs.WEEKDAY: ["Weekdays register", "Weekdays", "W"],
    AnnRegs.DAY: ["Days register", "Days", "D"],
    AnnRegs.MONTH: ["Months register", "Months", "Mons", "M"],
    AnnRegs.YEAR: ["Years register", "Years", "Yrs", "Y"],
    AnnRegs.CONTROL: ["Control register", "Control", "Ctrl", "C"],
    AnnRegs.NVRAM: ["Non-volatile memory register", "NV-RAM", "NVR", "R"],
}

bits = {
    AnnBits.RESERVED: ["Reserved", "Rsvd", "R"],
    AnnBits.DATA: ["Data", "D"],
    AnnBits.RS0: ["Rate select", "Rate", "RS"],
    AnnBits.SQWE: ["SQW enable", "SQWE", "SE", "S"],
    AnnBits.OUT: ["OUT", "O"],
    AnnBits.AMPM: ["AM/PM", "A/P", "A"],
    AnnBits.MODE: ["12/24 mode", "Mode", "M"],
    AnnBits.CH: ["Clock halt", "CH", "H"],
    AnnBits.SECOND: ["Second", "Sec", "S"],
    AnnBits.MINUTE: ["Minute", "Min", "M"],
    AnnBits.HOUR: ["Hour", "Hr", "H"],
    AnnBits.WEEKDAY: ["Weekday", "WD", "W"],
    AnnBits.DAY: ["Day", "D"],
    AnnBits.MONTH: ["Month", "Mon", "M"],
    AnnBits.YEAR: ["Year", "Yr", "Y"],
    AnnBits.NVRAM: ["NVRAM", "RAM", "R"],
}

info = {
    AnnInfo.WARN: ["Warnings", "Warn", "W"],
    AnnInfo.BADADD: ["Uknown slave address", "Unknown address", "Uknown",
                     "Unk", "U"],
    AnnInfo.CHECK: ["Slave presence check", "Slave check", "Check",
                    "Chk", "C"],
    AnnInfo.WRITE: ["Write", "Wr", "W"],
    AnnInfo.READ: ["Read", "Rd", "R"],
    AnnInfo.DATETIME: ["Datetime", "Date", "D"],
    AnnInfo.NVRAM: ["Memory", "Mem", "M"],
}


###############################################################################
# Decoder
###############################################################################
class Decoder(srd.Decoder):
    """Protocol decoder for real time clock chip ``DS1307``."""

    api_version = 3
    id = "ds1307"
    name = "DS1307"
    longname = "Dallas DS1307 RTC chip"
    desc = "Real time clock chip protocol decoder, v 1.0.0."
    license = "gplv2+"
    inputs = ["i2c"]
    outputs = ["ds1307"]

    options = (
        {"id": "radix", "desc": "Number format", "default": "Hex",
         "values": ("Hex", "Dec", "Oct", "Bin")},
        {"id": "start_weekday", "desc": "The first day of the week",
            "default": "Monday", "values": weekdays},
        {"id": "date_format", "desc": "Date format",
            "default": "European", "values": ("European", "American", "ANSI")}
    )

    annotations = hlp.create_annots(
        {
            "addr": addresses,
            "reg": registers,
            "bit": bits,
            "info": info,
        }
    )
    annotation_rows = (
        ("bits", "Bits", tuple(range(AnnBits.RESERVED, AnnBits.NVRAM + 1))),
        ("regs", "Registers", tuple(range(AnnAddrs.SLAVE, AnnRegs.NVRAM + 1))),
        ("datetime", "Datetime", (AnnInfo.DATETIME, AnnInfo.NVRAM)),
        ("warnings", "Warnings", (AnnInfo.WARN, AnnInfo.BADADD)),
    )

    def __init__(self):
        """Initialize decoder."""
        self.reset()

    def reset(self):
        """Reset decoder and initialize instance variables."""
        # Common parameters for I2C sampling
        self.ss = 0         # Start sample
        self.es = 0         # End sample
        self.ssb = 0        # Start sample of an annotation transmission block
        self.write = True   # Flag about recent write action (default write)
        self.state = "IDLE"
        # Specific parameters for a device
        self.addr = Address.SLAVE
        self.reg = -1
        self.second = -1
        self.minute = -1
        self.hour = -1
        self.weekday = -1
        self.day = -1
        self.month = -1
        self.year = -1
        self.clear_data()

    def clear_data(self):
        """Clear data cache."""
        self.ssd = 0
        self.bits = []
        self.bytes = []

    def start(self):
        """Actions before the beginning of the decoding."""
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def putd(self, sb, eb, data):
        """Span data output across bit range.

        - Because bits are order with MSB first, the output is an annotation
          block from the last sample of the start bit (sb) to the first sample
          of the end bit (eb).
        - The higher bit the lower sample number.
        """
        self.put(self.bits[eb][1], self.bits[sb][2], self.out_ann, data)
        # self.put(self.bits[ss][1], self.bits[es][2], self.out_ann, data)

    def putb(self, sb, eb=None, ann=AnnBits.RESERVED):
        """Span special bit annotation across bit range bit by bit.

        Arguments
        ---------
        sb : integer
            Number of the annotated start bit counting from 0.
        eb : integer
            Number of the end bit right after the last annotated bit
            counting from 0. If none value is provided, the method uses
            start value increased by 1, so that just the first bit will be
            annotated.
        ann : integer
            Index of the special bit's annotation in the annotations list
            `bits`. Default value is for reserved bit.

        """
        annots = hlp.compose_annot(bits[ann])
        for bit in range(sb, eb or (sb + 1)):
            self.put(self.bits[bit][1], self.bits[bit][2],
                     self.out_ann, [ann, annots])

    def check_addr(self, addr_slave):
        """Check correct slave address."""
        if addr_slave == Address.SLAVE:
            return True
        ann = AnnInfo.BADADD
        val = hlp.format_data(self.addr, self.options["radix"])
        annots = hlp.compose_annot(info[ann], ann_value=val)
        self.put(self.ss, self.es, self.out_ann, [ann, annots])
        return False

    def collect_data(self, databyte):
        """Collect data byte to a data cache."""
        if self.bytes:
            self.bytes.insert(0, databyte)
        else:
            self.ssd = self.ss
            self.bytes.append(databyte)

    def format_rw(self):
        """Format read/write action."""
        act = (AnnInfo.READ, AnnInfo.WRITE)[self.write]
        return info[act]

    def output_datetime(self):
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
        # Info row
        ann = AnnInfo.DATETIME
        val = dt_str
        act = self.format_rw()
        annots = hlp.compose_annot(info[ann], ann_value=val, ann_action=act)
        self.put(self.ssb, self.es, self.out_ann, [ann, annots])

    def handle_address(self):
        """Process slave address."""
        if not self.bytes:
            return
        # Registers row
        ann = AnnAddrs.SLAVE
        annots = hlp.compose_annot(addresses[ann])
        self.put(self.ssd, self.es, self.out_ann, [ann, annots])
        self.clear_data()

    def handle_pointer(self):
        """Process register pointer."""
        # Registers row
        ann = AnnRegs.POINTER
        val = hlp.format_data(self.reg, self.options["radix"])
        act = self.format_rw()
        annots = hlp.compose_annot(registers[ann], ann_value=val,
                                   ann_action=act)
        self.put(self.ssd, self.es, self.out_ann, [ann, annots])
        self.clear_data()

    def handle_nodata(self):
        """Process transmission without any data."""
        # Info row
        ann = AnnInfo.CHECK
        annots = hlp.compose_annot(info[ann])
        self.put(self.ssb, self.es, self.out_ann, [ann, annots])

    def handle_reg(self):
        """Create name and call corresponding slave registers handler.

        - Honor auto increment of the register at reading.
        - When the address reaches maximal nvram position, it will wrap around
          to address 0.
        """
        reg = self.reg if self.reg < NvRAM.MIN else NvRAM.MAX
        fn = getattr(self, "handle_reg_{:#04x}".format(reg))
        fn(self.bytes[0])
        self.reg += 1   # Address auto increment
        if self.reg > NvRAM.MAX:    # Address rollover
            self.reg = 0
        self.clear_data()

    def handle_reg_0x00(self, databyte):
        """Process seconds (0-59) and Clock halt bit."""
        # Bits row - Clock Halt bit
        ch = databyte >> TimeBits.CH & 1
        ch_l = ("Run", "Halt")[ch]
        ch_s = ch_l[0].upper()
        ann = AnnBits.CH
        val = [ch, ch_l, ch_s]
        annots = hlp.compose_annot(bits[ann], ann_value=val)
        self.putd(TimeBits.CH, TimeBits.CH, [ann, annots])
        # Bits row - Second bits
        self.second = hlp.bcd2int(databyte & ~(1 << TimeBits.CH))
        ann = AnnBits.SECOND
        val = self.second
        annots = hlp.compose_annot(bits[ann], ann_value=val)
        self.putd(0, TimeBits.CH - 1, [ann, annots])
        # Registers row
        ann = AnnRegs.SECOND
        act = self.format_rw()
        annots = hlp.compose_annot(registers[ann], ann_action=act)
        self.put(self.ssd, self.es, self.out_ann, [ann, annots])

    def handle_reg_0x01(self, databyte):
        """Process minutes (0-59)."""
        # Bits row
        self.putb(7)
        self.minute = hlp.bcd2int(databyte & 0x7f)
        ann = AnnBits.MINUTE
        val = self.minute
        annots = hlp.compose_annot(bits[ann], ann_value=val)
        self.putd(0, 6, [ann, annots])
        # Registers row
        ann = AnnRegs.MINUTE
        act = self.format_rw()
        annots = hlp.compose_annot(registers[ann], ann_action=act)
        self.put(self.ssd, self.es, self.out_ann, [ann, annots])

    def handle_reg_0x02(self, databyte):
        """Process hours (1-12+AM/PM or 0-23) and 12/24 hours mode.

        - In case of 12 hours mode convert hours to 24 hours mode to instance
          variable for formatting.
        """
        # Bits row
        self.putb(7)
        mode12h = databyte >> TimeBits.MODE & 1
        if mode12h:
            # Bits row - 12h mode
            ann = AnnBits.MODE
            val = "12h"
            annots = hlp.compose_annot(bits[ann], ann_value=val)
            self.putd(TimeBits.MODE, TimeBits.MODE, [ann, annots])
            # Bits row - AM/PM mode
            pm = databyte >> TimeBits.AMPM & 1
            pm_l = ("AM", "PM")[pm]
            pm_s = pm_l[0].upper()
            ann = AnnBits.AMPM
            val = [pm, pm_l, pm_s]
            annots = hlp.compose_annot(bits[ann], ann_value=val)
            self.putd(TimeBits.AMPM, TimeBits.AMPM, [ann, annots])
            # Bits row - hours
            self.hour = hlp.bcd2int(databyte & 0x1f)
            # Convert to 24h expression
            self.hour %= 12
            if pm:
                self.hour += 12
            ann = AnnBits.HOUR
            val = self.hour
            annots = hlp.compose_annot(bits[ann], ann_value=val)
            self.putd(0, TimeBits.AMPM - 1, [ann, annots])
        else:
            # Bits row - 24h mode
            ann = AnnBits.MODE
            val = "24h"
            annots = hlp.compose_annot(bits[ann], ann_value=val)
            self.putd(TimeBits.MODE, TimeBits.MODE, [ann, annots])
            # Bits row - hours
            self.hour = hlp.bcd2int(databyte & 0x3f)
            ann = AnnBits.HOUR
            val = self.hour
            annots = hlp.compose_annot(bits[ann], ann_value=val)
            self.putd(0, TimeBits.MODE - 1, [ann, annots])
        # Registers row
        ann = AnnRegs.HOUR
        act = self.format_rw()
        annots = hlp.compose_annot(registers[ann], ann_action=act)
        self.put(self.ssd, self.es, self.out_ann, [ann, annots])

    def handle_reg_0x03(self, databyte):
        """Process weekday (1-7).

        - Recalculate weekday in respect to starting weekday option to instance
          variable for formatting.
        """
        # Bits row - reserved
        self.putb(3, 8)
        # Bits row - calculate weekday
        self.weekday = hlp.bcd2int(databyte & 0x07)
        start_weekday_index = 0
        for i, weekday in enumerate(weekdays):
            if weekday == self.options["start_weekday"]:
                start_weekday_index = i
                break
        start_weekday_index += self.weekday - 1
        start_weekday_index %= 7
        self.weekday = start_weekday_index
        weekday = weekdays[self.weekday]
        # Bits row - weekday
        ann = AnnBits.WEEKDAY
        val = weekday
        annots = hlp.compose_annot(bits[ann], ann_value=val)
        self.putd(0, 2, [ann, annots])
        # Registers row
        ann = AnnRegs.WEEKDAY
        act = self.format_rw()
        annots = hlp.compose_annot(registers[ann], ann_action=act)
        self.put(self.ssd, self.es, self.out_ann, [ann, annots])

    def handle_reg_0x04(self, databyte):
        """Process day (1-31)."""
        # Bits row
        self.putb(6, 8)
        self.day = hlp.bcd2int(databyte & 0x3f)
        ann = AnnBits.DAY
        val = self.day
        annots = hlp.compose_annot(bits[ann], ann_value=val)
        self.putd(0, 5, [ann, annots])
        # Registers row
        ann = AnnRegs.DAY
        act = self.format_rw()
        annots = hlp.compose_annot(registers[ann], ann_action=act)
        self.put(self.ssd, self.es, self.out_ann, [ann, annots])

    def handle_reg_0x05(self, databyte):
        """Process month (1-12)."""
        # Bits row
        self.putb(5, 8)
        self.month = hlp.bcd2int(databyte & 0x1f)
        ann = AnnBits.MONTH
        val = months[self.month]
        annots = hlp.compose_annot(bits[ann], ann_value=val)
        self.putd(0, 4, [ann, annots])
        # Registers row
        ann = AnnRegs.MONTH
        act = self.format_rw()
        annots = hlp.compose_annot(registers[ann], ann_action=act)
        self.put(self.ssd, self.es, self.out_ann, [ann, annots])

    def handle_reg_0x06(self, databyte):
        """Process year (0-99).

        - Add 2000 to double digit year number (expect 21st century)
          to instance variable for formatting.
        """
        # Bits row
        self.year = hlp.bcd2int(databyte & 0xff) + 2000
        ann = AnnBits.YEAR
        val = self.year
        annots = hlp.compose_annot(bits[ann], ann_value=val)
        self.putd(0, 7, [ann, annots])
        # Registers row
        ann = AnnRegs.YEAR
        act = self.format_rw()
        annots = hlp.compose_annot(registers[ann], ann_action=act)
        self.put(self.ssd, self.es, self.out_ann, [ann, annots])

    def handle_reg_0x07(self, databyte):
        """Process control register."""
        # Bits row - Reserved bits
        self.putb(2, 4)
        self.putb(5, 7)
        # Bits row - OUT bit
        out = databyte >> ControlBits.OUT & 1
        ann = AnnBits.OUT
        annots = hlp.compose_annot(bits[ann], ann_value=out)
        self.putd(ControlBits.OUT, ControlBits.OUT, [ann, annots])
        # Bits row - SQWE bit
        sqwe = databyte >> ControlBits.SQWE & 1
        sqwe_l = ("dis", "en")[sqwe] + "abled"
        sqwe_s = sqwe_l[0].upper()
        ann = AnnBits.SQWE
        val = [sqwe, sqwe_l, sqwe_s]
        annots = hlp.compose_annot(bits[ann], ann_value=val)
        self.putd(ControlBits.SQWE, ControlBits.SQWE, [ann, annots])
        # Bits row - RS bits
        rate = rates[databyte & 0x03]
        ann = AnnBits.RS0
        val = rate
        unit = Params.UNIT_HZ
        annots = hlp.compose_annot(bits[ann], ann_value=val, ann_unit=unit)
        val //= 1000
        unit = Params.UNIT_KHZ
        annots_add = hlp.compose_annot(bits[ann], ann_value=val, ann_unit=unit)
        annots.extend(annots_add)
        self.putd(ControlBits.RS0, ControlBits.RS1, [ann, annots])
        # Registers row
        ann = AnnRegs.CONTROL
        act = self.format_rw()
        annots = hlp.compose_annot(registers[ann], ann_action=act)
        self.put(self.ssd, self.es, self.out_ann, [ann, annots])

    def handle_reg_0x3f(self, databyte):
        """Process NVRAM."""
        # Bits row
        ann = AnnBits.NVRAM
        val = hlp.format_data(databyte, self.options["radix"])
        annots = hlp.compose_annot(bits[ann], ann_value=val)
        self.putd(0, 7, [ann, annots])
        # Registers row
        ann = AnnRegs.NVRAM
        act = self.format_rw()
        annots = hlp.compose_annot(registers[ann], ann_action=act)
        self.put(self.ssd, self.es, self.out_ann, [ann, annots])

    def decode(self, ss, es, data):
        """Decode samples provided by parent decoder."""
        cmd, databyte = data
        self.ss, self.es = ss, es

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
            self.bits = databyte + self.bits
            return

        # State machine
        if self.state == "IDLE":
            """Wait for an I2C transmission."""
            if cmd != "START":
                return
            self.ssb = self.ss
            self.state = "ADDRESS SLAVE"

        elif self.state == "ADDRESS SLAVE":
            """Wait for a slave address."""
            if cmd in ["ADDRESS WRITE", "ADDRESS READ"]:
                if self.check_addr(databyte):
                    self.collect_data(databyte)
                    self.handle_address()
                    if cmd == "ADDRESS READ":
                        self.write = False
                        self.state = "REGISTER DATA"
                    elif cmd == "ADDRESS WRITE":
                        self.write = True
                        self.state = "REGISTER ADDRESS"
                else:
                    self.state = "IDLE"

        elif self.state == "REGISTER ADDRESS":
            """Initial slave register"""
            if cmd == "DATA WRITE":
                self.reg = databyte
                self.collect_data(databyte)
                self.handle_pointer()
                self.state = "REGISTER DATA"
            elif cmd == "STOP":
                """Output end of transmission without any register and data."""
                self.handle_nodata()
                self.state = "IDLE"

        elif self.state == "REGISTER DATA":
            """Process slave register"""
            if cmd in ["DATA WRITE", "DATA READ"]:
                self.collect_data(databyte)
                self.handle_reg()
                self.state = "REGISTER DATA"
            elif cmd == "START REPEAT":
                self.state = "ADDRESS SLAVE"
            elif cmd == "STOP":
                """Wait for next transmission."""
                self.output_datetime()
                self.state = "IDLE"
