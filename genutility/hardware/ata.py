from __future__ import generator_stop

from ctypes import LittleEndianStructure
from ctypes.wintypes import ULONG, USHORT

from cwinsdk.shared.ntdef import UCHAR

# Windows Kits\10\Include\10.0.17763.0\km\ata.h


class GeneralConfiguration(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("Reserved1", USHORT, 1),
        ("Retired3", USHORT, 1),
        ("ResponseIncomplete", USHORT, 1),
        ("Retired2", USHORT, 3),
        ("FixedDevice", USHORT, 1),
        ("RemovableMedia", USHORT, 1),
        ("Retired1", USHORT, 7),
        ("DeviceType", USHORT, 1),
    ]


class TrustedComputing(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("FeatureSupported", USHORT, 1),
        ("Reserved", USHORT, 15),
    ]


class Capabilities(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("CurrentLongPhysicalSectorAlignment", UCHAR, 2),
        ("ReservedByte49", UCHAR, 6),
        ("DmaSupported", UCHAR, 1),
        ("LbaSupported", UCHAR, 1),
        ("IordyDisable", UCHAR, 1),
        ("IordySupported", UCHAR, 1),
        ("Reserved1", UCHAR, 1),
        ("StandybyTimerSupport", UCHAR, 1),
        ("Reserved2", UCHAR, 2),
        ("ReservedWord50", USHORT),
    ]


class AdditionalSupported(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("ZonedCapabilities", USHORT, 2),
        ("NonVolatileWriteCache", USHORT, 1),
        ("ExtendedUserAddressableSectorsSupported", USHORT, 1),
        ("DeviceEncryptsAllUserData", USHORT, 1),
        ("ReadZeroAfterTrimSupported", USHORT, 1),
        ("Optional28BitCommandsSupported", USHORT, 1),
        ("IEEE1667", USHORT, 1),
        ("DownloadMicrocodeDmaSupported", USHORT, 1),
        ("SetMaxSetPasswordUnlockDmaSupported", USHORT, 1),
        ("WriteBufferDmaSupported", USHORT, 1),
        ("ReadBufferDmaSupported", USHORT, 1),
        ("DeviceConfigIdentifySetDmaSupported", USHORT, 1),
        ("LPSAERCSupported", USHORT, 1),
        ("DeterministicReadAfterTrimSupported", USHORT, 1),
        ("CFastSpecSupported", USHORT, 1),
    ]


class SerialAtaCapabilities(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("Reserved0", USHORT, 1),  # shall be set to 0
        ("SataGen1", USHORT, 1),
        ("SataGen2", USHORT, 1),
        ("SataGen3", USHORT, 1),
        ("Reserved1", USHORT, 4),
        ("NCQ", USHORT, 1),
        ("HIPM", USHORT, 1),
        ("PhyEvents", USHORT, 1),
        ("NcqUnload", USHORT, 1),
        ("NcqPriority", USHORT, 1),
        ("HostAutoPS", USHORT, 1),
        ("DeviceAutoPS", USHORT, 1),
        ("ReadLogDMA", USHORT, 1),
        ("Reserved2", USHORT, 1),  # shall be set to 0
        ("CurrentSpeed", USHORT, 3),
        ("NcqStreaming", USHORT, 1),
        ("NcqQueueMgmt", USHORT, 1),
        ("NcqReceiveSend", USHORT, 1),
        ("DEVSLPtoReducedPwrState", USHORT, 1),
        ("Reserved3", USHORT, 8),
    ]


class SerialAtaFeaturesSupported(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("Reserved0", USHORT, 1),  # shall be set to 0
        ("NonZeroOffsets", USHORT, 1),
        ("DmaSetupAutoActivate", USHORT, 1),
        ("DIPM", USHORT, 1),
        ("InOrderData", USHORT, 1),
        ("HardwareFeatureControl", USHORT, 1),
        ("SoftwareSettingsPreservation", USHORT, 1),
        ("NCQAutosense", USHORT, 1),
        ("DEVSLP", USHORT, 1),
        ("HybridInformation", USHORT, 1),
        ("Reserved1", USHORT, 6),
    ]


