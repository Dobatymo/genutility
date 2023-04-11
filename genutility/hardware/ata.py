from ctypes import LittleEndianStructure, c_uint8, c_uint16, c_uint32

# Windows Kits\10\Include\10.0.17763.0\km\ata.h


class GeneralConfiguration(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("Reserved1", c_uint16, 1),
        ("Retired3", c_uint16, 1),
        ("ResponseIncomplete", c_uint16, 1),
        ("Retired2", c_uint16, 3),
        ("FixedDevice", c_uint16, 1),
        ("RemovableMedia", c_uint16, 1),
        ("Retired1", c_uint16, 7),
        ("DeviceType", c_uint16, 1),
    ]


class TrustedComputing(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("FeatureSupported", c_uint16, 1),
        ("Reserved", c_uint16, 15),
    ]


class Capabilities(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("CurrentLongPhysicalSectorAlignment", c_uint8, 2),
        ("ReservedByte49", c_uint8, 6),
        ("DmaSupported", c_uint8, 1),
        ("LbaSupported", c_uint8, 1),
        ("IordyDisable", c_uint8, 1),
        ("IordySupported", c_uint8, 1),
        ("Reserved1", c_uint8, 1),
        ("StandybyTimerSupport", c_uint8, 1),
        ("Reserved2", c_uint8, 2),
        ("ReservedWord50", c_uint16),
    ]


class AdditionalSupported(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("ZonedCapabilities", c_uint16, 2),
        ("NonVolatileWriteCache", c_uint16, 1),
        ("ExtendedUserAddressableSectorsSupported", c_uint16, 1),
        ("DeviceEncryptsAllUserData", c_uint16, 1),
        ("ReadZeroAfterTrimSupported", c_uint16, 1),
        ("Optional28BitCommandsSupported", c_uint16, 1),
        ("IEEE1667", c_uint16, 1),
        ("DownloadMicrocodeDmaSupported", c_uint16, 1),
        ("SetMaxSetPasswordUnlockDmaSupported", c_uint16, 1),
        ("WriteBufferDmaSupported", c_uint16, 1),
        ("ReadBufferDmaSupported", c_uint16, 1),
        ("DeviceConfigIdentifySetDmaSupported", c_uint16, 1),
        ("LPSAERCSupported", c_uint16, 1),
        ("DeterministicReadAfterTrimSupported", c_uint16, 1),
        ("CFastSpecSupported", c_uint16, 1),
    ]


class SerialAtaCapabilities(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("Reserved0", c_uint16, 1),  # shall be set to 0
        ("SataGen1", c_uint16, 1),
        ("SataGen2", c_uint16, 1),
        ("SataGen3", c_uint16, 1),
        ("Reserved1", c_uint16, 4),
        ("NCQ", c_uint16, 1),
        ("HIPM", c_uint16, 1),
        ("PhyEvents", c_uint16, 1),
        ("NcqUnload", c_uint16, 1),
        ("NcqPriority", c_uint16, 1),
        ("HostAutoPS", c_uint16, 1),
        ("DeviceAutoPS", c_uint16, 1),
        ("ReadLogDMA", c_uint16, 1),
        ("Reserved2", c_uint16, 1),  # shall be set to 0
        ("CurrentSpeed", c_uint16, 3),
        ("NcqStreaming", c_uint16, 1),
        ("NcqQueueMgmt", c_uint16, 1),
        ("NcqReceiveSend", c_uint16, 1),
        ("DEVSLPtoReducedPwrState", c_uint16, 1),
        ("Reserved3", c_uint16, 8),
    ]


class SerialAtaFeaturesSupported(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("Reserved0", c_uint16, 1),  # shall be set to 0
        ("NonZeroOffsets", c_uint16, 1),
        ("DmaSetupAutoActivate", c_uint16, 1),
        ("DIPM", c_uint16, 1),
        ("InOrderData", c_uint16, 1),
        ("HardwareFeatureControl", c_uint16, 1),
        ("SoftwareSettingsPreservation", c_uint16, 1),
        ("NCQAutosense", c_uint16, 1),
        ("DEVSLP", c_uint16, 1),
        ("HybridInformation", c_uint16, 1),
        ("Reserved1", c_uint16, 6),
    ]


