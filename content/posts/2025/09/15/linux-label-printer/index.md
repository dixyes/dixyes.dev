---
title: Linux下标签打印机
date: 2025-09-15T12:22:40+0800
draft: false
tags:
  - 打印机
  - Linux
  - TSPL
toc: true
---

又到了更新基础系统镜像的时候，我要打个标签贴U盘上，但是linux下打印十分痛苦，记录一下

<!--more-->

## 打印机

我的打印机是GP-1134T，佳博的热转印标签打印机。Windows驱动是bartender做的，搜了下没搜到官方的Linux驱动。

## CUPS

打印这种事我第一个想到的肯定是CUPS，搜了下gprinter的CUPS驱动，发现有个[项目](https://github.com/feisuzhu/gprinter-cups)做了ppd和rastertotspl，改了下ppd，然而并不能用，打印机没反应

## lprint

搜了下相关信息 发现了[lprint](https://github.com/michaelrsweet/lprint)，arch下直接就有包，直接装上，用TSPL的驱动打印了也没反应

## tspl

没辙了 自己做/改吧

搜了下相关的文档，佳博基本上都用的TSPL指令，但rastertotspl之类的CUPS驱动已经被CUPS标记为已弃用，未来要移除。

考虑改一下lprint，支持一下，但lprint的代码实在是太抽象了，改不了一点。比如说：media是个枚举值，没法自定义media，通过TSPL `SIZE xx mm, yy mm`来设置纸张大小。 GAP也是写死的3mm没法定义

所以只能自己写个小程序试试了

先卸载usblp驱动

```bash
sudo modprobe -r usblp
```

然后用pyusb跑一下

```python
import sys
import usb.core, usb.util

VID = 0x0471
PID = 0x0055

printer = usb.core.find(idVendor=VID, idProduct=PID)
# print(printer)
for cfg in printer:
    intf = usb.util.find_descriptor(cfg, bInterfaceClass=0x7)
    if intf != None:
        break
if intf == None:
    raise ValueError("Interface not found")

def is_out_ep(ep):
    return 

epw = usb.util.find_descriptor(intf, custom_match=lambda x: not (x.bEndpointAddress & 0x80))
if epw == None:
    raise ValueError("Output endpoint not found")
epr = usb.util.find_descriptor(intf, custom_match=lambda x: x.bEndpointAddress & 0x80)
if epr == None:
    raise ValueError("Input endpoint not found")

epw.write(b"SELFTEST\r\n")
```

能正常打出自测标签，只要再把之前写的通过TCP打印的脚本改一下就行了

## TODO

虽然继续做的可能性很低，但未来可以考虑做的事有

- 把lprint改好：需要改很多lprint的设计，就算我做出来了，维护者不一定接受
- 做个CUPS驱动：已有的[项目](https://github.com/rndtrash/open-rastertotspl)只是开了个壳子，没实现tspl输出，我恰好懂一点tspl怎么写，可以继续。但问题是CUPS的driver是要移除的，接着用有点不太符合我的风格
- 做个IPP Everywhere的服务器来驱动usb/serial/tcp的TSPL打印机

人太懒了不想继续搞了，目前先用pyusb+tspl脚本打印了，未来有兴趣再继续吧
