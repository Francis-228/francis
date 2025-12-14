import os
import re
import requests
import time
import random
import concurrent.futures
import subprocess
import socket
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# ===============================
# 核心配置区（可根据需求调整）
FOFA_URLS = {
    "https://fofa.info/result?qbase64=InVkcHh5IiAmJiBjb3VudHJ5PSJDTiI%3D": {
        "output": "ip.txt",
        "max_pages": 3  # FOFA分页爬取最大页数
    },
}

# 动态User-Agent池（防反爬）
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/120.0.0.0"
]

# 代理配置（可选，需自行替换）
PROXIES = None  # 示例: {"http": "http://user:pass@proxy:port", "https": "http://user:pass@proxy:port"}

# 网络请求配置
REQUEST_TIMEOUT = 15          # 请求超时时间(秒)
RETRY_MAX_ATTEMPTS = 3       # 最大重试次数
RETRY_WAIT_MIN = 1           # 重试最小等待时间(秒)
RETRY_WAIT_MAX = 5           # 重试最大等待时间(秒)
MAX_DETECT_THREADS = 10      # 流检测最大线程数

# 路径配置
COUNTER_FILE = "计数.txt"
IP_DIR = "ip"
RTP_DIR = "rtp"
ZUBO_FILE = "zubo.txt"
IPTV_FILE = "IPTV.txt"
HISTORY_FILE = "history_ips.txt"  # 历史IP去重文件

# ===============================
# 频道分类与映射（完整配置）
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
# 工具函数（核心优化）
def get_random_headers():
    """生成随机请求头，降低反爬概率"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

@retry(
    stop=stop_after_attempt(RETRY_MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=RETRY_WAIT_MIN, max=RETRY_WAIT_MAX),
    retry=retry_if_exception_type((requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.HTTPError))
)
def safe_request(url, method="get", **kwargs):
    """带重试机制的安全HTTP请求"""
    kwargs.setdefault("headers", get_random_headers())
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)
    kwargs.setdefault("proxies", PROXIES)
    response = requests.request(method, url,** kwargs)
    response.raise_for_status()  # 触发HTTP错误（4xx/5xx）
    return response

def load_history_ips():
    """加载历史IP记录用于去重"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return set(line.strip() for line in f if line.strip())
        except Exception as e:
            print(f"⚠️ 读取历史IP文件失败：{e}，重新创建")
            return set()
    return set()

def save_to_history(ips):
    """将新IP写入历史记录"""
    if not ips:
        return
    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            for ip in ips:
                f.write(ip + "\n")
    except Exception as e:
        print(f"⚠️ 写入历史IP文件失败：{e}")

# ===============================
# 计数管理函数
def get_run_count():
    """获取当前运行计数"""
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                return int(content) if content.isdigit() else 0
        except Exception as e:
            print(f"⚠️ 读取计数文件失败：{e}，重置为0")
            return 0
    return 0

def save_run_count(count):
    """保存运行计数"""
    try:
        with open(COUNTER_FILE, "w", encoding="utf-8") as f:
            f.write(str(count))
    except Exception as e:
        print(f"⚠️ 写入计数文件失败：{e}")

# ===============================
# IP/域名处理函数
def get_ip_type(ip_or_domain):
    """判断IP类型（ipv4/ipv6/domain）"""
    # IPv6正则匹配
    ipv6_pattern = r'^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4})|(([0-9a-fA-F]{1,4}:){1,7}:)|(([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4})|(([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2})|(([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3})|(([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4})|(([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5})|([0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6}))|(:((:[0-9a-fA-F]{1,4}){1,7}|:))|(::([fF]{4}(:0{1,4}){0,1}:)?((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])$'
    if re.match(ipv6_pattern, ip_or_domain):
        return "ipv6"
    # IPv4正则匹配
    elif re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip_or_domain):
        return "ipv4"
    # 其余为域名
    else:
        return "domain"

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=3),
    retry=retry_if_exception_type((socket.gaierror, socket.timeout))
)
def resolve_domain(domain):
    """带重试的域名解析，返回(IPv4列表, IPv6列表)"""
    ipv4_list = []
    ipv6_list = []
    try:
        addrinfo = socket.getaddrinfo(domain, None, 0, socket.SOCK_STREAM)
        for addr in addrinfo:
            ip = addr[4][0]
            ip_type = get_ip_type(ip)
            if ip_type == "ipv4":
                ipv4_list.append(ip)
            elif ip_type == "ipv6":
                ipv6_list.append(ip)
        # 去重并返回
        return list(dict.fromkeys(ipv4_list)), list(dict.fromkeys(ipv6_list))
    except Exception as e:
        print(f"❌ 域名 {domain} 解析失败：{e}")
        raise  # 触发重试

