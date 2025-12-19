#!/bin/bash
# Serverga o'zgarishlarni yuklash scripti
# =======================================

echo "==============================================="
echo "  SERVER FIX DEPLOYMENT"
echo "==============================================="

# Ranglar
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Server ma'lumotlari (o'zingizniki bilan almashtiring)
SERVER_USER="your_user"
SERVER_HOST="your_server_ip"
SERVER_PATH="/var/www/face"

echo -e "${YELLOW}Server:${NC} $SERVER_USER@$SERVER_HOST:$SERVER_PATH"
echo ""

# 1. Yangilangan fayllarni serverga yuklash
echo -e "${YELLOW}1. Fayllarni yuklash...${NC}"

scp emotion_app/models.py $SERVER_USER@$SERVER_HOST:$SERVER_PATH/emotion_app/
scp emotion_app/views.py $SERVER_USER@$SERVER_HOST:$SERVER_PATH/emotion_app/
scp gunicorn_config.py $SERVER_USER@$SERVER_HOST:$SERVER_PATH/

echo -e "${GREEN}✓ Fayllar yuklandi${NC}"
echo ""

# 2. Serverda gunicorn'ni qayta ishga tushirish
echo -e "${YELLOW}2. Gunicorn'ni qayta ishga tushirish...${NC}"

ssh $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd /var/www/face

# Virtual environment aktivlashtirish
source venv/bin/activate

# Gunicorn'ni to'xtatish
sudo systemctl stop gunicorn

# Yangi konfig bilan ishga tushirish
sudo systemctl start gunicorn

# Status tekshirish
sudo systemctl status gunicorn --no-pager

echo ""
echo "✓ Gunicorn qayta ishga tushirildi"
ENDSSH

echo -e "${GREEN}✓ Deployment yakunlandi!${NC}"
echo ""
echo "==============================================="
echo "  Test qilish:"
echo "  curl http://your_server_ip:8000/api/statistics/"
echo "==============================================="
