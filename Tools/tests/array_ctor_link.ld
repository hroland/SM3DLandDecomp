ENTRY(__aeabi_vec_ctor_nocookie_nodtor)
SECTIONS {
    . = 0x820000;
    .text : { *(.text*) }
    .rodata : { *(.rodata*) }
    .data : { *(.data*) }
    .bss : { *(.bss*) }
    /DISCARD/ : { *(.comment) *(.ARM.exidx*) }
}
