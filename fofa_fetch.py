import os
import re
import requests
import time
import concurrent.futures
import subprocess
import socket
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
        "河北经济生活", "河北都市", "河北影视剧", "河北少儿科教", "河北公共", "河北农民", "睛彩河北","三佳购物",
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
# 计数相关函数
def get_run_count():
    if os.path.exists(COUNTER_FILE):
        try:
            return int(open(COUNTER_FILE, "r", encoding="utf-8").read().strip() or "0")
        except Exception:
            return 0
    return 0

def save_run_count(count):
    try:
        with open(COUNTER_FILE, "w", encoding="utf-8") as f:
            f.write(str(count))
    except Exception as e:
        print(f"⚠️ 写计数文件失败：{e}")

# ===============================
# IP/域名类型判断
def get_ip_type(ip_or_domain):
    # 匹配IPv6（完整规则）
    ipv6_pattern = r'^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4})|(([0-9a-fA-F]{1,4}:){1,7}:)|(([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4})|(([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2})|(([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3})|(([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4})|(([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5})|([0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6}))|(:((:[0-9a-fA-F]{1,4}){1,7}|:))|(::([fF]{4}(:0{1,4}){0,1}:)?((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])$'
    if re.match(ipv6_pattern, ip_or_domain):
        return "ipv6"
    # 匹配IPv4
    elif re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip_or_domain):
        return "ipv4"
    # 其余为域名
    else:
        return "domain"

# 域名解析（兼容IPv4/IPv6）
def resolve_domain(domain):
    """解析域名，返回 (ipv4列表, ipv6列表)"""
    ipv4_list = []
    ipv6_list = []
    try:
        # 获取所有地址信息
        addrinfo = socket.getaddrinfo(domain, None, 0, socket.SOCK_STREAM)
        for addr in addrinfo:
            ip = addr[4][0]
            if get_ip_type(ip) == "ipv4":
                ipv4_list.append(ip)
            elif get_ip_type(ip) == "ipv6":
                ipv6_list.append(ip)
    except Exception as e:
        print(f"❌ 域名 {domain} 解析失败：{e}")
    return list(set(ipv4_list)), list(set(ipv6_list))

# 运营商判断（API）
def get_isp_from_api(data):
    isp_raw = (data.get("isp") or "").lower()
    if "telecom" in isp_raw or "ct" in isp_raw or "chinatelecom" in isp_raw:
        return "电信"
    elif "unicom" in isp_raw or "cu" in isp_raw or "chinaunicom" in isp_raw:
        return "联通"
    elif "mobile" in isp_raw or "cm" in isp_raw or "chinamobile" in isp_raw:
        return "移动"
    elif "radio" in isp_raw or "cable" in isp_raw:
        return "广电"
    return "未知"

# 运营商判断（正则/精准匹配2025最新段）
def get_isp_by_regex(ip):
    ip_type = get_ip_type(ip)
    
    if ip_type == "ipv4":
        # IPv4 精准段（2025最新）
        # 电信 IPv4 段
        telecom_ipv4 = r"^(103\.|112\.|113\.|121\.|140\.143\.|180\.|181\.|189\.|202\.96\.|219\.133\.|220\.|223\.)$"
        # 联通 IPv4 段
        unicom_ipv4 = r"^(101\.|106\.|114\.|120\.|130\.|131\.|132\.|145\.|155\.|156\.|166\.|175\.|176\.|185\.|186\.|196\.|202\.106\.|202\.112\.|202\.165\.|202\.99\.|210\.42\.|218\.)$"
        # 移动 IPv4 段
        mobile_ipv4 = r"^(102\.|108\.|109\.|134\.|135\.|136\.|137\.|138\.|139\.|147\.|150\.|151\.|152\.|157\.|158\.|159\.|172\.|178\.|182\.|183\.|184\.|187\.|188\.|198\.)$"
        
        if re.match(telecom_ipv4, ip):
            return "电信"
        elif re.match(unicom_ipv4, ip):
            return "联通"
        elif re.match(mobile_ipv4, ip):
            return "移动"
    
    elif ip_type == "ipv6":
        # IPv6 精准匹配（2025三大运营商官方段）
        ip_lower = ip.lower()
        
        # 电信 IPv6：240e::/16、2409:8000::/20、2408:8000::/20
        if ip_lower.startswith("240e:") or \
           (ip_lower.startswith("2409:8") and len(ip_lower) >= 6 and ip_lower[5] == '8') or \
           (ip_lower.startswith("2408:8") and len(ip_lower) >= 6 and ip_lower[5] == '8'):
            return "电信"
        
        # 联通 IPv6：2408::/16（排除8000::/20）、2407::/16
        elif ip_lower.startswith("2407:") or \
             (ip_lower.startswith("2408:") and not (len(ip_lower) >= 6 and ip_lower[5] == '8')):
            return "联通"
        
        # 移动 IPv6：2409::/16（排除8000::/20）、240a::/16、240b::/16
        elif ip_lower.startswith(("240a:", "240b:")) or \
             (ip_lower.startswith("2409:") and not (len(ip_lower) >= 6 and ip_lower[5] == '8')):
            return "移动"
        
        # 广电 IPv6
        elif ip_lower.startswith("240c:"):
            return "广电"
    
    return "未知"

