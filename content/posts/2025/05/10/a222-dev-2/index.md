---
title: A222开发2
date: 2025-05-10T19:12:07+0800
draft: false
tags:
  - A222
  - Windows
toc: true
---

记一下Linux源码阅读和Windows学习，防止之后忘了

<!--more-->

## HNS3

## PF和VF

应该不会有错，PF是Physical Function，VF是Virtual Function

### CQP

[提交记录](https://github.com/torvalds/linux/commit/68c0a5c70614ce0adf8c6ff849534dd6d2c0ca43)里写了CQP是Command Queue Pair，分为CSQ和CRQ，合理猜测分别是命令发送队列和命令接收队列。

linux4.14和最新（6.15-rc4，下同）的驱动均未使用CRQ，合理猜测是给类似SD100之类的玩意设计的？

### TQP

我猜TQP是指Transmission Queue Pair，是网卡IO的队列对。

### TC

copylot猜测TC是Traffic Class，不保准

### RSS和TQP和TC

RSS实现要设置“TC_MODE”

我这个网卡刚启动的时候TQPCount是4个，TC是1个，合理猜测通过命令配置开启RSS后TC的数量会变成TQP数量

### VPORT

VPORT大约是虚拟端口，可能和SR-IOV有关。猜测当启用了SR-IOV后，每个VF对应一个VPORT

### ring和中断

ring配置在`HNS3_RING_RX_RING_BASEADDR_L/H_REG`

然后通过`HCLGE_OPC_ADD_RING_TO_VECTOR`配置关联的vector

vector开启配置在`HCLGE_VECTOR_REG_BASE`（见4.14的`hclge_get_vector`，新版的太抽象）

其中第0个索引对应第0个vector，这个是misc interrupt，似乎用在重置之类的地方

之后按顺序是vport的vector

也就是说vector 1 -> vport 0(PF) -> TQPs

### typo

大约是[typo](https://github.com/torvalds/linux/blob/1a33418a69cc801d48c59d7d803af5c9cd291be2/drivers/net/ethernet/hisilicon/hns3/hns3pf/hclge_main.h#L192)

```C
#define HCLGE_SUPPORT_1G_BIT		BIT(0)
#define HCLGE_SUPPORT_10G_BIT		BIT(1)
#define HCLGE_SUPPORT_25G_BIT		BIT(2)
#define HCLGE_SUPPORT_50G_R2_BIT	BIT(3)
#define HCLGE_SUPPORT_100G_R4_BIT	BIT(4)
/* to be compatible with exsit board */
#define HCLGE_SUPPORT_40G_BIT		BIT(5)
#define HCLGE_SUPPORT_100M_BIT		BIT(6)
#define HCLGE_SUPPORT_10M_BIT		BIT(7)
#define HCLGE_SUPPORT_200G_R4_EXT_BIT	BIT(8)
#define HCLGE_SUPPORT_50G_R1_BIT	BIT(9)
#define HCLGE_SUPPORT_100G_R2_BIT	BIT(10)
#define HCLGE_SUPPORT_200G_R4_BIT	BIT(11)
```

## Windows

### IRQL

中断的级别，分为PASSIVE_LEVEL和DISPATCH_LEVEL，DIRQL啥的

PASSIVE_LEVEL可以用PAGED内存，DISPATCH_LEVEL及更高不可以用PAGED内存

要避免在DISPATCH_LEVEL和更高的IRQL下搞什么阻塞的操作

如果用错了函数内存啥的，就会给你抛一个BSOD

### SAL

源码标记语言，用来描述参数属性啥的，比如`_In_`表示参数用于输入，VS里可以通过静态分析根据SAL标注检查代码

### NET_RING

[NET_RING](https://learn.microsoft.com/en-us/windows-hardware/drivers/netcx/introduction-to-net-rings)是netadapterCx的ring buffer，可以对应若干个tx/rx queue

其中的queue分为两种环形缓冲区，其中一个是Packet Ring，另一个是Fragment Ring。TX队列里每个packet可能有多个fragment，RX队列里似乎是一一对应的？从RX的角度看我应该不需要一个packet对应多个fragment？

### ISR和DPC

ISR是中断服务例程，DPC是延迟过程调用

ISR跑在DIRQL，在这里基本上啥设施都不能用，得最小化代码。DPC跑在DISPATCH_LEVEL，能用大部分设施。

处理中断的时候，现在ISR看看是不是自己的中断，如果不是，返回FALSE，如果是，保存一下交给DPC去跑，不在DIRQL直接处理。

DPC的时候再通知NET_RING之类的东西

## 进展

没啥进展，研究了好久A222到底咋工作的，linux驱动里套来套去的，很难阅读，要是a222有fbsd之类的驱动就好了。

两发单抽抽出来了爱可菲，好感队都没空位了，牛牛成带头大姐了，这两天得多肝点原了。

想玩哈摸你PC，看看是不是还用的HNS3的网卡
