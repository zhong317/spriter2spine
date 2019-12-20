# Spriter2Spine

支持将Spriter的scml文件转换为Spine的json文件.

基于Spriter Pro R11版本和Spine 3.8版本.



# 用法
## Windows
在命令行中执行以下指令

```
./spriter2spine.exe -i xxx -o xxxx
```

* -i 指向读入文件夹或文件

* -o 指向目标文件夹或文件

## 例子

* 在当前文件夹中搜索文件夹'test', 读取其中所有scml后缀的文件, 将其转换为spine格式, 并将转换后的文件存储回'test'文件夹中.

  ```
  spriter2spine -i ./test -o ./test
  ```

* 在当前文件夹中搜索文件夹'test', 读取其中所有scml后缀的文件, 将其转换为spine格式, 并将转换后的文件存储在'output'文件夹中.

  ```
  spriter2spine -i ./test -o ./output
  ```

* 将文件名为'Animation.scml' 转换为名为 'xxx-动画实例名.json'.

  ```
  spriter2spine -i ./Animation.scml -o xxx
  ```

## Linux 或 Mac OS
* [安装 Python 2.7](https://www.python.org/download/releases/2.7)

* [安装 pip](https://pip.pypa.io/en/stable/installing/)

* 安装 'xmltodict' 模块. 执行以下命令进行安装
  ```
  pip install xmltodict
  ```

*  执行以下命令进行文件格式转换. 和windows的用法类似.
   ```
   python ./src/spriter2spine.py -i xxx -o xxx
   ```
## 不支持的特性
* 骨骼层次动画. 也就是不支持在动画内改变骨骼之间的层次关系.

* 骨骼透明度设置. 如果动画中设置了骨骼透明度, 转为spine时这部分透明度会被忽略.

* 只支持线性的透明度动画, 其他诸如贝塞尔等类型不支持.

* 不支持 **'1d Speed Curve'**.

## TODO
* 优化导出的spine动画文件尺寸.

* 优化spine的骨骼命名管理.
   
* 提高代码的简洁性, 可读性和Python性.