class SerialAtaFeaturesEnabled(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("Reserved0", USHORT, 1),  # shall be set to 0
        ("NonZeroOffsets", USHORT, 1),
        ("DmaSetupAutoActivate", USHORT, 1),
        ("DIPM", USHORT, 1),
        ("InOrderData", USHORT, 1),
        ("HardwareFeatureControl", USHORT, 1),
        ("SoftwareSettingsPreservation", USHORT, 1),
        ("DeviceAutoPS", USHORT, 1),
        ("DEVSLP", USHORT, 1),
        ("HybridInformation", USHORT, 1),
        ("Reserved1", USHORT, 6),
    ]


class CommandSetSupport(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("SmartCommands", USHORT, 1),
        ("SecurityMode", USHORT, 1),
        ("RemovableMediaFeature", USHORT, 1),
        ("PowerManagement", USHORT, 1),  # shall be set to 1
        ("Reserved1", USHORT, 1),
        ("WriteCache", USHORT, 1),
        ("LookAhead", USHORT, 1),
        ("ReleaseInterrupt", USHORT, 1),
        ("ServiceInterrupt", USHORT, 1),
        ("DeviceReset", USHORT, 1),
        ("HostProtectedArea", USHORT, 1),
        ("Obsolete1", USHORT, 1),
        ("WriteBuffer", USHORT, 1),
        ("ReadBuffer", USHORT, 1),
        ("Nop", USHORT, 1),
        ("Obsolete2", USHORT, 1),
        ("DownloadMicrocode", USHORT, 1),
        ("DmaQueued", USHORT, 1),
        ("Cfa", USHORT, 1),
        ("AdvancedPm", USHORT, 1),
        ("Msn", USHORT, 1),
        ("PowerUpInStandby", USHORT, 1),
        ("ManualPowerUp", USHORT, 1),
        ("Reserved2", USHORT, 1),
        ("SetMax", USHORT, 1),
        ("Acoustics", USHORT, 1),
        ("BigLba", USHORT, 1),
        ("DeviceConfigOverlay", USHORT, 1),
        ("FlushCache", USHORT, 1),
        ("FlushCacheExt", USHORT, 1),
        ("WordValid83", USHORT, 2),  # shall be 01b
        ("SmartErrorLog", USHORT, 1),
        ("SmartSelfTest", USHORT, 1),
        ("MediaSerialNumber", USHORT, 1),
        ("MediaCardPassThrough", USHORT, 1),
        ("StreamingFeature", USHORT, 1),
        ("GpLogging", USHORT, 1),
        ("WriteFua", USHORT, 1),
        ("WriteQueuedFua", USHORT, 1),
        ("WWN64Bit", USHORT, 1),
        ("URGReadStream", USHORT, 1),
        ("URGWriteStream", USHORT, 1),
        ("ReservedForTechReport", USHORT, 2),
        ("IdleWithUnloadFeature", USHORT, 1),
        ("WordValid", USHORT, 2),  # shall be 01b
    ]


class CommandSetActive(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("SmartCommands", USHORT, 1),
        ("SecurityMode", USHORT, 1),
        ("RemovableMediaFeature", USHORT, 1),
        ("PowerManagement", USHORT, 1),
        ("Reserved1", USHORT, 1),
        ("WriteCache", USHORT, 1),
        ("LookAhead", USHORT, 1),
        ("ReleaseInterrupt", USHORT, 1),
        ("ServiceInterrupt", USHORT, 1),
        ("DeviceReset", USHORT, 1),
        ("HostProtectedArea", USHORT, 1),
        ("Obsolete1", USHORT, 1),
        ("WriteBuffer", USHORT, 1),
        ("ReadBuffer", USHORT, 1),
        ("Nop", USHORT, 1),
        ("Obsolete2", USHORT, 1),
        ("DownloadMicrocode", USHORT, 1),
        ("DmaQueued", USHORT, 1),
        ("Cfa", USHORT, 1),
        ("AdvancedPm", USHORT, 1),
        ("Msn", USHORT, 1),
        ("PowerUpInStandby", USHORT, 1),
        ("ManualPowerUp", USHORT, 1),
        ("Reserved2", USHORT, 1),
        ("SetMax", USHORT, 1),
        ("Acoustics", USHORT, 1),
        ("BigLba", USHORT, 1),
        ("DeviceConfigOverlay", USHORT, 1),
        ("FlushCache", USHORT, 1),
        ("FlushCacheExt", USHORT, 1),
        ("Resrved3", USHORT, 1),
        ("Words119_120Valid", USHORT, 1),
        ("SmartErrorLog", USHORT, 1),
        ("SmartSelfTest", USHORT, 1),
        ("MediaSerialNumber", USHORT, 1),
        ("MediaCardPassThrough", USHORT, 1),
        ("StreamingFeature", USHORT, 1),
        ("GpLogging", USHORT, 1),
        ("WriteFua", USHORT, 1),
        ("WriteQueuedFua", USHORT, 1),
        ("WWN64Bit", USHORT, 1),
        ("URGReadStream", USHORT, 1),
        ("URGWriteStream", USHORT, 1),
        ("ReservedForTechReport", USHORT, 2),
        ("IdleWithUnloadFeature", USHORT, 1),
        ("Reserved4", USHORT, 2),
    ]


