---
title: FT2000+的SMMU能用啦
date: 2026-05-22T18:52:55+0800
draft: false
tags:
  - FT2000+
  - SMMU
  - ARM
  - Linux
  - ACPI
toc: true
---

终于 SMMU/IOMMU 能用啦，记录一下过程

<!--more-->

## 背景

想把Atlas 300I型号3000的加速卡跑起来，但是华为官方提供的驱动太抽象了，得上古内核+上古发行版才能用。虽然我用的archlinux arm抽象程度不遑多让，但并不支持

先前只是把服务器跑了起来接了NVMe on ethernet，但并没解决SMMU的问题，这次费了点功夫让SMMU彻底能用啦

下面的FT2000+都是指FT2000+/64，跟FT2000/4没关系

## 内核Patch

FT2000+的SMMU说是兼容Corelink MMU500，但实际上有一点区别，导致并不能直接通过ACPI修复来成功运行，需要一些专门的patch，不知为何对应的维护者一直没向主线上游提交或者一直没被上游合并，因此必须进行内核patch

（下面的patch文本里的tab九成九会炸 所以请自行适配你的内核）

### SMMU stream ID问题

标准的的stream ID是1:1映射的但FT2000+就比较奇怪，[先前的文章](../../../../../2026/05/22/ft2000plus-smmu/index.md)已经提到过这一点（合理怀疑高位的那四个bit是INTx的标识位）

体现在提示unknown stream ID，丢中断导致卡死

这个这么patch就行：

```diff
diff --git a/drivers/iommu/arm/arm-smmu/arm-smmu.c b/drivers/iommu/arm/arm-smmu/arm-smmu.c
index 488632b8eeab..1ad463d2e551 100644
--- a/drivers/iommu/arm/arm-smmu/arm-smmu.c
+++ b/drivers/iommu/arm/arm-smmu/arm-smmu.c
@@ -1450,6 +1450,18 @@ static struct iommu_device *arm_smmu_probe_device(struct device *dev)
                smmu = arm_smmu_get_by_fwnode(fwspec->iommu_fwnode);
        }
 
+       /* FUCK FT2000+ */
+       if ((read_cpuid_id() & 0xff000fff0) == 0X70006620 /* phytium 0x70 FT2000+ 0x662 */) {
+               int num = fwspec->num_ids;
+
+               for (i = 0; i < num; i++) {
+                       /* mask 0x7000 sid=(rid >> 3) */
+                       u32 fwid = 0x70000000 | (fwspec->ids[i] >> 3);
+
+                       iommu_fwspec_add_ids(dev, &fwid, 1);
+               }
+       }
+
        ret = -EINVAL;
        for (i = 0; i < fwspec->num_ids; i++) {
                u16 sid = FIELD_GET(ARM_SMMU_SMR_ID, fwspec->ids[i]);
diff --git a/drivers/iommu/arm/arm-smmu/arm-smmu.c b/drivers/iommu/arm/arm-smmu/arm-smmu.c
index e40b5a49d83c..41912e915b71 100644
--- a/drivers/iommu/arm/arm-smmu/arm-smmu.c
+++ b/drivers/iommu/arm/arm-smmu/arm-smmu.c
@@ -1557,6 +1557,13 @@ static struct iommu_group *arm_smmu_device_group(struct device *dev)
                        return ERR_PTR(-EINVAL);
                }
 
+               if (
+                       (read_cpuid_id() & 0xff000fff0) == 0X70006620 /* phytium 0x70 FT2000+ 0x662 */ &&
+                       !smmu->s2crs[idx].group
+               ) {
+                       continue;
+               }
+
                group = smmu->s2crs[idx].group;
        }
```

### ITS地址

体现在提示ITS deadlock，丢中断卡死

它的ITS MSI映射有点问题，要绕过IOMMU

```diff
diff --git a/drivers/irqchip/irq-gic-v3-its.c b/drivers/irqchip/irq-gic-v3-its.c
index 23158fc8d392..18339a897ad6 100644
--- a/drivers/irqchip/irq-gic-v3-its.c
+++ b/drivers/irqchip/irq-gic-v3-its.c
@@ -1816,6 +1816,12 @@ static void its_irq_compose_msi_msg(struct irq_data *d, struct msi_msg *msg)
        struct its_device *its_dev = irq_data_get_irq_chip_data(d);
 
        msg->data = its_get_event_id(d);
+       if ((read_cpuid_id() & 0xff000fff0) == 0X70006620 /* phytium 0x70 FT2000+ 0x662 */) {
+               u64 addr = its_dev->its->get_msi_base(its_dev);
+               msg->address_lo = lower_32_bits(addr);
+               msg->address_hi = upper_32_bits(addr);
+               return;
+       }
        msi_msg_set_addr(irq_data_get_msi_desc(d), msg,
                         its_dev->its->get_msi_base(its_dev));
 }
```

