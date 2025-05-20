import os
import re
import time
import random
import subprocess
import psutil
import pyautogui
import cv2
import numpy as np
import pytesseract
from PIL import ImageGrab
from datetime import datetime
from config_loader import config


# ---------------------------
# 初始化配置
# ---------------------------
def check_tesseract():
    """Tesseract环境验证"""
    try:
        pytesseract.get_tesseract_version()
        print("Tesseract-OCR 环境验证通过")
        return True
    except pytesseract.TesseractNotFoundError:
        print(f"""
        [!] Tesseract-OCR未正确配置，请检查：
            1. 是否完成安装
            2. 路径配置是否正确：{config.get("ocr", "tesseract_path")}
            3. 是否重启了计算机
        """)
        return False


# ---------------------------
# 进程查找
# ---------------------------
def is_process_running(process_name: str) -> bool:
    """检查指定进程是否存在"""
    for proc in psutil.process_iter(['name']):
        if proc.info['name'].lower() == process_name.lower():
            return True
    return False
# ---------------------------
# 核心功能
# ---------------------------
def kill_process(process_name):
    """强制终止指定进程"""
    for proc in psutil.process_iter(['name']):
        if proc.info['name'].lower() == process_name.lower():
            try:
                proc.kill()
                print(f"已终止进程: {process_name}")
            except Exception as e:
                print(f"终止进程失败: {e}")

def random_delay():
    """随机延迟防止检测"""
    min_sec, max_sec = config.get("timing", "delays", "random")
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)

def login_steam(username, password):
    """Steam账户登录"""
    try:
        # 终止现有Steam进程
        kill_process("steam.exe")
        random_delay()

        # 通过命令行登录
        cmd = [config.get("steam", "path"), "-login", username, password]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[{datetime.now()}] 正在登录账户: {username}")

        # 等待登录完成
        time.sleep(config.get("timing", "login_delay"))
        
        # 检查Steam进程是否运行
        if not any(p.info['name'] == 'steam.exe' for p in psutil.process_iter(['name'])):
            raise Exception("Steam客户端启动失败")
            
    except Exception as e:
        print(f"登录失败: {str(e)}")
        raise

def handle_eula_agreement():
    """处理用户协议界面"""
    print(">> 正在检测用户协议界面...")
    try:
        # 构建按钮路径
        btn_path = os.path.join(
            config.get("paths", "button_images"),
            config.get("buttons", "eula_agree")
        )
        pyautogui.FAILSAFE=False
        # 全屏检索同意按钮
        agree_btn = pyautogui.locateOnScreen(
            btn_path,
            confidence=config.get("timing", "agreement", "confidence"),
            grayscale=True,
            minSearchTime=config.get("timing", "agreement", "search_time")
        )

        if agree_btn:
            # 拟人化点击操作
            x, y = pyautogui.center(agree_btn)
            move_duration = random.uniform(*config.get("timing", "delays", "post_click"))
            pyautogui.moveTo(x, y, duration=move_duration)
            pyautogui.click()
            print("<< 成功点击协议同意按钮")
            return True
        
        print("未检测到协议界面")
        return False

    except pyautogui.ImageNotFoundException:
        print("-- 全屏未找到协议按钮")
        return False
    except Exception as e:
        print(f"协议检测异常: {str(e)}")
        return False

def validate_screenshot_size(img_path):
    """验证截图尺寸有效性"""
    from PIL import Image
    try:
        screen_w, screen_h = pyautogui.size()
        img = Image.open(img_path)
        
        # 验证规则：不超过屏幕尺寸的1/4
        max_w = screen_w // 4
        max_h = screen_h // 4
        if img.width > max_w or img.height > max_h:
            print(f"截图尺寸过大（{img.width}x{img.height}），建议重新截取")
            return False
        return True
    except Exception as e:
        print(f"截图验证失败: {str(e)}")
        return False

