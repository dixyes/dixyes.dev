---
title: 0penBmc的DBus API
date: 2025-10-05T17:35:43+0800
draft: false
tags:
  - DBus
  - OpenBMC
  - Linux
toc: true
---

最近把FT2000/4收拾一下，记一下OpenBMC的dbus api怎么用

<!--more-->

## OpenBMC的DBus

这个BMC固件的OpenBMC有点毛病，配置无法正常保存，但是overlay还是正常的，用户分区的东西可以持久化

因此要用优雅的方式存储mac地址，就得用DBus接口来配置MAC地址

### busctl

先看看都有哪些东西

```bash
busctl list
```

确认要改的服务为xyz.openbmc_project.Network这个很好理解

先看看我要用的对象是啥

```bash
busctl tree xyz.openbmc_project.Network
```

```text
`-/xyz
  `-/xyz/openbmc_project
    `-/xyz/openbmc_project/network
      |-/xyz/openbmc_project/network/config
      | `-/xyz/openbmc_project/network/config/dhcp
      |-/xyz/openbmc_project/network/eth0
      | `-/xyz/openbmc_project/network/eth0/ipv4
      |   `-/xyz/openbmc_project/network/eth0/ipv4/12345678
      `-/xyz/openbmc_project/network/eth1
        `-/xyz/openbmc_project/network/eth1/ipv4
          `-/xyz/openbmc_project/network/eth1/ipv4/12345678
```

根据Google gemini的幻觉，应该是`/xyz/openbmc_project/network/eth0`

这个幻觉叫我用`xyz.openbmc_project.Network.EthernetInterface`接口，试了下报错`Unknown property or interface.`

于是

```bash
busctl introspect xyz.openbmc_project.Network /xyz/openbmc_project/network/eth0
```

```text
NAME                                              TYPE      SIGNATURE RESULT/VALUE                             FLAGS
org.freedesktop.DBus.Introspectable               interface -         -                                        -
.Introspect                                       method    -         s                                        -
org.freedesktop.DBus.Peer                         interface -         -                                        -
.GetMachineId                                     method    -         s                                        -
.Ping                                             method    -         -                                        -
org.freedesktop.DBus.Properties                   interface -         -                                        -
.Get                                              method    ss        v                                        -
.GetAll                                           method    s         a{sv}                                    -
.Set                                              method    ssv       -                                        -
.PropertiesChanged                                signal    sa{sv}as  -                                        -
xyz.openbmc_project.Collection.DeleteAll          interface -         -                                        -
.DeleteAll                                        method    -         -                                        -
xyz.openbmc_project.Network.EthernetInterface     interface -         -                                        -
.AutoNeg                                          property  b         false                                    emits-change writable
.DHCPEnabled                                      property  s         "xyz.openbmc_project.Network.Ethernet... emits-change writable
.DefaultGateway                                   property  s         ""                                       emits-change writable
.DefaultGateway6                                  property  s         ""                                       emits-change writable
.DomainName                                       property  as        0                                        emits-change writable
.IPv6AcceptRA                                     property  b         false                                    emits-change writable
.InterfaceName                                    property  s         "eth0"                                   emits-change writable
.LinkLocalAutoConf                                property  s         "xyz.openbmc_project.Network.Ethernet... emits-change writable
.LinkUp                                           property  b         false                                    const
.NICEnabled                                       property  b         true                                     emits-change writable
.NTPServers                                       property  as        0                                        emits-change writable
.Nameservers                                      property  as        0                                        emits-change writable
.Speed                                            property  u         0                                        emits-change writable
.StaticNameServers                                property  as        0                                        emits-change writable
.StaticNameServers6                               property  as        0                                        emits-change writable
xyz.openbmc_project.Network.IP.Create             interface -         -                                        -
.IP                                               method    ssys      o                                        -
xyz.openbmc_project.Network.MACAddress            interface -         -                                        -
.MACAddress                                       property  s         "00:00:00:00:00:01"                      emits-change writable
xyz.openbmc_project.Network.Neighbor.CreateStatic interface -         -                                        -
.Neighbor                                         method    ss        o                                        -
```

因此执行以下命令改mac

```bash
busctl set-property xyz.openbmc_project.Network /xyz/openbmc_project/network/eth0 xyz.openbmc_project.Network.MACAddress MACAddress s 'xx:xx:xx:xx:xx:xx'
```

改完没多久，又给我改回去了。。。

翻找一下发现了另一个地方

```bash
busctl set-property xyz.openbmc_project.Settings /xyz/openbmc_project/network/host0/intf xyz.openbmc_project.Network.MACAddress MACAddress s "xx:xx:xx:xx:xx:xx"
```

过了一会 还是给改回去

没辙了先咕了
