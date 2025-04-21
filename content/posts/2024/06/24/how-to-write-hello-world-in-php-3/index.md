---
title: 如何用PHP写一个hello world - 3
date: 2024-06-24T11:22:00+0800
draft: false
tags:
  - PHP
  - C
  - FFI
  - 汇编
toc: true
---

过去一年了，我终于要写这个~~最后一篇~~（划掉，看来还可以水一篇）。我们已经实现了一个可以被PHP调用的简单hello world，那么最后该用PHP FFI调用它了。
<!--more-->

## 0x00 FFI

首先大致了解一下FFI：FFI foreign function interface，外部函数接口，是一种从一种语言调用其他语言（或者说原生）函数的方法。在linux上由[libffi](https://github.com/libffi/libffi)实现（虽然其他系统大概上也是libffi干这个活）。

它工作其实就很简单，告诉libffi怎么调用一个原生函数，然后libffi找到它，并按照要求调用它。

例如这个C函数签名：

```C
void zif_hacky_hello(void *ed, zval* ret);
```

libffi根据它调用[dlsym(3)](https://man7.org/linux/man-pages/man3/dlsym.3.html)获取`zif_hacky_hello`的入口点地址。根据它的返回值`void`和参数类型`void *, void *`，libffi准备对应的调用方法。例如在linux上的x86_64 sysvabi，将传入的参数的地址分别放在rdi，rsi中，然后直接call这个函数的地址就行；如果是x86就压栈，有浮点数就用xmm ymm寄存器传参啥的。这里就不展开叙述了

ffi是可以设置回调的，如果我向ffi声明了下面的东西

```C
typedef int (*some_callback_t)(int a);
int some_func(some_callback_t callback);
```

那么ffi可以将“本地的函数”作为`callback`参数传入`some_func`。实现上，大致是libffi会准备一个特殊的函数（`trampoline`跳床），这个函数根据被调用时的上下文解析传入的参数，并将它喂给本地的目标函数，并将本地的目标函数的返回返回给调用它的外部函数。

除此之外ffi可以读取外部的变量：（毕竟所谓的函数只是一个地址，这个地址上是数据当然也可以读取）

```C
int errno;
```

## 0x10 PHP中使用FFI

PHP中的FFI是由Dmitry Stogov大佬实现的，作为扩展包含在7.4+源码中。构建php时使用`--with-ffi`来开启。要使用FFI，PHP必须是`shared`动态链接的，这是因为GLIBC的抽象设计，静态链接用不了很合理，但`static-pie`构建中dlso相关设施也不给你用（uclibc bionic musl啥的也继承了这点）

PHP中的FFI设计是面向对象的：

```PHP
final class FFI {
    /* Constants */
    public const int __BIGGEST_ALIGNMENT__;
    /* Methods */
    public static addr(FFI\CData &$ptr): FFI\CData
    public static alignof(FFI\CData|FFI\CType &$ptr): int
    public static arrayType(FFI\CType $type, array $dimensions): FFI\CType
    public cast(FFI\CType|string $type, FFI\CData|int|float|bool|null &$ptr): ?FFI\CData
    public static cdef(string $code = "", ?string $lib = null): FFI
    public static free(FFI\CData &$ptr): void
    public static isNull(FFI\CData &$ptr): bool
    public static load(string $filename): ?FFI
    public static memcmp(string|FFI\CData &$ptr1, string|FFI\CData &$ptr2, int $size): int
    public static memcpy(FFI\CData &$to, FFI\CData|string &$from, int $size): void
    public static memset(FFI\CData &$ptr, int $value, int $size): void
    public new(FFI\CType|string $type, bool $owned = true, bool $persistent = false): ?FFI\CData
    public static scope(string $name): FFI
    public static sizeof(FFI\CData|FFI\CType &$ptr): int
    public static string(FFI\CData &$ptr, ?int $size = null): string
    public type(string $type): ?FFI\CType
    public static typeof(FFI\CData &$ptr): FFI\CType
}
```

我们来写个上面提到的FFI的常见功能的demo：

调用一个函数：

```PHP
<?php
// 先告诉ffi动态库libc.so.6有这么个printf(3)函数
// 当然你也可也把第二个参数去掉，让libffi在整个flat namespace里找
$ffi = \FFI::cdef(<<<'C'
int printf(const char *format, ...);
C, 'libc.so.6');

// 然后调用它，PHP的ffi会自动把php字符串转化成C字符串，然后喂给C函数printf
$ret = $ffi->printf("hello\n");
var_dump($ret);
```

结果：
```text
hello
int(6)
```

设置回调，我们用[qsort(3)](https://man7.org/linux/man-pages/man3/qsort.3.html)举个例子：

```PHP
<?php
$ffi = \FFI::cdef(<<<'C'
void qsort(void *base, size_t nel, size_t width, int (*compar)(const void *, const void *));
C);

// php的数组
$phpArray = [1,2,5,2,3,7,1,2,7];
// 将这个数组放到一个buffer里
$buf = $ffi->new("uint32_t[" . count($phpArray) . "]");
foreach ($phpArray as $i => $item) {
    $buf[$i] =  $item;
}
var_dump($buf);

// 这是我们的回调函数，由于上面形参声明的是const void *, 所以参数会以\FFI\CData传入
function compare(\FFI\CData $a,\FFI\CData $b): int
{
    global $ffi;
    $intPA = $ffi->cast("uint32_t *", $a);
    $intA = $intPA[0];
    $intPB = $ffi->cast("uint32_t *", $b);
    $intB = $intPB[0];

    printf("compare %d vs %d: %d\n", $intA, $intB, $intA - $intB);
    return $intA - $intB;
}

$ffi->qsort(
    $buf,
    count($phpArray),
    4 /* 我们上面用的L，机器字节序uint32，所以这里用4 */,
    "compare"
);

// 排序过后的数组
var_dump($buf);
```

结果

```text
object(FFI\CData:uint32_t[9])#2 (9) {
  [0]=>
  int(1)
  [1]=>
  int(2)
  [2]=>
  int(5)
  [3]=>
  int(2)
  [4]=>
  int(3)
  [5]=>
  int(7)
  [6]=>
  int(1)
  [7]=>
  int(2)
  [8]=>
  int(7)
}
compare 1 vs 2: -1
compare 5 vs 2: 3
compare 1 vs 2: -1
compare 2 vs 2: 0
compare 3 vs 7: -4
compare 2 vs 7: -5
compare 1 vs 2: -1
compare 3 vs 1: 2
compare 3 vs 2: 1
compare 3 vs 7: -4
compare 7 vs 7: 0
compare 1 vs 1: 0
compare 2 vs 1: 1
compare 2 vs 2: 0
compare 2 vs 2: 0
compare 5 vs 2: 3
compare 5 vs 3: 2
compare 5 vs 7: -2
object(FFI\CData:uint32_t[9])#2 (9) {
  [0]=>
  int(1)
  [1]=>
  int(1)
  [2]=>
  int(2)
  [3]=>
  int(2)
  [4]=>
  int(2)
  [5]=>
  int(3)
  [6]=>
  int(5)
  [7]=>
  int(7)
  [8]=>
  int(7)
}
```

获取/修改一个变量：

```PHP
<?php
$ffi = \FFI::cdef(<<<'C'
int printf(const char *format, ...);
int errno;
ssize_t read(int fd, void *buf, size_t count);
C);

$ffi->printf("errno is %d\n", $ffi->errno);
$ffi->errno = 22 /* EINVAL */;
$ffi->printf("errno now is %d\n", $ffi->errno);

// 这个fd还不存在，根据man，会返回-1，设置errno为EBADF
$ffi->read(12345678, null, 0);
// 会显示9 EBADF
$ffi->printf("after read, errno is %d\n", $ffi->errno);

// printf（的地址）当然也是一个值，由于ASLR，这个值是随机的
$ffi->printf("printf is %p\n", $ffi->printf);
```

结果：

```text
errno is 0
errno now is 22
after read, errno is 9
printf is 0x72da9026bc40
```

好力，ffi大概就是这些了，离调用我们的PHP hello world只差调用了，改天再写吧
