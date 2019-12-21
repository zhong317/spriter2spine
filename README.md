# Spriter2Spine

Convert .scml files to spine .json files.

Base on Spriter Pro R11 and Spine 3.8.

[中文说明](./README-zh_CN.md)

# Usage
## Windows
Execute the following command from the command line

```
./spriter2spine.exe -i xxx -o xxxx
```

* -i specify the input folder or file

* -o specify the output folder or file

### Example

* search folder named 'test' from current folder, convert all the .scml file to spine json file, store them back in folder 'test' .

  ```
  ./spriter2spine.exe -i ./test -o ./test
  ```

* search folder named 'test' from current folder, convert all the .scml file to spine json file, store them in a folder named 'output'.

  ```
  ./spriter2spine.exe -i ./test -o ./output
  ```

* convert a file named 'Animation.scml' to 'xxx-entity name.json'.

  ```
  ./spriter2spine.exe -i ./Animation.scml -o xxx
  ```

## Linux or Mac OS
* [Install Python 2.7](https://www.python.org/download/releases/2.7)

* [Install pip](https://pip.pypa.io/en/stable/installing/)

* Install 'xmltodict' module. Execute the following command from the command line.
  ```
  pip install xmltodict
  ```

*  For Convert files, execute the following command. similar to windows's usage
   ```
   python ./src/spriter2spine.py -i xxx -o xxx
   ```
## Unsupported Features
* Bone hierarchy animation. it mean that you can't change the bone hierarchical relation in animation.

* Bone alpha. If you set alpha to a bone, it will not be convert to the spine version.

* Only supported **alpha** animation with linear, other curve types such as bezier will not take effect.

* Unsupported **'1d Speed Curve'**, other types such as 'bezier' and 'instant' was supported.

## TODO
* Optimze the spine file size.

* Optimze the spine bone 'name mangling'.
   
* Make the code more cleaner, readable and pythonic.