### ACS

体现在IOMMU不给分group

当acs_override patch用

```diff
diff --git a/drivers/pci/quirks.c b/drivers/pci/quirks.c
index d32a47e81fcf..b2125df1601b 100644
--- a/drivers/pci/quirks.c
+++ b/drivers/pci/quirks.c
@@ -5227,6 +5227,9 @@ static const struct pci_dev_acs_enabled {
        { PCI_VENDOR_ID_ZHAOXIN, PCI_ANY_ID, pci_quirk_zhaoxin_pcie_ports_acs },
        /* Wangxun nics */
        { PCI_VENDOR_ID_WANGXUN, PCI_ANY_ID, pci_quirk_wangxun_nic_acs },
+       /* Phytium */
+       { 0x10b5, PCI_ANY_ID, pci_quirk_xgene_acs },
+       { 0x17cd, PCI_ANY_ID, pci_quirk_xgene_acs },
        { 0 }
 };
```

### PCI BAR分配

体现在BAR alloc失败，然后设备没了

```text
[    4.925284] pci 0000:02:0c.0: bridge window [mem 0x82000000000-0x820040fffff 64bit pref]: assigned
[    4.934789] pci 0000:02:05.0: bridge window [mem size 0x05000000 64bit pref]: can't assign; no space
```

疑似是主线内核regression，6.17.9主线内核无此问题，6.18.32和7.0.9有问题

我写了个脏patch缓解了一下 需要根据实际情况patch

```diff
diff --git a/drivers/pci/setup-bus.c b/drivers/pci/setup-bus.c
index c2d640164f69..a09046bc8a51 100644
--- a/drivers/pci/setup-bus.c
+++ b/drivers/pci/setup-bus.c
@@ -1387,6 +1387,18 @@ static void pbus_size_mem(struct pci_bus *bus, unsigned long type,
                return;
        }
 
+       if (
+               bus->self &&
+               bus->self->bus->number == 0x02 &&
+               (PCI_SLOT(bus->self->devfn) == 0x0c || PCI_SLOT(bus->self->devfn) == 0x05) &&
+               PCI_FUNC(bus->self->devfn) == 0x00
+               //(b_res->flags & IORESOURCE_PREFETCH)
+       ) {
+               // fuck extend
+               size0 = 0x1 << 27; // 128M
+               min_align = 0x1 << 27;
+       }
+       pci_info(bus->self, "size0: 0x%016llx size1: 0x%016llx\n", size0, size1);
        resource_set_range(b_res, min_align, size0);
        b_res->flags |= IORESOURCE_STARTALIGN;
        if (bus->self && realloc_head && (size1 > size0 || add_align > min_align)) {
```

## ACPI fix

由于是用linux，可以在initcpio里面放ACPI override，所以不需要单独写个UEFI app来做这个事情。

### SSDT

先用[SSDT](./SSDT-FT2000plus-PCI.dsl)修复ECAM，PCI上的MMIO地址之类的东西

```bash
iasl SSDT-FT2000plus-PCI.dsl
```

### IORT

再用[IORT](./makeiort_reveg_fix.py)指定中断拓扑

mappings里面的东西需要根据实际情况修改，有一些设备可能加进去就炸了 比如我的nvme，我没仔细去研究原因

### initcpio

```bash
sudo cp iort_reveg.aml ssdt.aml /usr/lib/initcpio/acpi_override/
sudo mkinitcpio -P
```

## 效果

```bash
for g in $(find /sys/kernel/iommu_groups/ -maxdepth 1 -mindepth 1 -type d); do 
    echo "IOMMU Group ${g##*/}:"
    for d in $g/devices/*; do 
        echo -e "\t$(lspci -nns ${d##*/})"
    done
done
```

