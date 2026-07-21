---
title: 鲲鹏920的DDRC
date: 2026-07-21T21:59:44+0800
draft: false
tags:
  - Kunpeng 920
  - Hi1620
  - ARM
  - ACPI
toc: true
---

最近在研究能不能引导新版Linux和Windows，发现了用tablesfix后Linux DDRC还是会卡死，简单调了下，记录下

<!--more-->

## 卡死

卡在读取DDRC的MMIO的任意地址时，通过内核printk大法发现的，依次提前返回打日志，发现第一个readl就炸了。

## 实验

已知ACPI里四个DDRC分别在0x94d20000 0x94d30000 0x94d40000 0x94d50000，几个版本的固件和几台机器都是一样

在UEFI Shell里读取VERSION的MMIO地址

```
mm 0x94d20710
```

发现会卡死，但

```
mm 0x94d30710
```

不会卡死

通过查看smbios type 17发现，我的一条内存插在CHANNEL 1上

于是做了以下实验：

对于D920S10 四个槽从CPU最近到最远分别是DDR4_4 DDR4_2 DDR4_3 DDR4_1

| 设备 | 内存组态 | 现象 |
| --- | --- | --- |
| D920S10 | 单条插在DDR4_1，显示位于CHANNEL 0 | 读DDRC0 DDRC1没事，读DDRC2 DDRC3卡死 |
| D920S10 | 单条插在DDR4_2，显示位于CHANNEL 0 | 读DDRC1没事，读DDRC0 DDRC2 DDRC3卡死 |
| D920S10 | 单条插在其他插槽 | 不亮 |
| D920S10 | 两条分别插DDR4_1 DDR4_2，显示两条分别位于CHANNEL 0，1| 读DDRC0 DDRC1没事，读DDRC2 DDRC3卡死 |
| W510 | 两条全插，显示两条分别位于CHANNEL 1，3| 读DDRC0 DDRC1没事，读DDRC2 DDRC3卡死 |
| W510 | 只插靠近主板那条，显示位于CHANNEL 3| 读DDRC0 DDRC1没事，读DDRC2 DDRC3卡死 |
| W510 | 只插远离主板那条，显示位于CHANNEL 1| 读DDRC1没事，读DDRC0 DDRC2 DDRC3卡死 |
| TK630（不同固件的D920S10） | 和D920S10一致 | 和D920S10一致 |

## 猜测

只插CHANNEL 1的时候多少有点说法，要不要把这个逻辑实现到tablesfix里？
