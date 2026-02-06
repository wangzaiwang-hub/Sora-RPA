#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sora 自动化核心模块
使用 ixBrowser 官方 API + Selenium
"""

import time
import os
from ixbrowser_local_api import IXBrowserClient
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class SoraAutomation:
    def __init__(self, profile_id=None):
        """
        初始化 Sora 自动化工具
        
        Args:
            profile_id: ixBrowser 窗口 ID，如果为 None 则使用第一个窗口
        """
        self.client = IXBrowserClient()
        self.profile_id = profile_id
        self.driver = None
        self.debugging_address = None
        self.is_mobile = None  # 是否为手机UA
        
        # 创建错误截图保存目录
        self.error_screenshot_dir = os.path.join(os.path.dirname(__file__), '..', 'err_picture')
        os.makedirs(self.error_screenshot_dir, exist_ok=True)
    
    def _save_error_screenshot(self, prefix='error'):
        """保存错误截图到指定目录"""
        try:
            timestamp = int(time.time())
            filename = f'{prefix}_screenshot_{timestamp}.png'
            filepath = os.path.join(self.error_screenshot_dir, filename)
            self.driver.save_screenshot(filepath)
            print(f'  已保存截图: {filepath}')
            return filepath
        except Exception as e:
            print(f'  保存截图失败: {e}')
            return None
        
    def _get_profile_id(self):
        """获取窗口 ID - 优先使用窗口 23"""
        if self.profile_id:
            return self.profile_id
        
        # 直接尝试使用窗口 23
        print('  尝试使用窗口 23...')
        
        # 验证窗口 23 是否存在
        all_profiles = self.client.get_profile_list(limit=100)
        if all_profiles:
            for profile in all_profiles:
                if profile['profile_id'] == 23:
                    print(f'  ✓ 找到窗口 23: {profile.get("name")}')
                    return 23
        
        # 如果没找到，直接返回 23（让后续流程尝试打开）
        print('  ⚠️  窗口 23 不在列表中，但仍尝试使用')
        return 23
    
    def _open_browser(self):
        """打开浏览器窗口"""
        profile_id = self._get_profile_id()
        
        print(f'  连接到 ixBrowser 窗口: {profile_id}')
        
        # 尝试打开窗口（如果已打开会返回错误，但我们会处理）
        try:
            open_result = self.client.open_profile(
                profile_id,
                cookies_backup=False,
                load_profile_info_page=False
            )
        except Exception as e:
            print(f'  ❌ 打开窗口失败: {e}')
            raise
        
        # 如果窗口已经打开
        if open_result is None and self.client.message:
            error_msg = str(self.client.message).lower()
            if 'already open' in error_msg or '已经打开' in error_msg or '已打开' in error_msg:
                print('  ✓ 窗口已打开，获取连接信息...')
                
                # 再次尝试调用 API，有时会返回连接信息
                time.sleep(0.5)
                open_result = self.client.open_profile(
                    profile_id,
                    cookies_backup=False,
                    load_profile_info_page=False
                )
                
                # 如果还是失败，说明无法获取连接信息，需要重启窗口
                if open_result is None:
                    print('  ⚠️  无法获取连接信息，尝试重启窗口')
                    print('  关闭窗口...')
                    
                    close_result = self.client.close_profile(profile_id)
                    if close_result:
                        print('  ✓ 窗口已关闭')
                        time.sleep(3)
                    else:
                        error_msg = str(self.client.message).lower()
                        print(f'  ⚠️  关闭失败: {self.client.message}')
                        
                        # 检查是否是"进程不存在"的错误
                        if 'process not found' in error_msg or '进程不存在' in error_msg:
                            print('  ℹ️  窗口进程不存在，可能已经被手动关闭')
                            print('  等待 5 秒让 ixBrowser 清理状态...')
                            time.sleep(5)
                            print('  尝试直接打开窗口...')
                        else:
                            print('  ⚠️  窗口可能不是通过 API 打开的，无法控制')
                            print('  提示: 请手动关闭窗口，或使用其他窗口')
                            raise Exception(f'无法控制已打开的窗口 {profile_id}，请手动关闭或选择其他窗口')
                    
                    print('  重新打开窗口...')
                    max_retries = 3
                    for retry in range(max_retries):
                        try:
                            open_result = self.client.open_profile(
                                profile_id,
                                cookies_backup=False,
                                load_profile_info_page=False
                            )
                            print(f'  重新打开结果 (尝试 {retry + 1}/{max_retries}): {open_result}')
                            print(f'  API 消息: {self.client.message}')
                            
                            # 如果成功获取到连接信息，跳出循环
                            if open_result and 'webdriver' in open_result:
                                print(f'  ✓ 第 {retry + 1} 次尝试成功')
                                break
                            
                            # 如果还是说窗口已打开，尝试强制关闭
                            if open_result is None and self.client.message:
                                msg = str(self.client.message).lower()
                                if 'already open' in msg or '已经打开' in msg or '已打开' in msg:
                                    print(f'  ⚠️  第 {retry + 1} 次尝试：窗口仍显示为已打开')
                                    if retry < max_retries - 1:
                                        print(f'  等待 3 秒后重试...')
                                        time.sleep(3)
                                        # 再次尝试关闭
                                        print(f'  再次尝试关闭窗口...')
                                        self.client.close_profile(profile_id)
                                        time.sleep(2)
                                    continue
                            
                        except Exception as e:
                            print(f'  ❌ 第 {retry + 1} 次尝试失败: {e}')
                            if retry < max_retries - 1:
                                print(f'  等待 3 秒后重试...')
                                time.sleep(3)
                            else:
                                raise
                    
                    if open_result is None:
                        error_detail = f'打开窗口失败（已重试 {max_retries} 次）: {self.client.message}'
                        print(f'  ❌ {error_detail}')
                        print(f'  💡 建议：请在 ixBrowser 客户端中手动关闭窗口 {profile_id}，然后重试')
                        raise Exception(error_detail)
                    
                    print('  ✓ 窗口已重新打开')
            else:
                # 其他错误
                error_detail = f'打开窗口失败: {self.client.message}'
                print(f'  ❌ {error_detail}')
                raise Exception(error_detail)
        
        else:
            # 窗口成功打开
            print('  ✓ 窗口已打开')
        
        # 验证 open_result 是否有效
        if not open_result:
            error_detail = f'无法获取窗口连接信息，open_result 为空'
            print(f'  ❌ {error_detail}')
            raise Exception(error_detail)
        
        if 'webdriver' not in open_result or 'debugging_address' not in open_result:
            error_detail = f'窗口连接信息不完整: {open_result}'
            print(f'  ❌ {error_detail}')
            raise Exception(error_detail)
        
        # 获取连接信息
        web_driver_path = open_result['webdriver']
        self.debugging_address = open_result['debugging_address']
        
        print(f'  调试地址: {self.debugging_address}')
        print(f'  WebDriver 路径: {web_driver_path}')
        
        # 连接到浏览器
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", self.debugging_address)
        
        print('  正在连接 Selenium...')
        self.driver = Chrome(
            service=Service(web_driver_path),
            options=chrome_options
        )
        
        print('  ✓ Selenium 已连接')
        
        # 检测UA类型
        self._detect_ua_type()
    
    def _detect_ua_type(self):
        """检测UA类型（电脑或手机）"""
        try:
            user_agent = self.driver.execute_script("return navigator.userAgent;")
            print(f'  User Agent: {user_agent}')
            
            # 检测是否为移动设备UA
            mobile_keywords = ['Mobile', 'Android', 'iPhone', 'iPad', 'iPod', 'Windows Phone']
            self.is_mobile = any(keyword in user_agent for keyword in mobile_keywords)
            
            print(f'  UA类型: {"手机" if self.is_mobile else "电脑"}')
        except Exception as e:
            print(f'  检测UA失败: {e}，默认使用电脑模式')
            self.is_mobile = False

    
    def _check_login_status(self):
        """检测窗口是否已登录"""
        try:
            print('  检测登录状态...')
            
            # 等待页面加载
            time.sleep(2)
            
            current_url = self.driver.current_url
            print(f'  当前页面: {current_url}')
            
            # 检查是否在 Sora 页面
            if 'sora.chatgpt.com' in current_url.lower():
                print('  ✓ 已在 Sora 页面，账号已登录')
                return True
            
            # 检查是否在登录页面
            if 'auth' in current_url.lower() or 'login' in current_url.lower():
                print('  ⚠️  在登录页面，需要登录')
                return False
            
            # 尝试访问 Sora 页面来验证登录状态
            print('  尝试访问 Sora 页面验证登录状态...')
            self.driver.get('https://sora.chatgpt.com/explore')
            time.sleep(3)
            
            current_url = self.driver.current_url
            if 'sora.chatgpt.com' in current_url.lower():
                print('  ✓ 成功访问 Sora 页面，账号已登录')
                return True
            else:
                print('  ⚠️  无法访问 Sora 页面，需要登录')
                return False
                
        except Exception as e:
            print(f'  检测登录状态失败: {e}')
            return False
    
    def _login_account(self, username: str, password: str):
        """登录账号"""
        try:
            print(f'  开始登录账号: {username}')
            
            # 导航到登录页面
            self.driver.get('https://chatgpt.com/auth/login')
            time.sleep(3)
            
            # 这里需要根据实际的登录页面结构来实现登录逻辑
            # 由于 ChatGPT 的登录流程比较复杂，建议手动登录一次
            # 或者使用 cookies 来保持登录状态
            
            print('  ⚠️  请手动完成登录流程')
            print('  提示: 建议在 ixBrowser 中预先登录账号，系统会自动检测登录状态')
            
            # 等待用户手动登录（可选）
            # input('  登录完成后按回车继续...')
            
            return True
            
        except Exception as e:
            print(f'  登录失败: {e}')
            return False
    
    def _navigate_to_sora(self):
        """导航到 Sora 页面"""
        sora_url = 'https://sora.chatgpt.com/explore'
        
        try:
            # 等待页面加载完成
            time.sleep(1)
            
            current_url = self.driver.current_url
            print(f'  当前页面: {current_url}')
            
            # 检查是否已经在 Sora 页面
            if 'sora.chatgpt.com' in current_url.lower():
                print('  ✓ 已在 Sora 页面，跳过导航')
                return
            
            # 需要导航到 Sora
            print(f'  导航到 Sora: {sora_url}')
            
            # 设置页面加载超时
            self.driver.set_page_load_timeout(30)
            
            try:
                self.driver.get(sora_url)
            except Exception as nav_error:
                print(f'  ⚠️  导航超时或失败: {nav_error}')
                # 尝试停止加载
                try:
                    self.driver.execute_script("window.stop();")
                except:
                    pass
            
            # 等待页面加载
            time.sleep(3)
            
            # 验证导航成功
            try:
                new_url = self.driver.current_url
                if 'sora.chatgpt.com' in new_url.lower():
                    print('  ✓ 导航完成')
                else:
                    print(f'  ⚠️  当前 URL: {new_url}')
                    print('  提示: 可能需要手动登录或处理页面')
            except:
                print('  ⚠️  无法获取当前 URL')
            
        except Exception as e:
            print(f'  ⚠️  导航时出现问题: {e}')
            # 不抛出异常，继续执行
            print('  尝试继续...')
    
    def _click_create_button(self):
        """点击创建视频按钮"""
        try:
            print('  查找"创建视频"按钮...')
            # 查找"创建视频"按钮
            buttons = self.driver.find_elements(By.TAG_NAME, 'button')
            for btn in buttons:
                try:
                    if '创建视频' in btn.text or 'Create' in btn.text:
                        print('  点击"创建视频"按钮')
                        btn.click()
                        time.sleep(2)
                        return True
                except:
                    continue
            
            print('  未找到"创建视频"按钮，可能已在创建页面')
            return True  # 返回 True 继续执行
        except Exception as e:
            print(f'  查找按钮时出错: {e}')
            return True  # 返回 True 继续执行

    
    def _paste_image(self, image_data):
        """
        粘贴图片到输入框
        
        Args:
            image_data: 图片数据，支持以下格式：
                - URL字符串: "https://example.com/image.jpg"
                - Base64字符串: "data:image/jpeg;base64,/9j/4AAQ..."
                - 本地文件路径: "C:/path/to/image.jpg"
        """
        print('  准备粘贴图片...')
        print(f'  图片数据类型: {type(image_data)}')
        
        try:
            import requests
            import base64
            from io import BytesIO
            
            # 1. 将图片转换为Base64格式
            base64_image = None
            
            if image_data.startswith('data:image'):
                # 已经是Base64格式
                print('  图片已是Base64格式')
                base64_image = image_data
            elif image_data.startswith('http://') or image_data.startswith('https://'):
                # 从URL下载图片
                print(f'  从URL下载图片: {image_data[:50]}...')
                response = requests.get(image_data, timeout=10)
                if response.status_code == 200:
                    # 转换为Base64
                    image_bytes = response.content
                    base64_str = base64.b64encode(image_bytes).decode('utf-8')
                    
                    # 检测图片类型
                    content_type = response.headers.get('Content-Type', 'image/jpeg')
                    base64_image = f'data:{content_type};base64,{base64_str}'
                    print(f'  ✓ 图片已下载并转换为Base64 (大小: {len(base64_str)} 字符)')
                else:
                    raise Exception(f'下载图片失败: HTTP {response.status_code}')
            else:
                # 假设是本地文件路径
                print(f'  读取本地文件: {image_data}')
                with open(image_data, 'rb') as f:
                    image_bytes = f.read()
                    base64_str = base64.b64encode(image_bytes).decode('utf-8')
                    
                    # 根据文件扩展名判断类型
                    if image_data.lower().endswith('.png'):
                        mime_type = 'image/png'
                    elif image_data.lower().endswith('.jpg') or image_data.lower().endswith('.jpeg'):
                        mime_type = 'image/jpeg'
                    elif image_data.lower().endswith('.gif'):
                        mime_type = 'image/gif'
                    else:
                        mime_type = 'image/jpeg'
                    
                    base64_image = f'data:{mime_type};base64,{base64_str}'
                    print(f'  ✓ 本地图片已转换为Base64 (大小: {len(base64_str)} 字符)')
            
            if not base64_image:
                raise Exception('无法获取图片的Base64数据')
            
            # 2. 查找输入区域（textarea或可编辑div）
            print('  查找输入区域...')
            target_element = None
            
            # 尝试查找textarea
            try:
                textareas = self.driver.find_elements(By.TAG_NAME, 'textarea')
                for ta in textareas:
                    if ta.is_displayed():
                        target_element = ta
                        print('  ✓ 找到textarea输入框')
                        break
            except:
                pass
            
            # 如果没找到textarea，尝试查找contenteditable的div
            if not target_element:
                try:
                    editable_divs = self.driver.find_elements(By.CSS_SELECTOR, '[contenteditable="true"]')
                    for div in editable_divs:
                        if div.is_displayed():
                            target_element = div
                            print('  ✓ 找到contenteditable输入框')
                            break
                except:
                    pass
            
            if not target_element:
                raise Exception('未找到输入区域')
            
            # 3. 使用JavaScript模拟粘贴图片
            print('  使用JavaScript模拟粘贴图片...')
            
            # 方法：直接从Base64创建Blob，不使用fetch
            paste_script = """
            function pasteImage(element, base64Data) {
                try {
                    // 从Base64 Data URL中提取数据
                    const parts = base64Data.split(',');
                    const mimeType = parts[0].match(/:(.*?);/)[1];
                    const base64String = parts[1];
                    
                    // 将Base64转换为二进制数据
                    const binaryString = atob(base64String);
                    const bytes = new Uint8Array(binaryString.length);
                    for (let i = 0; i < binaryString.length; i++) {
                        bytes[i] = binaryString.charCodeAt(i);
                    }
                    
                    // 创建Blob
                    const blob = new Blob([bytes], { type: mimeType });
                    
                    // 创建File对象
                    const file = new File([blob], 'pasted-image.jpg', { type: mimeType });
                    
                    // 创建DataTransfer对象
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(file);
                    
                    // 聚焦元素
                    element.focus();
                    
                    // 创建并触发paste事件
                    const pasteEvent = new ClipboardEvent('paste', {
                        bubbles: true,
                        cancelable: true,
                        clipboardData: dataTransfer
                    });
                    
                    element.dispatchEvent(pasteEvent);
                    
                    return true;
                } catch (error) {
                    console.error('粘贴图片失败:', error);
                    return false;
                }
            }
            
            return pasteImage(arguments[0], arguments[1]);
            """
            
            result = self.driver.execute_script(paste_script, target_element, base64_image)
            
            if result:
                print('  ✓ 图片粘贴成功')
                time.sleep(2)  # 等待图片上传
                return True
            else:
                print('  ⚠️  粘贴事件已触发，但返回false')
                time.sleep(2)
                # 不抛出异常，继续执行
                return True
                
        except Exception as e:
            print(f'  ✗ 粘贴图片失败: {e}')
            import traceback
            traceback.print_exc()
            self._save_error_screenshot('paste_image_error')
            raise
    
    def _input_prompt(self, prompt):
        """输入提示词 - 根据UA类型使用不同策略"""
        print('  输入提示词...')
        print(f'  提示词内容: {prompt[:100]}{"..." if len(prompt) > 100 else ""}')
        print(f'  提示词长度: {len(prompt)} 字符')
        print(f'  当前UA类型: {"手机" if self.is_mobile else "电脑"}')
        
        if self.is_mobile:
            return self._input_prompt_mobile(prompt)
        else:
            return self._input_prompt_desktop(prompt)
    
    def _input_prompt_mobile(self, prompt):
        """手机UA的输入策略 - JavaScript输入 + 真实点击混合"""
        print('  使用手机UA输入策略（JavaScript + 真实点击混合）...')
        print('  [INFO] 手机端send_keys会卡住，使用JavaScript输入')
        
        try:
            from selenium.webdriver.common.keys import Keys
            
            # 等待页面完全加载
            print('  [DEBUG] 等待页面加载...')
            time.sleep(3)
            
            # 查找输入框 - 使用多种方法
            print('  [DEBUG] 查找输入框...')
            textarea = None
            
            # 方法1: 通过placeholder包含"Describe"
            try:
                textarea = self.driver.find_element(By.CSS_SELECTOR, 'textarea[placeholder*="Describe"]')
                print('  ✓ 找到输入框（方法1: placeholder包含Describe）')
            except:
                pass
            
            # 方法2: 通过placeholder包含"video"
            if not textarea:
                try:
                    textarea = self.driver.find_element(By.CSS_SELECTOR, 'textarea[placeholder*="video"]')
                    print('  ✓ 找到输入框（方法2: placeholder包含video）')
                except:
                    pass
            
            # 方法3: 通过class包含rounded-md的textarea
            if not textarea:
                try:
                    textarea = self.driver.find_element(By.CSS_SELECTOR, 'textarea.rounded-md')
                    print('  ✓ 找到输入框（方法3: class包含rounded-md）')
                except:
                    pass
            
            # 方法4: 查找所有textarea，使用第一个可见的
            if not textarea:
                try:
                    textareas = self.driver.find_elements(By.TAG_NAME, 'textarea')
                    print(f'  [DEBUG] 找到 {len(textareas)} 个 textarea 元素')
                    
                    for i, ta in enumerate(textareas):
                        try:
                            if ta.is_displayed():
                                textarea = ta
                                print(f'  ✓ 找到输入框（方法4: 第{i+1}个可见textarea）')
                                break
                        except:
                            continue
                except:
                    pass
            
            # 如果还是没找到，报错（手机UA）
            if not textarea:
                print('  [ERROR] 所有方法都未找到输入框')
                self._save_error_screenshot('mobile_input_notfound')
                raise Exception('未找到任何输入框')
            
            print('  ✓ 找到输入框，准备输入')
            
            # 步骤1: 使用JavaScript快速点击（不会卡）
            print('  [DEBUG] 使用JavaScript点击输入框...')
            for i in range(2):
                try:
                    self.driver.execute_script("arguments[0].click(); arguments[0].focus();", textarea)
                    time.sleep(0.2)
                    print(f'  ✓ 第{i+1}次JavaScript点击完成')
                except Exception as e:
                    print(f'  [DEBUG] 第{i+1}次点击失败: {e}')
            
            print('  [DEBUG] 准备输入')
            
            # 步骤2: 使用JavaScript输入（避免send_keys卡住）
            print('  [DEBUG] 使用JavaScript输入提示词...')
            print(f'  [DEBUG] 提示词: {prompt[:50]}{"..." if len(prompt) > 50 else ""}')
            try:
                self.driver.execute_script("""
                    var textarea = arguments[0];
                    var text = arguments[1];
                    
                    // 清空
                    textarea.value = '';
                    textarea.textContent = '';
                    
                    // 聚焦
                    textarea.focus();
                    
                    // 设置值（多种方式）
                    textarea.value = text;
                    textarea.textContent = text;
                    textarea.innerHTML = text;
                    
                    // 触发事件（模拟真实输入）
                    textarea.dispatchEvent(new Event('input', { bubbles: true }));
                    textarea.dispatchEvent(new Event('change', { bubbles: true }));
                    textarea.dispatchEvent(new Event('keyup', { bubbles: true }));
                    
                    // 保持焦点
                    textarea.focus();
                """, textarea, prompt)
                time.sleep(0.5)
                print('  ✓ JavaScript输入完成')
            except Exception as e:
                print(f'  [ERROR] JavaScript输入失败: {e}')
                raise
            
            # 验证输入（检查多个属性）
            print('  [DEBUG] 验证输入结果...')
            current_value = textarea.get_attribute('value') or textarea.get_attribute('textContent') or textarea.text or ''
            print(f'  验证输入结果: 当前长度 {len(current_value)}, 目标长度 {len(prompt)}')
            
            # 如果验证失败，尝试截图但不抛出异常（继续执行）
            if len(current_value) == 0:
                print('  ⚠️  输入验证失败，但继续执行（可能是检测方式问题）')
                self._save_error_screenshot('mobile_input_verify_failed')
            else:
                print(f'  ✓ 输入验证成功（当前长度: {len(current_value)}）')
            
            # 步骤3: 等待一下让页面响应
            print('  [DEBUG] 等待页面响应...')
            time.sleep(1)
            
            # 步骤4: 直接查找并点击发送按钮（手机端最可靠的方法）
            print('  [DEBUG] 查找发送按钮...')
            send_success = False
            
            try:
                # 查找所有按钮
                buttons = self.driver.find_elements(By.TAG_NAME, 'button')
                print(f'  找到 {len(buttons)} 个按钮元素')
                
                # 查找可用的发送按钮（通常是圆形按钮，且未禁用）
                for btn in buttons:
                    try:
                        # 检查按钮是否可见
                        if not btn.is_displayed():
                            continue
                        
                        # 检查是否禁用
                        disabled = btn.get_attribute('disabled')
                        aria_disabled = btn.get_attribute('aria-disabled')
                        
                        if disabled or aria_disabled == 'true':
                            continue
                        
                        # 检查class（通常发送按钮有rounded-full类）
                        class_name = btn.get_attribute('class') or ''
                        
                        if 'rounded-full' in class_name or 'send' in class_name.lower():
                            print(f'  [DEBUG] 找到可能的发送按钮: {class_name[:50]}...')
                            
                            # 尝试点击（使用JavaScript更可靠）
                            try:
                                self.driver.execute_script("arguments[0].click();", btn)
                                print('  ✓ 发送按钮已点击（JavaScript）')
                                send_success = True
                                time.sleep(1)
                                break
                            except Exception as e:
                                print(f'  [DEBUG] JavaScript点击失败: {e}，尝试常规点击')
                                try:
                                    btn.click()
                                    print('  ✓ 发送按钮已点击（常规方法）')
                                    send_success = True
                                    time.sleep(1)
                                    break
                                except:
                                    pass
                    except:
                        continue
                
                if not send_success:
                    print('  [WARNING] 未找到可用的发送按钮')
                    # 尝试使用回车键作为备选方案
                    print('  [DEBUG] 尝试使用回车键发送...')
                    try:
                        self.driver.execute_script("""
                            var textarea = arguments[0];
                            textarea.focus();
                            
                            // 触发回车键事件
                            var event = new KeyboardEvent('keydown', {
                                key: 'Enter',
                                code: 'Enter',
                                keyCode: 13,
                                which: 13,
                                bubbles: true,
                                cancelable: true
                            });
                            textarea.dispatchEvent(event);
                        """, textarea)
                        time.sleep(1)
                        print('  ✓ 回车键已触发')
                        send_success = True
                    except Exception as e:
                        print(f'  [DEBUG] 回车键触发失败: {e}')
                        
            except Exception as e:
                print(f'  [ERROR] 查找发送按钮失败: {e}')
            
            if not send_success:
                print('  [WARNING] 无法确认消息是否发送，请检查浏览器')
            
            print('  [DEBUG] 手机端输入流程完成')
            return True
            
        except Exception as e:
            print(f'  [ERROR] 手机UA输入失败: {e}')
            print(f'  [ERROR] 错误类型: {type(e).__name__}')
            import traceback
            traceback.print_exc()
            self._save_error_screenshot('mobile_input_error')
            raise
            raise

    
    def _input_prompt_desktop(self, prompt):
        """电脑UA的输入策略 - 真实点击和键盘输入"""
        print('  使用电脑UA输入策略...')
        
        try:
            # 等待页面完全加载
            time.sleep(2)
            
            # 查找输入框 - 使用多种方法
            print('  查找输入框...')
            textarea = None
            
            # 方法1: 通过placeholder包含"Describe"
            try:
                textarea = self.driver.find_element(By.CSS_SELECTOR, 'textarea[placeholder*="Describe"]')
                print('  ✓ 找到输入框（方法1: placeholder包含Describe）')
            except:
                pass
            
            # 方法2: 通过placeholder包含"video"
            if not textarea:
                try:
                    textarea = self.driver.find_element(By.CSS_SELECTOR, 'textarea[placeholder*="video"]')
                    print('  ✓ 找到输入框（方法2: placeholder包含video）')
                except:
                    pass
            
            # 方法3: 通过class包含rounded-md的textarea
            if not textarea:
                try:
                    textarea = self.driver.find_element(By.CSS_SELECTOR, 'textarea.rounded-md')
                    print('  ✓ 找到输入框（方法3: class包含rounded-md）')
                except:
                    pass
            
            # 方法4: 查找所有textarea，使用第一个可见的
            if not textarea:
                try:
                    textareas = self.driver.find_elements(By.TAG_NAME, 'textarea')
                    print(f'  找到 {len(textareas)} 个 textarea 元素')
                    
                    for i, ta in enumerate(textareas):
                        try:
                            if ta.is_displayed():
                                textarea = ta
                                print(f'  ✓ 找到输入框（方法4: 第{i+1}个可见textarea）')
                                break
                        except:
                            continue
                except:
                    pass
            
            # 如果还是没找到，报错（电脑UA）
            if not textarea:
                print('  [ERROR] 所有方法都未找到输入框')
                self._save_error_screenshot('desktop_input_notfound')
                raise Exception('未找到任何输入框')
            
            print('  找到输入框，准备输入')
            
            # 步骤1: 先清空输入框
            print('  清空输入框...')
            try:
                textarea.clear()
                time.sleep(0.3)
                print('  ✓ 输入框已清空')
            except Exception as e:
                print(f'  清空输入框失败: {e}，继续执行...')
            
            # 步骤2: 真实点击输入框（激活输入框）
            print('  真实点击输入框（激活）...')
            try:
                textarea.click()
                time.sleep(0.5)
                print('  ✓ 输入框已激活')
            except Exception as e:
                print(f'  点击输入框失败: {e}')
                raise
            
            # 步骤3: 使用 send_keys 真实输入（模拟键盘输入）
            print('  使用 send_keys 真实输入...')
            from selenium.webdriver.common.keys import Keys
            try:
                textarea.send_keys(prompt)
                time.sleep(0.5)
                print('  ✓ 提示词已输入')
            except Exception as e:
                print(f'  输入失败: {e}')
                raise
            
            # 验证输入是否成功
            current_value = textarea.get_attribute('value') or ''
            print(f'  验证输入结果: 当前长度 {len(current_value)}, 目标长度 {len(prompt)}')
            
            if len(current_value) == 0:
                print('  ⚠️  输入验证失败，输入框仍为空')
                self._save_error_screenshot('desktop_input_verify_failed')
                raise Exception('输入后验证失败，输入框仍为空')
            
            print(f'  ✓ 输入验证成功（当前长度: {len(current_value)}）')
            
            # 步骤4: 再次点击输入框（确保焦点在输入框上）
            print('  再次点击输入框（确保焦点）...')
            try:
                textarea.click()
                time.sleep(0.3)
                print('  ✓ 焦点已确认')
            except Exception as e:
                print(f'  再次点击失败: {e}，继续执行...')
            
            # 步骤5: 按回车键发送
            print('  按回车键发送...')
            try:
                textarea.send_keys(Keys.RETURN)
                time.sleep(1)
                print('  ✓ 已按回车键发送')
            except Exception as e:
                print(f'  按回车键失败: {e}')
                raise
            
            return True
            
        except Exception as e:
            print(f'  电脑UA输入失败: {e}')
            print(f'  错误类型: {type(e).__name__}')
            import traceback
            traceback.print_exc()
            self._save_error_screenshot('desktop_input_error')
            raise

    
    def _click_send_button(self):
        """点击发送按钮"""
        print('  查找发送按钮...')
        
        try:
            # 方法1: 查找带 sr-only 的按钮
            buttons = self.driver.find_elements(By.TAG_NAME, 'button')
            print(f'  找到 {len(buttons)} 个按钮元素')
            
            for btn in buttons:
                try:
                    sr_only_elements = btn.find_elements(By.CLASS_NAME, 'sr-only')
                    for sr_only in sr_only_elements:
                        if '创建视频' in sr_only.text or 'Create' in sr_only.text:
                            disabled = btn.get_attribute('data-disabled')
                            aria_disabled = btn.get_attribute('aria-disabled')
                            if disabled != 'true' and aria_disabled != 'true':
                                print('  找到发送按钮（sr-only方法），尝试点击...')
                                try:
                                    # 使用 JavaScript 点击，更可靠
                                    self.driver.execute_script("arguments[0].click();", btn)
                                    print('  ✓ 发送按钮已点击（JavaScript）')
                                    time.sleep(1)
                                    return True
                                except:
                                    # 如果 JS 点击失败，尝试常规点击
                                    btn.click()
                                    print('  ✓ 发送按钮已点击（常规方法）')
                                    time.sleep(1)
                                    return True
                except:
                    continue
            
            # 方法2: 查找圆形按钮
            print('  尝试查找圆形按钮...')
            for btn in buttons:
                try:
                    class_name = btn.get_attribute('class') or ''
                    if 'rounded-full' in class_name:
                        disabled = btn.get_attribute('data-disabled')
                        aria_disabled = btn.get_attribute('aria-disabled')
                        is_disabled = btn.get_attribute('disabled')
                        
                        if disabled != 'true' and aria_disabled != 'true' and not is_disabled:
                            print(f'  找到圆形按钮，class: {class_name[:50]}...')
                            try:
                                # 使用 JavaScript 点击
                                self.driver.execute_script("arguments[0].click();", btn)
                                print('  ✓ 发送按钮已点击（JavaScript）')
                                time.sleep(1)
                                return True
                            except:
                                btn.click()
                                print('  ✓ 发送按钮已点击（常规方法）')
                                time.sleep(1)
                                return True
                except:
                    continue
            
            # 方法3: 模拟按回车键
            print('  未找到可用按钮，尝试按回车键...')
            from selenium.webdriver.common.keys import Keys
            textareas = self.driver.find_elements(By.TAG_NAME, 'textarea')
            if textareas:
                print('  在输入框中按回车键...')
                textareas[0].send_keys(Keys.RETURN)
                print('  ✓ 已按回车键发送')
                time.sleep(1)
                return True
            
            # 方法4: 使用 JavaScript 触发表单提交
            print('  尝试使用 JavaScript 触发提交...')
            self.driver.execute_script("""
                // 查找输入框
                var textarea = document.querySelector('textarea');
                if (textarea) {
                    // 触发 Enter 键事件
                    var event = new KeyboardEvent('keydown', {
                        key: 'Enter',
                        code: 'Enter',
                        keyCode: 13,
                        which: 13,
                        bubbles: true
                    });
                    textarea.dispatchEvent(event);
                }
            """)
            print('  ✓ 已触发 Enter 键事件')
            time.sleep(1)
            return True
            
        except Exception as e:
            print(f'  点击发送按钮失败: {e}')
            import traceback
            traceback.print_exc()
            raise
    
    def _wait_for_video(self, timeout=None, progress_callback=None, task_id=None):
        """
        等待视频生成完成 - 只检测生成完成的通知
        
        Args:
            timeout: 超时时间（秒），None表示无限等待
            progress_callback: 进度回调函数
            task_id: 任务ID（用于从后端API检查进度）
        
        注意：不再尝试获取视频URL，URL将由插件通过提示词匹配来关联
        """
        print('  等待视频生成完成...')
        print('  注意：视频URL将由插件自动匹配，无需在此获取')
        print('  ⚠️  已禁用超时检测，将一直等待直到成功或失败')
        if task_id:
            print(f'  任务ID: {task_id}，将通过后端API检查进度')
        
        start_time = time.time()
        last_progress_report = 0
        notification_detected = False
        
        while True:  # 移除超时限制，无限等待
            try:
                elapsed = int(time.time() - start_time)
                
                # 计算进度（40%-90%之间，根据时间推算）
                if progress_callback and elapsed - last_progress_report >= 10:
                    # 假设生成需要300秒，线性增长
                    estimated_progress = min(40 + int((elapsed / 300) * 50), 90)
                    progress_callback(estimated_progress, f'视频生成中 ({elapsed}秒)')
                    last_progress_report = elapsed
                
                # 方法1: 检测右上角的成功通知弹窗
                if not notification_detected:
                    try:
                        # 查找可能的通知元素（通常包含"完成"、"成功"、"Complete"、"Success"等文字）
                        notification_keywords = ['完成', '成功', 'Complete', 'Success', 'finished', 'done']
                        
                        for keyword in notification_keywords:
                            # 查找包含关键词的元素
                            elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                            
                            for elem in elements:
                                try:
                                    if elem.is_displayed():
                                        # 检查元素位置是否在右上角（通常通知在页面右上角）
                                        location = elem.location
                                        size = self.driver.get_window_size()
                                        
                                        # 如果元素在页面右侧且靠近顶部，可能是通知
                                        if location['x'] > size['width'] * 0.5 and location['y'] < size['height'] * 0.3:
                                            print(f'  ✓ 检测到成功通知: {elem.text[:50]}...')
                                            notification_detected = True
                                            if progress_callback:
                                                progress_callback(95, '视频生成完成')
                                            break
                                except:
                                    continue
                            
                            if notification_detected:
                                break
                    except Exception as e:
                        if elapsed % 30 == 0:
                            print(f'  检查通知时出错: {e}')
                
                # 方法2: 通过后端API检查任务进度（从plug-renwu插件捕获的数据）
                if not notification_detected and task_id:
                    try:
                        import requests
                        # 检查任务状态，看是否已经有草稿数据（说明视频已生成）
                        response = requests.get(f'http://localhost:8000/api/tasks/{task_id}', timeout=2)
                        if response.status_code == 200:
                            task_data = response.json()
                            
                            # 🆕 最优先：检查是否已经有 video_url（说明插件已完成匹配）
                            if task_data.get('video_url'):
                                print(f'  ✓ 检测到视频URL已存在: {task_data["video_url"][:80]}...')
                                notification_detected = True
                                if progress_callback:
                                    progress_callback(100, '视频URL已获取')
                            # 优先检查任务状态是否已经是 success 或 published（说明插件已完成匹配）
                            elif task_data.get('status') in ['success', 'published']:
                                print(f'  ✓ 检测到任务状态已更新为 {task_data.get("status")}（插件已完成匹配）')
                                notification_detected = True
                                if progress_callback:
                                    progress_callback(95, '视频生成完成')
                            # 检查是否有generation_id（说明plug-renwu已捕获到草稿）
                            elif task_data.get('generation_id'):
                                print(f'  ✓ 检测到草稿数据: generation_id={task_data["generation_id"]}')
                                notification_detected = True
                                if progress_callback:
                                    progress_callback(95, '视频生成完成')
                    except Exception as e:
                        if elapsed % 30 == 0:
                            print(f'  检查任务状态时出错: {e}')
                
                # 如果检测到通知，视频生成完成
                if notification_detected:
                    elapsed_time = time.time() - start_time
                    print(f'  ✓ 视频生成完成！')
                    print(f'  总耗时: {elapsed_time:.1f}秒')
                    print(f'  💡 视频URL将由插件通过提示词匹配自动关联到任务')
                    
                    if progress_callback:
                        progress_callback(100, '视频生成完成，等待插件匹配')
                    
                    # 刷新页面，让插件脚本能够注入并捕获草稿数据
                    try:
                        print(f'  🔄 刷新页面以确保插件脚本注入...')
                        self.driver.refresh()
                        time.sleep(3)  # 等待页面加载
                        print(f'  ✓ 页面已刷新')
                    except Exception as e:
                        print(f'  ⚠️ 刷新页面失败: {e}')
                    
                    # 返回成功，但不包含video_url
                    # video_url将由插件通过提示词匹配来更新
                    return {
                        'success': True,
                        'video_url': None,  # 不再获取URL
                        'duration': elapsed_time,
                        'message': '视频生成完成，URL将由插件自动匹配'
                    }
                
                # 方法3: 检查错误
                try:
                    error_keywords = ['错误', 'error', 'Error', '失败', 'failed', 'Failed']
                    for keyword in error_keywords:
                        error_elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                        for elem in error_elements:
                            if elem.is_displayed():
                                error_text = elem.text.strip()
                                if error_text and len(error_text) > 3:
                                    print(f'  ✗ 检测到错误: {error_text}')
                                    if progress_callback:
                                        progress_callback(0, f'错误: {error_text}')
                                    return {'success': False, 'error': error_text, 'duration': elapsed}
                except:
                    pass
                
                # 每5秒检查一次
                time.sleep(5)
                
                # 显示等待进度（每30秒）
                if elapsed % 30 == 0 and elapsed > 0:
                    print(f'  ⏳ 生成中... ({elapsed}秒)')
            
            except Exception as e:
                print(f'  检查时出错: {e}')
                import traceback
                traceback.print_exc()
                time.sleep(5)
        
        # 这段代码永远不会执行到，因为上面是无限循环
        # 只有在检测到成功或错误时才会 return
    
    def _download_video(self, video_url):
        """下载视频"""
        print('  下载视频...')
        
        try:
            # 使用 JavaScript 触发下载
            script = f"""
            var a = document.createElement('a');
            a.href = '{video_url}';
            a.download = 'sora-{int(time.time())}.mp4';
            a.click();
            """
            self.driver.execute_script(script)
            print('  ✓ 下载已触发')
            return True
        except Exception as e:
            print(f'  下载失败: {e}')
            return False
    
    def generate_video(self, prompt, image=None, auto_download=True, progress_callback=None, task_id=None):
        """
        生成视频
        
        Args:
            prompt: 视频提示词
            image: 参考图片 URL（可选）
            auto_download: 是否自动下载
            progress_callback: 进度回调函数 callback(progress, message)
            task_id: 任务ID（用于从后端API检查进度）
        
        Returns:
            dict: 生成结果
        """
        try:
            # 1. 打开浏览器
            if self.driver is None:
                if progress_callback:
                    progress_callback(10, '打开浏览器窗口')
                self._open_browser()
            
            # 2. 导航到 Sora
            if progress_callback:
                progress_callback(20, '导航到Sora页面')
            self._navigate_to_sora()
            
            # 3. 如果有图片，先粘贴图片
            if image:
                if progress_callback:
                    progress_callback(25, '粘贴参考图片')
                print(f'  ========== 开始粘贴图片 ==========')
                print(f'  检测到图片参数: {image[:100] if isinstance(image, str) else image}...')
                try:
                    self._paste_image(image)
                    print(f'  ========== 图片粘贴完成 ==========')
                except Exception as e:
                    print(f'  ========== 图片粘贴失败 ==========')
                    print(f'  错误: {e}')
                    import traceback
                    traceback.print_exc()
                    # 不抛出异常，继续执行（图片是可选的）
                    print(f'  ⚠️  图片粘贴失败，但继续执行任务')
            else:
                print(f'  ℹ️  没有图片参数，跳过图片粘贴')
            
            # 4. 输入提示词（不需要先点击创建按钮）
            # 输入后会自动出现创建视频按钮
            if progress_callback:
                progress_callback(30, '输入提示词')
            self._input_prompt(prompt)
            
            # 5. 等待视频生成
            if progress_callback:
                progress_callback(40, '等待视频生成')
            result = self._wait_for_video(progress_callback=progress_callback, task_id=task_id)
            
            # 5. 不再下载视频（video_url由插件匹配）
            # 旧逻辑：下载视频
            # if result['success'] and auto_download:
            #     if progress_callback:
            #         progress_callback(95, '下载视频')
            #     self._download_video(result['video_url'])
            
            if result['success'] and progress_callback:
                progress_callback(100, '视频生成完成，等待插件匹配URL')
            
            return result
        
        except Exception as e:
            if progress_callback:
                progress_callback(0, f'错误: {str(e)}')
            return {'success': False, 'error': str(e)}
    
    def cleanup(self):
        """清理资源 - 带超时和强制关闭"""
        print(f'  清理窗口 {self.profile_id} 的资源...')
        
        # 先尝试关闭driver
        if self.driver:
            try:
                print(f'  尝试关闭 driver...')
                import threading
                
                quit_success = [False]
                
                def quit_driver():
                    try:
                        self.driver.quit()
                        quit_success[0] = True
                    except:
                        pass
                
                # 启动一个线程来关闭driver，最多等待3秒
                quit_thread = threading.Thread(target=quit_driver)
                quit_thread.daemon = True
                quit_thread.start()
                quit_thread.join(timeout=3)
                
                if quit_success[0]:
                    print(f'  ✓ driver 已关闭')
                else:
                    print(f'  ⚠️  driver.quit() 超时，强制继续')
                    
            except Exception as e:
                print(f'  ⚠️  关闭 driver 失败: {e}')
        
        # 通过API关闭窗口
        if self.profile_id:
            try:
                print(f'  通过 API 关闭窗口 {self.profile_id}...')
                result = self.client.close_profile(self.profile_id)
                if result:
                    print(f'  ✓ 窗口 {self.profile_id} 已通过API关闭')
                else:
                    print(f'  ⚠️  API关闭失败: {self.client.message}')
            except Exception as e:
                print(f'  ⚠️  API关闭窗口失败: {e}')
        
        print(f'  窗口 {self.profile_id} 清理完成')
