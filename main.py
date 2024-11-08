import pyautogui
import base64
import json
import hashlib
import hmac
import ssl
import websocket
from urllib.parse import urlparse, urlencode
from datetime import datetime
from time import mktime, sleep
from wsgiref.handlers import format_date_time
from io import BytesIO
import _thread as thread
import argparse
import config  # 导入配置文件

# 截图并转换为base64格式的函数
def capture_and_convert_to_base64(region):
    try:
        # 截取屏幕指定区域
        screenshot = pyautogui.screenshot(region=region)

        # 将截图保存为内存中的字节流
        img_byte_arr = BytesIO()
        screenshot.save(img_byte_arr, format="PNG")
        img_byte_arr.seek(0)

        # 将字节流转换为base64编码
        img_base64 = base64.b64encode(img_byte_arr.read()).decode('utf-8')

        # 确保 Base64 编码有效
        if not img_base64 or len(img_base64) < 10:
            print("无效的 Base64 数据，截图可能失败")
            return None

        return img_base64

    except Exception as e:
        print(f"截图或转换失败: {e}")
        return None


# Ws_Param 用于生成 WebSocket 请求 URL 和授权参数
class Ws_Param(object):
    def __init__(self, APPID, APIKey, APISecret, imageunderstanding_url):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.host = urlparse(imageunderstanding_url).netloc
        self.path = urlparse(imageunderstanding_url).path
        self.ImageUnderstanding_url = imageunderstanding_url

    def create_url(self):
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        signature_origin = "host: " + self.host + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + self.path + " HTTP/1.1"

        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()

        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = f'api_key="{self.APIKey}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'

        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')

        v = {
            "authorization": authorization,
            "date": date,
            "host": self.host
        }

        url = self.ImageUnderstanding_url + '?' + urlencode(v)
        return url

answer = ""

# 收到WebSocket消息的处理
def on_message(ws, message):
    data = json.loads(message)
    code = data['header']['code']
    if code != 0:
        print(f"请求错误: {code}, {data}")
        print(f"完整响应: {message}")
        ws.close()
    else:
        choices = data["payload"]["choices"]
        status = choices["status"]
        content = choices["text"][0]["content"]
        print(content, end="")
        global answer
        answer += content
        if status == 2:
            ws.close()

# WebSocket请求参数生成
def gen_params(appid, img_base64):
    data = {
        "header": {
            "app_id": appid
        },
        "parameter": {
            "chat": {
                "domain": config.SPARKAI_DOMAIN,
                "temperature": 0.5,
                "top_k": 4,
                "max_tokens": 8192,
                "auditing": "default"
            }
        },
        "payload": {
            "message": {
                "text": [
                  {
                    "role": "user",
                    "content": img_base64,
                    "content_type": "image"
                  },
                  {
                    "role": "user",
                    "content": config.IMAGE_QA
                  }
                ]
            }
        }
    }
    return data

# 收到WebSocket错误的处理
def on_error(ws, error):
    print("### error:", error)

# 收到WebSocket关闭的处理
def on_close(ws, one, two):
    print("Connection closed")

# WebSocket连接建立后的处理
def on_open(ws):
    thread.start_new_thread(run, (ws,))

def run(ws, *args):
    data = json.dumps(gen_params(appid=ws.appid, img_base64=ws.img_base64))
    ws.send(data)

# WebSocket主函数
def main(appid, api_key, api_secret, imageunderstanding_url, img_base64):
    if not img_base64:
        print("没有图像数据，退出。")
        return

    wsParam = Ws_Param(appid, api_key, api_secret, imageunderstanding_url)
    websocket.enableTrace(False)
    wsUrl = wsParam.create_url()
    ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_error=on_error, on_close=on_close, on_open=on_open)
    ws.appid = appid
    ws.img_base64 = img_base64

    try:
        print("尝试连接 WebSocket...")
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    except Exception as e:
        print(f"WebSocket 连接失败: {e}")

# 之前的截图的base64值
last_img_base64 = None

# 定时截图并与上次截图比较
def capture_periodically(region, interval=config.CAPTURE_INTERVAL, screenshot_image=False):
    if screenshot_image:
        # 只保存一次截图
        capture_and_save_image(region)
    else:
        global last_img_base64
        while True:
            # 获取当前截图并转换为base64
            img_base64 = capture_and_convert_to_base64(region)

            if img_base64 and img_base64 != last_img_base64:
                print("图片已更改，发送到AI模型...")
                # 更新最后一次截图
                last_img_base64 = img_base64
                print(f"发送的图像数据（部分）：{img_base64[:30]}...")  # 打印base64字符串的前30个字符进行验证

                # 启动WebSocket连接并将base64图像数据传递给模型
                main(config.SPARKAI_APP_ID, config.SPARKAI_API_KEY, config.SPARKAI_API_SECRET, config.SPARKAI_URL, img_base64)
            else:
                print("图片未变化，跳过请求")

            # 等待指定的时间间隔再进行下一次截图
            sleep(interval)

# 保存截图
def capture_and_save_image(region):
    try:
        # 截取屏幕指定区域
        screenshot = pyautogui.screenshot(region=region)

        # 将截图保存为本地文件
        screenshot.save("screenshot.png")
        print("本地图片已保存为 'screenshot.png'")

    except Exception as e:
        print(f"截图保存失败: {e}")


if __name__ == '__main__':
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="截图并测试图像")
    parser.add_argument('--screenshot_image', action='store_true', help="保存截图为本地文件并退出")
    args = parser.parse_args()

    capture_periodically(config.SCREENSHOT_REGION, interval=config.CAPTURE_INTERVAL, screenshot_image=args.screenshot_image)
