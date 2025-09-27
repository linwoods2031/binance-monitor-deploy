#!/bin/bash

# 币安监控程序GitHub一键部署脚本
# 使用方法: curl -sSL https://raw.githubusercontent.com/hit930906/binance-monitor-deploy/main/github_deploy.sh | bash

set -e  # 遇到错误立即退出

echo "========================================="
echo "    币安监控程序GitHub一键部署"
echo "========================================="
echo "开始时间: $(date)"
echo ""

# GitHub仓库信息
GITHUB_USER="linwoods2031"
REPO_NAME="binance-monitor-deploy"
BRANCH="main"
BASE_URL="https://raw.githubusercontent.com/${GITHUB_USER}/${REPO_NAME}/${BRANCH}"

# 检测操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    echo "无法检测操作系统版本"
    exit 1
fi

echo "检测到操作系统: $OS $VER"

# 更新系统包
echo ""
echo "步骤 1/7: 更新系统包..."
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    apt update && apt upgrade -y
    apt install -y python3 python3-pip git wget curl unzip
elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
    yum update -y
    yum install -y python3 python3-pip git wget curl unzip
else
    echo "不支持的操作系统: $OS"
    exit 1
fi

# 验证Python环境
echo ""
echo "步骤 2/7: 验证Python环境..."
python3 --version
pip3 --version

# 安装Python依赖
echo ""
echo "步骤 3/7: 安装Python依赖..."
pip3 install requests

# 创建工作目录
echo ""
echo "步骤 4/7: 创建工作目录..."
mkdir -p /root/binance_monitor
cd /root/binance_monitor

# 从GitHub下载文件
echo ""
echo "步骤 5/7: 从GitHub下载部署文件..."

# 下载主程序
echo "下载监控程序..."
curl -sSL "${BASE_URL}/binance_monitor.py" -o binance_monitor.py

# 下载配置文件
echo "下载配置文件..."
curl -sSL "${BASE_URL}/config.json" -o config.json

# 下载管理脚本
echo "下载管理脚本..."
curl -sSL "${BASE_URL}/start_monitor.sh" -o start_monitor.sh
curl -sSL "${BASE_URL}/stop_monitor.sh" -o stop_monitor.sh
curl -sSL "${BASE_URL}/check_status.sh" -o check_status.sh

# 设置执行权限
chmod +x *.sh *.py

echo ""
echo "步骤 6/7: 测试币安API连接..."
if curl -s --connect-timeout 10 "https://fapi.binance.com/fapi/v1/ping" > /dev/null; then
    echo "✅ 币安API连接测试成功"
else
    echo "❌ 币安API连接测试失败，请检查网络"
    exit 1
fi

echo ""
echo "步骤 7/7: 启动监控程序..."
./start_monitor.sh

echo ""
echo "========================================="
echo "           GitHub部署完成！"
echo "========================================="
echo ""
echo "📊 监控程序信息:"
echo "   - GitHub仓库: https://github.com/${GITHUB_USER}/${REPO_NAME}"
echo "   - 工作目录: /root/binance_monitor"
echo "   - 监控阈值: 5% 价格变动"
echo "   - 检查间隔: 60秒"
echo "   - 日志文件: /root/binance_monitor/monitor.log"
echo ""
echo "🔧 常用命令:"
echo "   查看状态: ./check_status.sh"
echo "   查看日志: tail -f monitor.log"
echo "   停止程序: ./stop_monitor.sh"
echo "   重启程序: ./stop_monitor.sh && ./start_monitor.sh"
echo ""
echo "🔄 更新程序:"
echo "   curl -sSL ${BASE_URL}/github_deploy.sh | bash"
echo ""
echo "🎉 部署成功！监控程序已开始运行。"
echo "完成时间: $(date)"