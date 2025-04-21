---
title: 如何用PHP写一个hello world - 2
date: 2023-03-03T18:44:00+0800
draft: false
tags:
  - PHP
  - C
  - 汇编
toc: true
---

[上回](/posts/2023/03/02/how-to-write-hello-world-in-php-1/)说道，我们要写一个[花里胡哨的hello world](https://gist.github.com/dixyes/558e31c2129607cfcba70a81d65f8c52)，我们用x86_64汇编进行了系统调用来打印了hello world。

但这么调用多少有些痛苦，而且跟PHP没设么关系嘛。众所周知PHP解释器是用C写的，那么今天我们用C来写一个hello world
<!--more-->
```C
#include <stdio.h>
int main()
{
    printf("hello world!\n");
    return 0;
}
```

当然不是这么简单啦，这也不够我水一篇文章的，我们要做的其实是用**C调用约定**写一个hello world

## 0x00 C调用约定

> 叠甲先：以下原理部分仅供参考，有大量省略或不准确的部分

上集讲了x86_64 SYSV ABI，ABI这种东西除了规定了系统调用的方法，也规定了比较通用的函数（或者叫子例程(subroutine)/过程(procedure)比较好？）调用方法，而C的调用也是采用了通用的调用约定。

在x86_64上，它是这么实现的：

1. 调用者保存一些寄存器里面的值，这些寄存器也被称为“volatile”（会蒸发的）“scratch”（划痕，用作草稿的）寄存器。一般的，如果调用者用到了这些寄存器，调用前，编译器将这些寄存器的值压栈
2. 调用者准备调用参数到几个参数寄存器: rdi rsi rdx rcx r8 r9 （大多数unix-like，和sysv abi系统调用是一样的） / rcx rdx r8 r9（windows）
3. 调用者[call](https://c9x.me/x86/html/file_module_x86_id_26.html)目标地址：
3.1. 将返回地址也就是下一条指令的有效地址压栈
3.2. 跳转到目标地址
4. 被调用者处理下栈基址和栈指针（如果它完全没用到栈也可以不做这步）
4.1. 将当前栈基址（rbp，也就是调用者的栈到哪了）压栈
4.2. 将当前栈指针（rsp）的值存到栈基址寄存器
4.3. 栈指针值减掉用到的内存大小
5. 被调用者执行逻辑，要注意的是，有些编译器可能动态调整rsp，但这里并不是讲逆向，就不深入了
6.被调用者返回前处理下栈指针和栈基址
6.1. 栈指针值加回去
6.2. 如果之前做了rsp/rbp的操作，那么再还原回去，或者直接用一个[leave](https://c9x.me/x86/html/file_module_x86_id_154.html)
7. [ret](https://c9x.me/x86/html/file_module_x86_id_280.html)，这个指令会返回到rsp的栈上返回地址

这过程中还少了一些比如浮点数传参，结构体传参，red zone，shadow stack，CET的endbr32/64一类的东西，hello world并用不到，就不讲了。

## 0x10 用C写的hello

众所周知PHP是用C实现的，PHP的内建函数也是用C实现的

按照PHP的风格，这些函数以`zif_`（zend internal function）开头， 我们也不免俗

PHP内建函数的形参长这样

```C
void zif_fn(zend_execute_data *execute_data, zval* return_val);
```

这个函数是没有返回值和PHP参数传入的，是不是很意外？

PHP变量传入是通过压栈到PHP栈，再由zend提供的C函数解析的，比如我们接下来会用到的

```C
zend_result /*就是int啦*/ zend_parse_parameters(int required_arg_nums, const char* format, ...);
```

这个函数很简单，`required_arg_nums`是必须要有的参数数量，小于这个数量就抛出了

`format`则是格式，用起来跟[scanf(3)](https://linux.die.net/man/3/scanf)似的，format里写一个格式，后面跟一个地址

至于返回值，我们通过`return_val`返回，它是指向返回值的指针，改写它的内存就可以返回了。

如果`execute_data`指针指向的内存里设置了抛出的异常，那么再返回时就被视为抛出了一个异常。

光写hello不是太无聊了，我们来把这个hello带一个参数和一个返回值

```C
// 简化版zval结构体
typedef struct _zval_struct {
    // union value
    uint64_t value;
    // union u1
    uint32_t type_info;
    // union u2
    uint32_t u2;
} zval;

// 我们没用到executed_data，直接void*也无所谓
void zif_hacky_hello(void *ed, zval* ret)
{
    uint64_t arg;
    // 我们要求至少一个参数，类型为LONG，传到arg里
    if(zend_parse_parameters(1, "l", &arg)) {
        // 上面这个函数如果失败了，它会自动设置exception，我们只需要返回就行了
        return;
    };

    // 其实是在.u1.type_info
    ret->type = 4; // (IS_LONG)
    // 其实是.value.long
    ret->value = arg * 7;
}
```

编译它

```bash
cc function.c -o function.o -g -c -fno-stack-protector -Ofast
```

康康它的汇编是不是和上面说的一样

```bash
objdump -M att -S function.o
```

```text

function.o:     file format elf64-x86-64


Disassembly of section .text:

0000000000000000 <zif_hacky_hello>:
    // union u2
    uint32_t u2;
} zval;

void zif_hacky_hello(void *ed, zval* ret)
{
   0:   53                      push   %rbx                  压栈栈基址
    uint64_t arg;
    if(zend_parse_parameters(1, "l", &arg)) {
   1:   31 c0                   xor    %eax,%eax             清空rax
{
   3:   48 89 f3                mov    %rsi,%rbx             第一个参数放进rbx暂存下
    if(zend_parse_parameters(1, "l", &arg)) {
   6:   bf 01 00 00 00          mov    $0x1,%edi             往第一个参数rdi存个1
                                                             相对于rip计算常量"l"的地址，这是PIE寻址的用法
                                                             这里的0x0不是真的要用0x0，而是连接时才会填入真的地址
                                                             将它存到rsi里
   b:   48 8d 35 00 00 00 00    lea    0x0(%rip),%rsi        # 12 <zif_hacky_hello+0x12>
{
  12:   48 83 ec 10             sub    $0x10,%rsp            准备栈空间
                                                             这个时候才准备，因为编译器有优化，优化器发现栈到这个时候才用到，那么这个时候在处理也是可以的
    if(zend_parse_parameters(1, "l", &arg)) {
  16:   48 8d 54 24 08          lea    0x8(%rsp),%rdx        计算arg的地址：它在栈指针+8的位置上，把它存到rdx
                                                             PIE调用zend_parse_parameters
  1b:   ff 15 00 00 00 00       call   *0x0(%rip)        # 21 <zif_hacky_hello+0x21>
  21:   85 c0                   test   %eax,%eax             康康返回值是不是0，test指令不是cmp指令，经常用于比较一个寄存器和0
                                                             如果等于就继续，不等于就跳到3f，也就是下面的ret上
  23:   75 1a                   jne    3f <zif_hacky_hello+0x3f>
        return;
    };

    ret->type_info = 4;
    ret->value = arg * 7;
  25:   48 8b 54 24 08          mov    0x8(%rsp),%rdx        将arg里的值放到rdx
    ret->type_info = 4;
  2a:   c7 43 08 04 00 00 00    movl   $0x4,0x8(%rbx)        将4存到（（rbx也就是返回值地址）+8）的8byte内存里
    ret->value = arg * 7;
  31:   48 8d 04 d5 00 00 00    lea    0x0(,%rdx,8),%rax     lea的骚操作用法之一：快速整数运算
                                                             把用户输入的整数当作是一个线性地址，乘上8
                                                             再存进rax里
  38:   00
  39:   48 29 d0                sub    %rdx,%rax             rax = rax - rdx，这时候rax里存的就是arg * 7了
  3c:   48 89 03                mov    %rax,(%rbx)           将rax存到rbx指向的内存
}
  3f:   48 83 c4 10             add    $0x10,%rsp            还原rsp   
  43:   5b                      pop    %rbx                  还原rbx
  44:   c3                      ret                          返回
```

这个函数就是可以被PHP调用的内建函数啦，距能在PHP里写这么一个内建函数还差关键的一步，今天也就写到这里了
