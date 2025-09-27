#!/bin/bash
echo "停止币安监控程序..."
if [ -f "monitor.pid" ]; then
    PID=$(cat monitor.pid)
    if ps -p $PID > /dev/null; then
        kill $PID
        echo "监控程序已停止 (PID: $PID)"
        rm monitor.pid
    else
        echo "监控程序未运行"
        rm monitor.pid
    fi
else
    pkill -f "binance_monitor.py"
    echo "已尝试停止所有相关进程"
fi