@lru_cache(maxsize=1000)
def get_ip_info(ip):
    """多源获取IP归属信息，缓存结果提高效率"""
    # 源1: ip-api.com（优先）
    try:
        res = safe_request(f"http://ip-api.com/json/{ip}?lang=zh-CN")
        data = res.json()
        if data.get("status") == "success":
            return {
                "province": data.get("regionName", "未知"),
                "isp": data.get("isp", "未知")
            }
    except Exception:
        pass

    # 源2: ipinfo.io（备用）
    try:
        res = safe_request(f"https://ipinfo.io/{ip}/json")
        data = res.json()
        return {
            "province": data.get("region", "未知"),
            "isp": data.get("org", "未知")
        }
    except Exception:
        pass

    return {"province": "未知", "isp": "未知"}

def get_isp_from_api(isp_raw):
    """从API返回值识别运营商"""
    isp_raw = isp_raw.lower()
    if any(key in isp_raw for key in ["telecom", "ct", "chinatelecom", "中国电信"]):
        return "电信"
    elif any(key in isp_raw for key in ["unicom", "cu", "chinaunicom", "中国联通"]):
        return "联通"
    elif any(key in isp_raw for key in ["mobile", "cm", "chinamobile", "中国移动"]):
        return "移动"
    elif any(key in isp_raw for key in ["radio", "cable", "广电", "广电网"]):
        return "广电"
    return "未知"

def get_isp_by_regex(ip):
    """通过IP段正则匹配运营商（备用方案）"""
    ip_type = get_ip_type(ip)
    
    if ip_type == "ipv4":
        # IPv4运营商网段匹配
        telecom_ipv4 = r"^(103\.|112\.|113\.|121\.|140\.143\.|180\.|181\.|189\.|202\.96\.|219\.133\.|220\.|223\.)"
        unicom_ipv4 = r"^(101\.|106\.|114\.|120\.|130\.|131\.|132\.|145\.|155\.|156\.|166\.|175\.|176\.|185\.|186\.|196\.|202\.106\.|202\.112\.|202\.165\.|202\.99\.|210\.42\.|218\.)"
        mobile_ipv4 = r"^(102\.|108\.|109\.|134\.|135\.|136\.|137\.|138\.|139\.|147\.|150\.|151\.|152\.|157\.|158\.|159\.|172\.|178\.|182\.|183\.|184\.|187\.|188\.|198\.)"
        
        if re.match(telecom_ipv4, ip):
            return "电信"
        elif re.match(unicom_ipv4, ip):
            return "联通"
        elif re.match(mobile_ipv4, ip):
            return "移动"
    
    elif ip_type == "ipv6":
        # IPv6运营商网段匹配
        ip_lower = ip.lower()
        # 电信IPv6
        if ip_lower.startswith("240e:") or \
           (ip_lower.startswith("2409:8") and len(ip_lower) >= 6 and ip_lower[5] == '8') or \
           (ip_lower.startswith("2408:8") and len(ip_lower) >= 6 and ip_lower[5] == '8'):
            return "电信"
        # 联通IPv6
        elif ip_lower.startswith("2407:") or \
             (ip_lower.startswith("2408:") and not (len(ip_lower) >= 6 and ip_lower[5] == '8')):
            return "联通"
        # 移动IPv6
        elif ip_lower.startswith(("240a:", "240b:")) or \
             (ip_lower.startswith("2409:") and not (len(ip_lower) >= 6 and ip_lower[5] == '8')):
            return "移动"
        # 广电IPv6
        elif ip_lower.startswith("240c:"):
            return "广电"
    
    return "未知"

