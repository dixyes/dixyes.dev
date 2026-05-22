#!/usr/bin/env python3

# reference DEN0049 Rev E.g

import os
import sys
import struct as st
from typing import Literal, Optional


class Chunk:
    offset: int

    def pack(self) -> bytes:
        raise NotImplemented("interface")

    def getLength(self) -> int:
        raise NotImplemented("interface")


class IORT(Chunk):
    items: list["Node"]

    def __init__(
        self,
        signature: str = "IORT",
        revision: int = 7,  # Rev E.g
        oemId: str = "DIXYES",
        oemTableId: str = "IORT    ",
        oemRevision: int = 0,
        creatorId: str = "DIXY",
        creatorRevison: int = 0,
    ):
        self.signature = signature
        self.revision = revision
        self.oemId = oemId
        self.oemTableId = oemTableId
        self.oemRevision = oemRevision
        self.creatorId = creatorId
        self.creatorRevison = creatorRevison

        self.offset = 0
        self.items = []

    def getLength(self) -> int:
        return 48 + sum([item.getLength() for item in self.items])

    def pack(self) -> bytes:
        offset = self.offset + 48

        data = b""

        # build header
        data += st.pack(
            "<4sIBB6s8sI4sIIII",
            self.signature.encode(),
            self.getLength(),
            self.revision,
            0,  # checksum here,
            self.oemId.encode(),
            self.oemTableId.encode(),
            self.oemRevision,
            self.creatorId.encode(),
            self.creatorRevison,
            len(self.items),
            48,  # offset to first item
            0,  # reserved
        )

        # build items
        for item in self.items:
            item.offset = offset
            offset += item.getLength()

        for item in self.items:
            data += item.pack()

        checksum = 0
        for char in data:
            checksum += char
            checksum &= 0xFF

        data = data[:9] + st.pack("<B", 0x100 - checksum) + data[10:]

        return data


class Node(Chunk):
    mappings: list["Mapping"]

    def packMappings(self) -> bytes:
        data = b""
        for mapping in self.mappings:
            data += st.pack(
                "<IIIII",
                mapping.inputBase,
                mapping.idCount,
                mapping.outputBase,
                mapping.outputReference.offset,
                mapping.flags,
            )
        return data


class Mapping(Chunk):
    def __init__(
        self,
        inputBase: int,
        idCount: int,
        outputBase: int,
        outputReference: Chunk,
        flags: int,
    ):
        self.inputBase = inputBase
        self.idCount = idCount
        self.outputBase = outputBase
        self.outputReference = outputReference
        self.flags = flags


class ITSGroupRevEg(Node):
    def __init__(
        self,
        identifier: int,
        identifiers: list[int],
    ):
        self.mappings = []  # its group has no mappings
        self.identifier = identifier
        self.identifiers = identifiers

    def getLength(self) -> int:
        return 20 + len(self.identifiers) * 4 + len(self.mappings) * 20

    def pack(self) -> bytes:
        data = st.pack(
            "<BHBIIII",
            0x00,  # type
            self.getLength(),
            0x01,  # revision
            self.identifier,  # identifier
            0,  # mapping count, 0
            0,  # offset to mapping entries, none
            len(self.identifiers),
        )

        for identifier in self.identifiers:
            data += st.pack("<I", identifier)

        data += self.packMappings()

        return data


class RootComplexRevEg(Node):
    def __init__(
        self,
        identifier: int,
        mappings: list[Mapping],
        memoryProperties: int,  # 8byte
        atsAttribute: int,  # 4byte
        pciSegmentNumber: int,  # 4byte
        memoryAddressSizeLimit: int,  # 1byte
        pasidCapabilities: int,  # 2byte
        flags: int = 0,  # 4byte
    ):
        self.identifier = identifier
        self.mappings = mappings
        self.memoryProperties = memoryProperties
        self.atsAttribute = atsAttribute
        self.pciSegmentNumber = pciSegmentNumber
        self.memoryAddressSizeLimit = memoryAddressSizeLimit
        self.pasidCapabilities = pasidCapabilities
        self.flags = flags

    def getLength(self) -> int:
        return 0x28 + len(self.mappings) * 20

    def pack(self) -> bytes:
        data = st.pack(
            "<BHBIIIQIIBHBI",
            0x02,  # type
            self.getLength(),
            0x04,  # revision
            self.identifier,
            len(self.mappings),
            0x28,  # offset to mapping entries
            self.memoryProperties,
            self.atsAttribute,
            self.pciSegmentNumber,
            self.memoryAddressSizeLimit,
            self.pasidCapabilities,
            0,  # reserved
            self.flags,
        )

        data += self.packMappings()

        return data