class NormalSecurityEraseUnit(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("TimeRequired", USHORT, 15),
        ("ExtendedTimeReported", USHORT, 1),
    ]


class EnhancedSecurityEraseUnit(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("TimeRequired", USHORT, 15),
        ("ExtendedTimeReported", USHORT, 1),
    ]


class PhysicalLogicalSectorSize(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("LogicalSectorsPerPhysicalSector", USHORT, 4),
        ("Reserved0", USHORT, 8),
        ("LogicalSectorLongerThan256Words", USHORT, 1),
        ("MultipleLogicalSectorsPerPhysicalSector", USHORT, 1),
        ("Reserved1", USHORT, 2),
    ]


class CommandSetSupportExt(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("ReservedForDrqTechnicalReport", USHORT, 1),
        ("WriteReadVerify", USHORT, 1),
        ("WriteUncorrectableExt", USHORT, 1),
        ("ReadWriteLogDmaExt", USHORT, 1),
        ("DownloadMicrocodeMode3", USHORT, 1),
        ("FreefallControl", USHORT, 1),
        ("SenseDataReporting", USHORT, 1),
        ("ExtendedPowerConditions", USHORT, 1),
        ("Reserved0", USHORT, 6),
        ("WordValid", USHORT, 2),  # shall be 01b
    ]


class CommandSetActiveExt(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("ReservedForDrqTechnicalReport", USHORT, 1),
        ("WriteReadVerify", USHORT, 1),
        ("WriteUncorrectableExt", USHORT, 1),
        ("ReadWriteLogDmaExt", USHORT, 1),
        ("DownloadMicrocodeMode3", USHORT, 1),
        ("FreefallControl", USHORT, 1),
        ("SenseDataReporting", USHORT, 1),
        ("ExtendedPowerConditions", USHORT, 1),
        ("Reserved0", USHORT, 6),
        ("Reserved1", USHORT, 2),
    ]


class SecurityStatus(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("SecuritySupported", USHORT, 1),
        ("SecurityEnabled", USHORT, 1),
        ("SecurityLocked", USHORT, 1),
        ("SecurityFrozen", USHORT, 1),
        ("SecurityCountExpired", USHORT, 1),
        ("EnhancedSecurityEraseSupported", USHORT, 1),
        ("Reserved0", USHORT, 2),
        ("SecurityLevel", USHORT, 1),
        ("Reserved1", USHORT, 7),
    ]


class CfaPowerMode1(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("MaximumCurrentInMA", USHORT, 12),
        ("CfaPowerMode1Disabled", USHORT, 1),
        ("CfaPowerMode1Required", USHORT, 1),
        ("Reserved0", USHORT, 1),
        ("Word160Supported", USHORT, 1),
    ]


class DataSetManagementFeature(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("SupportsTrim", USHORT, 1),
        ("Reserved0", USHORT, 15),
    ]


class SCTCommandTransport(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("Supported", USHORT, 1),
        ("Reserved0", USHORT, 1),
        ("WriteSameSuported", USHORT, 1),
        ("ErrorRecoveryControlSupported", USHORT, 1),
        ("FeatureControlSuported", USHORT, 1),
        ("DataTablesSuported", USHORT, 1),
        ("Reserved1", USHORT, 6),
        ("VendorSpecific", USHORT, 4),
    ]