# ===============================
# 第一阶段：FOFA爬取与IP分类
def first_stage():
    """核心爬取逻辑：FOFA分页爬取→IP解析→运营商分类→文件存储"""
    os.makedirs(IP_DIR, exist_ok=True)
    all_targets = set()
    history_ips = load_history_ips()  # 加载历史IP去重

    # 遍历FOFA配置爬取
    for base_url, config in FOFA_URLS.items():
        output_file = config["output"]
        max_pages = config["max_pages"]
        print(f"\n📡 开始爬取 FOFA 数据（{output_file}，最多{max_pages}页）...")

        for page in range(1, max_pages + 1):
            try:
                # 构造分页URL
                page_url = f"{base_url}&page={page}" if "?" in base_url else f"{base_url}?page={page}"
                response = safe_request(page_url)
                
                # 增强版链接提取（兼容不同HTML格式）
                urls_all = re.findall(r'<a[^>]+href=["\'](http://[^"\']+)["\']', response.text)
                # 清洗数据：去重+过滤无效链接+排除历史IP
                new_targets = {
                    u.split("//")[-1].strip() for u in urls_all 
                    if u.strip() and ":" in u.strip()
                } - history_ips

                if not new_targets:
                    print(f"📄 第{page}页无新目标，停止分页爬取")
                    break

                all_targets.update(new_targets)
                print(f"📄 第{page}页爬取到 {len(new_targets)} 个新目标")
                time.sleep(random.uniform(2, 5))  # 随机间隔防反爬

            except Exception as e:
                print(f"❌ 第{page}页爬取失败：{e}")
                break  # 分页失败则停止当前URL爬取

    # 保存新目标到历史记录
    save_to_history(all_targets)
    if not all_targets:
        print("ℹ️ 未获取到新目标，跳过IP分类")
        count = get_run_count() + 1
        save_run_count(count)
        return count

    # IP解析与运营商分类
    province_isp_dict = {}
    print(f"\n🔍 开始解析 {len(all_targets)} 个目标...")
    for target_port in all_targets:
        try:
            host, port = target_port.rsplit(":", 1)
            # 端口合法性校验
            if not port.isdigit() or not (1 <= int(port) <= 65535):
                print(f"⚠️ 非法端口，跳过：{target_port}")
                continue

            ip_type = get_ip_type(host)
            resolve_ips = []
            
            # 域名解析
            if ip_type == "domain":
                ipv4_list, ipv6_list = resolve_domain(host)
                resolve_ips = ipv4_list + ipv6_list
                if not resolve_ips:
                    print(f"❌ 域名 {host} 无有效解析，跳过：{target_port}")
                    continue
                print(f"🌐 域名解析: {host} → IPv4:{len(ipv4_list)}个, IPv6:{len(ipv6_list)}个")
            else:
                resolve_ips = [host]

            # 运营商判断
            for ip in resolve_ips:
                ip_info = get_ip_info(ip)
                province = ip_info["province"] or "未知"
                isp = get_isp_from_api(ip_info["isp"])
                
                # API失败时使用正则匹配
                if isp == "未知":
                    isp = get_isp_by_regex(ip)

                if isp == "未知":
                    print(f"⚠️ 无法识别运营商，跳过：{ip}:{port}")
                    continue

                # 按省份+运营商分类存储
                fname = f"{province}{isp}.txt"
                province_isp_dict.setdefault(fname, set()).add(target_port)

        except Exception as e:
            print(f"⚠️ 处理 {target_port} 出错：{e}")
            continue

    # 更新运行计数
    count = get_run_count() + 1
    save_run_count(count)

    # 批量写入文件（减少IO操作）
    print(f"\n💾 开始写入IP文件...")
    for filename, target_set in province_isp_dict.items():
        path = os.path.join(IP_DIR, filename)
        try:
            # 读取现有内容去重
            existing = set()
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    existing = set(f.read().splitlines())
            
            # 合并新内容并去重
            new_content = existing.union(target_set)
            # 写入文件
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(new_content)) + "\n")
            
            print(f"✅ {path} → 总计 {len(new_content)} 条记录（新增 {len(new_content) - len(existing)} 条）")
        except Exception as e:
            print(f"❌ 写入 {path} 失败：{e}")

    print(f"\n✅ 第一阶段完成，当前运行轮次：{count}")
    return count

