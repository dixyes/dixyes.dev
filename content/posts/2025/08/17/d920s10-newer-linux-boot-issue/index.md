---
title: D920S10新版Linux启动问题
date: 2025-08-17T14:31:42+0800
draft: false
tags:
  - D920S10
  - Linux
  - ARM
  - UEFI
toc: true
---

主线Linux启动会炸到EL3，记录下问题啥情况

<!--more-->

## 问题

我在Windows驱动里创建了A222TQP，但是硬件行为很奇怪，应该还是少初始化了什么东西，于是决定拿Linux测一下，加点printk看看啥个情况

结果一启动直接炸到EL3，跟Windows 24H2启动的症状差不多，于是开始研究一下

![EL3 boom](EL3_boom.png)

## 调查

我先后换了多个发行版的内核，和群友的内核，都启动不了。earlyprintk都没打出来，应该是一开始的初始化就炸了，群大佬建议搁arch/arm64/kernel/head.S整一点写串口来看看炸哪了，但我太懒了，懒得去翻PL011文档就没搞，直接开始二分。

我发现能用的最后已知版本是6.12；6.13开始就炸了。于是开始bisect

用的linux-stable的linux-rolling-stable分支

经过13次紧张刺激bisect，终于定位到第一个有问题的提交：

![第一个坏提交](first_bad_commit.png)

相关有问题的代码：

```
.macro __init_el2_mpam
	/* Memory Partitioning And Monitoring: disable EL2 traps */
	mrs	x1, id_aa64pfr0_el1
	ubfx	x0, x1, #ID_AA64PFR0_EL1_MPAM_SHIFT, #4
	cbz	x0, .Lskip_mpam_\@		// skip if no MPAM
	msr_s	SYS_MPAM2_EL2, xzr		// use the default partition
						// and disable lower traps
	mrs_s	x0, SYS_MPAMIDR_EL1
	tbz	x0, #MPAMIDR_EL1_HAS_HCR_SHIFT, .Lskip_mpam_\@	// skip if no MPAMHCR reg
	msr_s	SYS_MPAMHCR_EL2, xzr		// clear TRAP_MPAMIDR_EL1 -> EL2
.Lskip_mpam_\@:
.endm
```

linux先读了MSR id_aa64pfr0_el1，固件返回有MPAM支持，然后Linux配置了一下MAPM，EL3就炸了

稍微深入调查了一下，我用的这个机器的固件的EL3固件（疑似是BL1部分？不确定）的加载基址在`0x3fc8adc0`，没有ASLR，每次启动都一样

![出问题的ESR](ESR.png)

然后在`msr SYS_MPAM2_EL2`的时候，EL3 MSR的时候触发了一个异常，EL3的异常处理处理这个异常时又触发异常，就死循环卡死了

介于我不懂逆向，调查就只能到这为止了

## 解决方法

### 去掉MPAM初始化

最简单的方法（也是现在我用的办法），把导致这个问题的MPAM FGT2和GCS初始化逻辑去掉就行，但这个办法过于粗暴，而且要修改操作系统。如果Windows 24h2也是同款问题，这法子就比较痛苦，还要被数字签名拷打

### 劫持MSR

已知EL2出问题的地方是MSR，那么可以劫持MSR来避免炸EL3，具体有俩手段

#### 劫持MRS

想办法`mrs id_aa64pfr0_el1`的时候把MPAM位掩掉

首先我想到的是简单的去写一下这个寄存器，看看这固件有没给我留一点后门：

```C
#include <uefi.h>

int main(int argc, char **argv)
{
    register uint64_t ret;

    printf("mrs r, id_aa64pfr0_el1\n");
    asm volatile("mrs %0, id_aa64pfr0_el1" : "=r"(ret)); // 01 04 38 d5

    printf("id_aa64pfr0_el1: 0x%016x\n", ret);

    // mask bit 43:40
    ret &= ~(15ULL << 40);
    printf("msr id_aa64pfr0_el1, r as 0x%016x\n", ret);
    asm volatile("msr s3_0_c0_c4_0, %0" : : "r"(ret));

    printf("mrs r, id_aa64pfr0_el1\n");
    asm volatile("mrs %0, id_aa64pfr0_el1" : "=r"(ret));

    printf("id_aa64pfr0_el1: 0x%016x\n", ret);

    return 0;
}
```

一跑，同步异常，没有给我留点后门，那这个方法就搞不了了

#### 修改EL3固件

我现在已经能通过EFI协议读写SPI flash。另根据群友说，SD100的固件不会炸MPAM，合理怀疑SD100的固件更新一些，MPAM实现修复了这个问题。

因此或许可以替换EL3固件来修复这个问题。

修复有俩方法，内存里修改和改SPI flash

我还没有尝试直接内存修改固件，但在EL2改EL3固件多半是不行，只能靠SPI刷写patch一下。

而这个办法的真正问题是，群友说要发，结果咕咕咕了两周了，我觉得放弃这个想法先继续A222的研究，等哪天他们想起来再说吧。

### 嵌套虚拟化

群友提出来的骚操作

虽然这个想法很扯淡，但可能是能搞定Windows的最终解决方案，做一个假的hypervisor，trap掉内核的MSR，就能避免炸EL3的问题，但这个对于现在的我来说 我还没啥能力搞这个。

## 结论

新版Linux在D920S10上启动会炸EL3，原因是固件的一些设施实现有问题，介于这东西没有客服，全靠自己折腾，没辙只能先用最简单的手段，阉割掉操作系统的MPAM等支持
