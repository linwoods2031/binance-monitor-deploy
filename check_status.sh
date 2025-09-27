#!/bin/bash
echo "========================================="
echo "    币安监控程序状态检查"
echo "========================================="
echo "检查时间: $(date)"
echo ""

# 检查进程状态
echo "1. 进程状态:"
if ps aux | grep -v grep | grep binance_monitor.py > /dev/null; then
    echo "✅ 监控程序正在运行"
    ps aux | grep -v grep | grep binance_monitor.py
else
    echo "❌ 监控程序未运行"
fi

echo ""

# 检查网络连接
echo "2. 网络连接测试:"
if curl -s --connect-timeout 5 "https://fapi.binance.com/fapi/v1/ping" > /dev/null; then
    echo "✅ 币安API连接正常"
else
    echo "❌ 币安API连接失败"
fi

echo ""

# 检查日志文件
echo "3. 最新日志 (最后5行):"
if [ -f "/root/binance_monitor/monitor.log" ]; then
    tail -5 /root/binance_monitor/monitor.log
else
    echo "❌ 日志文件不存在"
fi

echo ""
echo "========================================="