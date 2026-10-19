ENTRY(_ZN2al11NerveKeeper6updateEv)
SECTIONS {
    . = 0x800000;
    .text : { *(.text*) }
    .rodata : { *(.rodata*) }
    .data : { *(.data*) }
    .bss : { *(.bss*) }
    /DISCARD/ : { *(.comment) *(.ARM.exidx*) }
}
_Znwj = 0x002932b0;
_ZN2al14NerveStateCtrlC1Ei = 0x001cad2c;
_ZN2al14NerveStateCtrl18tryEndCurrentStateEv = 0x001cac3c;
_ZN2al14NerveStateCtrl10startStateEPKNS_5NerveE = 0x001cabd8;
