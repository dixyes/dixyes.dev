---
title: RH2288v3 PCIE拆分配置
date: 2025-02-05T18:33:00+0800
draft: false
tags:
  - RH2288v3
  - PCIe
  - UEFI
  - BIOS
toc: true
---

试图使用RH2288v3的PCI直接接nvme盘，改了下BIOS配置（大约是爆出来高级菜单了）

<!--more-->

如果你只是想改差分，直接看3（**很危险，变砖后果自负**)

## 1. 获取IFR

先得提取bios，用Intel FPT就行，Haswell EP，Broadwell EP对应的版本是9.1

```cmd
FS1:> fpt.efi -bios -d dump.bin
```

使用[UEFITool](https://github.com/LongSoft/UEFITool/releases)打开dump

以Unicode `$ifr` 搜索，发现IFR在SetupUtility里，使用[IFR Extractor](https://github.com/LongSoft/IFRExtractor-RS/releases)提取

搜索`x8x8`，在Section_PE32_image_SetupUtility_SetupUtility_body.efi.1.0.en-US.ifr.txt里发现相关配置，其对应的GrayOutIf条件为

```text
0x56049: 		GrayOutIf  { 19 82 }
0x5604B: 			EqIdVal QuestionId: 0x42, Value: 0x0 { 12 86 42 00 00 00 }
0x56051: 				EqIdVal QuestionId: 0xA5B, Value: 0x2 { 12 06 5B 0A 02 00 }
0x56057: 				EqIdVal QuestionId: 0xA5A, Value: 0x1 { 12 06 5A 0A 01 00 }
0x5605D: 				And  { 15 02 }
0x5605F: 				Or  { 16 02 }
0x56061: 			End  { 29 02 }
```

即`问题0x42 == 0`或者`(问题0xA5B == 2 且 问题0xA5A == 1)`时GrayOut

那么将0x42改为非零是最简单的方法

搜索发现0x42是"Dynamic Form"，0x42本身的隐藏条件是0x42为0或1，也就是说怎么都隐藏了，意味不明

它的存储在store 0x1234 "SystemConfig" A04A27F4-DF00-4D42-B552-39511302113D，偏移0xe4，8bit（1byte）大小
，默认0

## 2. PCI拓扑

根据哇为/超聚变官方文档，PCI拓扑如下（未核验，请自行查证）

| slot | cpu | port |
| - | - | - |
| Slot4 | CPU1 | Port3A |
| Slot5 | CPU1 | Port3C |
| Slot6 | CPU2 | Port1A |
| Slot7 | CPU2 | Port2A |
| Slot8 | CPU2 | Port2C |
| raid | CPU1 | Port1A |
| eth | CPU1 | Port2A |

IIO是CPU的PCI控制器，IIO 1对应CPU1，IIO 2对应CPU2

Port1对应IOU2，Port2对应IOU0，Port3对应IOU1

## 3. 修改

使用[setup_var.efi](https://github.com/datasone/setup_var.efi/releases)修改存储名为SystemConfig的存储的0xe4

发现了问题，这个BIOS并没有名为SystemConfig的存储，其他几个存储名称也找不到，原理不明。

但存在相同GUID的`Setup`存储，通过setup_var查验几个已知默认值的选项，发现`Setup`存储内的数据与SystemConfig匹配。

于是修改Setup存储的0xe4（此步为高风险操作，请确认你理解了这篇文章写的什么，要么炸了也没救）：

```cmd
FS1:> setup_var.efi Setup:0xe4=1
```

修改后重启进入bios界面，发现IIO配置里出现了IOU拆分选项，根据步骤2中的信息进行修改

## 4. 问题

我们修改完成后发现，拆分配置生效，但是PCI根口降速了，下面的所有设备也降速了，原理不明，待观察研究。