# ===============================
# 第一阶段：爬取+解析IP/域名+分类存储
def first_stage():
    os.makedirs(IP_DIR, exist_ok=True)
    all_targets = set()  # 存储 域名/IP:端口

    for url, filename in FOFA_URLS.items():
        print(f"📡 正在爬取 {filename} ...")
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            urls_all = re.findall(r'<a href="http://(.*?)"', r.text)
            all_targets.update(u.strip() for u in urls_all if u.strip())
        except Exception as e:
            print(f"❌ 爬取失败：{e}")
        time.sleep(3)

    province_isp_dict = {}

    for target_port in all_targets:
        try:
            # 拆分 地址:端口
            if ":" not in target_port:
                print(f"⚠️ 无端口，跳过：{target_port}")
                continue
            host, port = target_port.rsplit(":", 1)
            if not port.isdigit():
                print(f"⚠️ 端口非法，跳过：{target_port}")
                continue

            # 区分IP类型
            ip_type = get_ip_type(host)
            resolve_ips = []
            
            if ip_type == "domain":
                # 解析域名，优先IPv4，再IPv6
                ipv4_list, ipv6_list = resolve_domain(host)
                resolve_ips = ipv4_list + ipv6_list
                if not resolve_ips:
                    print(f"❌ 域名 {host} 无有效解析，跳过：{target_port}")
                    continue
                print(f"🌐 域名解析结果: {host} → IPv4:{ipv4_list} IPv6:{ipv6_list}")
            else:
                # IP直接使用
                resolve_ips = [host]

            # 遍历解析后的IP（域名可能解析出多个IP）
            for ip in resolve_ips:
                # 获取IP归属和运营商
                try:
                    # ip-api.com 支持IPv6
                    res = requests.get(f"http://ip-api.com/json/{ip}?lang=zh-CN", timeout=10)
                    data = res.json()
                    province = data.get("regionName", "未知")
                    isp = get_isp_from_api(data)
                    if isp == "未知":
                        isp = get_isp_by_regex(ip)
                except Exception as e:
                    print(f"⚠️ IP {ip} 归属查询失败：{e}")
                    province = "未知"
                    isp = "未知"

                if isp == "未知":
                    print(f"⚠️ 无法判断运营商，跳过：{ip}:{port}")
                    continue

                # 保留原始目标（域名/IP:端口）
                fname = f"{province}{isp}.txt"
                province_isp_dict.setdefault(fname, set()).add(target_port)

        except Exception as e:
            print(f"⚠️ 解析 {target_port} 出错：{e}")
            continue

    count = get_run_count() + 1
    save_run_count(count)

    for filename, target_set in province_isp_dict.items():
        path = os.path.join(IP_DIR, filename)
        try:
            with open(path, "a", encoding="utf-8") as f:
                for target_port in sorted(target_set):
                    f.write(target_port + "\n")
            print(f"{path} 已追加写入 {len(target_set)} 个目标（域名/IP）")
        except Exception as e:
            print(f"❌ 写入 {path} 失败：{e}")

    print(f"✅ 第一阶段完成，当前轮次：{count}")
    return count

