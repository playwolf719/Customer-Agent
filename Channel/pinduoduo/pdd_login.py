"""
拼多多账号异步登录认证
"""
from http import cookies
import requests
import json
import os
import hashlib
import asyncio
from typing import Optional, Dict, Any, Tuple
from utils.logger import get_logger
from database import db_manager
from playwright.async_api import async_playwright
from Channel.pinduoduo.utils.API.get_shop_info import GetShopInfo
from Channel.pinduoduo.utils.API.get_user_info import GetUserInfo
from config import config

class PDDLogin():
    def __init__(self,name,password):
        self.logger = get_logger("Pdd_login")
        self.channel_name = "pinduoduo"  # 渠道名称固定为"pinduoduo"
        self.base_url = "https://mms.pinduoduo.com/login"
        self.name = name
        self.password = password
    async def login(self):
        """使用账号密码登录
        
        Args:
            name: 账号名称
            password: 账号密码

        """
        try:
            # 启动Playwright
            playwright = await async_playwright().start()
            
            # 创建独立的用户数据目录，避免多实例冲突
            user_data_dir = f"./user_data/{(self.name)}"
            self.logger.debug(f"使用用户数据目录: {user_data_dir}")
            
            # 使用持久化上下文，自动处理用户数据目录
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir,
                headless=False,
                executable_path=config.get("chrome_executable_path",None),
                args=[
                    '--disable-gpu',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-notifications',  # 禁用通知
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            page = await context.new_page()
            
            # 访问登录页面
            await page.goto(self.base_url)
            
            # 点击账号密码登录
            await page.click("div.tab-item.last-item:has-text('账号登录')")
            
            # 等待页面加载
            await page.wait_for_selector("input[type='text']")
            
            # 输入店铺名
            await page.fill("input[type='text']", self.name)
            
            # 输入密码
            await page.fill("input[type='password']", self.password)
            
            # 点击登录按钮
            await page.click("button:has-text('登录')")
            
            # 等待页面 title等于 拼多多 商家后台，首页或者订单查询
            await page.wait_for_function("() => document.title === '拼多多 商家后台' || document.title === '首页' || document.title === '订单查询'", timeout=30000)
            
            # 获取cookies并转换为字典格式
            cookies_list = await context.cookies()
            # 将playwright格式的cookies列表转换为字典格式
            cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies_list}
            cookies_json = json.dumps(cookies_dict)
            # 关闭浏览器上下文
            await context.close()
            await playwright.stop()
                
            return cookies_json
            
        except Exception as e:
            self.logger.error(f"登录失败: {str(e)}")
            return False
        
    async def refresh_cookies(self):
        """重新获取cookies，使用已保存的用户数据，无需再次登录
        
        Returns:
            str: cookies的JSON字符串，如果失败返回False
        """
        try:
            # 启动Playwright
            playwright = await async_playwright().start()
            
            # 使用相同的用户数据目录
            user_data_dir = f"./user_data/{hash(self.name)}"
            self.logger.debug(f"使用用户数据目录刷新cookies: {user_data_dir}")
            
            # 检查用户数据目录是否存在
            if not os.path.exists(user_data_dir):
                self.logger.error(f"用户数据目录不存在: {user_data_dir}，请先登录")
                await playwright.stop()
                return False
            
            # 使用持久化上下文，自动加载用户数据
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir,
                headless=True,  # 刷新cookies时可以使用无头模式
                args=[
                    '--disable-gpu',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-notifications',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            page = await context.new_page()
            
            # 访问拼多多商家后台首页，验证登录状态
            await page.goto("https://mms.pinduoduo.com/home/")
            
            # 等待页面加载，检查是否需要重新登录
            try:
                # 如果页面跳转到登录页面，说明登录状态已失效
                await page.wait_for_url("**/login**", timeout=5000)
                self.logger.warning("登录状态已失效，需要重新登录")
                await context.close()
                await playwright.stop()
                return False
            except:
                # 没有跳转到登录页面，说明登录状态有效
                pass
            
            # 获取最新的cookies
            cookies_list = await context.cookies()
            cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies_list}
            cookies_json = json.dumps(cookies_dict)
            
            # 关闭浏览器上下文
            await context.close()
            await playwright.stop()
            
            self.logger.info(f"成功刷新账号 '{self.name}' 的cookies")
            return cookies_json
            
        except Exception as e:
            self.logger.error(f"刷新cookies失败: {str(e)}")
            if 'playwright' in locals():
                await playwright.stop()
            return False

    def Set_user_info(self,cookies_json):
        user_info = GetUserInfo(cookies_json)
        user_id,user_name,mall_id = user_info.get_user_info()
     
        return user_id,user_name,mall_id

    def Set_shop_info(self,cookies_json):
        shop_info = GetShopInfo(cookies_json)
        shop_id,shop_name,mallLogo = shop_info.get_shop_info()
        return shop_id,shop_name,mallLogo
    