class SerialAtaFeaturesEnabled(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("Reserved0", c_uint16, 1),  # shall be set to 0
        ("NonZeroOffsets", c_uint16, 1),
        ("DmaSetupAutoActivate", c_uint16, 1),
        ("DIPM", c_uint16, 1),
        ("InOrderData", c_uint16, 1),
        ("HardwareFeatureControl", c_uint16, 1),
        ("SoftwareSettingsPreservation", c_uint16, 1),
        ("DeviceAutoPS", c_uint16, 1),
        ("DEVSLP", c_uint16, 1),
        ("HybridInformation", c_uint16, 1),
        ("Reserved1", c_uint16, 6),
    ]


class CommandSetSupport(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("SmartCommands", c_uint16, 1),
        ("SecurityMode", c_uint16, 1),
        ("RemovableMediaFeature", c_uint16, 1),
        ("PowerManagement", c_uint16, 1),  # shall be set to 1
        ("Reserved1", c_uint16, 1),
        ("WriteCache", c_uint16, 1),
        ("LookAhead", c_uint16, 1),
        ("ReleaseInterrupt", c_uint16, 1),
        ("ServiceInterrupt", c_uint16, 1),
        ("DeviceReset", c_uint16, 1),
        ("HostProtectedArea", c_uint16, 1),
        ("Obsolete1", c_uint16, 1),
        ("WriteBuffer", c_uint16, 1),
        ("ReadBuffer", c_uint16, 1),
        ("Nop", c_uint16, 1),
        ("Obsolete2", c_uint16, 1),
        ("DownloadMicrocode", c_uint16, 1),
        ("DmaQueued", c_uint16, 1),
        ("Cfa", c_uint16, 1),
        ("AdvancedPm", c_uint16, 1),
        ("Msn", c_uint16, 1),
        ("PowerUpInStandby", c_uint16, 1),
        ("ManualPowerUp", c_uint16, 1),
        ("Reserved2", c_uint16, 1),
        ("SetMax", c_uint16, 1),
        ("Acoustics", c_uint16, 1),
        ("BigLba", c_uint16, 1),
        ("DeviceConfigOverlay", c_uint16, 1),
        ("FlushCache", c_uint16, 1),
        ("FlushCacheExt", c_uint16, 1),
        ("WordValid83", c_uint16, 2),  # shall be 01b
        ("SmartErrorLog", c_uint16, 1),
        ("SmartSelfTest", c_uint16, 1),
        ("MediaSerialNumber", c_uint16, 1),
        ("MediaCardPassThrough", c_uint16, 1),
        ("StreamingFeature", c_uint16, 1),
        ("GpLogging", c_uint16, 1),
        ("WriteFua", c_uint16, 1),
        ("WriteQueuedFua", c_uint16, 1),
        ("WWN64Bit", c_uint16, 1),
        ("URGReadStream", c_uint16, 1),
        ("URGWriteStream", c_uint16, 1),
        ("ReservedForTechReport", c_uint16, 2),
        ("IdleWithUnloadFeature", c_uint16, 1),
        ("WordValid", c_uint16, 2),  # shall be 01b
    ]