def launch_game():
    """启动游戏主流程"""
    try:
        # 初始化按钮配置
        button_config = config.get("buttons", "config")
        button_images = {
            "start_game": os.path.join(
                config.get("paths", "button_images"),
                config.get("buttons", "start_game")
            ),
            "agreement": os.path.join(
                config.get("paths", "button_images"),
                config.get("buttons", "agreement")
            )
        }

        # 文件预检
        for btn_type in ["start_game", "agreement"]:
            if not os.path.exists(button_images[btn_type]):
                raise FileNotFoundError(f"按钮截图缺失: {button_images[btn_type]}")

        # 启动游戏进程
        subprocess.Popen([
            config.get("steam", "path"),
            "-applaunch",
            config.get("steam", "game_id")
        ])
        print(f"[{datetime.now()}] 游戏启动命令已发送")

        # 进程监控
        game_started = False
        start_time = time.time()
        process_cfg = config.get("timing", "process_check")
        
        max_attempts = 3  # 最大检测次数
        attempt = 0       # 当前尝试次数
        game_started = False

        while time.time() - start_time < process_cfg["timeout"]:
            if any(p.info['name'].lower() == config.get("steam", "process_name").lower()
                for p in psutil.process_iter(['name'])):
                game_started = True
                break
            
            attempt += 1
            print(f"等待游戏进程启动...（尝试 {attempt}/{max_attempts}）")
            
            if attempt >= max_attempts:
                print("检测到游戏进程未启动，处理协议")
                # 处理用户协议
                agreement_handled = handle_eula_agreement()
                print(f"协议处理状态: {'成功' if agreement_handled else '未检测到'}")
                break
            
            time.sleep(process_cfg["interval"])

        if not game_started:
            raise Exception(f"进程启动超时（{process_cfg['timeout']}秒）")

        print("游戏进程启动成功")
        time.sleep(random.uniform(*config.get("timing", "delays", "game_loading")))



        # 智能点击流程
        def smart_click(btn_type):
            cfg = button_config[btn_type]
            print(f"[{btn_type}] 最大重试次数: {cfg['retries']}")
            
            for attempt in range(cfg["retries"]):
                try:
                    print(f"尝试 {attempt+1}/{cfg['retries']}")
                    location = pyautogui.locateOnScreen(
                        button_images[btn_type],
                        confidence=max(0.7, 0.85 - attempt*0.05),
                        grayscale=True,
                        minSearchTime=1 + attempt
                    )
                    
                    if location:
                        center = pyautogui.center(location)
                        pyautogui.moveTo(center, duration=random.uniform(0.5, 1.2))
                        pyautogui.click()
                        time.sleep(random.uniform(*cfg["post_delay"]))
                        return True
                    time.sleep(min(2 + attempt*3, 10))
                except pyautogui.ImageNotFoundException:
                    continue
            return False

        # 执行点击流程
        if not smart_click("start_game"):
            raise Exception("无法进入游戏主界面")

        try:
            if button_config["agreement"]["optional"]:
                smart_click("agreement")
        except Exception as e:
            print(f"可选步骤跳过: {str(e)}")

        # 最终验证
        print("验证游戏状态...")
        delay_min, delay_max = config.get("timing", "final_validation", "delay_range")
        validation_delay = random.uniform(delay_min, delay_max)
        print(f"最终验证等待时长: {validation_delay:.1f}秒")
        time.sleep(validation_delay)

        if not is_process_running(config.get("steam", "process_name")):
            raise Exception(f"游戏进程 {config.get('steam', 'process_name')} 未运行")
        
        print("游戏启动完成")
        return True

    except Exception as e:
        print(f"游戏启动失败: {str(e)}")
        debug_img = pyautogui.screenshot()
        debug_path = os.path.join(
            config.get("paths", "debug"),
            f"failure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        debug_img.save(debug_path)
        print(f"调试截图已保存至: {debug_path}")
        raise

def capture_ban_info(username):
    """封禁信息检测"""
    try:
        # 截图处理
        screenshot = ImageGrab.grab()
        screenshot_dir = config.get("paths", "screenshots")
        screenshot_path = os.path.join(
            screenshot_dir,
            f"{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
        )
        screenshot.save(screenshot_path)

        # 图像处理
        img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)

        # OCR识别
        text = pytesseract.image_to_string(thresh, lang='chi_sim+eng').strip()
        
        # 封禁状态分析
        ban_status = {
            "is_banned": False,
            "duration": "未知",
            "unban_time": "未知",
            "screenshot": screenshot_path,
            "raw_text": text
        }

        # 检测封禁关键词
        keywords = ["封禁", "封停", "解封", "Ban", "Duration"]
        if any(kw in text for kw in keywords):
            ban_status["is_banned"] = True
            
            # 提取详细信息
            patterns = [
                (r"(\d+)天", "duration"),
                (r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", "unban_time"),
                (r"(\d+ days \d+ hours)", "duration")
            ]
            for pattern, field in patterns:
                if match := re.search(pattern, text):
                    ban_status[field] = match.group(1)

        return ban_status

    except Exception as e:
        print(f"封禁检测异常: {str(e)}")
        return {
            "is_banned": False,
            "error": str(e),
            "screenshot": ""
        }

def logout_steam():
    """退出当前账号"""
    try:
        processes = ["steam.exe", config.get("steam", "process_name")]
        processes.extend(config.get("steam", "child_processes"))
        
        for proc in processes:
            kill_process(proc)
        
        print("已退出当前账号")
        time.sleep(random.uniform(5, 10))
    except Exception as e:
        print(f"退出失败: {str(e)}")

def main():
    print("售后反馈交流群1047597689")
    print("请先看使用说明")
    """主执行流程"""
    if not check_tesseract():
        return

    for idx, acc in enumerate(config.get("accounts")):
        print(f"\n{'='*40}")
        print(f"处理账号 ({idx+1}/{len(config.get('accounts'))}): {acc['username']}")
        
        try:
            login_steam(acc['username'], acc['password'])
            launch_game()
            
            # 封禁检测，这里我给了15秒开游戏
            time.sleep(15)
            ban_info = capture_ban_info(acc['username'])
            
            # 记录日志
            log_msg = f"{datetime.now()}, {acc['username']}, "
            if ban_info["is_banned"]:
                log_msg += f"封禁 | 时长:{ban_info['duration']} | 解封:{ban_info['unban_time']}"
                print(f"!!! 封禁警报 !!! 详情: {ban_info['raw_text'][:50]}...")
            else:
                log_msg += "正常"
            
            with open("result.log", "a", encoding="utf-8") as f:
                f.write(log_msg + "\n")
                
        except Exception as e:
            print(f"流程异常: {str(e)}")
        finally:
            logout_steam()

if __name__ == "__main__":
    # OCR初始化
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建 Tesseract 的相对路径（假设 tesseract.exe 在项目根目录的 tesseract-ocr 文件夹下）
    tesseract_path = os.path.join(current_dir, "tesseract-ocr", "tesseract.exe")
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    main()
    print("\n所有账号处理完成")
    input("输入任意字符结束")