class SMMUv1v2RevEg(Node):
    def __init__(
        self,
        identifier: int,
        mappings: list[Mapping],
        baseAddress: int,  # 8byte
        span: int,  # 8byte
        model: int,  # 4byte
        flags: int,  # 4byte
        NSgIrpt: int,  # 4byte
        NSgIrptFlags: int,  # 4byte
        NSgCfgIrpt: int,  # 4byte
        NSgCfgIrptFlags: int,  # 4byte
        contextInterrupts: list[int],
        pmuInterrupts: list[int],
    ):
        self.identifier = identifier
        self.mappings = mappings
        self.baseAddress = baseAddress
        self.span = span
        self.model = model
        self.flags = flags
        # global interrupt info
        self.NSgIrpt = NSgIrpt
        self.NSgIrptFlags = NSgIrptFlags
        self.NSgCfgIrpt = NSgCfgIrpt
        self.NSgCfgIrptFlags = NSgCfgIrptFlags
        # mutable part
        self.contextInterrupts = contextInterrupts
        self.pmuInterrupts = pmuInterrupts

    def getLength(self) -> int:
        return (
            0x4C  # fixed part + global interrupt info
            + len(self.contextInterrupts) * 8
            + len(self.pmuInterrupts) * 8
            + len(self.mappings) * 20
        )

    def pack(self) -> bytes:
        data = b""
        data += st.pack(
            "<BHBIII",
            0x03,  # type
            self.getLength(),
            0x03,  # revision
            self.identifier,
            len(self.mappings),
            (
                0x4C  # fixed part + global interrupt info
                + len(self.contextInterrupts) * 8
                + len(self.pmuInterrupts) * 8
                if len(self.mappings) > 0
                else 0
            ),
        )

        data += st.pack(
            "<QQIIIIIII",
            self.baseAddress,
            self.span,
            self.model,
            self.flags,
            0x3C,  # offset from start of this item to the SMMU global interrupt info
            len(self.contextInterrupts),
            0x4C,
            len(self.pmuInterrupts),
            0x4C + len(self.contextInterrupts) * 8,
        )

        data += st.pack(
            "<IIII",
            self.NSgIrpt,
            self.NSgIrptFlags,
            self.NSgCfgIrpt,
            self.NSgCfgIrptFlags,
        )

        for contenttInterrupt in self.contextInterrupts:
            data += st.pack("<Q", contenttInterrupt)

        for pmuInterrupt in self.pmuInterrupts:
            data += st.pack("<Q", pmuInterrupt)

        data += self.packMappings()

        return data