async def login_pdd(name, password):
    """
    使用账号密码登录并返回账号、店铺信息，不直接操作数据库。
    如果登录成功，返回包含详细信息的字典。
    如果登录失败，返回 False。

    :param name: 用户名
    :param password: 密码
    :return: dict or bool
    """
    pdd_login = PDDLogin(name=name, password=password)
    cookies_json = await pdd_login.login()
    if not cookies_json:
        pdd_login.logger.error(f"账号 '{name}' 登录失败，未能获取cookies")
        return False

    try:
        # 获取用户信息和店铺信息
        user_id, user_name, mall_id = pdd_login.Set_user_info(cookies_json)
        shop_id, shop_name, mallLogo = pdd_login.Set_shop_info(cookies_json)

        pdd_login.logger.info(f"账号 '{name}' 登录成功，获取到店铺: {shop_name}({shop_id})")

        # 登录成功，返回包含所有信息的字典
        return {
            "channel_name": pdd_login.channel_name,
            "shop_id": shop_id,
            "shop_name": shop_name,
            "shop_logo": mallLogo,
            "user_id": user_id,
            "username": name,  # 使用传入的登录名
            "password": password, # 使用传入的密码
            "cookies": cookies_json,
        }
    except Exception as e:
        pdd_login.logger.error(f"账号 '{name}' 登录成功，但在处理后续信息时出错: {e}")
        return False

async def refresh_pdd_cookies(name, password=None):
    """
    刷新拼多多账号的cookies，使用已保存的用户数据，无需再次输入账号密码。
    如果刷新成功，返回包含最新cookies的字典。
    如果刷新失败（如登录状态已失效），返回 False。

    :param name: 用户名
    :param password: 密码（可选，仅用于创建PDDLogin实例）
    :return: dict or bool
    """
    pdd_login = PDDLogin(name=name, password=password or "")
    cookies_json = await pdd_login.refresh_cookies()
    
    if not cookies_json:
        pdd_login.logger.error(f"账号 '{name}' cookies刷新失败")
        return False

    try:
        # 获取用户信息和店铺信息
        user_id, user_name, mall_id = pdd_login.Set_user_info(cookies_json)
        shop_id, shop_name, mallLogo = pdd_login.Set_shop_info(cookies_json)

        pdd_login.logger.info(f"账号 '{name}' cookies刷新成功，店铺: {shop_name}({shop_id})")

        # 刷新成功，返回包含最新信息的字典
        return {
            "channel_name": pdd_login.channel_name,
            "shop_id": shop_id,
            "shop_name": shop_name,
            "shop_logo": mallLogo,
            "user_id": user_id,
            "username": name,
            "password": password or "",
            "cookies": cookies_json,
        }
    except Exception as e:
        pdd_login.logger.error(f"账号 '{name}' cookies刷新成功，但在处理后续信息时出错: {e}")
        return False

