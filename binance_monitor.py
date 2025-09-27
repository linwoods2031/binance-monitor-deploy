#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
币安异动行情监控工具
监控币种5分钟涨幅超过7%的情况并报警
"""

import requests
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

class BinanceMonitor:
    def __init__(self, config_file="config.json"):
        # 加载配置
        self.config = self.load_config(config_file)
        
        self.base_url = self.config['api_settings']['base_url']
        self.price_history = {}  # 存储价格历史数据
        self.alert_threshold = self.config['monitor_settings']['alert_threshold']
        self.monitor_interval = self.config['monitor_settings']['monitor_interval']
        self.time_window = self.config['monitor_settings']['time_window']
        self.max_symbols = self.config['monitor_settings']['max_symbols']
        self.timeout = self.config['api_settings']['timeout']
        self.api_key = self.config['api_settings']['api_key']
        self.secret_key = self.config['api_settings']['secret_key']
        
        # 设置日志
        log_file = self.config['alert_settings']['log_file']
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # 添加每小时状态邮件和报警汇总功能
        self.last_status_email_time = datetime.now()
        self.hourly_alerts = []  # 存储一小时内的报警信息
        
    def load_config(self, config_file: str) -> dict:
        """加载配置文件"""
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 使用默认配置
                return {
                    "monitor_settings": {
                        "alert_threshold": 0.10,
                        "monitor_interval": 30,
                        "time_window": 300,
                        "max_symbols": 50
                    },
                    "api_settings": {
                        "base_url": "https://api.binance.com",
                        "timeout": 10,
                        "api_key": "",
                        "secret_key": ""
                    },
                    "alert_settings": {
                        "console_output": True,
                        "log_file": "binance_monitor.log"
                    },
                    "symbol_filters": {
                        "market_type": "spot",
                        "quote_asset": "USDT",
                        "status": "TRADING",
                        "exclude_symbols": []
                    }
                }
        except Exception as e:
            print(f"加载配置文件失败: {e}，使用默认配置")
            return self.load_config("")  # 递归调用获取默认配置
    
    def send_email_alert(self, subject: str, content: str):
        """发送邮件报警"""
        try:
            if not self.config['alert_settings']['email_alert']:
                return
            
            sender_email = self.config['alert_settings']['sender_email']
            sender_password = self.config['alert_settings']['sender_password']
            receiver_emails = self.config['alert_settings']['receiver_emails']
            smtp_server = self.config['alert_settings']['smtp_server']
            smtp_port = self.config['alert_settings']['smtp_port']
            
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ', '.join(receiver_emails)
            msg['Subject'] = Header(subject, 'utf-8')
            
            # 邮件正文
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            # 连接SMTP服务器并发送邮件
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()  # 启用TLS加密
            server.login(sender_email, sender_password)
            
            # 发送给所有接收者
            for receiver_email in receiver_emails:
                msg['To'] = Header(receiver_email, 'utf-8')
                text = msg.as_string()
                server.sendmail(sender_email, receiver_email, text)
                self.logger.info(f"邮件报警已发送至: {receiver_email}")
            
            server.quit()
            
        except Exception as e:
            self.logger.error(f"发送邮件失败: {e}")
         
    def get_all_symbols(self) -> List[str]:
        """获取所有交易对"""
        try:
            market_type = self.config['symbol_filters']['market_type']
            
            if market_type == 'futures':
                # 获取合约交易对
                url = f"{self.base_url}/fapi/v1/exchangeInfo"
            else:
                # 获取现货交易对
                url = f"{self.base_url}/api/v3/exchangeInfo"
            
            headers = {}
            if self.api_key:
                headers['X-MBX-APIKEY'] = self.api_key
                
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            symbols = []
            
            status = self.config['symbol_filters']['status']
            exclude_symbols = self.config['symbol_filters']['exclude_symbols']
            quote_asset = self.config['symbol_filters'].get('quote_asset')
            
            for symbol_info in data['symbols']:
                symbol = symbol_info['symbol']
                # 基本过滤条件
                if (symbol_info['status'] == status and
                    symbol not in exclude_symbols):
                    
                    # 如果指定了quote_asset，则进行过滤
                    if quote_asset:
                        if market_type == 'futures':
                            # 合约交易对通常以USDT结尾
                            if symbol.endswith(quote_asset):
                                symbols.append(symbol)
                        else:
                            # 现货交易对检查quoteAsset字段
                            if symbol_info.get('quoteAsset') == quote_asset:
                                symbols.append(symbol)
                    else:
                        # 没有指定quote_asset，添加所有符合条件的交易对
                        symbols.append(symbol)
            
            market_name = "合约" if market_type == 'futures' else "现货"
            self.logger.info(f"获取到 {len(symbols)} 个{market_name}交易对")
            return symbols[:self.max_symbols]  # 限制监控数量，避免API限制
            
        except Exception as e:
            self.logger.error(f"获取交易对失败: {e}")
            return []
    
    def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """获取当前价格"""
        try:
            market_type = self.config['symbol_filters']['market_type']
            
            if market_type == 'futures':
                # 获取合约价格
                url = f"{self.base_url}/fapi/v1/ticker/price"
            else:
                # 获取现货价格
                url = f"{self.base_url}/api/v3/ticker/price"
            
            headers = {}
            if self.api_key:
                headers['X-MBX-APIKEY'] = self.api_key
                
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            prices = {}
            
            for item in data:
                if item['symbol'] in symbols:
                    prices[item['symbol']] = float(item['price'])
            
            return prices
            
        except Exception as e:
            self.logger.error(f"获取价格失败: {e}")
            return {}
    
    def update_price_history(self, current_prices: Dict[str, float]):
        """更新价格历史记录"""
        current_time = datetime.now()
        
        for symbol, price in current_prices.items():
            if symbol not in self.price_history:
                self.price_history[symbol] = []
            
            # 添加当前价格记录
            self.price_history[symbol].append({
                'timestamp': current_time,
                'price': price
            })
            
            # 清理超过时间窗口的历史数据
            cutoff_time = current_time - timedelta(seconds=self.time_window)
            self.price_history[symbol] = [
                record for record in self.price_history[symbol]
                if record['timestamp'] > cutoff_time
            ]
    
    def calculate_price_change(self, symbol: str) -> Optional[float]:
        """计算5分钟内的价格变化百分比"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 2:
            return None
        
        history = self.price_history[symbol]
        current_price = history[-1]['price']
        
        # 找到5分钟前的价格
        five_minutes_ago = datetime.now() - timedelta(seconds=self.time_window)
        
        # 找到最接近5分钟前的价格记录
        old_price = None
        for record in history:
            if record['timestamp'] <= five_minutes_ago:
                old_price = record['price']
            else:
                break
        
        if old_price is None:
            old_price = history[0]['price']  # 使用最早的价格记录
        
        # 计算涨幅百分比
        price_change = (current_price - old_price) / old_price
        return price_change
    
    def send_alert(self, symbol: str, price_change: float, current_price: float):
        """发送报警"""
        change_percent = price_change * 100
        alert_message = f"🚨 异动报警！\n" \
                       f"币种: {symbol}\n" \
                       f"当前价格: ${current_price:.6f}\n" \
                       f"5分钟涨幅: {change_percent:.2f}%\n" \
                       f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 控制台输出报警（如果启用）
        if self.config['alert_settings']['console_output']:
            print("=" * 50)
            print(alert_message)
            print("=" * 50)
        
        # 邮件报警（如果启用）
        if self.config['alert_settings']['email_alert']:
            email_subject = f"币安异动报警 - {symbol} 涨幅 {change_percent:.2f}%"
            self.send_email_alert(email_subject, alert_message)
        
        # 记录到日志
        self.logger.warning(f"异动报警 - {symbol}: {change_percent:.2f}% 涨幅，当前价格: ${current_price:.6f}")
        
        # 添加到每小时报警汇总
        self.hourly_alerts.append({
            'symbol': symbol,
            'price_change': change_percent,
            'current_price': current_price,
            'time': datetime.now()
        })
    
    def send_hourly_status_email(self):
        """发送每小时状态邮件和报警汇总"""
        try:
            current_time = datetime.now()
            runtime_minutes = (current_time - self.last_status_email_time).total_seconds() / 60
            
            # 构建邮件内容
            status_message = f"📊 币安监控程序状态报告\n\n" \
                            f"✅ 程序正常运行中\n" \
                            f"⏱️ 运行时间: {runtime_minutes:.0f}分钟\n" \
                            f"🕒 当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n" \
                            f"📈 监控条件: 5分钟涨幅超过{self.alert_threshold*100}%\n\n"
            
            # 添加报警汇总信息
            if self.hourly_alerts:
                status_message += f"🚨 过去一小时内的报警汇总 ({len(self.hourly_alerts)}条):\n\n"
                
                for alert in self.hourly_alerts:
                    status_message += f"币种: {alert['symbol']}\n" \
                                     f"涨幅: {alert['price_change']:.2f}%\n" \
                                     f"价格: ${alert['current_price']:.6f}\n" \
                                     f"时间: {alert['time'].strftime('%H:%M:%S')}\n\n"
            else:
                status_message += "🟢 过去一小时内无异动报警\n"
            
            # 发送邮件
            if self.config['alert_settings']['email_alert']:
                email_subject = f"币安监控程序状态报告 - {current_time.strftime('%Y-%m-%d %H:%M')}"
                self.send_email_alert(email_subject, status_message)
                self.logger.info("已发送每小时状态邮件")
            
            # 重置报警列表和时间
            self.hourly_alerts = []
            self.last_status_email_time = current_time
            
        except Exception as e:
            self.logger.error(f"发送状态邮件失败: {e}")
    
    def send_startup_email(self):
        """发送程序启动邮件"""
        try:
            current_time = datetime.now()
            
            # 构建启动邮件内容
            startup_message = f"🚀 币安监控程序启动通知\n\n" \
                             f"✅ 监控程序已成功启动\n" \
                             f"🕒 启动时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n" \
                             f"📈 监控条件: 5分钟涨幅超过{self.alert_threshold*100}%\n" \
                             f"📊 监控交易对数量: {self.max_symbols}个合约交易对\n" \
                             f"⏰ 状态报告频率: 每小时一次\n\n" \
                             f"程序将持续监控币安合约交易对的价格变动，" \
                             f"当发现异动时会立即发送报警邮件。\n\n" \
                             f"祝您交易愉快！"
            
            # 发送邮件
            if self.config['alert_settings']['email_alert']:
                email_subject = f"币安监控程序启动通知 - {current_time.strftime('%Y-%m-%d %H:%M')}"
                self.send_email_alert(email_subject, startup_message)
                self.logger.info("已发送程序启动邮件")
            
        except Exception as e:
            self.logger.error(f"发送启动邮件失败: {e}")
    
    def monitor(self):
        """主监控循环"""
        self.logger.info("开始监控币安异动行情...")
        
        # 获取要监控的交易对
        symbols = self.get_all_symbols()
        if not symbols:
            self.logger.error("无法获取交易对，退出监控")
            return
        
        self.logger.info(f"开始监控 {len(symbols)} 个交易对")
        
        # 发送程序启动邮件
        self.send_startup_email()
        
        try:
            while True:
                current_time = datetime.now()
                
                # 检查是否需要发送每小时状态邮件
                time_since_last_email = (current_time - self.last_status_email_time).total_seconds()
                if time_since_last_email >= 3600:  # 3600秒 = 1小时
                    self.send_hourly_status_email()
                
                # 获取当前价格
                current_prices = self.get_current_prices(symbols)
                if not current_prices:
                    self.logger.warning("获取价格失败，等待下次检查")
                    time.sleep(self.monitor_interval)
                    continue
                
                # 更新价格历史
                self.update_price_history(current_prices)
                
                # 检查异动
                alerts_count = 0
                for symbol in symbols:
                    price_change = self.calculate_price_change(symbol)
                    if price_change is not None and price_change >= self.alert_threshold:
                        self.send_alert(symbol, price_change, current_prices[symbol])
                        alerts_count += 1
                
                if alerts_count == 0:
                    self.logger.info(f"检查完成，无异动 - 监控了 {len(current_prices)} 个币种")
                
                # 等待下次检查
                time.sleep(self.monitor_interval)
                
        except KeyboardInterrupt:
            self.logger.info("监控已停止")
        except Exception as e:
            self.logger.error(f"监控过程中发生错误: {e}")

def main():
    """主函数"""
    print("币安异动行情监控工具")
    print("监控条件: 5分钟涨幅超过7%")
    print("按 Ctrl+C 停止监控\n")
    
    monitor = BinanceMonitor()
    monitor.monitor()

if __name__ == "__main__":
    main()