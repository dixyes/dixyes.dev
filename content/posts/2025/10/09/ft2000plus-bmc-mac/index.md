---
title: FT2000+的BMC设置MAC地址
date: 2025-10-09T23:49:02+0800
draft: false
tags:
  - AST2500
  - Linux
toc: true
---

终于把bmc的mac搞明白了，记录一下

<!--more-->

## 问题

这个bmc的mac地址总会被重置成00:00:00:00:00:01，[上次](/content/posts/2025/10/05/openbmc-dbus-api)通过OpenBMC的dbus api礼貌的改是行不通，改完后很快就会自动重置回去。

## 换个思路

我首先找了下OpenBMC的源码，翻了半天也没找到对应这个bmc对应的0.09是啥OpenBMC版本。目前来看是中电自己改的某个OpenBMC的fork。

然后我翻了下日志，发现了一些蛛丝马迹

```bash
journalctl -u xyz.openbmc_project.Network -b
```

```text
...
Jun 02 14:35:26  phosphor-network-manager[244]: eth0 mac offset is: 407
Jun 02 14:35:26  phosphor-network-manager[244]: eth1 mac offset is: 535
...
```

可见他从某个地方的偏移407和535读取了mac地址

可这是啥地方并不知道。由于我不会逆向，没法知道它到底怎么做的，但还好有群友友情提供了一个静态链接的strace

strace下phosphor-network-manager发现

```text
...
openat(AT_FDCWD, "/etc/default/obmc/eeproms/system/chassis/motherboard", O_RDWR|O_LARGEFILE) = 12
read(12, "SYSFS_PATH=/sys/bus/i2c/devices/"..., 8191) = 54
close(12)                               = 0
openat(AT_FDCWD, "/sys/bus/i2c/devices/4-0050/eeprom", O_RDWR|O_LARGEFILE) = 12
...
```

于是看一下`/sys/bus/i2c/devices/4-0050/eeprom`的内容

```bash
hexdump -C /sys/bus/i2c/devices/4-0050/eeprom
```

```text
...
*
00000190  ff ff ff ff ff ff ff 00  00 00 00 00 01 ff ff ff  |................|
000001a0  ff ff ff ff ff ff ff ff  ff ff ff ff ff ff ff ff  |................|
*
00000200  ff ff ff ff ff ff ff ff  xx xx xx xx xx xx ff ff  |................|
00000210  ff ff ff ff ff ff ff 00  00 00 00 00 02 ff ff ff  |................|
...
```

正确的mac在0x208处，但是程序读的不是这里，合理猜测是新版bmc不兼容旧版eeprom的格式

可以发现407(0x197)和535(0x217)偏移处分别是00:00:00:00:00:01和00:00:00:00:00:02

随修改下：

```bash
printf '\x00\x25\x00\x12\x34\x56' > /tmp/002500123456
dd if=/tmp/002500123456 of=/sys/bus/i2c/devices/4-0050/eeprom bs=1 seek=407 conv=notrunc
printf '\x00\x25\x00\x12\x34\x57' > /tmp/002500123457
dd if=/tmp/002500123457 of=/sys/bus/i2c/devices/4-0050/eeprom bs=1 seek=535 conv=notrunc
```

其中002500123456是要替换的mac

然后重启下，结果mac正常了。
