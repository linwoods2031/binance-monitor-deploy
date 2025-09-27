#!/bin/bash
cd /root/binance_monitor
echo "启动币安监控程序..."
echo "时间: $(date)"
mkdir -p logs
nohup python3 binance_monitor.py > logs/monitor_output.log 2>&1 &
PID=$!
echo $PID > monitor.pid
echo "监控程序已启动，进程ID: $PID"
echo "查看日志: tail -f /root/binance_monitor/monitor.log"