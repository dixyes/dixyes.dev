---
title: Windows 11在没有TPM的机器上更新
date: 2025-01-24T16:15:00+0800
draft: false
tags:
  - Windows
  - 杂记
toc: true
---

今天想起来更新下Windows，结果发现之前的注册表都不顶用了，稍微研究了下解决了。（省流：resource hacker编辑hwreqchk.dll）

<!--more-->

## hwreqchk.dll

首先在sources目录搜索TPM，发现包含的文件是hwreqchk.dll

``` plain
$ dumpbin /exports hwreqchk.dll
Microsoft (R) COFF/PE Dumper Version 14.29.30154.0
Copyright (C) Microsoft Corporation.  All rights reserved.


Dump of file hwreqchk.dll

File Type: DLL

  Section contains the following exports for HwReqChk.dll

    00000000 characteristics
    F66E8205 time date stamp
        0.00 version
           1 ordinal base
           7 number of functions
           7 number of names

    ordinal hint RVA      name

          1    0 0000B3E0 CheckHardwareRequirement
          2    1 0000B640 EvaluateHardwareRequirement
          3    2 0000B730 EvaluateHardwareRequirementV2
          4    3 0000B830 GetHardwareRequirementSystemInfo
          5    4 0000B930 GetHardwareRequirementSystemInfoV3
          6    5 0000BA30 GetHardwareRequirements
          7    6 0000BB10 GetLatestHardwareRequirement

  Summary

        2000 .data
        3000 .pdata
       19000 .rdata
        1000 .reloc
        4000 .rsrc
       41000 .text
        1000 fothk

```

在网上搜索它，搜到了https://github.com/asdcorp/hwreqchk

试了下并不好使，看了下源码，VOID了返回结果，并没返回，EAX直接就回去了，这个用不了

于是clone下改一改

## 自己改hwreqchk.dll

在ms的[文档](https://learn.microsoft.com/en-us/windows/win32/api/_hwreqchk/)里发现了部分这个dll提供的函数

直接抄过来，这样就剩三个需要猜一猜形参的函数

### GetHardwareRequirementSystemInfoV3

这个最简单，和GetHardwareRequirementSystemInfo一样是一个参数，简单写了个摸了一下，发现结构体多了8个uint32，标记一下

```C
// guessed from return
typedef struct HWREQCHK_DEVICE_HARDWARE_SYSINFO_V3
{
    // ...

    // guessed from here
    BOOL PopCntInstructionSupport; // 0x454
    BOOL SSE4_2ProcessorSupport; // 0x458
    BOOL NXProcessorSupport2; // 0x45c
    BOOL CompareExchange128Support2; // 0x460
    BOOL LahfSahfSupport2; // 0x464
    BOOL PrefetchWSupport2; // 0x468
    BOOL SecureBootEnabled; // 0x46c
    DWORD ARMv82LRCPCProcessorSupport; // 0x470
} HWREQCHK_DEVICE_HARDWARE_SYSINFO_V3;

```

欺骗一下

```C
HRESULT WINAPI GetHardwareRequirementSystemInfoV3(
    HWREQCHK_DEVICE_HARDWARE_SYSINFO_V3 *deviceHardwareSystemInfo)
{
    HRESULT hr = origGetHardwareRequirementSystemInfoV3(deviceHardwareSystemInfo);
    deviceHardwareSystemInfo->SecureBootCapable = TRUE;
    deviceHardwareSystemInfo->TpmVersion = 2;
    deviceHardwareSystemInfo->SecureBootEnabled = TRUE;
    return hr;
}
```

### EvaluateHardwareRequirementV2

比起EvaluateHardwareRequirement多了两个参数，不知道啥意义，猜一下：

```C
HRESULT WINAPI EvaluateHardwareRequirementV2(
    const HWREQCHK_DEVICE_HARDWARE_REQUIREMENT *hardwareRequirement,
    BOOL *evaluationResult,
    HWREQCHK_DEVICE_HARDWARE_EVALUATION **constraintsEvaluated,
    ULONG *constraintEvaluationCount,
    EvaluateHardwareRequirementV2Unknown *unknownArg1,
    ULONG countUnknownArg1);
```

### CheckHardwareRequirement

完全没有公开信息，由于我不会逆向，准备跑一下看看setup.exe传了什么参数

```C
HRESULT WINAPI CheckHardwareRequirement(
    intptr_t arg1,
    intptr_t arg2,
    intptr_t arg3,
    intptr_t arg4)
{
    fprintf(logFile, "CheckHardwareRequirement(%p, %p, %p, %p)", (void*)arg1, (void*)arg2, (void*)arg3, (void*)arg4);
    HRESULT hr = origCheckHardwareRequirement(arg1, arg2, arg3, arg4);
    fprintf(logFile, " -> %d\n", hr);
    return hr;
}
```

## resource hacker

于是编译了放进sources目录，运行setup，报错：0x8什么玩意

看日志:

```text
GetLatestHardwareRequirement(2, 000000016577E160) -> -2147023084
```

`-2147023084` = `0x80070714` ERROR_RESOURCE_DATA_NOT_FOUND 居然缺资源。。。

于是resource hacker打开原版dll，发现有个JSON把规则写里面了。。。

![删掉这些][resource_hacker.png]

删掉其中的TPM TPM_REQUIRED secure boot啥的(只删最后的规则就行)，再启动安装程序就正常了
