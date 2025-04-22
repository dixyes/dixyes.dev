---
title: MTT MTGPU驱动更新
date: 2025-04-23T00:28:14+0800
draft: false
tags:
  - MTT
  - Linux
  - 杂记
toc: true
---

今天更新了下MTGPU mod

<!--more-->

一周前MTT官方发布了4.0.1版本的驱动，今天才看到，于是搞了下。

## 6.13 IOMMU

6.13移除iommu两个API的问题没救了，官方还没修，官方不修我只能用我的脏方法：在驱动probe的时候判断下bus上有没启用iommu 这么搞能构建，但是能不能炸就不知道了。

这个脏方法还是不发AUR的PKGBUILD，只放在仓库里

## bootlin anubis

去bootlin elixir看源码参考时看到了这个

![bootlin anubis](anubis.png)

拿我浏览器挖矿是吧，疑似有点激进了，看在有猫娘的份上就不计较了

## 4.0.1

quyuan和chunxiao又合一起了 ~~天下大势，分久必合，合久必分~~

打包迷惑行为也少不了，真心希望MTT能搞一个发版的自动workflow出来，老整这种打包仙人行为太难崩了

之前带的xserver也不带了，体积少了一些但也甭想在arch上用mtgpu开X了，它那个driver和arch的X不太对付

## 性能

用llama-cpp跑了下`Qwen2.5-14B-Instruct-Q6_K.gguf` 只有4-6tps

mthreads-gmi看占用跑不满，不知道是不是我驱动改歪来
