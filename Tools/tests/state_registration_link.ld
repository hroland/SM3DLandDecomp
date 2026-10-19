ENTRY(_ZN2al14initNerveStateEPNS_9IUseNerveEPNS_14NerveStateBaseEPKNS_5NerveEPKc)
SECTIONS {
    . = 0x810000;
    .text : { *(.text*) }
    .rodata : { *(.rodata*) }
    .data : { *(.data*) }
    .bss : { *(.bss*) }
    /DISCARD/ : { *(.comment) *(.ARM.exidx*) }
}
