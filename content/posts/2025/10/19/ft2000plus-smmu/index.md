---
title: FT2000+的SMMU
date: 2025-10-19T21:52:36+0800
draft: false
tags:
  - ARM
  - OpenBMC
  - FT2000+
  - Linux
toc: true
---

试图带IOMMU启动FT2000+，结果发现问题很大，记录一下

<!--more-->

## OpenBMC远程挂载

之前老是拷到U盘来回插拔，效率极低，研究了一下OpenBMC的远程挂载。

OpenBMC用的nbd+usb gadget的方式实现远程挂载。

抄了个脚本来实现远程挂载

```bash
#!/bin/sh

gadget_name=mass-storage
gadget_dir=/sys/kernel/config/usb_gadget/$gadget_name
nbd_device=/dev/nbd2

set -ex

action="$1"

case "$action" in
start)
    nbd-client -N default !!HOST!! !!PORT!! "${nbd_device}"
    mkdir -p $gadget_dir
    (
        cd $gadget_dir
        # http://www.linux-usb.org/usb.ids
        #    |-> 1d6b  Linux Foundation
        #          |-> 0104  Multifunction Composite Gadget
        echo "0x1d6b" > idVendor
        echo "0x0104" > idProduct
        mkdir -p strings/0x409
        echo "OpenBMC" > strings/0x409/manufacturer
        echo "Virtual Media Device" > strings/0x409/product
        mkdir -p configs/c.1/strings/0x409
        echo "config 1" > configs/c.1/strings/0x409/configuration
        mkdir -p functions/mass_storage.usb0
        ln -s functions/mass_storage.usb0 configs/c.1
        echo 1 > functions/mass_storage.usb0/lun.0/removable
        echo 1 > functions/mass_storage.usb0/lun.0/ro
        echo 0 > functions/mass_storage.usb0/lun.0/cdrom
        echo $nbd_device > functions/mass_storage.usb0/lun.0/file
        echo "1e6a0000.usb-vhub:p4" > UDC
    )
    ;;
stop)
    (
        cd $gadget_dir
        rm configs/c.1/mass_storage.usb0
        rmdir functions/mass_storage.usb0
        rmdir configs/c.1/strings/0x409
        rmdir configs/c.1
        rmdir strings/0x409
        nbd-client -d "${nbd_device}"
    )
    rmdir $gadget_dir
    ;;
*)
    echo "invalid action $action" >&2
    exit 1
esac

exit 0
```

nbd服务器配置：

```text
[generic]
    max_threads = 12
    user = dixyes
    group = dixyes
    listenaddr = 0.0.0.0
    port = 12345
    allowlist = true
[default]
    exportname = disk.raw
    authfile = auth.conf
    readonly = true
    multifile = false
    copyonwrite = false
```

有了这个东西后就可以远程挂盘更新IORT之类的东西了

## IORT

ARM的ACPI上有IORT（IO Remapping Table）表，用于描述DMA/MSI的拓扑结构，也描述IOMMU

如果不开IOMMU的话，这块板子的IORT默认将所有设备绑到ITS上。

开了IOMMU后，XHCI就寄了

### 这块板子的PCI结构

```text
-[0000:00]-+-00.0-[01-0a]----00.0-[02-0a]--+-04.0-[03]-- SLOT3
           |                               +-05.0-[04]-- SLOT4
           |                               +-08.0-[05]-- SLOT1
           |                               +-09.0-[06-07]----00.0-[07]----00.0  1a03:2000
           |                               +-0a.0-[08-09]--+-00.0  8086:1521 i350
           |                               |               +-00.1  8086:1521 i350
           |                               |               +-00.2  8086:1521 i350
           |                               |               \-00.3  8086:1521 i350
           |                               \-0c.0-[0a]-- SLOT2
           +-01.0-[0b]----00.0  1912:0014 前面板USB（插针） uPD020201
           \-02.0-[0c-17]----00.0-[0d-17]--+-04.0-[0e]----00.0  1b4b:9230 88SE9230
                                           +-05.0-[0f]----00.0  1b4b:9230 88SE9230
                                           +-06.0-[10]----00.0  1b4b:9230 88SE9230
                                           +-07.0-[11]----00.0  1b4b:9230 88SE9230
                                           +-08.0-[12]-- SLOT5
                                           +-09.0-[13]--
                                           +-0a.0-[14]--
                                           +-0c.0-[15]-- SLOT7
                                           +-0d.0-[16]-- M.2 slot
                                           \-0e.0-[17]----00.0  1912:0014 后面板USB uPD020201
```

### 调试

根据dmesg

```text
arm-smmu arm-smmu.1.auto: Blocked unknown Stream ID 0x22e0; boot with "arm-smmu.disable_bypass=0" to allow, but this may have security implications
```

猜测两个XHCI对应Stream ID是0x2160和0x22e0

通过修改IORT表，将0b:00和17:00分别绑上0x2160和0x22e0重启

好嘛，这次变unknown Stream ID 0x160和0x2e0了，依旧不能用

通过这个思路 我找了几个对应关系

| SID | BDF | RID |
| - | - | - |
| 0x0060 | 03:00.0 | 0x0300 |
| 0x0080 | 04:00.0 | 0x0400 |
| 0x00a0 | 05:00.0 | 0x0500 |
| 0x20a0 | 05:00.0 | 0x0500 |
| 0x0140 | 0a:00.0 | 0x0a00 |
| 0x0160 | 0b:00.0 | 0x0b00 |
| 0x2160 | 0b:00.0 | 0x0b00 |
| 0x41c0 | 0e:00.0 | 0x0e00 |
| 0x61c0 | 0e:00.0 | 0x0e00 |
| 0x02e0 | 17:00.0 | 0x1700 |
| 0x22e0 | 17:00.0 | 0x1700 |
| 0x1700 | 17:00.0 | 0x1700 |

猜测对应关系是
- 存在SID == RID
- RID >> 3，然后高14-12位可能是任意值

有点迷惑

联想到OpenEuler的[patch](https://mailweb.openeuler.org/archives/list/kernel@openeuler.org/thread/G47FHZ45JL4VBZHACTXFCS3LNQXNIFHA/)

```C
#ifdef CONFIG_ARCH_PHYTIUM
	/* ft2000+ */
	if (typeof_ft2000plus()) {
		int num = fwspec->num_ids;

		for (i = 0; i < num; i++) {
#define FWID_READ(id) (((u16)(id) >> 3) | (((id) >> SMR_MASK_SHIFT | 0x7000) << SMR_MASK_SHIFT))
			u32 fwid = FWID_READ(fwspec->ids[i]);

			iommu_fwspec_add_ids(dev, &fwid, 1);
		}
	}
#endif
```

是一个意思

### 改内核

根据ARM的规范，一个Requester ID只能对应一个Stream ID，但如果不声明操作系统会拦截DMA请求。

考虑利用下口alias来做这个额外的SID的映射。比如00:01上的0b:00，我可以分别给两个设备设置0x0160和0x2160两个SID

我本以为只有0x0yyy和0x2yyy两种情况，结果发现还有0x4yyy和0x6yyy，这个方法就泡汤了，老实改内核吧