class BlockAlignment(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("AlignmentOfLogicalWithinPhysical", USHORT, 14),
        ("Word209Supported", USHORT, 1),  # shall be set to 1
        ("Reserved0", USHORT, 1),  # shall be cleared to 0
    ]


class NVCacheCapabilities(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("NVCachePowerModeEnabled", USHORT, 1),
        ("Reserved0", USHORT, 3),
        ("NVCacheFeatureSetEnabled", USHORT, 1),
        ("Reserved1", USHORT, 3),
        ("NVCachePowerModeVersion", USHORT, 4),
        ("NVCacheFeatureSetVersion", USHORT, 4),
    ]


class NVCacheOptions(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("NVCacheEstimatedTimeToSpinUpInSeconds", UCHAR),
        ("Reserved", UCHAR),
    ]


class TransportMajorVersion(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("MajorVersion", USHORT, 12),
        ("TransportType", USHORT, 4),
    ]


class IDENTIFY_DEVICE_DATA(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("GeneralConfiguration", GeneralConfiguration),  # word 0
        ("NumCylinders", USHORT),
        ("SpecificConfiguration", USHORT),
        ("NumHeads", USHORT),
        ("Retired1", USHORT * 2),
        ("NumSectorsPerTrack", USHORT),
        ("VendorUnique1", USHORT * 3),
        ("SerialNumber", UCHAR * 20),
        ("Retired2", USHORT * 2),
        ("Obsolete1", USHORT),
        ("FirmwareRevision", UCHAR * 8),
        ("ModelNumber", UCHAR * 40),
        ("MaximumBlockTransfer", UCHAR),
        ("VendorUnique2", UCHAR),
        ("TrustedComputing", TrustedComputing),  # word 48
        ("Capabilities", Capabilities),
        ("ObsoleteWords51", USHORT * 2),
        ("TranslationFieldsValid", USHORT, 3),
        ("Reserved3", USHORT, 5),
        ("FreeFallControlSensitivity", USHORT, 8),
        ("NumberOfCurrentCylinders", USHORT),
        ("NumberOfCurrentHeads", USHORT),
        ("CurrentSectorsPerTrack", USHORT),  # word 56
        ("CurrentSectorCapacity", ULONG),
        ("CurrentMultiSectorSetting", UCHAR),
        ("MultiSectorSettingValid", UCHAR, 1),
        ("ReservedByte59", UCHAR, 3),
        ("SanitizeFeatureSupported", UCHAR, 1),
        ("CryptoScrambleExtCommandSupported", UCHAR, 1),
        ("OverwriteExtCommandSupported", UCHAR, 1),
        ("BlockEraseExtCommandSupported", UCHAR, 1),
        ("UserAddressableSectors", ULONG),
        ("ObsoleteWord62", USHORT),
        ("MultiWordDMASupport", USHORT, 8),
        ("MultiWordDMAActive", USHORT, 8),
        ("AdvancedPIOModes", USHORT, 8),
        ("ReservedByte64", USHORT, 8),
        ("MinimumMWXferCycleTime", USHORT),
        ("RecommendedMWXferCycleTime", USHORT),
        ("MinimumPIOCycleTime", USHORT),
        ("MinimumPIOCycleTimeIORDY", USHORT),
        ("AdditionalSupported", AdditionalSupported),
        ("ReservedWords70", USHORT * 5),  # word 74
        ("QueueDepth", USHORT, 5),
        ("ReservedWord75", USHORT, 11),
        ("SerialAtaCapabilities", SerialAtaCapabilities),
        ("SerialAtaFeaturesSupported", SerialAtaFeaturesSupported),
        ("SerialAtaFeaturesEnabled", SerialAtaFeaturesEnabled),
        ("MajorRevision", USHORT),
        ("MinorRevision", USHORT),
        ("CommandSetSupport", CommandSetSupport),
        ("CommandSetActive", CommandSetActive),
        ("UltraDMASupport", USHORT, 8),
        ("UltraDMAActive", USHORT, 8),
        ("NormalSecurityEraseUnit", NormalSecurityEraseUnit),
        ("EnhancedSecurityEraseUnit", EnhancedSecurityEraseUnit),  # word 90
        ("CurrentAPMLevel", USHORT, 8),
        ("ReservedWord91", USHORT, 8),
        ("MasterPasswordID", USHORT),
        ("HardwareResetResult", USHORT),
        ("CurrentAcousticValue", USHORT, 8),
        ("RecommendedAcousticValue", USHORT, 8),
        ("StreamMinRequestSize", USHORT),
        ("StreamingTransferTimeDMA", USHORT),
        ("StreamingAccessLatencyDMAPIO", USHORT),
        ("StreamingPerfGranularity", ULONG),
        ("Max48BitLBA", ULONG * 2),
        ("StreamingTransferTime", USHORT),
        ("DsmCap", USHORT),
        ("PhysicalLogicalSectorSize", PhysicalLogicalSectorSize),  # 106
        ("InterSeekDelay", USHORT),
        ("WorldWideName", USHORT * 4),
        ("ReservedForWorldWideName128", USHORT * 4),
        ("ReservedForTlcTechnicalReport", USHORT),
        ("WordsPerLogicalSector", USHORT * 2),
        ("CommandSetSupportExt", CommandSetSupportExt),
        ("CommandSetActiveExt", CommandSetActiveExt),
        ("ReservedForExpandedSupportandActive", USHORT * 6),  # 126
        ("MsnSupport", USHORT, 2),
        ("ReservedWord127", USHORT, 14),
        ("SecurityStatus", SecurityStatus),
        ("ReservedWord129", USHORT * 31),
        ("CfaPowerMode1", CfaPowerMode1),  # word 160
        ("ReservedForCfaWord161", USHORT * 7),
        ("NominalFormFactor", USHORT, 4),
        ("ReservedWord168", USHORT, 12),
        ("DataSetManagementFeature", DataSetManagementFeature),
        ("AdditionalProductID", USHORT * 4),
        ("ReservedForCfaWord174", USHORT * 2),
        ("CurrentMediaSerialNumber", USHORT * 30),
        ("SCTCommandTransport", SCTCommandTransport),  # 206
        ("ReservedWord207", USHORT * 2),
        ("BlockAlignment", BlockAlignment),
        ("WriteReadVerifySectorCountMode3Only", USHORT * 2),
        ("WriteReadVerifySectorCountMode2Only", USHORT * 2),
        ("NVCacheCapabilities", NVCacheCapabilities),
        ("NVCacheSizeLSW", USHORT),
        ("NVCacheSizeMSW", USHORT),
        ("NominalMediaRotationRate", USHORT),
        ("ReservedWord218", USHORT),
        ("NVCacheOptions", NVCacheOptions),
        ("WriteReadVerifySectorCountMode", USHORT, 8),
        ("ReservedWord220", USHORT, 8),
        ("ReservedWord221", USHORT),
        ("TransportMajorVersion", TransportMajorVersion),  # 222
        ("TransportMinorVersion", USHORT),
        ("ReservedWord224", USHORT * 6),
        ("ExtendedNumberOfUserAddressableSectors", ULONG * 2),
        ("MinBlocksPerDownloadMicrocodeMode03", USHORT),
        ("MaxBlocksPerDownloadMicrocodeMode03", USHORT),
        ("ReservedWord236", USHORT * 19),
        ("Signature", USHORT, 8),  # word 255
        ("CheckSum", USHORT, 8),
    ]


# SMART sub command list
IDE_SMART_READ_ATTRIBUTES = 0xD0
IDE_SMART_READ_THRESHOLDS = 0xD1
IDE_SMART_ENABLE_DISABLE_AUTOSAVE = 0xD2
IDE_SMART_SAVE_ATTRIBUTE_VALUES = 0xD3
IDE_SMART_EXECUTE_OFFLINE_DIAGS = 0xD4
IDE_SMART_READ_LOG = 0xD5
IDE_SMART_WRITE_LOG = 0xD6
IDE_SMART_ENABLE = 0xD8
IDE_SMART_DISABLE = 0xD9
IDE_SMART_RETURN_STATUS = 0xDA
IDE_SMART_ENABLE_DISABLE_AUTO_OFFLINE = 0xDB
