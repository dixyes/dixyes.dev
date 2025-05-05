---
title: A222开发1
date: 2025-05-05T23:55:33+0800
draft: false
tags:
  - A222
  - Windows
toc: true
---

今天实现了A222的固件版本读取（好艰难啊

<!--more-->

## A222

很早以前就开始了A222的开发，当时列了个OKR：

- Objective: 实现A222 Windows驱动
- KR1: 实现A222固件版本读取
- KR2: 实现环形缓冲区
- KR3: 实现MAC
- KR4: 实现上层

然后一眨眼好几年过去了，虽然之前实际上受制于Windows AA64沙雕bug一堆根本妹法搞，23年开始才勉强能部署驱动

## 历史

为了实现第一个KR，得先了解Windows驱动的基本结构，23年基本就只做了这些，看了亿点点文档，新建了两个KMDF项目，然后没有下文

24年终于算是能把远程部署的环境搭出来了，驱动开发才算踏上正轨

## 坑和进展

今年重新整理开发环境，由于原先的环境比较乱，旧版本的Windows WDK的Target Setup有点抽风，部署奇奇怪怪的老是不成功，于是重装了24H2，结果启动不了，直接陷到EL3报错。。。据群友说是MS为了兼容高通整出的奇怪活，24H2在a72上跑不了了。我寻思TSV110也不是cortex啊，按理来说很像neoverse-n1，但neoverse-n1的qemu他就能跑。。。也没别的法子就装了23h2。MS之后要是不修，D920S10就要凉啦

24年的代码今年拿来理了一下，重新参照[RtEthSample](https://github.com/microsoft/NetAdapter-Cx-Driver-Samples/tree/release_2004/RtEthSample)和[if_re-win](https://github.com/coolstar/if_re-win)整理了一下，结果不知道为啥报错不加载，写了个`((void(*)())0)()`都不蓝屏。

听完了星铁演唱会心念通达，猜NetAdapterCx的版本有限制，一查果然是。。。而我顺手更新到2.5，24H2才支持它，MS疑似历史包袱有点少了，居然不向下兼容（

总归重新降回2.3（最小22H2），继续开发

抄了一大坨东西过来，回调全是简单粗暴空函数，先观察生命周期。

```C
EvtDevicePrepareHardware(
    _In_ WDFDEVICE device,
    _In_ WDFCMRESLIST resourcesRaw,
    _In_ WDFCMRESLIST resourcesTranslated
)
```

发现了MS的抽象活，这个回调它不告诉我mapped的内存对应的是哪个BAR，官方驱动Demo里直接写死了用第1个MemoryResource。。。一般来说我不太信这种纯靠约定的骚操作，但MS就是这样写的

```C
    for (ULONG i = 0; i < rawCount; i++)
    {
        // 这个PCM_PARTIAL_RESOURCE_DESCRIPTOR里只有Memory的Length和Start，没说对应的啥资源
        PCM_PARTIAL_RESOURCE_DESCRIPTOR rawDescriptor = WdfCmResourceListGetDescriptor(resourcesRaw, i);
        PCM_PARTIAL_RESOURCE_DESCRIPTOR translatedDescriptor = WdfCmResourceListGetDescriptor(resourcesTranslated, i);

        if (rawDescriptor->Type == CmResourceTypeMemory)
        {
            // RTL8168D has 2 memory IO regions, first region is MAC regs, second region is MSI-X
            if (memRegCnt == 0) // 官方demo直接写死了。。。
            {
                NT_ASSERT(rawDescriptor->u.Memory.Length >= sizeof(RT_MAC));

                memAddressTranslated = translatedDescriptor->u.Memory.Start;
                hasMemoryResource = true;
            }

            memRegCnt++;
        }
    }
```

算了我也这么抄来，将就用吧。我的BAR是第二个MemoryResource

之后大概了解了一下后开启DMA，实现个playground函数，结果它就是不行，正当我以为寄了又可以光明正大项目休眠两年的时候，突然意识到写registry的宏是copilot写的，于是拿来一看

```C
#define A222WriteReg(adapter, offset, value) \
    WRITE_REGISTER_ULONG((PULONG)((adapter)->ConfRegBase) + (offset), (value))

#define A222ReadReg(adapter, offset) \
    READ_REGISTER_ULONG((PULONG)((adapter)->ConfRegBase) + (offset))
```

![你有病吧](niyoubingba.webp)

谁家好人offset用ULONG指针啊

改完之后它就成了，今天又是被LLM害了的一天

![Version Read](version_read.jpg)

成了，洗洗睡，改天继续研究怎么写ringbuffer
