---
title: 在D920S10上使用Windows 24H2+
date: 2026-10-12T20:31:20+0800
draft: false
tags:
  - Kunpeng 920
  - Hi1620
  - ARM
  - Windows
  - UEFI
toc: true
---

[undefshim](https://github.com/dixyes-digital-wastes/undefshim)在大肥鱼的努力下基本能用了，记一下

<!--more-->

## 背景

经过亿点点小小的研究，我最终确定了24H2+在920上无法启动的原因：

一个是很好修的MPAM问题：哇为早期固件的BL31未设置MPAMEN和trap位，导致MPAM相关的访问会触发异常，这个小改一下固件就行。

24H2开始Windows强制要求lrcpc指令即Load RCpc或者ldapr指令族（他们宣称要求的是ARMV8.2，但lrcpc是ARMV8.3强制要求的指令，8.2时还是optional）但TSV110恰好没有lrcpc。

```text
TSV110:

Flags: fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics fphp asimdhp cpuid asimdrdm jscvt fcma dcpop asimddp asimdfhm

BCM2712:

Flags: fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics fphp asimdhp cpuid asimdrdm lrcpc dcpop asimddp
```

这个指令集的被强制要求感觉上像是一种副作用：我猜可能是MSVC中做了lrcpc的支持与优化，然后用了宣称是V8.2的Cortex-A76发现lrcpc很好，提升了一点性能，然后就顺带在编译器中把它开启了。而Windows官方支持的ARM CPU，也就是高通那些，恰好也都有，自然非官方支持的这个真ARMV8.2就不兼容了。

## undefshim

之前这种级别的工作我是没有能力完成的，它稍微超出了一丢丢我的能力边界，但还好这年头便宜的LLM有了一些。我根大肥鱼商量了许久，终于商量出一个大概的思路：

1. 注册一个uefi driver
2. driver找到Windows中的异常处理例程，劫持它并模拟lrcpc

这个事对我来说缺的最多的是对ARM页表，异常处理机制，以及Windows运行机制的理解。在模仿EfiGuard的操作下，我们最终成功劫持了这部分逻辑并模拟lrcpc。

这个过程经历了最主要的问题是项目管理失控：大肥鱼知识比我多得多，但对于代码实现比较有自己的想法，而且每个对话甚至每个round都不同，导致代码光速屎山化，屎山化的代码带来了严重的注意力问题：它总是在已经犯过的错误上反复踩坑。

文档/上下文管理上也问题很大，一开始我只采用记账本的方式记录发现问题和架构，到后面账本长度上天，大肥鱼要么不肯看完这些账本，然后重复猜未知的坑；要么看了部分账本里错误的结论，然后踩已知的坑。

为了解决这个问题，我换了状态+账本的文档模式

- 状态文档只有状态，例如已知的确认的事实，项目预期的架构设计，未来工作计划等，不允许追加只允许变更，所有依据历史沿革全部只有到账本文件的路径和章节索引
- 账本：记录调试记录，代码修改记录，架构变更，文档变更记录等：只做现象记录不记结论

在这样的设计下，agent可以一次性读完状态文档，迅速理解项目状态，同时避免了错误结论的传播：结论总是在被修改到新的认知，历史沿革全部记录在账本中，确保了信息的完整性和可追溯性。

我重新开始了undefshim，放弃了之前将就用posix-uefi等项目，改为直接fork上修改的模式，提高了发挥的空间，也避免了一些上游的bug，这次我在一开始就重新要求大肥鱼设计了新的架构，并之后按照这个架构继续实现

调试上，大肥鱼解决了arch官方arm64版强制要用lrcpc的问题（没错 arch官方也做了同样的选择，因为这世界上大多数ARMV8.2实现确实都有lrcpc）：我们又搞了个linux模拟lrcpc的linux fork，让我能通过KVM qemu来进行调试，这比我当agent手替的真机调试效率高多了，大大加快了开发进度。

最终结果是undefshim已经可以在920上引导26100和28000，性能还是有所折扣的（中断占用很高），但起码能用。

## 下一步

不太指望Windows能允许非lrcpc机器，因为对于微软来说，TSV110可能不算ARMV8.2，未来的TSV121估计上ARMV9了，也不需要这个东西，现在能帮助我写A222就行了，不太有过多奢望
