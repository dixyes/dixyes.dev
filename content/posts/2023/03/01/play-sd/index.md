---
title: 玩玩stable-diffusion
date: 2023-03-01T17:31:00+0800
draft: false
tags:
  - 杂记
---

想玩sd已久，苦于没有支持cuda的显卡，一致咕咕咕着，终于最近下定决心要玩一下。

于是买了一块矿难后首选的炼丹显卡RTX3060，开始试着玩sd~~（买完后就发现pytorch支持了rocm）~~
<!--more-->
![12G显存的3060](3060.png)

![GPU-Z信息](gpuz.gif)

买回来一看，是LHR的，各个地方都很干净，连电源接口都干净的跟没用过似的，让我产生了2023年买到了没矿过的3060的错觉

然后拔下来我的6800xt，装上3060，进行一个在线降级，就可以开始愉快的sd了

才怪

开始进行痛苦的依赖安装过程，明明是requirements.txt就能解决的问题，但愣是让我装了一下午，快装完了发现，我的python3.11太新了，有几个关键依赖（numba，onnxruntime-gpu）还没支持，不得不当场装了旧的python，又重复了一遍过程

终于 sd webui可以打开了

![sd webui](sdwebui.png)

接下来就可以愉快的画图了