class CommandSetActive(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("SmartCommands", c_uint16, 1),
        ("SecurityMode", c_uint16, 1),
        ("RemovableMediaFeature", c_uint16, 1),
        ("PowerManagement", c_uint16, 1),
        ("Reserved1", c_uint16, 1),
        ("WriteCache", c_uint16, 1),
        ("LookAhead", c_uint16, 1),
        ("ReleaseInterrupt", c_uint16, 1),
        ("ServiceInterrupt", c_uint16, 1),
        ("DeviceReset", c_uint16, 1),
        ("HostProtectedArea", c_uint16, 1),
        ("Obsolete1", c_uint16, 1),
        ("WriteBuffer", c_uint16, 1),
        ("ReadBuffer", c_uint16, 1),
        ("Nop", c_uint16, 1),
        ("Obsolete2", c_uint16, 1),
        ("DownloadMicrocode", c_uint16, 1),
        ("DmaQueued", c_uint16, 1),
        ("Cfa", c_uint16, 1),
        ("AdvancedPm", c_uint16, 1),
        ("Msn", c_uint16, 1),
        ("PowerUpInStandby", c_uint16, 1),
        ("ManualPowerUp", c_uint16, 1),
        ("Reserved2", c_uint16, 1),
        ("SetMax", c_uint16, 1),
        ("Acoustics", c_uint16, 1),
        ("BigLba", c_uint16, 1),
        ("DeviceConfigOverlay", c_uint16, 1),
        ("FlushCache", c_uint16, 1),
        ("FlushCacheExt", c_uint16, 1),
        ("Resrved3", c_uint16, 1),
        ("Words119_120Valid", c_uint16, 1),
        ("SmartErrorLog", c_uint16, 1),
        ("SmartSelfTest", c_uint16, 1),
        ("MediaSerialNumber", c_uint16, 1),
        ("MediaCardPassThrough", c_uint16, 1),
        ("StreamingFeature", c_uint16, 1),
        ("GpLogging", c_uint16, 1),
        ("WriteFua", c_uint16, 1),
        ("WriteQueuedFua", c_uint16, 1),
        ("WWN64Bit", c_uint16, 1),
        ("URGReadStream", c_uint16, 1),
        ("URGWriteStream", c_uint16, 1),
        ("ReservedForTechReport", c_uint16, 2),
        ("IdleWithUnloadFeature", c_uint16, 1),
        ("Reserved4", c_uint16, 2),
    ]


class NormalSecurityEraseUnit(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("TimeRequired", c_uint16, 15),
        ("ExtendedTimeReported", c_uint16, 1),
    ]


class EnhancedSecurityEraseUnit(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("TimeRequired", c_uint16, 15),
        ("ExtendedTimeReported", c_uint16, 1),
    ]


class PhysicalLogicalSectorSize(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("LogicalSectorsPerPhysicalSector", c_uint16, 4),
        ("Reserved0", c_uint16, 8),
        ("LogicalSectorLongerThan256Words", c_uint16, 1),
        ("MultipleLogicalSectorsPerPhysicalSector", c_uint16, 1),
        ("Reserved1", c_uint16, 2),
    ]


class CommandSetSupportExt(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("ReservedForDrqTechnicalReport", c_uint16, 1),
        ("WriteReadVerify", c_uint16, 1),
        ("WriteUncorrectableExt", c_uint16, 1),
        ("ReadWriteLogDmaExt", c_uint16, 1),
        ("DownloadMicrocodeMode3", c_uint16, 1),
        ("FreefallControl", c_uint16, 1),
        ("SenseDataReporting", c_uint16, 1),
        ("ExtendedPowerConditions", c_uint16, 1),
        ("Reserved0", c_uint16, 6),
        ("WordValid", c_uint16, 2),  # shall be 01b
    ]


class CommandSetActiveExt(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("ReservedForDrqTechnicalReport", c_uint16, 1),
        ("WriteReadVerify", c_uint16, 1),
        ("WriteUncorrectableExt", c_uint16, 1),
        ("ReadWriteLogDmaExt", c_uint16, 1),
        ("DownloadMicrocodeMode3", c_uint16, 1),
        ("FreefallControl", c_uint16, 1),
        ("SenseDataReporting", c_uint16, 1),
        ("ExtendedPowerConditions", c_uint16, 1),
        ("Reserved0", c_uint16, 6),
        ("Reserved1", c_uint16, 2),
    ]


class SecurityStatus(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("SecuritySupported", c_uint16, 1),
        ("SecurityEnabled", c_uint16, 1),
        ("SecurityLocked", c_uint16, 1),
        ("SecurityFrozen", c_uint16, 1),
        ("SecurityCountExpired", c_uint16, 1),
        ("EnhancedSecurityEraseSupported", c_uint16, 1),
        ("Reserved0", c_uint16, 2),
        ("SecurityLevel", c_uint16, 1),
        ("Reserved1", c_uint16, 7),
    ]


class CfaPowerMode1(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("MaximumCurrentInMA", c_uint16, 12),
        ("CfaPowerMode1Disabled", c_uint16, 1),
        ("CfaPowerMode1Required", c_uint16, 1),
        ("Reserved0", c_uint16, 1),
        ("Word160Supported", c_uint16, 1),
    ]