# ===============================
# 第二阶段：生成zubo.txt
def second_stage():
    """组合IP和RTP文件，生成zubo.txt"""
    print("\n🔔 启动第二阶段：生成zubo.txt...")
    if not os.path.exists(IP_DIR) or not os.path.exists(RTP_DIR):
        print("⚠️ ip或rtp目录不存在，跳过第二阶段")
        return

    # 预加载所有RTP文件（缓存提高效率）
    rtp_cache = {}
    for rtp_file in os.listdir(RTP_DIR):
        if not rtp_file.endswith(".txt"):
            continue
        rtp_path = os.path.join(RTP_DIR, rtp_file)
        try:
            with open(rtp_path, encoding="utf-8") as f:
                rtp_cache[rtp_file] = [
                    line.strip() for line in f 
                    if line.strip() and "," in line.strip()
                ]
        except Exception as e:
            print(f"⚠️ 读取RTP文件 {rtp_file} 失败：{e}")

    if not rtp_cache:
        print("⚠️ 无有效RTP文件，跳过第二阶段")
        return

    # 组合IP和RTP生成链接
    combined_lines = []
    for ip_file in os.listdir(IP_DIR):
        if not ip_file.endswith(".txt") or ip_file not in rtp_cache:
            continue

        ip_path = os.path.join(IP_DIR, ip_file)
        try:
            with open(ip_path, encoding="utf-8") as f:
                ip_lines = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"⚠️ 读取IP文件 {ip_file} 失败：{e}，跳过")
            continue

        if not ip_lines:
            continue

        # 生成组合链接
        for ip_port in ip_lines:
            for rtp_line in rtp_cache[ip_file]:
                ch_name, rtp_url = rtp_line.split(",", 1)
                rtp_url = rtp_url.strip()

                if "rtp://" in rtp_url:
                    part = rtp_url.split("rtp://", 1)[1]
                    combined_lines.append(f"{ch_name},http://{ip_port}/rtp/{part}")
                elif "udp://" in rtp_url:
                    part = rtp_url.split("udp://", 1)[1]
                    combined_lines.append(f"{ch_name},http://{ip_port}/udp/{part}")

    # 去重：倒序保留最新链接
    unique_lines = {}
    for line in reversed(combined_lines):
        if "," not in line:
            continue
        url_part = line.split(",", 1)[1]
        if url_part not in unique_lines:
            unique_lines[url_part] = line
    # 恢复正序
    final_lines = list(reversed(unique_lines.values()))

    # 写入zubo.txt
    try:
        with open(ZUBO_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(final_lines) + "\n")
        print(f"✅ zubo.txt 生成完成 → 总计 {len(final_lines)} 条有效链接")
    except Exception as e:
        print(f"❌ 写入zubo.txt失败：{e}")

