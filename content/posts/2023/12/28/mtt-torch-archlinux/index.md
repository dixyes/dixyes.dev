---
title: MTT S80上炼丹 - archlinux
date: 2023-12-28T19:07:00+0800
draft: false
tags:
  - Linux
  - Archlinux
  - MTT S80
  - MUSA
toc: true
---

jd上抢到了1200的MTT S80，目的就是便宜的大显存，可以整一些比较大的活。开始了在archlinux上的折腾，

<!--more-->

## 系统和软件准备

我的archlinux炼丹系统和linux-lts内核

## 内核驱动

首先这东西需要个驱动，也就是个内核模块，还好官方有提供：https://developer.mthreads.com/sdk/download/musa?equipment=&os=&driverVersion=&version=

注册账号下载最新的 rc1.4.1 Intel CPU_Ubuntu 

## 懒人：PKGBUILD

```bash
git clone https://github.com/dixyes/musa-pkgbuild
cd musa-pkgbuild
# 把下载到zip丢到这个目录
makepkg -Cf
sudo pacman -U ./mtgpu<tab>
sudo pacman -U ./musa-userspace<tab>
```

## 强迫症：DIY

### mtgpu

首先，mtgpu对于lts内核构建有问题 我修（糊）了下，你可以用https://github.com/dixyes/mtgpu-drv的2.1.2-6.1分支构建
```bash
git clone --branch 2.1.2-6.1 https://github.com/dixyes/mtgpu-drv
cd mtgpu-drv
make ARCH=x86_64 KERNELVER="$(uname -r)" V=1
```

如果构建成功了就可以插入模块了
```bash
# 依赖
sudo modprobe drm_display_helper
sudo modprobe snd_pcm
# 插入（这俩参数包里面的 不知道什么意思）
sudo insmod mtgpu.ko display=mt EnableFWContextSwitch=27
```

没有oops或者panic就代表没问题了，有的话可以去我的repo提issue，但我技术力有限你提了我也不一定会修

（crtc相关的报错不用在意，少插一个显示器报一个 没啥影响 单纯的驱动里有bug）

### userspace

它的包是ubuntu的，自己解压 提取下要用的东西

由于我的目的是跑pytorch，所以不需要musa的构建环境：

```bash
# 解压zip
unzip <这个zip>
# 你会看到若干个tarball和一个deb
# 解压deb
ar x <这个deb>
# data.tar.gz就是安装文件系统了 我们需要从它里面提取一些库和mthreads-gmi
# deb里面的其他的几个文件control.tar.gz 对我们的arch没有用，删了就好
tar -xf data.tar.gz
# 你可以先试下显卡认了没：
./usr/lib/mthread-gmi
# 按照你的喜好复制粘贴so库到你的lib目录：需要几乎全部的so
# 或者设一下ldconf啥的

# 安装mudnn
tar -xf <mudnn的包>
cd <mudnn那个目录>
# 还是会造一些垃圾的 你也可以手动复制lib里面的so们到你的ldpath
sudo ./install.sh

# 安装mccl
# 对于pytorch是必要的，同mudnn 不写了

# 安装musart
tar -xf <toolkit那个包>
# 把lib里面的libmusa libmusart libmuffi啥的放到ldpath
```

### pytorch

准备一个python3.9，作为arch用户，直接aur了就：
```bash
aurman -S python3.9 # 当然 你也可以yay
```

准备一个venv
```venv
python3.9 -m venv venv
```

安装官方的轮子和没写的依赖们：
```bash
. venv/bin/activate
pip install <torch轮子> <torch_musa轮子> numpy packaging pytest
```

应该能用了：
```bash
. venv/bin/activate
python -c "import torch; import torch_musa; print(torch.musa.is_available())"
```
