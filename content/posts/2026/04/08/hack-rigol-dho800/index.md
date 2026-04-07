---
title: Hacking DHO800
date: 2026-04-08T00:06:40+0800
draft: false
tags:
  - Android
  - 逆向
  - 示波器
  - DHO800
toc: true
---

被[傻逼假开源项目](https://github.com/mriscoc/Sparrow-Extended-GUI-for-RIGOL-DHO800_DHO900)坑了，遂自己折腾了一下。

<!--more-->

这里就记录下过程和成果，操作包违反用户协议的，不会具体写。

## 更新固件

群友有想要买示波器看SPI的，我就寻思要不要把我的DHO812卖了，但它的协议解析功能特别难用，卖给群友纯属坑人，于是我就搜了下新版固件

我的DHO812的固件版本是1.14，比官网第一个版本还老。。。 毕竟我是第一批买家，刚上市就买了

![version](version.png)

于是就更新了下固件，顺便拆包看一眼，结果发现有个叫Sparrow的App。

## 傻逼假开源项目

于是我就顺手google了一下，发现了这个[傻逼假开源项目](https://github.com/mriscoc/Sparrow-Extended-GUI-for-RIGOL-DHO800_DHO900)

看起来功能超强，我就无脑打开了安装教程，直接开始安装

执行完卸载原版，我才发现这傻逼玩意没有下载的，得花钱买，它是真不怕被普源搞。。。

而我已经把原版卸载了，只能硬着头继续

经过一番（下午）折腾，我终于把它仓库里面的apktool项目构建出来了，你猜怎么着，跟原版的一毛一样，说的那些功能一个没有，这个仓库就是个clickbait

我立即就想给他发个issue问如何reproduce，结果发现这个仓库把issue关了

## 自己做

我原版都删了，你告诉我你根本没开源，完事了还没issue，火气一下就上来了，就照着这个思路自己搞。

- 主要的功能判断在libscope-auklet.so里面，需要修改一些判断，可以用[傻逼项目的脚本](https://github.com/mriscoc/Sparrow-Extended-GUI-for-RIGOL-DHO800_DHO900/blob/master/SparrowApp/patch_lib.py)patch
- smali里面需要修改一些型号判断，还有一些不大不小的bug可以帮rigol修一下

改完了之后装进去

![result](result.png)

相较于用rigol_vendor_bin改成900系列，这个没有假的三四通道，同时EXT触发可用，别的功能也都能用了。