class DataSetManagementFeature(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("SupportsTrim", c_uint16, 1),
        ("Reserved0", c_uint16, 15),
    ]


class SCTCommandTransport(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("Supported", c_uint16, 1),
        ("Reserved0", c_uint16, 1),
        ("WriteSameSuported", c_uint16, 1),
        ("ErrorRecoveryControlSupported", c_uint16, 1),
        ("FeatureControlSuported", c_uint16, 1),
        ("DataTablesSuported", c_uint16, 1),
        ("Reserved1", c_uint16, 6),
        ("VendorSpecific", c_uint16, 4),
    ]


class BlockAlignment(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("AlignmentOfLogicalWithinPhysical", c_uint16, 14),
        ("Word209Supported", c_uint16, 1),  # shall be set to 1
        ("Reserved0", c_uint16, 1),  # shall be cleared to 0
    ]


class NVCacheCapabilities(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("NVCachePowerModeEnabled", c_uint16, 1),
        ("Reserved0", c_uint16, 3),
        ("NVCacheFeatureSetEnabled", c_uint16, 1),
        ("Reserved1", c_uint16, 3),
        ("NVCachePowerModeVersion", c_uint16, 4),
        ("NVCacheFeatureSetVersion", c_uint16, 4),
    ]


class NVCacheOptions(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("NVCacheEstimatedTimeToSpinUpInSeconds", c_uint8),
        ("Reserved", c_uint8),
    ]


class TransportMajorVersion(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("MajorVersion", c_uint16, 12),
        ("TransportType", c_uint16, 4),
    ]


