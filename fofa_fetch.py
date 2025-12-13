import os
import re
import socket
import requests
import time
import concurrent.futures
import subprocess
from datetime import datetime, timezone, timedelta

# ===============================
# 配置区
FOFA_URLS = {
    "https://fofa.info/result?qbase64=InVkcHh5IiAmJiBjb3VudHJ5PSJDTiI%3D": "ip.txt",
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

COUNTER_FILE = "计数.txt"
IP_DIR = "ip"
RTP_DIR = "rtp"
ZUBO_FILE = "zubo.txt"
IPTV_FILE = "IPTV.txt"
# 补充缺失的声明URL
DISCLAIMER_URL = "https://github.com/your-repo/iptv"

# ===============================
# 分类与映射配置
CHANNEL_CATEGORIES = {
    "央视频道": [
        "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV4欧洲", "CCTV4美洲", "CCTV5", "CCTV5+", "CCTV6", "CCTV7",
        "CCTV8", "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15", "CCTV16", "CCTV17", "CCTV4K", "CCTV8K",
        "兵器科技", "风云音乐", "风云足球", "风云剧场", "怀旧剧场", "第一剧场", "女性时尚", "世界地理", "央视台球", "高尔夫网球",
        "央视文化精品", "卫生健康", "电视指南", "中学生", "发现之旅", "书法频道", "国学频道", "环球奇观"
    ],
    "卫视频道": [
        "湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "深圳卫视", "北京卫视", "广东卫视", "广西卫视", "东南卫视", "海南卫视",
        "河北卫视", "河南卫视", "湖北卫视", "江西卫视", "四川卫视", "重庆卫视", "贵州卫视", "云南卫视", "天津卫视", "安徽卫视",
        "山东卫视", "辽宁卫视", "黑龙江卫视", "吉林卫视", "内蒙古卫视", "宁夏卫视", "山西卫视", "陕西卫视", "甘肃卫视", "青海卫视",
        "新疆卫视", "西藏卫视", "三沙卫视", "兵团卫视", "延边卫视", "安多卫视", "康巴卫视", "农林卫视", "山东教育卫视",
        "中国教育1台", "中国教育2台", "中国教育3台", "中国教育4台", "早期教育"
    ],
    "数字频道": [
        "CHC动作电影", "CHC家庭影院", "CHC影迷电影", "淘电影", "淘精彩", "淘剧场", "淘4K", "淘娱乐", "淘BABY", "淘萌宠", "重温经典",
        "星空卫视", "CHANNEL[V]", "凤凰卫视中文台", "凤凰卫视资讯台", "凤凰卫视香港台", "凤凰卫视电影台", "求索纪录", "求索科学",
        "求索生活", "求索动物", "纪实人文", "金鹰纪实", "纪实科教", "睛彩青少", "睛彩竞技", "睛彩篮球", "睛彩广场舞", "魅力足球", "五星体育",
        "劲爆体育", "快乐垂钓", "茶频道", "先锋乒羽", "天元围棋", "汽摩", "梨园频道", "文物宝库", "武术世界", "哒啵赛事", "哒啵电竞", "黑莓电影", "黑莓动画", 
        "乐游", "生活时尚", "都市剧场", "欢笑剧场", "游戏风云", "金色学堂", "动漫秀场", "新动漫", "卡酷少儿", "金鹰卡通", "优漫卡通", "哈哈炫动", "嘉佳卡通", 
        "中国交通", "中国天气", "华数4K", "华数星影", "华数动作影院", "华数喜剧影院", "华数家庭影院", "华数经典电影", "华数热播剧场", "华数碟战剧场",
        "华数军旅剧场", "华数城市剧场", "华数武侠剧场", "华数古装剧场", "华数魅力时尚", "华数少儿动画", "华数动画"
    ],
    "河北": [
       "河北经济生活", "河北三农频道", "河北都市", "河北影视剧", "河北少儿科教", "河北文旅·公共", 
    ],
}

# ===== 映射（别名 -> 标准名） =====
CHANNEL_MAPPING = {
    "CCTV1": ["CCTV-1", "CCTV-1 HD", "CCTV1 HD", "CCTV-1综合"],
    "CCTV2": ["CCTV-2", "CCTV-2 HD", "CCTV2 HD", "CCTV-2财经"],
    "CCTV3": ["CCTV-3", "CCTV-3 HD", "CCTV3 HD", "CCTV-3综艺"],
    "CCTV4": ["CCTV-4", "CCTV-4 HD", "CCTV4 HD", "CCTV-4中文国际"],
    "CCTV4欧洲": ["CCTV-4欧洲", "CCTV-4欧洲", "CCTV4欧洲 HD", "CCTV-4 欧洲", "CCTV-4中文国际欧洲", "CCTV4中文欧洲"],
    "CCTV4美洲": ["CCTV-4美洲", "CCTV-4北美", "CCTV4美洲 HD", "CCTV-4 美洲", "CCTV-4中文国际美洲", "CCTV4中文美洲"],
    "CCTV5": ["CCTV-5", "CCTV-5 HD", "CCTV5 HD", "CCTV-5体育"],
    "CCTV5+": ["CCTV-5+", "CCTV-5+ HD", "CCTV5+ HD", "CCTV-5+体育赛事"],
    "CCTV6": ["CCTV-6", "CCTV-6 HD", "CCTV6 HD", "CCTV-6电影"],
    "CCTV7": ["CCTV-7", "CCTV-7 HD", "CCTV7 HD", "CCTV-7国防军事"],
    "CCTV8": ["CCTV-8", "CCTV-8 HD", "CCTV8 HD", "CCTV-8电视剧"],
    "CCTV9": ["CCTV-9", "CCTV-9 HD", "CCTV9 HD", "CCTV-9纪录"],
    "CCTV10": ["CCTV-10", "CCTV-10 HD", "CCTV10 HD", "CCTV-10科教"],
    "CCTV11": ["CCTV-11", "CCTV-11 HD", "CCTV11 HD", "CCTV-11戏曲"],
    "CCTV12": ["CCTV-12", "CCTV-12 HD", "CCTV12 HD", "CCTV-12社会与法"],
    "CCTV13": ["CCTV-13", "CCTV-13 HD", "CCTV13 HD", "CCTV-13新闻"],
    "CCTV14": ["CCTV-14", "CCTV-14 HD", "CCTV14 HD", "CCTV-14少儿"],
    "CCTV15": ["CCTV-15", "CCTV-15 HD", "CCTV15 HD", "CCTV-15音乐"],
    "CCTV16": ["CCTV-16", "CCTV-16 HD", "CCTV-16 4K", "CCTV-16奥林匹克", "CCTV16 4K", "CCTV-16奥林匹克4K"],
    "CCTV17": ["CCTV-17", "CCTV-17 HD", "CCTV17 HD", "CCTV-17农业农村"],
    "CCTV4K": ["CCTV4K超高清", "CCTV-4K超高清", "CCTV-4K 超高清", "CCTV 4K"],
    "CCTV8K": ["CCTV8K超高清", "CCTV-8K超高清", "CCTV-8K 超高清", "CCTV 8K"],
    "兵器科技": ["CCTV-兵器科技", "CCTV兵器科技"],
    "风云音乐": ["CCTV-风云音乐", "CCTV风云音乐"],
    "第一剧场": ["CCTV-第一剧场", "CCTV第一剧场"],
    "风云足球": ["CCTV-风云足球", "CCTV风云足球"],
    "风云剧场": ["CCTV-风云剧场", "CCTV风云剧场"],
    "怀旧剧场": ["CCTV-怀旧剧场", "CCTV怀旧剧场"],
    "女性时尚": ["CCTV-女性时尚", "CCTV女性时尚"],
    "世界地理": ["CCTV-世界地理", "CCTV世界地理"],
    "央视台球": ["CCTV-央视台球", "CCTV央视台球"],
    "高尔夫网球": ["CCTV-高尔夫网球", "CCTV高尔夫网球", "CCTV央视高网", "CCTV-高尔夫·网球", "央视高网"],
    "央视文化精品": ["CCTV-央视文化精品", "CCTV央视文化精品", "CCTV文化精品", "CCTV-文化精品", "文化精品"],
    "卫生健康": ["CCTV-卫生健康", "CCTV卫生健康"],
    "电视指南": ["CCTV-电视指南", "CCTV电视指南"],
    "农林卫视": ["陕西农林卫视"],
    "三沙卫视": ["海南三沙卫视"],
    "兵团卫视": ["新疆兵团卫视"],
    "延边卫视": ["吉林延边卫视"],
    "安多卫视": ["青海安多卫视"],
    "康巴卫视": ["四川康巴卫视"],
    "山东教育卫视": ["山东教育"],
    "中国教育1台": ["CETV1", "中国教育一台", "中国教育1", "CETV-1 综合教育", "CETV-1"],
    "中国教育2台": ["CETV2", "中国教育二台", "中国教育2", "CETV-2 空中课堂", "CETV-2"],
    "中国教育3台": ["CETV3", "中国教育三台", "中国教育3", "CETV-3 教育服务", "CETV-3"],
    "中国教育4台": ["CETV4", "中国教育四台", "中国教育4", "CETV-4 职业教育", "CETV-4"],
    "早期教育": ["中国教育5台", "中国教育五台", "CETV早期教育", "华电早期教育", "CETV 早期教育"],
    "湖南卫视": ["湖南卫视4K"],
    "北京卫视": ["北京卫视4K"],
    "东方卫视": ["东方卫视4K"],
    "广东卫视": ["广东卫视4K"],
    "深圳卫视": ["深圳卫视4K"],
    "山东卫视": ["山东卫视4K"],
    "四川卫视": ["四川卫视4K"],
    "浙江卫视": ["浙江卫视4K"],
    "CHC影迷电影": ["CHC高清电影", "CHC-影迷电影", "影迷电影", "chc高清电影"],
    "淘电影": ["IPTV淘电影", "北京IPTV淘电影", "北京淘电影"],
    "淘精彩": ["IPTV淘精彩", "北京IPTV淘精彩", "北京淘精彩"],
    "淘剧场": ["IPTV淘剧场", "北京IPTV淘剧场", "北京淘剧场"],
    "淘4K": ["IPTV淘4K", "北京IPTV4K超清", "北京淘4K", "淘4K", "淘 4K"],
    "淘娱乐": ["IPTV淘娱乐", "北京IPTV淘娱乐", "北京淘娱乐"],
    "淘BABY": ["IPTV淘BABY", "北京IPTV淘BABY", "北京淘BABY", "IPTV淘baby", "北京IPTV淘baby", "北京淘baby"],
    "淘萌宠": ["IPTV淘萌宠", "北京IPTV萌宠TV", "北京淘萌宠"],
    "魅力足球": ["上海魅力足球"],
    "睛彩青少": ["睛彩羽毛球"],
    "求索纪录": ["求索记录", "求索纪录4K", "求索记录4K", "求索纪录 4K", "求索记录 4K"],
    "金鹰纪实": ["湖南金鹰纪实", "金鹰记实"],
    "纪实科教": ["北京纪实科教", "BRTV纪实科教", "纪实科教8K"],
    "星空卫视": ["星空衛視", "星空衛视", "星空卫視"],
    "CHANNEL[V]": ["CHANNEL-V", "Channel[V]"],
    "凤凰卫视中文台": ["凤凰中文", "凤凰中文台", "凤凰卫视中文", "凤凰卫视"],
    "凤凰卫视香港台": ["凤凰香港台", "凤凰卫视香港", "凤凰香港"],
    "凤凰卫视资讯台": ["凤凰资讯", "凤凰资讯台", "凤凰咨询", "凤凰咨询台", "凤凰卫视咨询台", "凤凰卫视资讯", "凤凰卫视咨询"],
    "凤凰卫视电影台": ["凤凰电影", "凤凰电影台", "凤凰卫视电影", "鳳凰衛視電影台", " 凤凰电影"],
    "茶频道": ["湖南茶频道"],
    "快乐垂钓": ["湖南快乐垂钓"],
    "先锋乒羽": ["湖南先锋乒羽"],
    "天元围棋": ["天元围棋频道"],
    "汽摩": ["重庆汽摩", "汽摩频道", "重庆汽摩频道"],
    "梨园频道": ["河南梨园频道", "梨园", "河南梨园"],
    "文物宝库": ["河南文物宝库"],
    "武术世界": ["河南武术世界"],
    "乐游": ["乐游频道", "上海乐游频道", "乐游纪实", "SiTV乐游频道", "SiTV 乐游频道"],
    "欢笑剧场": ["上海欢笑剧场4K", "欢笑剧场 4K", "欢笑剧场4K", "上海欢笑剧场"],
    "生活时尚": ["生活时尚4K", "SiTV生活时尚", "上海生活时尚"],
    "都市剧场": ["都市剧场4K", "SiTV都市剧场", "上海都市剧场"],
    "游戏风云": ["游戏风云4K", "SiTV游戏风云", "上海游戏风云"],
    "金色学堂": ["金色学堂4K", "SiTV金色学堂", "上海金色学堂"],
    "动漫秀场": ["动漫秀场4K", "SiTV动漫秀场", "上海动漫秀场"],
    "卡酷少儿": ["北京KAKU少儿", "BRTV卡酷少儿", "北京卡酷少儿", "卡酷动画"],
    "哈哈炫动": ["炫动卡通", "上海哈哈炫动"],
    "优漫卡通": ["江苏优漫卡通", "优漫漫画"],
    "金鹰卡通": ["湖南金鹰卡通"],
    "中国交通": ["中国交通频道"],
    "中国天气": ["中国天气频道"],
    "华数4K": ["华数低于4K", "华数4K电影", "华数爱上4K"],
}

# ===============================
def get_run_count():
    """获取运行计数"""
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, "r", encoding="utf-8") as f:
                return int(f.read().strip() or "0")
        except (ValueError, IOError) as e:
            print(f"⚠️ 读取计数文件失败：{e}，重置为0")
            return 0
    return 0

