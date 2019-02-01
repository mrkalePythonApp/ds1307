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
from common.srdhelper import bcd2int


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
    ) = range(0, 9)


class CommonBits:
    """Enumeration of common bits."""

    (RESERVED,) = (0xff,)


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


###############################################################################
# Enumeration classes for annotations
###############################################################################
class AnnAddrs:
    """Enumeration of annotations for addresses."""

    (SLAVE,) = (0,)


class AnnRegs:
    """Enumeration of annotations for registers."""

    (
        SECOND, MINUTE, HOUR, WEEKDAY, DAY, MONTH, YEAR,
        CONTROL, NVRAM
    ) = range(AnnAddrs.SLAVE + 1, (AnnAddrs.SLAVE + 1) + 9)


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
        DATETIME, NVRAM,    # Datetime formatting
    ) = range(AnnBits.NVRAM + 1, (AnnBits.NVRAM + 1) + 7)


###############################################################################
# Parameters mapping
###############################################################################
radixes = {  # Convert radix option to format mask
    "Hex": "{:#02x}",
    "Dec": "{:#d}",
    "Oct": "{:#o}",
}

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

params = {
    "UNIT_HZ": "Hz",
    "UNIT_KHZ": "kHz",
}


###############################################################################
# Parameters anotations definitions
###############################################################################
"""
- If a parameter has a value, the last item of an annotation list is used
  repeatedly without a value.
- If a parameter has measurement unit alongside with value, the last two items
  are used repeatedly without that measurement unit.
"""
addresses = {
    AnnAddrs.SLAVE: ["Device address", "Address", "Add", "A"],
}

