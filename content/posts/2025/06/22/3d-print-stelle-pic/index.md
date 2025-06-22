---
title: 3D打印阿星表情包
date: 2025-06-22T21:44:24+0800
draft: false
tags:
  - 3D打印
toc: true
---

终于忍不住买了拓竹P1S，开始玩一玩多色3D打印。打一个表情包玩玩，本来想搞遐蝶的，但是要起码7种颜色，要两个AMS，不太舍得掏钱买。

小灰毛的表情包就简单多了，只要3种颜色，于是就做了模型。

![stelle](stelle.jpg)

<!--more-->

## 多色打印

反正就是有个AMS负责帮你换料，比自己换省事的多。

## jittering

![mita jittering](mitamiao.png)

我先用原先这个米塔的图片的jittering demo做了单层jittering的效果测试。

刚开始尝试把图片丢到inkscape，使用白描位图，像素图模式，导出为svg，丢到openscad，结果它不认。。。发现是openscad不太喜欢poly元素，于是写了个小python文件将图片转换为path组成的svg，就可以用了

```python
from PIL import Image

image = Image.open("mitamiao.png")
width, height = image.size

print(f"Image size: {width}x{height}")

header = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg
    xmlns="http://www.w3.org/2000/svg"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    width="51.2mm" height="51.2mm"
    viewBox="0 0 {width} {height}">
'''
tail = '''
</svg>
'''
indent = "    "

f = open("mitavector2.svg", "w")
f.write(header)

for y in range(height):
    for x in range(width):
        r, g, b = image.getpixel((x, y))
        if r > 127 and g > 127 and b > 127:
            # Skip white pixels
            continue
        path = f'''{indent}<path fill='black' d='M{x},{y} H{x+0.99} V{y+1.01} H{x} Z' />
'''
        f.write(path)

f.write(tail)
f.close()

```

转换完成后用openscad生成黑白两种颜色的模型

```openscad
// linear_extrude(0.2) {
//     import(file = "mitavector2.svg");
// }
module mita() {
    linear_extrude(0.2) {
        import(file = "mitavector2.svg");
    }
}

difference() {
    cube([51.2, 51.2, 1]);
    mita();
}
```

分别试了51.2和128mm的尺寸

![mita printed](mita.jpg)

麻麻赖赖的，只要不是瞎子就肉眼可见的没法看，背光就效果还行，怪不得官方的cmyw打印要配合背光。

## 混色

如果不采用耗材混色，就算是打印小灰毛都要许多种类的耗材，对钱包极不友好，所以还是要考虑混色。

由于之前那个bw jittering的测试效果不算很理想，我怀疑混色效果也好不到哪去，于是就先做了一个混色的测试。

```openscad
width = 50;
height = 50;
layer = 0.2;
thickness = 1;

layers = thickness / layer;

module black() {
    for (i = [0:layers - 1]) {
        translate([0, 0, i * layer]) {
            cube([width * i / layers, height / 2, layer]);
        }
        translate([width * i / layers, height / 2, i * layer]) {
            cube([width * 1.5 / layers, height / 2, layer]);
        }
    }
}

difference() {
    cube([(1 + (0.5 / layers)) * width, height, thickness]);
    black();
}
```

大概思路就是一层有点透明的A颜色，和一层不太透明的B颜色，然后就能获得AB的中间色，在这里就是黑色和白色混合出灰度。

结果混色效果就还行。可以注意到但凡有一层黑色，就不会暴露桌子的颜色，混色的色块颜色也比较均匀

![color mixing](color_mixing.jpg)

## 小灰毛模型