# ===============================
# 第二阶段：生成zubo.txt
def second_stage():
    print("🔔 第二阶段触发：生成 zubo.txt")
    if not os.path.exists(IP_DIR):
        print("⚠️ ip 目录不存在，跳过第二阶段")
        return

    combined_lines = []

    if not os.path.exists(RTP_DIR):
        print("⚠️ rtp 目录不存在，无法进行第二阶段组合，跳过")
        return

    for ip_file in os.listdir(IP_DIR):
        if not ip_file.endswith(".txt"):
            continue

        ip_path = os.path.join(IP_DIR, ip_file)
        rtp_path = os.path.join(RTP_DIR, ip_file)

        if not os.path.exists(rtp_path):
            continue

        try:
            with open(ip_path, encoding="utf-8") as f1, open(rtp_path, encoding="utf-8") as f2:
                ip_lines = [x.strip() for x in f1 if x.strip()]
                rtp_lines = [x.strip() for x in f2 if x.strip()]
        except Exception as e:
            print(f"⚠️ 文件读取失败：{e}")
            continue

        if not ip_lines or not rtp_lines:
            continue

        for ip_port in ip_lines:
            for rtp_line in rtp_lines:
                if "," not in rtp_line:
                    continue

                ch_name, rtp_url = rtp_line.split(",", 1)

                if "rtp://" in rtp_url:
                    part = rtp_url.split("rtp://", 1)[1]
                    combined_lines.append(f"{ch_name},http://{ip_port}/rtp/{part}")

                elif "udp://" in rtp_url:
                    part = rtp_url.split("udp://", 1)[1]
                    combined_lines.append(f"{ch_name},http://{ip_port}/udp/{part}")

    # 去重
    unique = {}
    for line in combined_lines:
        url_part = line.split(",", 1)[1]
        if url_part not in unique:
            unique[url_part] = line

    try:
        with open(ZUBO_FILE, "w", encoding="utf-8") as f:
            for line in unique.values():
                f.write(line + "\n")
        print(f"🎯 第二阶段完成，写入 {len(unique)} 条记录")
    except Exception as e:
        print(f"❌ 写文件失败：{e}")