def save_run_count(count):
    """保存运行计数"""
    try:
        with open(COUNTER_FILE, "w", encoding="utf-8") as f:
            f.write(str(count))
    except IOError as e:
        print(f"⚠️ 写计数文件失败：{e}")

# ===============================
def get_isp_from_api(data):
    """从IP-API返回数据识别运营商"""
    isp_raw = (data.get("isp") or "").lower()

    if any(key in isp_raw for key in ["telecom", "ct", "chinatelecom"]):
        return "电信"
    elif any(key in isp_raw for key in ["unicom", "cu", "chinaunicom"]):
        return "联通"
    elif any(key in isp_raw for key in ["mobile", "cm", "chinamobile"]):
        return "移动"
    return "未知"

def get_isp_by_regex(ip):
    """通过IP段正则识别运营商"""
    # 修正正则表达式，避免重复匹配
    # 电信IP段
    telecom_pattern = r"^(103|112|113|114|115|116|117|118|119|120|121|122|123|180|181|189|202|203|219|220|221|222)\."
    # 联通IP段
    unicom_pattern = r"^(106|110|130|131|132|145|155|156|166|175|176|185|186|196|202|203|210|211|218)\."
    # 移动IP段
    mobile_pattern = r"^(100|134|135|136|137|138|139|147|150|151|152|157|158|159|178|182|183|184|187|188|198|223)\."

    if re.match(telecom_pattern, ip):
        return "电信"
    elif re.match(unicom_pattern, ip):
        return "联通"
    elif re.match(mobile_pattern, ip):
        return "移动"
    return "未知"

