---
title: 如何用PHP写一个hello world - 4
date: 2024-06-24T15:58:00+0800
draft: false
tags:
  - PHP
  - C
  - FFI
  - 汇编
toc: true
---

开始调用hello world
<!--more-->

## 0x00 内存保护

老样子，先叠甲：这篇文章是科普向的，东西写的比较简略，并不保证完全与实际相符。

我们这些计算机程序都是放在内存里的，内存的基本组织形式叫“页”page，每个页具有固定的大小（比如x86的4k，arm的4k/16k之类的）一些页组成段“segment”（也就是segment fault里的那个segment）。现代计算机可以给页加上属性，这些属性用于保护内存不被恶意软件或者bug破坏。因此，如果我们把之前写的x86机器码直接丢到内存，它是跑不起来的。

有关内存的更多知识，可以在搜索引擎搜索关键词“页表”“NX位”等关键词，这里就不再赘述了，我们只考虑如何让他跑起来。

在Linux（或者说unix-like）中，内存保护通过系统调用[mprotect(2)](https://man7.org/linux/man-pages/man2/mprotect.2.html)来修改，我们就来实现一下：

```C
#include <sys/mman.h>

#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>

// 假定页大小是4096（x86默认这么大
#define PAGESIZE 4096

// 第一篇文章里写的hello
const char myprint[] = {
    0x48, 0xc7, 0xc0, 0x01, 0x00, 0x00, 0x00, // mov $0x1,%rax
    0x48, 0xc7, 0xc7, 0x01, 0x00, 0x00, 0x00, // mov $0x1,%rdi
    0x48, 0x8d, 0x35, 0x0b, 0x00, 0x00, 0x00, // 0xb(%rip),%rsi
    0x48, 0xc7, 0xc2, 0x0d, 0x00, 0x00, 0x00, // mov $0xd,%rdx
    0x0f, 0x05, // syscall
    0xc2, // ret
    0x90, // nop'
    'h', 'e', 'l', 'l', 'o', ' ', 'w', 'o', 'r', 'l', 'd', '!', '\n',
};

int main() {
    int ret;
    char *execBuf = NULL;

    // 直接这么跑会segv，毕竟静态初始化数据在data，rodata，bss段之类的只读的地方
    // 它们一般来说都不可执行
    // ((void(*)())myprint)();

#ifdef __linux__
    // 根据Linux manpage，linux下可以mprotect任何地址
    execBuf = (char *) myprint;
    // 对齐到上一个页的边缘
    char *_execBuf = (char *)((intptr_t)execBuf / PAGESIZE * PAGESIZE);
    // 让相邻的两个页可执行
    ret = mprotect(_execBuf, PAGESIZE * 2, PROT_READ | PROT_EXEC);
    if (ret != 0) {
        printf("failed mprotect1: %d\n", errno);
        return 1;
    }
#else
    // 不是Linux
    // 先申请一个mmap，根据POSIX文档，mmap(2)出来的内存才能mprotect
    execBuf = mmap(NULL, PAGESIZE, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, 0, 0);

    // 拷贝代码到buffer里
    memcpy(execBuf, myprint, sizeof(myprint));

    // 令buffer可执行，注意有些平台不能同时具有写和执行，最严格的模式下一个页写过东西就不能再启用执行
    ret = mprotect(execBuf, PAGESIZE, PROT_READ | PROT_EXEC);
    if (ret != 0) {
        printf("failed mprotect: %d\n", errno);
        return 1;
    }
#endif

    ((void(*)())execBuf)();

    return 0;
}

```

## 0x10 换成php写

结合之前三篇的内容，整理成一个代码（全文见[gist](https://gist.github.com/dixyes/558e31c2129607cfcba70a81d65f8c52)）：

```PHP
<?php

$code = "<这里填上第二篇文章写的PHP的zif函数>";

// 声明调用php zif函数需要的工具
$ffi = FFI::cdef(<<<C
typedef uint64_t size_t;
typedef int64_t off_t;
/* not used, so only empty struct */
typedef struct _zend_class_entry {} zend_class_entry;
typedef struct _zend_execute_data {} zend_execute_data;
typedef struct _zend_array {} HashTable;
/* fake */
typedef char* zval;
/* used */
typedef struct {
    void *ptr;
    uint32_t type_mask;
} zend_type;
typedef void (*zif_handler)(zend_execute_data *execute_data, zval *return_value);
typedef struct _zend_internal_arg_info {
    const char *name;
    zend_type type;
    const char *default_value;
} zend_internal_arg_info;
typedef struct _zend_function_entry {
    const char *fname;
    zif_handler handler;
    const struct _zend_internal_arg_info *arg_info;
    uint32_t num_args;
    uint32_t flags;
} zend_function_entry;
/* sys/mman.h */
void *mmap (void *__addr, size_t __len, int __prot, int __flags, int __fd, off_t __offset);
int mprotect (void *__addr, size_t __len, int __prot);
/* zend_API.h */
int zend_register_functions(zend_class_entry *scope, const zend_function_entry *functions, HashTable *function_table, int type);
int zend_parse_parameters(uint32_t num_args, const char *type_spec, ...);
/* errno.h */
int errno;
/* string.h */
char *strerror (int __errnum);
/* stdlib.h */
void *malloc (size_t __size);
/* stdio.h */
int printf (const char *__restrict __fmt, ...);
C);

// 创建一个buffer
$buf = $ffi->mmap(null, 4096, 0x2 /* PROT_WRITE */, 0x20 /* MAP_ANONYMOUS */ | 0x02 /* MAP_PRIVATE */, 0, 0);

// 拷代码进去
FFI::memcpy($buf, $code, strlen($code));

// 使buffer可执行
$ret = $ffi->mprotect($buf, 4096, 0x1 /* PROT_READ */ | 0x4 /* PROT_EXEC */);

// 创建arginfo 
$arg_info = $ffi->new("zend_internal_arg_info[2]", false, true);
$arg_info[0]->name = FFI::cast("char*", $required_args);
// ...

// 创建fe（zend_function_entry）
$fe = $ffi->new("zend_function_entry[2]", false, true);
$fe[0]->fname = $fname;
$fe[0]->handler = $ffi->cast("zif_handler", $buf);
// ...

// 注册这个fe
$ret = $ffi->zend_register_functions(
    null, // scope设置为NULL，我们不需要它
    $fe,
    null, // 使用全局函数表
    1, // 这是个persistent的，不是请求级别的
);

// 这时候PHP的全局上下文已经有了一个叫hello的PHP函数，用reflection可以看到函数的信息
$r = new ReflectionFunction('hello');
$params = $r->getParameters();
foreach ($params as $param) {
    var_dump($param->getType()->getName(), $param->getName());
}
var_dump($r->getReturnType()->getName());

// 调用它
var_dump(hello(6));
```

至此，一个花里胡哨的php “hello world”就写好了