def main():
    iort = IORT(
        revision=0,
        oemId="PHYLTD",
        oemTableId="ARM-PHYT",
        oemRevision=0x20251020,
        creatorId="ARM ",
        creatorRevison=0x99,
    )

    itsGroup = ITSGroupRevEg(
        identifier=0,
        identifiers=[0],
    )
    iort.items.append(itsGroup)

    smmu0 = SMMUv1v2RevEg(
        mappings=[
            Mapping(
                inputBase=0,
                idCount=0xFFFF,  # 00:00 -> ff:ff
                outputBase=0,
                outputReference=itsGroup,
                flags=0,
            ),
        ],
        identifier=1,
        baseAddress=0x000008002C000000,
        span=0x0000000000400000,
        model=3,  # MMU-500
        flags=2,
        NSgIrpt=0x79,
        NSgIrptFlags=0,
        NSgCfgIrpt=0,
        NSgCfgIrptFlags=0,
        contextInterrupts=[x for x in range(0x59, 0x79)],
        pmuInterrupts=[],
    )
    smmu1 = SMMUv1v2RevEg(
        mappings=[
            Mapping(
                inputBase=0,
                idCount=0xFFFF,  # 00:00 -> ff:ff
                outputBase=0,
                outputReference=itsGroup,
                flags=0,
            ),
        ],
        identifier=2,
        baseAddress=0x000008002C400000,
        span=0x0000000000400000,
        model=3,  # MMU-500
        flags=2,
        NSgIrpt=0x9B,
        NSgIrptFlags=0,
        NSgCfgIrpt=0,
        NSgCfgIrptFlags=0,
        contextInterrupts=[x for x in range(0x7B, 0x9B)],
        pmuInterrupts=[],
    )

    def mapItem(startSeg: str, endSeg: str, outputBase:int, outputRef: Chunk):
        bus, devFunc = startSeg.split(":")
        dev, func = devFunc.split(".")
        bus = int(bus, 16)
        dev = int(dev, 16)
        func = int(func, 16)

        inputBase = (bus << 8) | (dev << 3) | func

        bus, devFunc = endSeg.split(":")
        dev, func = devFunc.split(".")
        bus = int(bus, 16)
        dev = int(dev, 16)
        func = int(func, 16)
        idCount = ((bus << 8) | (dev << 3) | func) - inputBase - 1

        if outputBase == -1:
            outputBase = inputBase

        return Mapping(
            inputBase=inputBase,
            idCount=idCount,
            outputBase=outputBase,
            outputReference=outputRef,
            flags=0,
        )
        
    rootComplex = RootComplexRevEg(
        identifier=3,
        mappings=[
            # # RC 00:00.0
            # mapItem("00:00.0", "00:01.0", -1, smmu0),
            # # RC 00:01.0
            # mapItem("00:01.0", "00:02.0", -1, smmu0),
            # # RC 00:02.0
            # mapItem("00:02.0", "00:03.0", -1, smmu1),

            # # down bridges on RC 00:00.0
            # mapItem("02:00.0", "03:00.0", -1, smmu0),
            # # down bridges on RC 00:01.0
            # mapItem("01:00.0", "02:00.0", -1, smmu0),
            # # down bridges on RC 00:02.0
            # mapItem("0f:00.0", "10:00.0", -1, smmu1),

            # # devices on down bridge 02:xx.x of RC 00:00.0
            # mapItem("03:00.0", "0d:00.0", -1, smmu0),
            # # devices on down bridge 01:xx.x of RC 00:01.0
            # mapItem("0d:00.0", "0e:00.0", -1, smmu0),
            # # devices on down bridge 0f:xx.x of RC 00:02.0
            # mapItem("10:00.0", "1a:00.0", -1, smmu1),

            # devices on down bridge 02:xx.x of RC 00:00.0
            mapItem("03:00.0", "04:00.0", -1, smmu0), # 03:00.x LPe15000
            mapItem("05:00.0", "06:00.0", -1, smmu0), # 05:00.x Cx4 LX
            mapItem("07:00.0", "08:00.0", -1, smmu0), # 07:00.0 SAS3008
            mapItem("08:00.0", "0a:00.0", -1, smmu0), # 08:00.0 AST2500 PCI bridge + 09:00.0 VGA
            mapItem("0a:00.0", "0b:00.0", -1, smmu0), # 0a:00.x I350
            mapItem("0c:00.0", "0d:00.0", -1, smmu0), # 0c:00.0 A300-3000

            # devices on down bridge 01:xx.x of RC 00:01.0
            mapItem("0d:00.0", "0e:00.0", -1, smmu0), # 0d:00.0 uPD720201

            # devices on down bridge 0f:xx.x of RC 00:02.0
            mapItem("10:00.0", "11:00.0", -1, smmu1), # 10:00.0 88SE9230
            mapItem("11:00.0", "12:00.0", -1, smmu1), # 11:00.0 88SE9230
            mapItem("12:00.0", "13:00.0", -1, smmu1), # 12:00.0 88SE9230
            mapItem("13:00.0", "14:00.0", -1, smmu1), # 13:00.0 88SE9230
            # mapItem("18:00.0", "19:00.0", -1, smmu1), # 18:00.0 nvme
            mapItem("19:00.0", "1a:00.0", -1, smmu1), # 19:00.0 uPD720201
        ],
        memoryProperties=0x0300000000000001,
        atsAttribute=0,
        pciSegmentNumber=0,
        memoryAddressSizeLimit=0x30,
        pasidCapabilities=0,
    )
    iort.items.append(rootComplex)
    iort.items.append(smmu0)
    iort.items.append(smmu1)

    open("iort_reveg.aml", "wb").write(iort.pack())


if __name__ == "__main__":
    main()


