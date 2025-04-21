---
title: 如何用PHP写一个hello world - 1
date: 2023-03-02T13:34:00+0800
draft: false
tags:
  - Linux
  - PHP
  - C
  - 汇编
toc: true
---

其实挺简单的不是：

```PHP
<?php
echo "hello world!" . PHP_EOL;
```

但这么不够花里胡哨，不足以让我水一篇文章，所以我们今天来写一个[花里胡哨的hello world](https://gist.github.com/dixyes/558e31c2129607cfcba70a81d65f8c52)
<!--more-->

## 0x00 如何用linux写一个hello world

那就要调用[write(2)](https://linux.die.net/man/2/write)系统调用，往[stdout](https://linux.die.net/man/3/stdout)里写入一个"hello world"字符串啦：

```C
// C里面
write(1, "hello world!\n", sizeof("hello world!\n") -1);
```

## 0x10 简要的原理说明

> 以下有关原理的部分仅方便理解，不是正式说明，可能存在错误或省略

现代操作系统的内核和上层应用是隔离开来的，这保证了用户xjb写程序时不会干挂内核，也不能同内核窃取其他程序的信息。
当一个程序需要内核帮他做些事情的时候，比如让内核在用户的屏幕上打印"hello world"，就需要系统调用。
系统调用这种东西就是让CPU从用户的内存空间中跳出来，回到内核的内存空间里，恢复内核的特权级别的一种手段。

1. 在i386（就是32位x86啦）上，系统调用通过0x80中断来实现，中断是一种中断当前cpu的执行来实现比如网络请求的传输之类的机制。内核注册中断的handler，当中断发生时，中断控制器将CPU执行中断，将他的PC指向handler的地址执行（想象一下把唱片的头抬起来放到别处）
2. 在x86_64上，系统调用通过快速系统调用指令来实现，这个指令相较于中断来说效率更高，具体的原因可以康康相关的文章，这篇文章就不再讲了
3. 在arm上，系统调用通过svc指令来进行

## 0x20 x86_64 SYSV ABI

那么接下来，我们就用x86_64的linux来描述了，毕竟这是我们最常见的平台和OS

x86_64的linux使用[x86_64 SYSV ABI](https://wiki.osdev.org/System_V_ABI)，这个东西分为三部分，x86_64代表它是64位x86的；SYSV代表[System V](https://en.wikipedia.org/wiki/UNIX_System_V)，这是UNIX的一个版本，后面几乎所有UNIX和UNIX-like的OS都是继承或者兼容于它的，linux也不例外；ABI则是[Application Binary Interface](https://en.wikipedia.org/wiki/Application_binary_interface)，指一套如何调用函数之类的约定

在这个ABI中呢，系统调用需要这么做：
1. rax（eax）寄存器存储syscall号，syscall号用于区分不同的系统调用，比如1是`SYS_write`，也就是`write(2)`的系统调用号了
2. rdi rsi rdx rcx r8 r9六个寄存器分别存储第1-6个参数（如果有更多的参数怎么传呢
3. 然后通过`syscall`指令进行系统调用
4. 返回值放在rax里

## 0x30 汇编

知道了怎么系统调用，我们先用汇编写个hello world

（为什么不用C或者其他高级语言呢：高级语言/c的标准库glibc或者musl封装了系统调用，他们会让这一过程变得十分复杂，不利于理解）

```asm
// 这是GAS格式的汇编，也就是gcc会生成/汇编的汇编格式，一般的这样的汇编扩展名是.S
.text // 告诉汇编器，以下的东西放在text段，也就是我们CPU执行的时候用到的段
.global _start // 告诉汇编器，下面有个叫_start的符号，它是全局可用的

_start: // _start符号指向这里
// gas汇编采用AT&T格式，有这些特点：
// 参数顺序和intel反过来的：他是 operand source, source, dest
// 参数之间有逗号
// 常量前使用$，寄存器前使用%
mov $0x1, %rax // 将SYS_write 1存入rax
mov $0x1, %rdi // 将stdout的fd号1存入rdi
// 这是PIE寻址的方式，其中rip就是x86_64的可编程计数器（PC）寄存器
// 它存储的值是下一条指令开头的内存地址
lea hello(%rip), %rsi // 将rip +（hello符号到这里的距离）这个地址存入rsi
mov $0xd, %rdx // 将0xd（"hello world!\n"字符串长度）存入rdx
syscall // 进行系统调用
ret // 返回
nop // 没有作用的空指令，用来padding
hello:
.ascii "hello world!\n" // 以ascii方式存储"hello world!\n"
```

汇编它：
```bash
cc -nostartfiles -nostdlib hello.S -o hello
```

执行它：
```
~/play % ./hello
hello world!
zsh: segmentation fault (core dumped)  ./hello
```

可以看到，我们成功的在裸linux上跑了hello world

它随后segfault了，因为我们让他返回了，但他返回地址是空的，所以cpu执行到NULL上就直接炸掉了，这是正常的

还要好久才能讲完这个hello，今天就到这里吧