# ===============================
# 第三阶段：流检测与IPTV生成
def third_stage():
    """检测可用流→生成IPTV.txt→清理无效IP"""
    print("\n🧩 启动第三阶段：流检测与IPTV生成...")
    if not os.path.exists(ZUBO_FILE):
        print("⚠️ zubo.txt不存在，跳过第三阶段")
        return

    def check_stream(url, timeout=5):
        """优化版流检测：限制资源+超时"""
        try:
            cmd = [
                "ffprobe", "-v", "error", "-show_streams", "-i", url,
                "-timeout", f"{timeout * 1000000}",  # 超时（微秒）
                "-dns_cache_timeout", "0",           # 禁用DNS缓存
                "-probesize", "5000000",             # 限制探测数据量（5MB）
                "-analyzeduration", "5000000",       # 限制分析时间（5秒）
                "-hide_banner"
            ]
            # 执行检测，降低进程优先级
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout + 2,
                text=False,
                preexec_fn=lambda: os.nice(10)  # 降低优先级
            )
            # 验证是否有视频流
            return b"codec_type=video" in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False

    # 构建频道别名映射
    alias_map = {}
    for main_name, aliases in CHANNEL_MAPPING.items():
        for alias in aliases:
            alias_map[alias] = main_name
        alias_map[main_name] = main_name  # 自身映射

    # 读取IP-运营商映射
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
                        if ip_port and ":" in ip_port:
                            ip_info[ip_port] = province_operator
            except Exception as e:
                print(f"⚠️ 读取IP文件 {fname} 失败：{e}")

    # 按IP:PORT分组频道
    groups = {}
    try:
        with open(ZUBO_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "," not in line:
                    continue

                ch_name, url = line.split(",", 1)
                ch_main = alias_map.get(ch_name, ch_name)
                # 提取IP:PORT
                m = re.match(r"http://([^/]+)/", url)
                if m:
                    ip_port = m.group(1)
                    groups.setdefault(ip_port, []).append((ch_main, url))
    except Exception as e:
        print(f"❌ 读取zubo.txt失败：{e}")
        return

    if not groups:
        print("⚠️ 无有效分组数据，跳过检测")
        return

    # 动态调整线程数
    max_workers = min(MAX_DETECT_THREADS, len(groups))
    print(f"🚀 启动多线程检测 → 线程数：{max_workers}，目标数：{len(groups)}")
    
    # 多线程检测可用IP
    playable_ips = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交检测任务（优先检测CCTV1）
        futures = {}
        for ip_port, entries in groups.items():
            # 优先检测CCTV1，无则检测第一个频道
            test_urls = [u for c, u in entries if c == "CCTV1"] or [entries[0][1]]
            futures[executor.submit(check_stream, test_urls[0])] = ip_port

        # 处理检测结果
        for future in concurrent.futures.as_completed(futures):
            ip_port = futures[future]
            try:
                if future.result():
                    playable_ips.add(ip_port)
                    print(f"✅ {ip_port} → 检测通过")
                else:
                    print(f"❌ {ip_port} → 检测失败")
            except Exception as e:
                print(f"⚠️ 检测 {ip_port} 异常：{e}")

    print(f"\n✅ 检测完成 → 可用IP总数：{len(playable_ips)}")
    if not playable_ips:
        print("⚠️ 无可用IP，跳过IPTV生成")
        return

    # 生成有效频道列表
    valid_lines = []
    seen = set()
    operator_playable_ips = {}

    for ip_port in playable_ips:
        operator = ip_info.get(ip_port, "未知")
        # 收集可用IP的运营商
        operator_playable_ips.setdefault(operator, set()).add(ip_port)
        
        # 生成频道行
        for ch_name, url in groups.get(ip_port, []):
            key = f"{ch_name},{url}"
            if key not in seen:
                seen.add(key)
                valid_lines.append(f"{ch_name},{url}${operator}")

    # 清理空IP文件
    print("\n🧹 清理无效IP文件...")
    for fname in os.listdir(IP_DIR):
        file_path = os.path.join(IP_DIR, fname)
        if not fname.endswith(".txt"):
            continue
        # 删除空文件
        if os.path.getsize(file_path) == 0:
            os.remove(file_path)
            print(f"✅ 删除空文件：{fname}")
        # 删除无可用IP的文件
        operator = fname.replace(".txt", "")
        if operator not in operator_playable_ips and os.path.getsize(file_path) > 0:
            os.remove(file_path)
            print(f"✅ 删除无效文件：{fname}")

    # 写回可用IP文件
    print("\n💾 写回可用IP文件...")
    for operator, ip_set in operator_playable_ips.items():
        target_file = os.path.join(IP_DIR, f"{operator}.txt")
        try:
            with open(target_file, "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(ip_set)) + "\n")
            print(f"✅ {target_file} → 保留 {len(ip_set)} 个可用IP")
        except Exception as e:
            print(f"❌ 写回 {target_file} 失败：{e}")

    # 生成最终IPTV.txt
    print("\n📺 生成IPTV.txt...")
    beijing_now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(IPTV_FILE, "w", encoding="utf-8") as f:
            # 写入头部信息
            f.write(f"# IPTV列表 - 更新时间：{beijing_now}（北京时间）\n")
            f.write(f"# 格式：频道名,播放地址$运营商\n")
            f.write(f"# 总计有效频道：{len(valid_lines)}\n\n")
            
            # 按分类写入频道
            for category, ch_list in CHANNEL_CATEGORIES.items():
                f.write(f"# === {category} ===\n")
                # 筛选当前分类的频道
                category_lines = [
                    line for line in valid_lines 
                    if line.split(",", 1)[0] in ch_list
                ]
                # 写入分类频道
                for line in category_lines:
                    f.write(line + "\n")
                f.write("\n")
                print(f"✅ {category} → {len(category_lines)} 个有效频道")

        print(f"\n🎉 IPTV.txt 生成完成 → 总计 {len(valid_lines)} 条有效频道")
    except Exception as e:
        print(f"❌ 生成IPTV.txt失败：{e}")

# ===============================
# GitHub推送函数（安全版）
def push_all_files():
    """安全推送文件到GitHub，避免命令注入"""
    print("\n🚀 推送更新到GitHub...")
    try:
        from subprocess import run, PIPE, CalledProcessError

        # 封装Git命令执行
        def git_exec(args):
            try:
                result = run(
                    args,
                    check=True,
                    stdout=PIPE,
                    stderr=PIPE,
                    text=True
                )
                return result.stdout
            except CalledProcessError as e:
                print(f"⚠️ Git命令失败：{e.stderr}")
                return None

        # 配置Git用户
        git_exec(["git", "config", "--global", "user.name", "github-actions"])
        git_exec(["git", "config", "--global", "user.email", "github-actions@users.noreply.github.com"])

        # 添加文件
        git_exec(["git", "add", COUNTER_FILE])
        git_exec(["git", "add", f"{IP_DIR}/*.txt"])
        git_exec(["git", "add", ZUBO_FILE])
        git_exec(["git", "add", IPTV_FILE])
        git_exec(["git", "add", HISTORY_FILE])

        # 检查是否有变更
        status = git_exec(["git", "status", "--porcelain"])
        if not status:
            print("ℹ️ 无文件变更，无需提交")
            return

        # 提交并推送
        commit_msg = f"自动更新IPTV列表 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        git_exec(["git", "commit", "-m", commit_msg])
        git_exec(["git", "push", "origin", "main"])

        print("✅ 推送成功！")
    except Exception as e:
        print(f"❌ 推送失败：{e}")

# ===============================
# 主执行逻辑
if __name__ == "__main__":
    print("="*50)
    print("🎬 启动FOFA IPTV自动爬取程序")
    print(f"🕒 当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)

    # 确保目录存在
    os.makedirs(IP_DIR, exist_ok=True)
    os.makedirs(RTP_DIR, exist_ok=True)

    try:
        # 第一阶段：爬取与分类
        run_count = first_stage()

        # 触发条件：每10轮 或 凌晨3点-3点15分之间
        now = datetime.now()
        trigger_full = (run_count % 10 == 0) or (now.hour == 3 and 0 <= now.minute < 15)
        
        if trigger_full:
            # 第二阶段：生成zubo.txt
            second_stage()
            # 第三阶段：检测与IPTV生成
            third_stage()
        else:
            print(f"\nℹ️ 当前轮次 {run_count}，未触发第二、三阶段（每10轮或凌晨3点执行全量检测）")

        # 推送更新到GitHub
        push_all_files()

    except Exception as e:
        print(f"\n💥 程序执行异常：{e}")
        # 尝试推送错误状态
        push_all_files()

    print("\n="*50)
    print("🔚 程序执行结束")
    print("="*50)