```text
IOMMU Group 7:
        10:00.0 SATA controller [0106]: Marvell Technology Group Ltd. 88SE9230 PCIe 2.0 x2 4-port SATA 6 Gb/s RAID Controller [1b4b:9230] (rev 11)
        12:00.0 SATA controller [0106]: Marvell Technology Group Ltd. 88SE9230 PCIe 2.0 x2 4-port SATA 6 Gb/s RAID Controller [1b4b:9230] (rev 11)
IOMMU Group 5:
        0c:00.0 Processing accelerators [1200]: Huawei Technologies Co., Ltd. Device [19e5:d100] (rev 20)
IOMMU Group 3:
        08:00.0 PCI bridge [0604]: ASPEED Technology, Inc. AST1150 PCI-to-PCI Bridge [1a03:1150] (rev 04)
        09:00.0 VGA compatible controller [0300]: ASPEED Technology, Inc. ASPEED Graphics Family [1a03:2000] (rev 41)
IOMMU Group 1:
        05:00.0 Ethernet controller [0200]: Mellanox Technologies MT27710 Family [ConnectX-4 Lx] [15b3:1015]
        05:00.1 Ethernet controller [0200]: Mellanox Technologies MT27710 Family [ConnectX-4 Lx] [15b3:1015]
IOMMU Group 8:
        11:00.0 SATA controller [0106]: Marvell Technology Group Ltd. 88SE9230 PCIe 2.0 x2 4-port SATA 6 Gb/s RAID Controller [1b4b:9230] (rev 11)
IOMMU Group 6:
        0d:00.0 USB controller [0c03]: Renesas Electronics Corp. uPD720201 USB 3.0 Host Controller [1912:0014] (rev 03)
IOMMU Group 4:
        0a:00.0 Ethernet controller [0200]: Intel Corporation I350 Gigabit Network Connection [8086:1521] (rev 01)
        0a:00.1 Ethernet controller [0200]: Intel Corporation I350 Gigabit Network Connection [8086:1521] (rev 01)
        0a:00.2 Ethernet controller [0200]: Intel Corporation I350 Gigabit Network Connection [8086:1521] (rev 01)
        0a:00.3 Ethernet controller [0200]: Intel Corporation I350 Gigabit Network Connection [8086:1521] (rev 01)
IOMMU Group 2:
        07:00.0 Serial Attached SCSI controller [0107]: Broadcom / LSI SAS3008 PCI-Express Fusion-MPT SAS-3 [1000:0097] (rev 02)
IOMMU Group 10:
        19:00.0 USB controller [0c03]: Renesas Electronics Corp. uPD720201 USB 3.0 Host Controller [1912:0014] (rev 03)
IOMMU Group 0:
        03:00.0 Fibre Channel [0c04]: Emulex Corporation LPe15000/LPe16000 Series 8Gb/16Gb Fibre Channel Adapter [10df:e200] (rev 30)
        03:00.1 Fibre Channel [0c04]: Emulex Corporation LPe15000/LPe16000 Series 8Gb/16Gb Fibre Channel Adapter [10df:e200] (rev 30)
IOMMU Group 9:
        13:00.0 SATA controller [0106]: Marvell Technology Group Ltd. 88SE9230 PCIe 2.0 x2 4-port SATA 6 Gb/s RAID Controller [1b4b:9230] (rev 11)
```

```text
dixyes@dixft2000plus ~/linux % sudo lspci -kvns 0c:00.0 
0c:00.0 1200: 19e5:d100 (rev 20)
        Subsystem: 0200:0100
        Flags: fast devsel, IRQ 82, IOMMU group 5
        Memory at 8200c000000 (64-bit, prefetchable) [disabled] [size=128K]
        Memory at 80068000000 (64-bit, non-prefetchable) [disabled] [size=16M]
        Memory at 82008000000 (64-bit, prefetchable) [disabled] [size=64M]
        Capabilities: [40] Express Endpoint, IntMsgNum 0
        Capabilities: [a0] MSI-X: Enable- Count=128 Masked-
        Capabilities: [b0] Power Management version 3
        Capabilities: [100] Advanced Error Reporting
        Capabilities: [150] Alternative Routing-ID Interpretation (ARI)
        Capabilities: [2a0] Transaction Processing Hints
        Capabilities: [310] Secondary PCI Express
        Capabilities: [4e0] Device Serial Number ff-ff-ff-ff-ff-ff-ff-ff
        Kernel driver in use: vfio-pci
```

![result](./result.png)

看来PCI拆分还有点问题，只认出来一块npu，得空再修吧