# ===============================
# 第一阶段：爬取IP并按省份运营商分类
def first_stage():
    """第一阶段：爬取IP并按省份+运营商分类保存"""
    os.makedirs(IP_DIR, exist_ok=True)
    all_ips = set()

    # 爬取FOFA上的IP
    for url, filename in FOFA_URLS.items():
        print(f"📡 正在爬取 {filename} 对应的FOFA链接: {url}")
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()  # 抛出HTTP错误
            # 提取IP:PORT
            urls_all = re.findall(r'<a href="http://([\d.:]+)"', response.text)
            valid_ips = {u.strip() for u in urls_all if u.strip() and ":" in u}
            all_ips.update(valid_ips)
            print(f"✅ 爬取到 {len(valid_ips)} 个IP:PORT")
        except requests.exceptions.RequestException as e:
            print(f"❌ 爬取失败：{e}")
        time.sleep(3)  # 防反爬

    if not all_ips:
        print("⚠️ 未爬取到任何IP，第一阶段结束")
        return get_run_count() + 1

    # 识别省份和运营商
    province_isp_dict = {}
    for ip_port in all_ips:
        try:
            host = ip_port.split(":", 1)[0]
            ip = None

            # 验证是否为IP，不是则解析域名
            if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
                ip = host
            else:
                try:
                    ip = socket.gethostbyname(host)
                    print(f"🌐 域名解析: {host} → {ip}")
                except socket.gaierror:
                    print(f"❌ 域名解析失败，跳过: {ip_port}")
                    continue

            # 查询IP信息
            ip_api_url = f"http://ip-api.com/json/{ip}?lang=zh-CN"
            response = requests.get(ip_api_url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "success":
                print(f"⚠️ IP查询失败: {ip} → {data.get('message', '未知错误')}")
                continue

            # 提取省份和运营商
            province = data.get("regionName", "未知").strip() or "未知"
            isp = get_isp_from_api(data)
            if isp == "未知":
                isp = get_isp_by_regex(ip)

            if isp == "未知":
                print(f"⚠️ 无法识别运营商，跳过: {ip_port}")
                continue

            # 构建文件名并添加IP
            fname = f"{province}{isp}.txt"
            province_isp_dict.setdefault(fname, set()).add(ip_port)

        except Exception as e:
            print(f"⚠️ 处理 {ip_port} 出错: {e}")
            continue

    # 保存计数
    count = get_run_count() + 1
    save_run_count(count)

    # 写入文件（追加模式）
    for filename, ip_set in province_isp_dict.items():
        if not ip_set:
            continue
        path = os.path.join(IP_DIR, filename)
        try:
            # 去重写入（先读现有，再合并）
            existing = set()
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    existing = {line.strip() for line in f if line.strip()}
            # 合并新IP并去重
            all_ip = existing.union(ip_set)
            with open(path, "w", encoding="utf-8") as f:
                for ip_port in sorted(all_ip):
                    f.write(ip_port + "\n")
            print(f"✅ {path} → 总计 {len(all_ip)} 个IP（新增 {len(ip_set - existing)} 个）")
        except IOError as e:
            print(f"❌ 写入 {path} 失败: {e}")

    print(f"✅ 第一阶段完成，当前轮次: {count}")
    return count

# ===============================
# 第二阶段：组合IP和RTP生成zubo.txt
def second_stage():
    """第二阶段：组合IP和RTP文件生成zubo.txt"""
    print("🔔 开始第二阶段：生成zubo.txt")
    
    if not os.path.exists(IP_DIR):
        print("⚠️ IP目录不存在，跳过第二阶段")
        return
    if not os.path.exists(RTP_DIR):
        print("⚠️ RTP目录不存在，跳过第二阶段")
        return

    combined_lines = []

    # 遍历所有IP文件
    for ip_filename in os.listdir(IP_DIR):
        if not ip_filename.endswith(".txt"):
            continue
        
        ip_path = os.path.join(IP_DIR, ip_filename)
        rtp_path = os.path.join(RTP_DIR, ip_filename)
        
        if not os.path.exists(rtp_path):
            print(f"⚠️ 未找到对应的RTP文件: {rtp_path}，跳过")
            continue

        # 读取IP和RTP内容
        try:
            with open(ip_path, "r", encoding="utf-8") as f:
                ip_lines = [line.strip() for line in f if line.strip()]
            with open(rtp_path, "r", encoding="utf-8") as f:
                rtp_lines = [line.strip() for line in f if line.strip()]
        except IOError as e:
            print(f"⚠️ 读取文件失败 {ip_filename}: {e}")
            continue

        if not ip_lines or not rtp_lines:
            print(f"⚠️ IP或RTP文件为空: {ip_filename}")
            continue

        # 组合URL
        for ip_port in ip_lines:
            for rtp_line in rtp_lines:
                if "," not in rtp_line:
                    continue
                ch_name, rtp_url = rtp_line.split(",", 1)
                ch_name = ch_name.strip()
                rtp_url = rtp_url.strip()

                # 处理RTP和UDP链接
                if rtp_url.startswith("rtp://"):
                    part = rtp_url[len("rtp://"):]
                    combined_lines.append(f"{ch_name},http://{ip_port}/rtp/{part}")
                elif rtp_url.startswith("udp://"):
                    part = rtp_url[len("udp://"):]
                    combined_lines.append(f"{ch_name},http://{ip_port}/udp/{part}")

    # 去重（按URL去重）
    unique_lines = {}
    for line in combined_lines:
        if "," not in line:
            continue
        name, url = line.split(",", 1)
        if url not in unique_lines:
            unique_lines[url] = line

    # 写入zubo.txt
    try:
        with open(ZUBO_FILE, "w", encoding="utf-8") as f:
            for line in unique_lines.values():
                f.write(line + "\n")
        print(f"✅ 第二阶段完成，写入 {len(unique_lines)} 条唯一记录到 {ZUBO_FILE}")
    except IOError as e:
        print(f"❌ 写入 {ZUBO_FILE} 失败: {e}")

# ===============================
# 第三阶段：检测可用流并生成IPTV.txt
def third_stage():
    """第三阶段：检测可用流，生成IPTV.txt并更新可用IP"""
    print("🧩 开始第三阶段：检测可用流并生成IPTV.txt")
    
    if not os.path.exists(ZUBO_FILE):
        print(f"⚠️ {ZUBO_FILE} 不存在，跳过第三阶段")
        return

    def check_stream(url, timeout=5):
        """检测流是否可播放"""
        try:
            # 使用ffprobe检测流
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_streams", "-i", url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=False
            )
            # 存在codec_type说明有有效流
            return b"codec_type" in result.stdout
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError) as e:
            return False
        except Exception as e:
            print(f"⚠️ 检测流异常 {url}: {e}")
            return False

    # 构建别名映射（反向）
    alias_to_main = {}
    for main_name, aliases in CHANNEL_MAPPING.items():
        alias_to_main[main_name] = main_name  # 自身映射
        for alias in aliases:
            alias_to_main[alias.strip()] = main_name

    # 读取IP-运营商映射
    ip_operator_map = {}
    if os.path.exists(IP_DIR):
        for fname in os.listdir(IP_DIR):
            if not fname.endswith(".txt"):
                continue
            operator = fname[:-4]  # 去掉.txt
            try:
                with open(os.path.join(IP_DIR, fname), "r", encoding="utf-8") as f:
                    for line in f:
                        ip_port = line.strip()
                        if ip_port:
                            ip_operator_map[ip_port] = operator
            except IOError as e:
                print(f"⚠️ 读取IP文件 {fname} 失败: {e}")

    # 读取zubo.txt并按IP分组
    ip_channel_groups = {}
    try:
        with open(ZUBO_FILE, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or "," not in line:
                    continue
                ch_name, url = line.split(",", 1)
                # 匹配标准频道名
                ch_main = alias_to_main.get(ch_name.strip(), ch_name.strip())
                # 提取IP:PORT
                ip_match = re.match(r"http://([^/]+)/", url)
                if not ip_match:
                    continue
                ip_port = ip_match.group(1)
                # 分组
                ip_channel_groups.setdefault(ip_port, []).append((ch_main, url))
    except IOError as e:
        print(f"❌ 读取 {ZUBO_FILE} 失败: {e}")
        return

    if not ip_channel_groups:
        print("⚠️ 未解析到任何IP-频道组，跳过检测")
        return

    # 多线程检测可用IP
    print(f"🚀 启动多线程检测 {len(ip_channel_groups)} 个IP的流可用性...")
    playable_ips = set()
    max_workers = min(20, len(ip_channel_groups))  # 限制线程数
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交任务：优先检测CCTV1，无则检测第一个频道
        future_tasks = {}
        for ip_port, channels in ip_channel_groups.items():
            # 筛选CCTV1频道
            cctv1_urls = [url for ch, url in channels if ch == "CCTV1"]
            # 无CCTV1则取第一个
            test_urls = cctv1_urls if cctv1_urls else [channels[0][1]]
            future = executor.submit(
                lambda urls: any(check_stream(url) for url in urls),
                test_urls
            )
            future_tasks[future] = ip_port

        # 处理结果
        for future in concurrent.futures.as_completed(future_tasks):
            ip_port = future_tasks[future]
            try:
                is_playable = future.result()
                if is_playable:
                    playable_ips.add(ip_port)
                    print(f"✅ IP可用: {ip_port}")
                else:
                    print(f"❌ IP不可用: {ip_port}")
            except Exception as e:
                print(f"⚠️ 检测IP {ip_port} 异常: {e}")

    print(f"✅ 检测完成，可用IP数量: {len(playable_ips)}")

    # 收集有效频道并更新IP文件
    valid_channels = []
    seen_urls = set()
    operator_playable_ips = {}

    for ip_port in playable_ips:
        operator = ip_operator_map.get(ip_port, "未知")
        # 收集该IP的有效频道
        for ch_main, url in ip_channel_groups.get(ip_port, []):
            if url in seen_urls:
                continue
            seen_urls.add(url)
            # 格式：频道名,URL$运营商
            valid_channels.append(f"{ch_main},{url}${operator}")
        # 按运营商分组保存可用IP
        operator_playable_ips.setdefault(operator, set()).add(ip_port)

    # 写回可用IP到IP目录（覆盖模式）
    for operator, ip_set in operator_playable_ips.items():
        if not ip_set:
            continue
        ip_file = os.path.join(IP_DIR, f"{operator}.txt")
        try:
            with open(ip_file, "w", encoding="utf-8") as f:
                for ip_port in sorted(ip_set):
                    f.write(ip_port + "\n")
            print(f"✅ 更新可用IP文件: {ip_file} → {len(ip_set)} 个IP")
        except IOError as e:
            print(f"❌ 写入IP文件 {ip_file} 失败: {e}")

    # 生成IPTV.txt（按分类排序）
    try:
        # 获取北京时间
        beijing_tz = timezone(timedelta(hours=8))
        now = datetime.now(beijing_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        with open(IPTV_FILE, "w", encoding="utf-8") as f:
            # 写入头部信息
            f.write(f"更新时间: {now}（北京时间）\n\n")
            f.write(f"更新时间,#genre#\n")
            f.write(f"{now},{DISCLAIMER_URL}\n\n")

            # 按分类写入频道
            for category, ch_list in CHANNEL_CATEGORIES.items():
                f.write(f"{category},#genre#\n")
                # 筛选该分类下的频道
                category_channels = [
                    line for line in valid_channels 
                    if line.split(",", 1)[0] in ch_list
                ]
                # 写入频道
                for line in category_channels:
                    f.write(line + "\n")
                f.write("\n")  # 分类间空行

        print(f"✅ 生成 {IPTV_FILE} → 总计 {len(valid_channels)} 条有效频道")
    except IOError as e:
        print(f"❌ 写入 {IPTV_FILE} 失败: {e}")

# ===============================
# 文件推送
def push_all_files():
    """推送文件到GitHub"""
    print("🚀 开始推送文件到GitHub...")
    try:
        # 配置Git
        subprocess.run(
            ["git", "config", "--global", "user.name", "github-actions"],
            check=False, capture_output=True
        )
        subprocess.run(
            ["git", "config", "--global", "user.email", "github-actions@users.noreply.github.com"],
            check=False, capture_output=True
        )

        # 添加文件
        subprocess.run(["git", "add", COUNTER_FILE], check=False)
        subprocess.run(["git", "add", f"{IP_DIR}/*.txt"], check=False)
        subprocess.run(["git", "add", IPTV_FILE], check=False)

        # 提交
        commit_msg = f"自动更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 计数={get_run_count()}"
        commit_result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            capture_output=True, text=True
        )
        if "nothing to commit" in commit_result.stderr:
            print("ℹ️ 无文件变更，无需提交")
        else:
            print(f"✅ 提交成功: {commit_msg}")

        # 推送
        push_result = subprocess.run(
            ["git", "push", "origin", "main"],
            capture_output=True, text=True
        )
        if push_result.returncode == 0:
            print("✅ 推送成功到GitHub")
        else:
            print(f"❌ 推送失败: {push_result.stderr}")

    except Exception as e:
        print(f"❌ 推送过程异常: {e}")

# ===============================
# 主执行逻辑
if __name__ == "__main__":
    # 初始化目录
    os.makedirs(IP_DIR, exist_ok=True)
    os.makedirs(RTP_DIR, exist_ok=True)

    # 执行第一阶段
    run_count = first_stage()

    # 每10轮执行第二、三阶段
    if run_count % 10 == 0:
        second_stage()
        third_stage()
    else:
        print(f"ℹ️ 当前轮次 {run_count} 不是10的倍数，跳过第二、三阶段")

    # 推送文件
    push_all_files()

    print("🎉 所有流程执行完成！")
