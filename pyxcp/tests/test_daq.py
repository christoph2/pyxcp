#!/usr/bin/env python

from pyxcp.daq_stim import Daq, DaqList


DAQ_INFO = {
    "channels": [
        {
            "cycle": 0,
            "maxDaqList": 1,
            "name": "Key T",
            "priority": 0,
            "properties": {"consistency": "CONSISTENCY_ODT", "daq": True, "packed": False, "stim": False},
            "unit": "EVENT_CHANNEL_TIME_UNIT_1MS",
        },
        {
            "cycle": 10,
            "maxDaqList": 1,
            "name": "10 ms",
            "priority": 1,
            "properties": {"consistency": "CONSISTENCY_ODT", "daq": True, "packed": False, "stim": True},
            "unit": "EVENT_CHANNEL_TIME_UNIT_1MS",
        },
        {
            "cycle": 100,
            "maxDaqList": 1,
            "name": "100ms",
            "priority": 2,
            "properties": {"consistency": "CONSISTENCY_ODT", "daq": True, "packed": False, "stim": True},
            "unit": "EVENT_CHANNEL_TIME_UNIT_1MS",
        },
        {
            "cycle": 1,
            "maxDaqList": 1,
            "name": "1ms",
            "priority": 3,
            "properties": {"consistency": "CONSISTENCY_ODT", "daq": True, "packed": False, "stim": True},
            "unit": "EVENT_CHANNEL_TIME_UNIT_1MS",
        },
        {
            "cycle": 10,
            "maxDaqList": 1,
            "name": "FilterBypassDaq",
            "priority": 4,
            "properties": {"consistency": "CONSISTENCY_ODT", "daq": True, "packed": False, "stim": True},
            "unit": "EVENT_CHANNEL_TIME_UNIT_1MS",
        },
        {
            "cycle": 10,
            "maxDaqList": 1,
            "name": "FilterBypassStim",
            "priority": 5,
            "properties": {"consistency": "CONSISTENCY_ODT", "daq": False, "packed": False, "stim": True},
            "unit": "EVENT_CHANNEL_TIME_UNIT_1MS",
        },
    ],
    "processor": {
        "keyByte": {
            "addressExtension": "AE_DIFFERENT_WITHIN_ODT",
            "identificationField": "IDF_REL_ODT_NUMBER_ABS_DAQ_LIST_NUMBER_BYTE",
            "optimisationType": "OM_DEFAULT",
        },
        "maxDaq": 0,
        "minDaq": 0,
        "properties": {
            "bitStimSupported": False,
            "configType": "DYNAMIC",
            "overloadEvent": False,
            "overloadMsb": True,
            "pidOffSupported": False,
            "prescalerSupported": True,
            "resumeSupported": True,
            "timestampSupported": True,
        },
    },
    "resolution": {
        "granularityOdtEntrySizeDaq": 1,
        "granularityOdtEntrySizeStim": 1,
        "maxOdtEntrySizeDaq": 218,
        "maxOdtEntrySizeStim": 218,
        "timestampMode": {"fixed": False, "size": "S4", "unit": "DAQ_TIMESTAMP_UNIT_10US"},
        "timestampTicks": 10,
    },
}

SLAVE_INFO = {
    "addressGranularity": 0,
    "byteOrder": 0,
    "interleavedMode": False,
    "masterBlockMode": True,
    "maxBs": 2,
    "maxCto": 255,
    "maxDto": 1500,
    "maxWriteDaqMultipleElements": 31,
    "minSt": 0,
    "optionalCommMode": True,
    "pgmProcessor": {},
    "protocolLayerVersion": 1,
    "queueSize": 0,
    "slaveBlockMode": True,
    "supportsCalpag": True,
    "supportsDaq": True,
    "supportsPgm": True,
    "supportsStim": True,
    "transportLayerVersion": 1,
    "xcpDriverVersionNumber": 25,
}


class AttrDict(dict):
    def __getattr__(self, name):
        return self[name]


class MockMaster:
    def __init__(self):
        self.slaveProperties = AttrDict(
            {
                "maxDto": 1500,
                "supportsDaq": True,
            }
        )

    def getDaqInfo(self):
        return DAQ_INFO

    def freeDaq(self):
        pass

    def allocDaq(self, daq_count):
        self.daq_count = daq_count

    def allocOdt(self, daq_num, odt_count):
        pass

    def allocOdtEntry(self, daq_num, odt_num, entry_count):
        pass

    def setDaqPtr(self, daqListNumber, odtNumber, odtEntryNumber):
        pass

    def writeDaq(self, bitOffset, entrySize, addressExt, address):
        pass

    def setDaqListMode(self, mode, daqListNumber, eventChannelNumber, prescaler, priority):
        pass

    def startStopDaqList(self, mode, daqListNumber):
        pass

    def startStopSynch(self, mode):
        pass


DAQ_LISTS = [
    DaqList(
        1,
        [
            ("channel1", 0x1BD004, 0, 4, "U32"),
            ("channel2", 0x1BD008, 0, 4, "U32"),
            ("PWMFiltered", 0x1BDDE2, 0, 1, "U8"),
            ("PWM", 0x1BDDDF, 0, 1, "U8"),
            ("Triangle", 0x1BDDDE, 0, 1, "U8"),
        ],
    ),
    DaqList(
        3,
        [
            ("TestWord_001", 0x1BE120, 0, 2, "U16"),
            ("TestWord_003", 0x1BE128, 0, 2, "U16"),
            ("TestWord_004", 0x1BE12C, 0, 2, "U16"),
            ("TestWord_005", 0x1BE134, 0, 2, "U16"),
            ("TestWord_006", 0x1BE134, 0, 2, "U16"),
            ("TestWord_007", 0x1BE138, 0, 2, "U16"),
            ("TestWord_008", 0x1BE13C, 0, 2, "U16"),
            ("TestWord_009", 0x1BE140, 0, 2, "U16"),
            ("TestWord_011", 0x1BE148, 0, 2, "U16"),
            # ("", ),
        ],
    ),
]

daq = Daq()
daq.set_master(MockMaster())

daq.add_daq_lists(DAQ_LISTS)
daq.setup()
daq.start()
