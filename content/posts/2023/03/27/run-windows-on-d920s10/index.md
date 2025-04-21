---
title: D920S10上跑Windows
date: 2023-03-27T10:54:00+0800
draft: false
tags:
  - Windows
  - ARM64
  - D920S10
  - BIOS
  - UEFI
toc: true
---

TL；DR： https://github.com/dixyes/d920s10

<!--more-->

D920S10是哇为出品的一款搭载8核鲲鹏920的桌面主板，MATX板型

它标配两个PCIEx16插槽（x16+x4）， 两个Mkey m2，一个Akey m2，一个SFP一个GE电口，规格还是阔以的

官方宣传页上写的只支持udimm，然而文档里写了支持rdimm。

这么完美的arm64桌面主板，不得安排下Windows ARM64？

于是21年12月，我买了一块，并且配了个猛男粉色的机箱，然后我就傻了：串口并不能用，Windows也跑不起来，一番折腾无果，于是放弃思考，22年差不多这时候，将bios吹下来，换成了底座，寄给了Renegade Project的大佬们去艹了

[https://www.bilibili.com/video/BV1ij411G7t8/](https://www.bilibili.com/video/BV1ij411G7t8/)

终于大佬发现了串口能用，只是我的PL2302线有问题（坑货2302，我现在ttl线无脑选ch34x了），Windows引导是因为PCCT不知道哪里配炸开来。

最近这电脑回到了我这，开始研究怎么引导Windows ARM64，于是我重新连接上新买的ch340，居然真的能用，开始了新一阶段的折腾。

首先补上DBG2和SPCR表，这俩是给Windows串口调试提供串口信息的，根据大佬的描述，用系统串口也就是DSDT里的COM0，0x94080000就行了。

然后调查了一番PCCT，本来想修好它，结果发现这东西大约是OS和BMC一类的设备通信用的，D920S10哪有BMC...

结合DSDT里巨量垃圾设备描述，几乎可以肯定百敖是偷懒直接把D06的bios搬过来了，也没做啥精简直接就上了，PCCT也是这么搞歪了。

然后删掉PCCT跑起来，MEMORY_MANAGEMENT报错没了，变成了ACPI_BIOS_ERROR，打开windbg，进行我的第一次win32内核调试。
经过一番折腾，发现是DSDT的RTC0缺少了_HID或_ADR，于是我用SSDT加上

![Windows on 920](windows-on-920.jpg)

他 就 亮 了！
