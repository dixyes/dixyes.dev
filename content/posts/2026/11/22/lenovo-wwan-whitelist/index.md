---
title: 联想WWAN的白名单
date: 2026-11-22T19:55:53+0800
draft: false
tags:
  - AMD
  - PSB
  - Lenovo
  - WWAN
  - 21RV
  - P14s
toc: true
---

折腾了下P14s的WWAN模块白名单，未能成功，记录一下

<!--more-->

## 设备

我买了台P14s Gen 6 AMD，型号为21RV，这东西有两条SODIMM，可以随便升级内存，加上CPU也还行，就当之后的工作电脑了，但我想装个WWAN模块，这样就不用单独开热点了。

加了NFC，读卡器（我可能会开发PKI程序，有个读卡器很合适）之后才发现这玩意天线和sim卡托还挺难买，我随便买的Gen 4的天线居然还不通用，在[联想香港官网](https://pcsupport.lenovo.com/hk/zh/products/laptops-and-netbooks/thinkpad-p-series-laptops/thinkpad-p14s-gen-6-type-21rv-21rw/21rv/parts/display/compatible)搜了下需要的型号是5A30Z88262，淘宝一搜价格好家伙要100多，卡托也要三四十（顺便吐槽，联想也够黑的，一个SIM卡托都要488HKD），买了，顺便买了个联想的FM350-GL（联发科）。

装完天线之后发现，woc居然后盖还分WWAN/WLAN两种版本，WLAN版本少两个WWAN天线屏蔽铜箔，和多了一些塑料架子挡住了天线，需要削一下才能合上盖，但我偷懒了，于是又60块钱买了WWAN版的（型号5CB1P50410）

我怀疑联想这些备件号前5位（比如5A30Z/5CB1P）是型号，后面的是批号，因为我买的这些能用的后三位不太一样。

然后试试WWAN模块：我手头有SIM8262E-M2（高通X62），RM500U-CNV（紫光展锐）以及新买的FM350-GL，结果您猜怎么着，全都不在白名单。。。

## 大肥鱼启动

一边让大肥鱼看着，我又买了个联想ES的RM520，反正我一堆乱七八糟的模块再多一个也无所谓，总要有个确定能用的。

下面的发现让大肥鱼自己来写，我都懒得理解它说的东西了：

### 先看镜像结构

镜像有两份 DXE 固件卷（FV）：正常启动使用的主 DXE（0x3525000），和自愈使用的备份 DXE（0x1BF2000）。

PEI 的 `SelfHealingDetectCorruptionPei` 用 `$HASHTBL` 中的 SHA-256 校验 DXE、PEI、FV_IMAGE、AMD 固件区四个区域。`$HASHTBL` 也有主表和备份表。

0x2FF9000 附近有 5 条 ECDSA P-256 签名记录。每条记录签一段连续区域。page2 签 0x3F0C000 至 0x4000000 的尾部 FV 组。主 `$HASHTBL` 在这个组内。

主 DXE 不在 page2 内。主 `$HASHTBL` 在 page2 内。

### 1802 和保护层

1802 错误来自 DXE 里的 `LenovoWmaPciDxe` 和 `LenovoWmaPolicyDxe`。

`LenovoWmaPolicyDxe` 从静态白名单表选择条目。平台配置数据库（PCD）0x2E9 选择使用哪张表。PCD 0x2F7 为真时，策略直接放行。

修改主 DXE 后，必须修改主哈希表。修改主哈希表会破坏 page2 签名。AMD 平台安全启动（PSB）只验证 BIOS BIN 和 AMD 组件，不覆盖主 DXE。

### 可写但不可执行的 FV

0x34B6000 有一个 32 KiB 的 SystemFirmwareDescriptor FV。它不在 `$HASHTBL` 的覆盖区，也不在已知 ECDSA 页内。

写入 27 字节标记后，系统正常启动，标记保留。看起来可以在 FV 内注入代码。

FV 内有 PEI 模块（PEIM）。我们做实验：改 PEIM 为延时、设 RTC、换开机 logo、改成死循环。这些实验都没有可观察效果。

最后把 PEIM 的 depex 改成 TRUE，系统仍正常启动。结论：正常启动不 dispatch 这个 FV 的 PEIM。

反汇编 `SystemFirmwareDescriptorFvLoader` 后看到：它只调用 `InstallPpi` 安装 FvInfo，告诉 PEI Core “这里有 FV”。loader 自己的 PEI depex 依赖一个 PPI。该 PPI 在整个镜像、解压后的 PEI FV 和已提取 PEIM 中都找不到。

正常启动不运行 loader。PEI Core 没有把 FV 注册进 dispatch 列表。这个 FV 可写，但不可执行。注入路线不可行。

### 一字节探针

下一步只剩一个办法：改主 DXE 的白名单分支，同时改主 `$HASHTBL` 里对应的 SHA-256。备份 DXE 和备份表不改。

这个办法只有一处不确定：启动时是否强制校验 page2。

做单字节探针：改 tail FV1 的 0x3F0D000 一个空闲字节。该字节在 page2 内，不在 `$HASHTBL` 的覆盖区。

上电后屏幕出现 Esc/F1/F4 闪灯，系统进入自恢复。结论：page2 在启动时强制校验。

这个结果说明：改主哈希表会触发同样的自恢复。BIOS 签名区修改路线不可行。用备份整片恢复芯片。

### EC 与 P-256

BIOS 走不通后，分析嵌入式控制器（EC）固件。16 MiB EC dump 的 payload 是 Nuvoton NPCX9 的 ARM Thumb 代码。它含 P-256 库，能解析 LADDR 表，能读主 SPI。

最初判断 EC 是 page2 校验者。继续分析后，这个判断不成立。

EC 应用没有“先算 SHA-256(0x3F0C000 至 0x4000000)，再做 P-256 验签”的路径。EC 应用没有 page2 记录页的验签实现。LADDR 消费者只读、写、比较、搬备份。

唯一的 ECDSA 验签入口在 0x10089F0C 附近，属于 `responderrequester` 安全会话。`fcn.1008FD00` 是会话状态机，不是验签核心。

EC boot ROM 只检查 NPCX 头 CRC。`sig_header` 和 `sig_fw_image` 按 ECST 算法复核一致。容器 0x60 的签名和 0x4F100 的摘要在 NPCX 映像外。EC 应用不引用它们。

容器签名是否在第一阶段启动时校验，仍不确定。EC dump 偏移 0 的 `{0x1000,0xA0000}` 表说明存在 dump 外的第一阶段代码。

密码学捷径也排除。5 条记录是 ECDSA P-256 对 SHA-256 摘要的签名，属于 prehash。SHA-256 碰撞和前像不可行。5 条记录的 r 值不同，没有 nonce 重用。EC 应用没有 page2 验签实现，也没有索引混淆和范围检查缺失两类缺陷。

### 结论

page2 校验者不在主 BIOS 的 x86 代码里，也不在 EC 应用 payload 里。它可能在 NPCX 内部第一阶段 ROM 或 flash，也可能在 PSP。

继续定位需要逻辑分析仪抓 SPI/eSPI，或 NPCX 调试接口读内部 flash 和 ROM。即使定位，如果校验在 Mask ROM 或 PSP 内，仍不可修改。

BIOS 和 EC 软件修改路线基本不可行：BIOS 签名区无私钥，未签名 FV 不执行，EC 应用不碰 page2，哈希碰撞不可行。

剩余方向超出固件代码修改。可选方向有四个：SPI 总线仿真、电源时序旁路、外部 USB 或 USB4 转接、部分模块的 USB ID 伪装。

## JBIOS1/UE4

虽然白名单靠改BIOS暂且搞不成，但JBIOS1的定义大概清楚了:

JBIOS1是一个1.27的2x4pin排针接口，可以用线转成8pin 2.54杜邦线。我转成杜邦线挂LA看了下，上面跑的是50Mbps的四线SPI协议，芯片ID：

```text
ID(9F): 204420
ID(90): 2019
ID(AB): 19
ID(15): 2020
```

应当是XMC的XM25RU512（不同批次可能用的不一样 我这块主板是这个）

JBIOS1的针脚标号是zig-zag排列的，和SOIC-8的逆时针不一样，连线时要注意。（1.27转2.54 杜邦线也要注意具体的连接方式，我买到的这个线的排序也跟这个zig-zag的线序一致）

我注意到 1，2，3，6，7，8六个脚的线序与SOIC-8的逆时针排序的六个脚完全相同，猜测4，5号脚也是如此，但未验证（标记了？），使用时要注意。

![JBIOS1](jbios1.webp)

UE4是XMC的XM25QU128C，1.8V SPI flash，应该是EC的固件。

![UE4](ue4.webp)

## 21RV的LenovoWmaPolicyDxe支持的模块

根据大肥鱼的逆向：

| 类型 | 主 ID | 子系统 ID | 对应模块 |
|---|---|---|---|
| PCIe | `1EAC:1007` | `1EAC:100B` | Quectel RM520N-GL（Lenovo 变体） |
| PCIe | `1EAC:1007` | `1EAC:100C` | Quectel RM520N-GL-T |
| PCIe | `1EAC:100D` | `1EAC:5001` | Quectel EM160R-GL |
| PCIe | `17CB:0308` | `17CB:0308` | Qualcomm SDX61/62/65 平台模块（如 Foxconn） |
| PCIe | `17CB:0304` | `17CB:0307` | Qualcomm SDX24 系列 4G |
| USB | `2C7C:6008` | — | Quectel EM061K-GL |
| USB | `05C6:9008` | — | Qualcomm EDL 下载模式（正常不可用） |

## 未来

目前我能想到最靠谱的用任意型号模块的方法是：

1. 把WWAN EN的引脚和主板断开连接（贴个fpc上去？或者直接画一个3042转3052的小板子做这个）
2. 做一个小延时电路，延时半分钟左右再开启EN引脚，或者干脆接到一个可用的GPIO上，由操作系统开启

这样就实现了热插入模块的方法，白名单就管不到了，但我先懒得搞了，毕竟我有能用的，啥时候有兴趣了研究一下画个板子啥的。

SPI模拟器+TOCTOU是比较终极的BIOS入侵手段了，等啥时候这个机器不再用了我再考虑做个SPI模拟器来搞这个

对于部分模块，比如移远的一些，可以通过AT指令直接换usbid，换成支持的那些就行，倒也能用，就是驱动上需要费点心思。
