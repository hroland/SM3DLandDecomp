#include "types.h"

// Reviewed prefixes only. Original class/method names and complete sizes are
// unknown. Keep the temporary EU entry names until their identities are known.
namespace {
struct HandleArrayPrefix {
    int count;
    u8 _4[4];
    void** buffer;
};

struct AudioObjectPrefix;
struct AudioVtablePrefix {
    void* _0;
    void (*dispatch)(AudioObjectPrefix*);
    void* _8[7];
    bool (*query)(AudioObjectPrefix*);
};

struct AudioReceiverPrefix;
struct AudioReceiverVtablePrefix {
    void* _0[2];
    void (*dispatch)(AudioReceiverPrefix*, AudioObjectPrefix*);
};

struct AudioReceiverPrefix {
    const AudioReceiverVtablePrefix* vtable;
};

struct AudioObjectPrefix {
    const AudioVtablePrefix* vtable;
    u8 _4[0x48 - 4];
    AudioReceiverPrefix* receiver;
};

struct HandleEntryPrefix {
    AudioObjectPrefix* object;
};

struct OwnerPrefix {
    u8 _0[8];
    int count;
};

struct AudioNodePrefix {
    AudioNodePrefix* prev;
    AudioNodePrefix* next;
    AudioObjectPrefix* object;
    OwnerPrefix* owner;

    void unlinkOwner();
};

struct AudioControlPrefix {
    u8 _0[0x20];
    // Only the sentinel's two link pointers are read; object/owner are not
    // part of the reviewed sentinel layout (control count is at +0x28).
    AudioNodePrefix sentinel;
};
} // namespace

// Independently identified as the existing sead::ListNode::erase_ source body.
extern "C" void FUN_0028e964(void*);

// Retain the observed caller boundaries; noinline is a matching-source choice,
// not evidence of the original annotation or translation-unit boundaries.
extern "C" __attribute__((noinline)) void FUN_001c21a4(void* pointer)
{
    AudioObjectPrefix* object = static_cast<HandleEntryPrefix*>(pointer)->object;
    object->vtable->dispatch(object);
}

extern "C" __attribute__((noinline)) void FUN_001c25d8(void* pointer)
{
    AudioObjectPrefix* object = static_cast<AudioObjectPrefix*>(pointer);
    AudioReceiverPrefix* receiver = object->receiver;
    receiver->vtable->dispatch(receiver, object);
}

void AudioNodePrefix::unlinkOwner()
{
    OwnerPrefix* previousOwner = owner;
    if (previousOwner) {
        owner = nullptr;
        FUN_0028e964(this);
        --previousOwner->count;
    }
}

extern "C" void FUN_001d9dc0(void* handle)
{
    HandleArrayPrefix* array = static_cast<HandleArrayPrefix*>(handle);
    for (int i = 0; i < array->count; ++i)
        FUN_001c21a4(array->buffer[i]);
}

extern "C" void FUN_001da074(void* pointer)
{
    AudioControlPrefix* control = static_cast<AudioControlPrefix*>(pointer);
    AudioNodePrefix* end = &control->sentinel;
    AudioNodePrefix* node = end->next;
    AudioNodePrefix* next = node->next;
    while (node != end) {
        AudioObjectPrefix* object = node->object;
        if (object->vtable->query(object)) {
            node->unlinkOwner();
        } else {
            FUN_001c25d8(object);
        }
        node = next;
        next = next->next;
    }
}