class IDENTIFY_DEVICE_DATA(LittleEndianStructure):
    __slots__ = ()
    _pack_ = 1
    _fields_ = [
        ("GeneralConfiguration", GeneralConfiguration),  # word 0
        ("NumCylinders", c_uint16),
        ("SpecificConfiguration", c_uint16),
        ("NumHeads", c_uint16),
        ("Retired1", c_uint16 * 2),
        ("NumSectorsPerTrack", c_uint16),
        ("VendorUnique1", c_uint16 * 3),
        ("SerialNumber", c_uint8 * 20),
        ("Retired2", c_uint16 * 2),
        ("Obsolete1", c_uint16),
        ("FirmwareRevision", c_uint8 * 8),
        ("ModelNumber", c_uint8 * 40),
        ("MaximumBlockTransfer", c_uint8),
        ("VendorUnique2", c_uint8),
        ("TrustedComputing", TrustedComputing),  # word 48
        ("Capabilities", Capabilities),
        ("ObsoleteWords51", c_uint16 * 2),
        ("TranslationFieldsValid", c_uint16, 3),
        ("Reserved3", c_uint16, 5),
        ("FreeFallControlSensitivity", c_uint16, 8),
        ("NumberOfCurrentCylinders", c_uint16),
        ("NumberOfCurrentHeads", c_uint16),
        ("CurrentSectorsPerTrack", c_uint16),  # word 56
        ("CurrentSectorCapacity", c_uint32),
        ("CurrentMultiSectorSetting", c_uint8),
        ("MultiSectorSettingValid", c_uint8, 1),
        ("ReservedByte59", c_uint8, 3),
        ("SanitizeFeatureSupported", c_uint8, 1),
        ("CryptoScrambleExtCommandSupported", c_uint8, 1),
        ("OverwriteExtCommandSupported", c_uint8, 1),
        ("BlockEraseExtCommandSupported", c_uint8, 1),
        ("UserAddressableSectors", c_uint32),
        ("ObsoleteWord62", c_uint16),
        ("MultiWordDMASupport", c_uint16, 8),
        ("MultiWordDMAActive", c_uint16, 8),
        ("AdvancedPIOModes", c_uint16, 8),
        ("ReservedByte64", c_uint16, 8),
        ("MinimumMWXferCycleTime", c_uint16),
        ("RecommendedMWXferCycleTime", c_uint16),
        ("MinimumPIOCycleTime", c_uint16),
        ("MinimumPIOCycleTimeIORDY", c_uint16),
        ("AdditionalSupported", AdditionalSupported),
        ("ReservedWords70", c_uint16 * 5),  # word 74
        ("QueueDepth", c_uint16, 5),
        ("ReservedWord75", c_uint16, 11),
        ("SerialAtaCapabilities", SerialAtaCapabilities),
        ("SerialAtaFeaturesSupported", SerialAtaFeaturesSupported),
        ("SerialAtaFeaturesEnabled", SerialAtaFeaturesEnabled),
        ("MajorRevision", c_uint16),
        ("MinorRevision", c_uint16),
        ("CommandSetSupport", CommandSetSupport),
        ("CommandSetActive", CommandSetActive),
        ("UltraDMASupport", c_uint16, 8),
        ("UltraDMAActive", c_uint16, 8),
        ("NormalSecurityEraseUnit", NormalSecurityEraseUnit),
        ("EnhancedSecurityEraseUnit", EnhancedSecurityEraseUnit),  # word 90
        ("CurrentAPMLevel", c_uint16, 8),
        ("ReservedWord91", c_uint16, 8),
        ("MasterPasswordID", c_uint16),
        ("HardwareResetResult", c_uint16),
        ("CurrentAcousticValue", c_uint16, 8),
        ("RecommendedAcousticValue", c_uint16, 8),
        ("StreamMinRequestSize", c_uint16),
        ("StreamingTransferTimeDMA", c_uint16),
        ("StreamingAccessLatencyDMAPIO", c_uint16),
        ("StreamingPerfGranularity", c_uint32),
        ("Max48BitLBA", c_uint32 * 2),
        ("StreamingTransferTime", c_uint16),
        ("DsmCap", c_uint16),
        ("PhysicalLogicalSectorSize", PhysicalLogicalSectorSize),  # 106
        ("InterSeekDelay", c_uint16),
        ("WorldWideName", c_uint16 * 4),
        ("ReservedForWorldWideName128", c_uint16 * 4),
        ("ReservedForTlcTechnicalReport", c_uint16),
        ("WordsPerLogicalSector", c_uint16 * 2),
        ("CommandSetSupportExt", CommandSetSupportExt),
        ("CommandSetActiveExt", CommandSetActiveExt),
        ("ReservedForExpandedSupportandActive", c_uint16 * 6),  # 126
        ("MsnSupport", c_uint16, 2),
        ("ReservedWord127", c_uint16, 14),
        ("SecurityStatus", SecurityStatus),
        ("ReservedWord129", c_uint16 * 31),
        ("CfaPowerMode1", CfaPowerMode1),  # word 160
        ("ReservedForCfaWord161", c_uint16 * 7),
        ("NominalFormFactor", c_uint16, 4),
        ("ReservedWord168", c_uint16, 12),
        ("DataSetManagementFeature", DataSetManagementFeature),
        ("AdditionalProductID", c_uint16 * 4),
        ("ReservedForCfaWord174", c_uint16 * 2),
        ("CurrentMediaSerialNumber", c_uint16 * 30),
        ("SCTCommandTransport", SCTCommandTransport),  # 206
        ("ReservedWord207", c_uint16 * 2),
        ("BlockAlignment", BlockAlignment),
        ("WriteReadVerifySectorCountMode3Only", c_uint16 * 2),
        ("WriteReadVerifySectorCountMode2Only", c_uint16 * 2),
        ("NVCacheCapabilities", NVCacheCapabilities),
        ("NVCacheSizeLSW", c_uint16),
        ("NVCacheSizeMSW", c_uint16),
        ("NominalMediaRotationRate", c_uint16),
        ("ReservedWord218", c_uint16),
        ("NVCacheOptions", NVCacheOptions),
        ("WriteReadVerifySectorCountMode", c_uint16, 8),
        ("ReservedWord220", c_uint16, 8),
        ("ReservedWord221", c_uint16),
        ("TransportMajorVersion", TransportMajorVersion),  # 222
        ("TransportMinorVersion", c_uint16),
        ("ReservedWord224", c_uint16 * 6),
        ("ExtendedNumberOfUserAddressableSectors", c_uint32 * 2),
        ("MinBlocksPerDownloadMicrocodeMode03", c_uint16),
        ("MaxBlocksPerDownloadMicrocodeMode03", c_uint16),
        ("ReservedWord236", c_uint16 * 19),
        ("Signature", c_uint16, 8),  # word 255
        ("CheckSum", c_uint16, 8),
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