# ===============================
# 第三阶段：检测+生成IPTV.txt+写回可用IP
def third_stage():
    print("🧩 第三阶段：多线程检测代表频道生成 IPTV.txt 并写回可用 IP 到 ip/目录（覆盖）")

    if not os.path.exists(ZUBO_FILE):
        print("⚠️ zubo.txt 不存在，跳过第三阶段")
        return

    # 改造：ffprobe检测兼容IPv6/域名
    def check_stream(url, timeout=5):
        try:
            cmd = [
                "ffprobe", "-v", "error", "-show_streams", "-i", url,
                "-timeout", f"{timeout * 1000000}",  # 超时（微秒）
                "-dns_cache_timeout", "0"  # 禁用DNS缓存
            ]
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout + 2
            )
            return b"codec_type" in result.stdout
        except Exception:
            return False

    # 别名映射
    alias_map = {}
    for main_name, aliases in CHANNEL_MAPPING.items():
        for alias in aliases:
            alias_map[alias] = main_name

    # 读取现有 ip 文件，建立 ip_port -> operator 映射
    ip_info = {}
    if os.path.exists(IP_DIR):
        for fname in os.listdir(IP_DIR):
            if not fname.endswith(".txt"):
                continue
            province_operator = fname.replace(".txt", "")
            try:
                with open(os.path.join(IP_DIR, fname), encoding="utf-8") as f:
                    for line in f:
                        ip_port = line.strip()
                        if ip_port:
                            ip_info[ip_port] = province_operator
            except Exception as e:
                print(f"⚠️ 读取 {fname} 失败：{e}")

    # 读取 zubo.txt 并按 ip:port 分组
    groups = {}
    with open(ZUBO_FILE, encoding="utf-8") as f:
        for line in f:
            if "," not in line:
                continue

            ch_name, url = line.strip().split(",", 1)
            ch_main = alias_map.get(ch_name, ch_name)
            m = re.match(r"http://([^/]+)/", url)
            if not m:
                continue

            ip_port = m.group(1)
            groups.setdefault(ip_port, []).append((ch_main, url))

    # 选择代表频道并检测
    def detect_ip(ip_port, entries):
        rep_channels = [u for c, u in entries if c == "CCTV1"]
        if not rep_channels and entries:
            rep_channels = [entries[0][1]]
        playable = any(check_stream(u) for u in rep_channels)
        return ip_port, playable

    print(f"🚀 启动多线程检测（共 {len(groups)} 个目标）...")
    playable_ips = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(detect_ip, ip, chs): ip for ip, chs in groups.items()}
        for future in concurrent.futures.as_completed(futures):
            try:
                ip_port, ok = future.result()
            except Exception as e:
                print(f"⚠️ 线程检测返回异常：{e}")
                continue
            if ok:
                playable_ips.add(ip_port)

    print(f"✅ 检测完成，可播放目标共 {len(playable_ips)} 个")

    valid_lines = []
    seen = set()
    operator_playable_ips = {}

    for ip_port in playable_ips:
        operator = ip_info.get(ip_port, "未知")

        for c, u in groups.get(ip_port, []):
            key = f"{c},{u}"
            if key not in seen:
                seen.add(key)
                valid_lines.append(f"{c},{u}${operator}")

                operator_playable_ips.setdefault(operator, set()).add(ip_port)

    for operator, ip_set in operator_playable_ips.items():
        target_file = os.path.join(IP_DIR, operator + ".txt")
        try:
            with open(target_file, "w", encoding="utf-8") as wf:
                for ip_p in sorted(ip_set):
                    wf.write(ip_p + "\n")
            print(f"📥 写回 {target_file}，共 {len(ip_set)} 个可用地址")
        except Exception as e:
            print(f"❌ 写回 {target_file} 失败：{e}")

    # 写 IPTV.txt
    beijing_now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(IPTV_FILE, "w", encoding="utf-8") as f:
            f.write(f"更新时间: {beijing_now}（北京时间）\n\n")
            f.write("更新时间,#genre#\n")
            f.write(f"{beijing_now},\n\n")
            for category, ch_list in CHANNEL_CATEGORIES.items():
                f.write(f"{category},#genre#\n")
                for ch in ch_list:
                    for line in valid_lines:
                        name = line.split(",", 1)[0]
                        if name == ch:
                            f.write(line + "\n")
                f.write("\n")
        print(f"🎯 IPTV.txt 生成完成，共 {len(valid_lines)} 条频道")
    except Exception as e:
        print(f"❌ 写 IPTV.txt 失败：{e}")

# ===============================
# 文件推送
def push_all_files():
    print("🚀 推送所有更新文件到 GitHub...")
    try:
        os.system('git config --global user.name "github-actions"')
        os.system('git config --global user.email "github-actions@users.noreply.github.com"')
    except Exception:
        pass

    os.system("git add 计数.txt || true")
    os.system("git add ip/*.txt || true")
    os.system("git add IPTV.txt || true")
    os.system('git commit -m "自动更新：计数、IP文件、IPTV.txt" || echo "⚠️ 无需提交"')
    os.system("git push origin main || echo '⚠️ 推送失败'")

# ===============================
# 主执行逻辑
if __name__ == "__main__":
    # 确保目录存在
    os.makedirs(IP_DIR, exist_ok=True)
    os.makedirs(RTP_DIR, exist_ok=True)

    run_count = first_stage()

    if run_count % 10 == 0:
        second_stage()
        third_stage()
    else:
        print("ℹ️ 本次不是 10 的倍数，跳过第二、三阶段")

    push_all_files()
