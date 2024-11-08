# xf-image-identify


图片识别、自动化问答 AI助手，使用 python 语言，基于讯飞AI的图片识别及问答功能。


# 使用
### 1. 安装依赖（需要使用 python3.x）
```shell
pip install -r pip-env.txt
```

如果是 Mac M 系列芯片，需要在命令之前加上 `arch -arm64`，如下：
```shell
arch -arm64 pip install -r pip-env.txt
```

### 2. 配置参数

修改 `config.py` 配置文件内容

讯飞星火API申请地址：https://xinghuo.xfyun.cn/sparkapi ，有免费额度。

主要参数如下：
- SPARKAI_APP_ID：讯飞星火API的APPID
- SPARKAI_API_SECRET：讯飞星火API的API_SECRET
- SPARKAI_API_KEY：讯飞星火API的API_KEY
- SCREENSHOT_REGION：截图区域配置 (x, y, width, height)
- IMAGE_QA：描述
- CAPTURE_INTERVAL：截图间隔，单位为秒，默认为 3 秒 

### 3. 运行程序

在本地生成图片，用来测试图片是否符合自己要求
```shell
python main.py --screenshot_image
```

轮询问答

```shell
python main.py
```