我找了[呵纹的表情包](https://www.bilibili.com/opus/1049715686809534481)，作者是[仓鼠饭团c](https://space.bilibili.com/83968703/)，先无授权用一下，如果行得通再要一下授权，能要到的话再发一下模型到什么地方。

![原图](stelle.webp)

直接白描会由于jpeg伪影效果极其糟糕。所以丢进ComfyUI,用模型去JPEG噪点和升采样。

![upscale](upscale_by_comfyui.png)

接下来丢进inkscape，进行白描。

白描完了之后一通修改整理成svg，用脚本拆分path

```python
from copy import deepcopy
from xml.etree import ElementTree

file = 'stelle.svg'

# register the SVG namespace, avoid ns0:
ElementTree.register_namespace('', 'http://www.w3.org/2000/svg')

# open the file
root = ElementTree.parse(file)

# remove <image> elements
layer1 = root.find('.//{http://www.w3.org/2000/svg}g[@id="layer1"]')
layer1.remove(layer1.find('.//{http://www.w3.org/2000/svg}image'))

outputTree = deepcopy(root)
outputGroup = outputTree.find('.//{http://www.w3.org/2000/svg}g[@id="group"]')
outputGroup.clear()

group = root.find('.//{http://www.w3.org/2000/svg}g[@id="group"]')
for path in group.findall('.//{http://www.w3.org/2000/svg}path'):
    # get the id of the path
    id = path.get('id')
    if id is None:
        continue
    print(f'Processing {id}')
    outputGroup.append(path)
    with open(f'{id}.svg', 'wb') as f:
        outputTree.write(f, encoding='utf-8', xml_declaration=True)
    outputGroup.clear()
```

拆分成一堆`颜色名.svg`给scad用：

```openscad

layer = 0.2;
thickness = 2;

// filaments:
whiteFila = 0;
blackFila = 1;
yellowFila = 2;
backgroundFila = whiteFila;

layers = thickness / layer;

// colors names, note: this is ordered with color maps
colorNames = [
    // TOP
    "black",
    "darkgray",
    "gray",
    "lightgray",
    "brown",
    "gold",
    // BOTTOM
];

colorMaps = [
    /*
        colorIndex: [
            [ startLayer, thickness, filamentIndex ],...
        ]
    */
    [
        [0, layers, blackFila],
    ], // black
    [
        [0, 2, whiteFila],
        [2, 2, blackFila],
        [4, layers - 8, whiteFila],
        [layers - 4, 2, blackFila],
        [layers - 2, 2, whiteFila],

    ], // darkgray
    [
        [0, 3, whiteFila],
        [3, 1, blackFila],
        [4, layers - 8, whiteFila],
        [layers - 4, 1, blackFila],
        [layers - 3, 3, whiteFila],
    ], // gray
    [
        [0, 4, whiteFila],
        [4, 1, blackFila],
        [5, layers - 10, whiteFila],
        [layers - 5, 1, blackFila],
        [layers - 4, 4, whiteFila],
    ], // lightgray
    [
        [0, 2, yellowFila],
        [2, layers - 4, blackFila],
        [layers - 2, 2, yellowFila],
    ], // brown
    [
        [0, layers, yellowFila],
    ], // gold(yellow)
];

module singleFila(filaIndex) {
    for (colorIndex = [0 : len(colorNames) - 1]) {
        colorMap = colorMaps[colorIndex];
        for (data = colorMap) {
            startLayer = data[0];
            thickness = data[1];
            if (
                filaIndex == data[2] &&
                backgroundFila != data[2] &&
                thickness > 0
            ) {
                translate([0, 0, startLayer * layer])
                    linear_extrude(height = (thickness * layer))
                        import(file = str(colorNames[colorIndex], ".svg"), dpi = 96);
            }
        }
    }
}

// for (i = [1:4]) {
//     fn = str("lightgray", i, ".svg");
//     // fn = str("lightgray.svg");
//     echo(fn);
//     linear_extrude(height = 0.4)
//         import(file = fn, dpi = 96);
//     linear_extrude(height = 0.4)
//         import(file = fn, dpi = 96);
// }

// singleFila(blackFila);
// singleFila(yellowFila);

difference() {
    cube([64, 64, 2]);
    singleFila(blackFila);
    singleFila(yellowFila);
}
```

结果openscad就报错了路径未闭合，很神奇的是只有路径线性挤出两次才会报错。。。

检查了好久svg，路径没啥问题，但我之前遇到过类似的报错，是self-intersecting路径的问题，这次实在不知道咋回事了，调了半天。

后来想到将路径分离，再二分查找其中有那些路径有问题于是写了上面注释掉的那段代码，结果发现了坑爹的问题

![wrong path](wrong_path.png)

这里有自交的路径和重合的节点，CGAL遇到这个就会寄。

手动修了这些，然后就可以正常生成模型了。

![stelle_black](stelle_black.png) ![stelle_white](stelle_white.png)

丢进Bambu Lab切片打印（没买黄色材料，先打一个怪怪的绿眼阿星）

![slicing](stelle_slicing.png)

## 结论

多色打印直接用层与层混色问题不大，可以搞。

openscad对svg好多用法不太友好，最好是有svg原稿再做这种东西，要么有点痛苦。