registers = {
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
    AnnBits.RESERVED: ["Reserved bit", "Reserved", "Rsvd", "R"],
    AnnBits.DATA: ["Data bit", "Data", "D"],
    AnnBits.RS0: ["Rate select bits", "Rate select", "Rate", "RS"],
    AnnBits.SQWE: ["SQW enable bit", "SQW enable", "SQWE", "SE", "S"],
    AnnBits.OUT: ["OUT bit", "OUT", "O"],
    AnnBits.AMPM: ["AM/PM bit", "AM/PM", "A/P", "A"],
    AnnBits.MODE: ["12/24 hours mode bit", "12/24 mode", "Mode", "M"],
    AnnBits.CH: ["Clock halt bit", "Clock halt", "CH", "H"],
    AnnBits.SECOND: ["Second bits", "Second", "Sec", "S"],
    AnnBits.MINUTE: ["Minute bits", "Minute", "Min", "M"],
    AnnBits.HOUR: ["Hour bits", "Hour", "Hr", "H"],
    AnnBits.WEEKDAY: ["Weekday bits", "Weekday", "WD", "W"],
    AnnBits.DAY: ["Day bits", "Day", "D"],
    AnnBits.MONTH: ["Month bits", "Month", "Mon", "M"],
    AnnBits.YEAR: ["Year bits", "Year", "Yr", "Y"],
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


def create_annots():
    """Create a tuple with all annotation definitions."""
    annots = []
    # Addresses
    for attr, value in vars(AnnAddrs).items():
        if not attr.startswith('__') and value in addresses:
            annots.append(tuple(["addr-" + attr.lower(), addresses[value][0]]))
    # Registers
    for attr, value in vars(AnnRegs).items():
        if not attr.startswith('__') and value in registers:
            annots.append(tuple(["reg-" + attr.lower(), registers[value][0]]))
    # Bits
    for attr, value in vars(AnnBits).items():
        if not attr.startswith('__') and value in bits:
            annots.append(tuple(["bit-" + attr.lower(), bits[value][0]]))
    # Info
    for attr, value in vars(AnnInfo).items():
        if not attr.startswith('__') and value in info:
            annots.append(tuple(["info-" + attr.lower(), info[value][0]]))
    return tuple(annots)


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
         "values": ("Hex", "Dec", "Oct")},
        {"id": "start_weekday", "desc": "The first day of the week",
            "default": "Monday", "values": weekdays},
        {"id": "date_format", "desc": "Date format",
            "default": "European", "values": ("European", "American", "ANSI")}
    )

    annotations = create_annots()
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
        self.ssd = 0        # Start sample of an annotation data block
        self.esd = 0        # End sample of an annotation data block
        self.bits = []      # List of recent processed byte bits
        self.bytes = []     # List of recent processed bytes
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

    def start(self):
        """Actions before the beginning of the decoding."""
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def compose_annot(self, ann_label, ann_value=None, ann_unit=None,
                      ann_action=None):
        """Compose list of annotations enriched with value and unit.

        Arguments
        ---------
        ann_label : list
            List of annotation label for enriching with values and units and
            prefixed with actions.
            *The argument is mandatory and has no default value.*
        ann_value : list
            List of values to be added item by item to all annotations.
        ann_unit : list
            List of measurement units to be added item by item to all
            annotations. The method does not add separation space between
            the value and the unit.
        ann_action : list
            List of action prefixes prepend item by item to all annotations.
            The method separates action and annotation with a space.

        Returns
        -------
        list of str
            List of a annotations potentially enriched with values and units
            with items sorted by length descending.

        Notes
        -----
        - Usually just one value and one unit is used. However for flexibility
          more of them can be used.
        - If the annotation values list is not defined, the annotation units
          list is not used, even if it is defined.

        """
        if not isinstance(ann_label, list):
            tmp = ann_label
            ann_label = []
            ann_label.append(tmp)

        if ann_value is None:
            ann_value = []
        elif not isinstance(ann_value, list):
            tmp = ann_value
            ann_value = []
            ann_value.append(tmp)

        if ann_unit is None:
            ann_unit = []
        elif not isinstance(ann_unit, list):
            tmp = ann_unit
            ann_unit = []
            ann_unit.append(tmp)

        if ann_action is None:
            ann_action = []
        elif not isinstance(ann_action, list):
            tmp = ann_action
            ann_action = []
            ann_action.append(tmp)
        if len(ann_action) == 0:
            ann_action = [""]

        # Compose annotation
        annots = []
        for act in ann_action:
            for lbl in ann_label:
                ann = "{} {}".format(act, lbl).strip()
                ann_item = None
                for val in ann_value:
                    ann_item = "{}: {}".format(ann, val)
                    annots.append(ann_item)  # Without units
                    for unit in ann_unit:
                        ann_item += "{}".format(unit)
                        annots.append(ann_item)  # With units
                if ann_item is None:
                    annots.append(ann)

        # Add last 2 annotation items without values
        if len(ann_value) > 0:
            for ann in ann_label[-2:]:
                annots.append(ann)
        annots.sort(key=len, reverse=True)
        return annots

    def put_data(self, bit_start, bit_stop, data):
        """Span data output across bit range.

        - Output is an annotation block from the start sample of the first bit
          to the end sample of the last bit.
        """
        self.put(self.bits[bit_start][1], self.bits[bit_stop][2],
                 self.out_ann, data)

    def put_bit_data(self, bit_reserved):
        """Span output under general data bit.

        - Output is an annotation block from the start to the end sample
          of a data bit.
        """
        annots = self.compose_annot(bits[AnnBits.DATA])
        self.put(self.bits[bit_reserved][1], self.bits[bit_reserved][2],
                 self.out_ann, [AnnBits.DATA, annots])

    def put_bit_reserve(self, bit_reserved):
        """Span output under reserved bit.

        - Output is an annotation block from the start to the end sample
          of a reserved bit.
        """
        annots = self.compose_annot(bits[AnnBits.RESERVED])
        self.put(self.bits[bit_reserved][1], self.bits[bit_reserved][2],
                 self.out_ann, [AnnBits.RESERVED, annots])

    def check_addr(self, addr_slave):
        """Check correct slave address."""
        if addr_slave == Address.SLAVE:
            return True
        annots = self.compose_annot(AnnInfo.BADADD,
                                    ann_value=self.format_data(self.addr))
        self.put(self.ssb, self.es, self.out_ann, [AnnInfo.BADADD, annots])
        return False

    def collect_data(self, databyte):
        """Collect data byte to a data cache."""
        self.esd = self.es
        if len(self.bytes) == 0:
            self.ssd = self.ss
            self.bytes.append(databyte)
        else:
            self.bytes.insert(0, databyte)

    def clear_data(self):
        """Clear data cache."""
        self.ssd = self.esd = 0
        self.bytes = []
        self.bits = []

    def format_data(self, data):
        """Format data value according to the radix option."""
        return radixes[self.options["radix"]].format(data)

    def format_action(self):
        """Format r/w action ."""
        act_idx = AnnInfo.WRITE if (self.write) else AnnInfo.READ
        return info[act_idx]

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
        annots = self.compose_annot(info[AnnInfo.DATETIME],
                                    ann_value=dt_str,
                                    ann_action=self.format_action())
        self.put(self.ssb, self.es, self.out_ann, [AnnInfo.DATETIME, annots])

    def handle_addr(self):
        """Process slave address."""
        if len(self.bytes) == 0:
            return
        # Registers row
        self.addr = self.bytes[0]
        annots = self.compose_annot(addresses[AnnAddrs.SLAVE])
        self.put(self.ssd, self.esd, self.out_ann, [AnnAddrs.SLAVE, annots])
        self.clear_data()

    def handle_nodata(self):
        """Process transmission without any data."""
        # Info row
        annots = self.compose_annot(info[AnnInfo.CHECK])
        self.put(self.ssb, self.es, self.out_ann, [AnnInfo.CHECK, annots])

    def handle_reg(self):
        """Create name and call corresponding slave registers handler.

        - Honor auto increment of the register at reading.
        - When the address reaches maximal nvram position, it will wrap around
          to address 0.
        """
        reg = self.reg if self.reg < NvRAM.MIN else NvRAM.MAX
        fn = getattr(self, "handle_reg_{:#04x}".format(reg))
        fn()
        self.reg += 1   # Address auto increment
        if self.reg > NvRAM.MAX:    # Address rollover
            self.reg = 0
        self.clear_data()

    def handle_reg_0x00(self):
        """Process seconds (0-59) and Clock halt bit."""
        # Bits row - Clock Halt bit
        ch = 1 if (self.bytes[0] & (1 << TimeBits.CH)) else 0
        ch_l = "Halt" if (ch) else "Run"
        ch_s = ch_l[0].upper()
        annots = self.compose_annot(bits[AnnBits.CH],
                                    ann_value=[ch, ch_l, ch_s])
        self.put_data(TimeBits.CH, TimeBits.CH, [AnnBits.CH, annots])
        # Bits row - Second bits
        self.second = bcd2int(self.bytes[0] & ~(1 << TimeBits.CH))
        annots = self.compose_annot(bits[AnnBits.SECOND],
                                    ann_value=self.second)
        self.put_data(TimeBits.CH - 1, 0, [AnnBits.SECOND, annots])
        # Registers row
        annots = self.compose_annot(registers[AnnRegs.SECOND],
                                    ann_action=self.format_action())
        self.put(self.ssd, self.esd, self.out_ann, [AnnRegs.SECOND, annots])

    def handle_reg_0x01(self):
        """Process minutes (0-59)."""
        # Bits row
        self.put_bit_reserve(7)
        self.minute = bcd2int(self.bytes[0] & 0x7f)
        annots = self.compose_annot(bits[AnnBits.MINUTE],
                                    ann_value=self.minute)
        self.put_data(6, 0, [AnnBits.MINUTE, annots])
        # Registers row
        annots = self.compose_annot(registers[AnnRegs.MINUTE],
                                    ann_action=self.format_action())
        self.put(self.ssd, self.esd, self.out_ann, [AnnRegs.MINUTE, annots])

    def handle_reg_0x02(self):
        """Process hours (1-12+AM/PM or 0-23) and 12/24 hours mode.

        - In case of 12 hours mode convert hours to 24 hours mode to instance
          variable for formatting.
        """
        # Bits row
        self.put_bit_reserve(7)
        mode12h = True if (self.bytes[0] & (1 << TimeBits.MODE)) else False
        if mode12h:
            # Bits row - 12h mode
            annots = self.compose_annot(bits[AnnBits.MODE],
                                        ann_value="12h")
            self.put_data(TimeBits.MODE, TimeBits.MODE, [AnnBits.MODE, annots])
            # Bits row - AM/PM mode
            pm = 1 if (self.bytes[0] & (1 << TimeBits.AMPM)) else 0
            pm_l = "PM" if (pm) else "AM"
            pm_s = pm_l[0].upper()
            annots = self.compose_annot(bits[AnnBits.AMPM],
                                        ann_value=[pm, pm_l, pm_s])
            self.put_data(TimeBits.AMPM, TimeBits.AMPM, [AnnBits.AMPM, annots])
            # Bits row - hours
            self.hour = bcd2int(self.bytes[0] & 0x1f)
            # Convert to 24h expression
            self.hour %= 12
            if pm:
                self.hour += 12
            annots = self.compose_annot(bits[AnnBits.HOUR],
                                        ann_value=self.hour)
            self.put_data(TimeBits.AMPM - 1, 0, [AnnBits.MODE, annots])
        else:
            # Bits row - 24h mode
            annots = self.compose_annot(bits[AnnBits.MODE],
                                        ann_value="24h")
            self.put_data(TimeBits.MODE, TimeBits.MODE, [AnnBits.MODE, annots])
            # Bits row - hours
            self.hour = bcd2int(self.bytes[0] & 0x3f)
            annots = self.compose_annot(bits[AnnBits.HOUR],
                                        ann_value=self.hour)
            self.put_data(TimeBits.MODE - 1, 0, [AnnBits.MODE, annots])
        # Registers row
        annots = self.compose_annot(registers[AnnRegs.HOUR],
                                    ann_action=self.format_action())
        self.put(self.ssd, self.esd, self.out_ann, [AnnRegs.HOUR, annots])

    def handle_reg_0x03(self):
        """Process weekday (1-7).

        - Recalculate weekday in respect to starting weekday option to instance
          variable for formatting.
        """
        # Bits row - reserved
        for i in range(7, 2, -1):
            self.put_bit_reserve(i)
        # Bits row - calculate weekday
        self.weekday = bcd2int(self.bytes[0] & 0x07)
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
        annots = self.compose_annot(bits[AnnBits.WEEKDAY],
                                    ann_value=weekday)
        self.put_data(2, 0, [AnnBits.WEEKDAY, annots])
        # Registers row
        annots = self.compose_annot(registers[AnnRegs.WEEKDAY],
                                    ann_action=self.format_action())
        self.put(self.ssd, self.esd, self.out_ann, [AnnRegs.WEEKDAY, annots])

    def handle_reg_0x04(self):
        """Process day (1-31)."""
        # Bits row
        for i in (7, 6):
            self.put_bit_reserve(i)
        self.day = bcd2int(self.bytes[0] & 0x3f)
        annots = self.compose_annot(bits[AnnBits.DAY],
                                    ann_value=self.day)
        self.put_data(5, 0, [AnnBits.DAY, annots])
        # Registers row
        annots = self.compose_annot(registers[AnnRegs.DAY],
                                    ann_action=self.format_action())
        self.put(self.ssd, self.esd, self.out_ann, [AnnRegs.DAY, annots])

    def handle_reg_0x05(self):
        """Process month (1-12)."""
        # Bits row
        for i in range(7, 4, -1):
            self.put_bit_reserve(i)
        self.month = bcd2int(self.bytes[0] & 0x1f)
        annots = self.compose_annot(bits[AnnBits.MONTH],
                                    ann_value=months[self.month])
        self.put_data(4, 0, [AnnBits.MONTH, annots])
        # Registers row
        annots = self.compose_annot(registers[AnnRegs.MONTH],
                                    ann_action=self.format_action())
        self.put(self.ssd, self.esd, self.out_ann, [AnnRegs.MONTH, annots])

    def handle_reg_0x06(self):
        """Process year (0-99).

        - Add 2000 to double digit year number (expect 21st century)
          to instance variable for formatting.
        """
        # Bits row
        self.year = bcd2int(self.bytes[0] & 0xff)
        self.year += 2000
        annots = self.compose_annot(bits[AnnBits.YEAR],
                                    ann_value=self.year)
        self.put_data(7, 0, [AnnBits.YEAR, annots])
        # Registers row
        annots = self.compose_annot(registers[AnnRegs.YEAR],
                                    ann_action=self.format_action())
        self.put(self.ssd, self.esd, self.out_ann, [AnnRegs.YEAR, annots])

    def handle_reg_0x07(self):
        """Process control register."""
        # Bits row
        for i in (6, 5, 3, 2):
            self.put_bit_reserve(i)
        # Bits row - OUT bit
        out = 1 if (self.bytes[0] & (1 << ControlBits.OUT)) else 0
        annots = self.compose_annot(bits[AnnBits.OUT],
                                    ann_value=out)
        self.put_data(ControlBits.OUT, ControlBits.OUT, [AnnBits.OUT, annots])
        # Bits row - SQWE bit
        sqwe = 1 if (self.bytes[0] & (1 << ControlBits.SQWE)) else 0
        sqwe_l = ("en" if (sqwe) else "dis") + "abled"
        sqwe_s = sqwe_l[0].upper()
        annots = self.compose_annot(bits[AnnBits.SQWE],
                                    ann_value=[sqwe, sqwe_l, sqwe_s])
        self.put_data(ControlBits.SQWE, ControlBits.SQWE,
                      [AnnBits.SQWE, annots])
        # Bits row - RS bits
        rate = rates[self.bytes[0] & 0x03]
        annots = self.compose_annot(bits[AnnBits.RS0],
                                    ann_value=rate,
                                    ann_unit=params["UNIT_HZ"])
        rate //= 1000
        annots_add = self.compose_annot(bits[AnnBits.RS0],
                                        ann_value=rate,
                                        ann_unit=params["UNIT_KHZ"])
        annots.extend(annots_add)
        self.put_data(ControlBits.RS1, ControlBits.RS0, [AnnBits.RS0, annots])
        # Registers row
        annots = self.compose_annot(registers[AnnRegs.CONTROL],
                                    ann_action=self.format_action())
        self.put(self.ssd, self.esd, self.out_ann, [AnnRegs.CONTROL, annots])

    def handle_reg_0x3f(self):
        """Process NVRAM."""
        # Bits row
        annots = self.compose_annot(bits[AnnBits.NVRAM],
                                    ann_value=self.format_data(self.bytes[0]))
        self.put_data(7, 0, [AnnBits.NVRAM, annots])
        # Registers row
        annots = self.compose_annot(registers[AnnRegs.NVRAM],
                                    ann_action=self.format_action())
        self.put(self.ssd, self.esd, self.out_ann, [AnnRegs.NVRAM, annots])

    def decode(self, startsample, endsample, data):
        """Decode samples provided by parent decoder."""
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
                    self.handle_addr()
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
