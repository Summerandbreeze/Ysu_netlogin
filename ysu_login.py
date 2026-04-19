# -*- coding: utf-8 -*-
"""
燕山大学校园网自动登录脚本 v2.0
适配新版 CAS/OAuth2 认证系统 (auth1.ysu.edu.cn + cer.ysu.edu.cn)

认证流程（从 debug 脚本逆向分析得出）:
1. 新版认证服务器: auth1.ysu.edu.cn (Portal + CAS SSO SPA)
2. 旧版统一身份认证: cer.ysu.edu.cn (传统 CAS, 需要验证码)
3. Portal API: /api/aggregation/portal/portalAuthen/login (JSON, 需要 queryString)

关键发现:
- portalAuthen/login 返回 "Portal认证失败" = CAS session 未建立
- 旧 CAS 服务器需要验证码(captcha)
- 密码通过 AES-ECB 加密传输 (key from login-croypto 字段)
- queryString 包含设备信息 (wlanuserip, nasip, mac 等)
- 使用 curl.exe 绕过 TUN 模式的 SSL 拦截

特性:
- curl.exe 作为 HTTP 客户端 (绕过 TUN/Clash 代理)
- 自动检测网络状态
- 支持守护模式
- 完整日志记录
"""

import json
import sys
import os
import re
import time
import subprocess
import socket
import uuid
import logging
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# ========== 配置 ==========
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
LOG_FILE = os.path.join(SCRIPT_DIR, "login.log")
COOKIE_FILE = os.path.join(SCRIPT_DIR, ".login_cookies.txt")

# 服务器地址
NEW_AUTH_HOST = "https://auth1.ysu.edu.cn"      # 新版 Portal + CAS SSO
OLD_AUTH_HOST = "https://cer.ysu.edu.cn"       # 旧版统一身份认证 (CAS)
PORTAL_API = f"{NEW_AUTH_HOST}/api/aggregation/portal/portalAuthen/login"
PORTAL_LOGIN_ESCAPE = f"{NEW_AUTH_HOST}/api/aggregation/portal/portalAuthen/login_escape"

# 网络测试地址
TEST_URLS = [
    "http://www.baidu.com",
    "http://www.qq.com",
    "http://connectivitycheck.gstatic.com/generate_204",
]

NETWORK_CHECKS = [
    {
        "url": "http://connectivitycheck.gstatic.com/generate_204",
        "expect_status": 204,
    },
    {
        "url": "http://www.msftconnecttest.com/connecttest.txt",
        "expect_text": "Microsoft Connect Test",
        "expect_host": "www.msftconnecttest.com",
    },
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ============================================================
# curl 封装 - 绕过 TUN/代理
# ============================================================

def _curl_cmd():
    """?? curl ???????"""
    curl_path = shutil.which("curl.exe") or shutil.which("curl")
    if not curl_path:
        raise FileNotFoundError("curl executable not found")
    return curl_path

def curl_get(url, cookie_jar=None, extra_headers=None, timeout=15, follow=0):
    """
    使用 curl.exe 发起 GET 请求
    返回: (body_text, header_text)
    """
    ck = cookie_jar or COOKIE_FILE
    cmd = [
        _curl_cmd(), '-k', '--noproxy', '*',
        '-s',
        '-b', ck, '-c', ck,
        '--connect-timeout', str(timeout), '--max-time', str(timeout),
        '-H', f'User-Agent: {USER_AGENT}',
    ]
    if extra_headers:
        for h in extra_headers:
            cmd += ['-H', h]
    if follow:
        cmd.append('-L')

    # 用临时文件捕获响应
    body_file = os.path.join(SCRIPT_DIR, '._curl_body.tmp')
    hdr_file = os.path.join(SCRIPT_DIR, '._curl_hdr.tmp')
    
    cmd += ['-D', hdr_file, '-o', body_file, url]

    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout+5, 
                          env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        
        body = ''
        hdr = ''
        if os.path.exists(body_file):
            with open(body_file, 'rb') as f:
                body = f.read().decode('utf-8', errors='replace')
            os.remove(body_file)
        if os.path.exists(hdr_file):
            with open(hdr_file, 'r', errors='ignore') as f:
                hdr = f.read()
            os.remove(hdr_file)
        
        return body, hdr
        
    except FileNotFoundError:
        # curl.exe not found fallback - try with urllib
        return _urllib_fallback('GET', url, timeout=timeout)
    except Exception as e:
        return '', str(e)


def curl_post(url, data_str, content_type='application/json;charset=UTF-8',
               cookie_jar=None, timeout=15, follow=0):
    """
    使用 curl.exe 发起 POST 请求
    返回: (body_text, header_text)
    """
    ck = cookie_jar or COOKIE_FILE
    
    # 写入 POST 数据到临时文件
    post_file = os.path.join(SCRIPT_DIR, '._curl_post.tmp')
    with open(post_file, 'wb') as f:
        f.write(data_str.encode('utf-8'))
    
    body_file = os.path.join(SCRIPT_DIR, '._curl_body.tmp')
    hdr_file = os.path.join(SCRIPT_DIR, '._curl_hdr.tmp')
    
    cmd = [
        _curl_cmd(), '-k', '--noproxy', '*',
        '-s',
        '-b', ck, '-c', ck,
        '--connect-timeout', str(timeout), '--max-time', str(timeout),
        '-H', f'User-Agent: {USER_AGENT}',
        '-H', f'Content-Type: {content_type}',
        '-D', hdr_file, '-o', body_file,
    ]
    if follow:
        cmd.append('-L')
    cmd += ['--data-binary', '@' + post_file, url]

    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout+5,
                          env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        
        # 清理 post 文件
        if os.path.exists(post_file):
            os.remove(post_file)
        
        body = ''
        hdr = ''
        if os.path.exists(body_file):
            with open(body_file, 'rb') as f:
                body = f.read().decode('utf-8', errors='replace')
            os.remove(body_file)
        if os.path.exists(hdr_file):
            with open(hdr_file, 'r', errors='ignore') as f:
                hdr = f.read()
            os.remove(hdr_file)
        
        return body, hdr
            
    except FileNotFoundError:
        if os.path.exists(post_file):
            os.remove(post_file)
        return _urllib_fallback('POST', url, data_str, content_type, timeout)
    except Exception as e:
        if os.path.exists(post_file):
            os.remove(post_file)
        return '', str(e)


def _urllib_fallback(method, url, data=None, ctype='', timeout=10):
    """curl 不可用时的 urllib 回退方案"""
    try:
        import urllib.request
        headers = {'User-Agent': USER_AGENT}
        if method == 'POST' and data:
            headers['Content-Type'] = ctype or 'application/x-www-form-urlencoded'
            req = urllib.request.Request(url, data=data.encode('utf-8'), headers=headers)
        else:
            req = urllib.request.Request(url, headers=headers)
        
        # 不使用代理
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        resp = opener.open(req, timeout=timeout)
        return resp.read().decode('utf-8', errors='replace'), ''
    except Exception as e:
        return '', str(e)


# ============================================================
# 工具函数
# ============================================================

def get_local_ip():
    """?????????????? IPv4 ??"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("211.81.208.243", 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith('169.254.') and not ip.startswith('127.'):
                return ip
    except:
        pass

    try:
        hostname = socket.gethostname()
        for _, _, _, _, sockaddr in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = sockaddr[0]
            if ip and not ip.startswith('169.254.') and not ip.startswith('127.'):
                return ip
    except:
        pass

    raise RuntimeError("??????????? IPv4??????????? Wi-Fi/????")

def get_mac_address():
    """获取本机 MAC 地址"""
    try:
        mac_num = uuid.getnode()
        return ':'.join([f'{(mac_num >> (8*i)) & 0xff:02x}' for i in range(6)][::-1])
    except:
        return "00:00:00:00:00:00"


def build_query_string(ip=None, ssid='YSU-5G'):
    """构建设备信息 queryString"""
    if ip is None:
        ip = get_local_ip()
    mac = get_mac_address()
    mac_dash = mac.replace(':', '-').upper()
    
    # NAS IP 是认证设备的网关 IP (燕山大学校园网固定)
    nas_ip = "211.81.208.243"  
    
    return (
        f"wlanuserip={ip}"
        f"&wlanacname={ssid}"
        f"&wlanssid={ssid}"
        f"&nasip={nas_ip}"
        f"&mac={mac_dash}"
    )



def _parse_status_code(header_text):
    """? curl ???????? HTTP ???"""
    if not header_text:
        return None
    matches = re.findall(r'HTTP/\d+(?:\.\d+)?\s+(\d{3})', header_text)
    if not matches:
        return None
    try:
        return int(matches[-1])
    except ValueError:
        return None


def _extract_final_url(header_text, fallback_url):
    """???? URL???????????????"""
    if header_text:
        locations = re.findall(r'^[Ll]ocation:\s*(\S+)', header_text, re.MULTILINE)
        if locations:
            return locations[-1].strip()
    return fallback_url

def setup_logging(log_file):
    """配置日志"""
    logger = logging.getLogger("YSU_NetLogin")
    logger.setLevel(logging.DEBUG)
    
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', 
                            datefmt='%Y-%m-%d %H:%M:%S')
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def load_config(config_file):
    """加载配置文件"""
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    uid = config.get('userId', config.get('username', ''))
    pwd = config.get('password', '')
    
    if not uid or not pwd or uid in ('在这里填你的学号', '') or pwd in ('在这里填你的密码', ''):
        print("[!] 请先编辑 config.json，填入你的学号和密码！")
        sys.exit(1)
    
    return config


# ============================================================
# 核心功能：网络检测与登录
# ============================================================

def is_network_ok(logger=None):
    """????????????????????"""
    for check in NETWORK_CHECKS:
        try:
            url = check["url"]
            body, hdr = curl_get(url, timeout=6, follow=1)
            status_code = _parse_status_code(hdr)
            final_url = _extract_final_url(hdr, url)
            final_host = urlparse(final_url).netloc.lower()

            expect_status = check.get("expect_status")
            if expect_status is not None and status_code == expect_status:
                return True

            expect_text = check.get("expect_text")
            expect_host = check.get("expect_host", "").lower()
            if expect_text and expect_text in body:
                if not expect_host or final_host == expect_host:
                    return True
        except:
            continue
    return False

def check_portal_login_status(logger=None):
    """检查 Portal 登录状态"""
    try:
        qs = build_query_string()
        payload = json.dumps({"userId": "_status_check", "password": "", "queryString": qs})
        body, hdr = curl_post(PORTAL_API, payload)
        
        if body:
            try:
                rj = json.loads(body)
                d = rj.get('data', {})
                if isinstance(d, dict) and d.get('result') == 'success':
                    return True
            except:
                pass
    except:
        pass
    return False


def login_via_portal(userId, password, service_type='3', logger=None):
    """
    方案 A: 直接通过 Portal API 登录
    这是新系统的直接方式 - 如果 CAS session 已存在则可以直接入网
    """
    if logger is None:
        logger = logging.getLogger("YSU_NetLogin")
    
    try:
        # 先 GET portal 页面建立 session
        page_body, page_hdr = curl_get(f"{NEW_AUTH_HOST}/portal/index.html")
        
        qs = build_query_string()
        
        # 构建 JSON payload
        payload_data = {
            "userId": userId,
            "password": password,
            "queryString": qs,
            "service": str(service_type),
        }
        payload_str = json.dumps(payload_data, ensure_ascii=False)
        
        logger.info(f"POST -> portalAuthen/login ({len(qs)}b queryString)")
        
        body, hdr = curl_post(PORTAL_API, payload_str)
        
        if not body:
            return False, "无响应 (可能需要先完成 CAS 认证)"
        
        try:
            rj = json.loads(body)
            code = rj.get('code', -1)
            d = rj.get('data', {})
            
            if isinstance(d, dict):
                result = d.get('result', '')
                msg_raw = d.get('message', '')
                # Fix Chinese encoding
                try:
                    msg = msg_raw.encode('gbk', errors='replace').decode('utf-8', errors='replace')
                except:
                    msg = msg_raw
                
                user_index = d.get('userIndex')
                session_id = d.get('sessionId')
                
                if str(result).lower() == 'success':
                    logger.info(f"[OK] Portal 登录成功! userIndex={user_index}")
                    return True, f"认证成功 (sessionId={session_id})"
                elif code == 200:
                    logger.warning(f"[FAIL] {msg}")
                    return False, f"Portal: {msg}"
                else:
                    logger.warning(f"[FAIL] code={code}: {msg}")
                    return False, f"Portal error({code}): {msg}"
            else:
                msg = str(rj.get('message', body[:100]))
                logger.warning(f"[FAIL] 响应异常: {msg}")
                return False, msg
                
        except json.JSONDecodeError:
            logger.warning(f"[FAIL] 非 JSON 响应: {body[:200]}")
            return False, f"非标准响应: {body[:100]}"
            
    except Exception as e:
        logger.error(f"Portal 登录异常: {e}")
        return False, str(e)


def login_via_old_cas(userId, password, service_url=None, logger=None):
    """
    方案 B: 通过旧版 CAS 服务器 (cer.ysu.edu.cn) 登录
    传统 CAS 表单认证 - 可能需要验证码
    """
    if logger is None:
        logger = logging.getLogger("YSU_NetLogin")
    
    if service_url is None:
        service_url = f"{NEW_AUTH_HOST}/portal/index.html"
    
    try:
        # Step 1: GET 登录页获取 execution token
        login_url = f"{OLD_AUTH_HOST}/authserver/login?service={service_url}"
        body, hdr = curl_get(login_url)
        
        if not body or len(body) < 500:
            return False, "无法连接旧认证服务器"
        
        # 提取 form token
        exec_m = re.search(r'name=["\']execution["\'][^>]*value=["\']([^"\']+)"', body)
        lt_m = re.search(r'name=["\']lt["\'][^>]*value=["\']([^"\']+)"', body)
        
        exec_tok = exec_m.group(1) if exec_m else None
        lt_tok = lt_m.group(1) if lt_m else None
        
        if not exec_tok:
            return False, "无法获取 CAS execution token"
        
        # 检查是否有验证码要求
        has_captcha = bool(re.search(
            r'(?:captcha|randcode|verifyCode|validateCode|验证码)',
            body, re.I
        ))
        
        if has_captcha:
            logger.warning("[WARN] 旧 CAS 服务器需要验证码!")
            # TODO: 可以集成验证码识别 (如 ddddocr / OCR)
            return False, "CAS 服务器需要验证码 (请手动在浏览器登录一次或使用新流程)"
        
        # Step 2: POST 登录表单
        form_data = f"username={userId}&password={password}&execution={exec_tok}&_eventId=submit"
        if lt_tok:
            form_data += f"&lt={lt_tok}"
        
        resp_body, resp_hdr = curl_post(
            f"{OLD_AUTH_HOST}/authserver/login",
            form_data,
            'application/x-www-form-urlencoded',
            follow=1  # Follow redirect on success!
        )
        
        # 检查是否成功 (有 CASTGC cookie 或 ticket)
        castgc_match = re.findall(r'Set-Cookie:\s*(CASTGC=[^;\s]+)', resp_hdr)
        has_castgc = any('Max-Age=0' not in c for c in castgc_match)
        
        loc_m = re.search(r'[Ll]ocation:\s*(.+)', resp_hdr)
        final_loc = loc_m.group(1).strip() if loc_m else ''
        has_ticket = 'ticket=' in final_loc.lower()
        
        still_login_page = 'execution' in resp_body[:3000]
        
        if has_castgc or has_ticket:
            logger.info("[OK] CAS 登录成功!")
            
            # 提取 ticket
            ticket_m = re.search(r'ticket=([^&\s]+)', final_loc)
            ticket = ticket_m.group(1) if ticket_m else None
            if ticket:
                logger.info(f"Service Ticket: {ticket[:30]}...")
            
            return True, "CAS 认证成功"
            
        elif still_login_page:
            # 查找错误消息
            err_patterns = [
                r'[\'"]([^"\']*(?:错误|失败|无效|不存在|锁定)[^"\']*)[\'"]',
                r'class="[^"]*error[^"]*"[^>]*>([^<]{10,300})',
            ]
            for ep in err_patterns:
                em = re.search(ep, resp_body, re.I)
                if em:
                    err_msg = em.group(1)[:150]
                    return False, f"CAS: {err_msg}"
            
            return False, "CAS 登录失败 (密码错误或账号问题)"
            
        else:
            return False, f"CAS 响应异常 (body={len(resp_body)}b)"
            
    except Exception as e:
        logger.error(f"CAS 登录异常: {e}")
        return False, str(e)


def do_full_login(userId, password, service_type='3', logger=None):
    """
    完整登录流程:
    1. 尝试直接通过 Portal API 入网
    2. 若失败，尝试旧 CAS 认证后再 Portal 入网
    """
    if logger is None:
        logger = logging.getLogger("YSU_NetLogin")
    
    logger.info("=" * 50)
    logger.info(f"开始登录 | userId={userId} | service={service_type}")
    
    # ===== 方法 1: 直接 Portal API =====
    logger.info("--- 方法 1/2: 直接 Portal API ---")
    success, msg = login_via_portal(userId, password, service_type, logger)
    if success:
        return True, msg
    
    logger.info(f"方法1失败: {msg}")
    
    # ===== 方法 2: 旧 CAS → Portal =====
    logger.info("--- 方法 2/2: 旧 CAS 认证 → Portal ---")
    
    cas_success, cas_msg = login_via_old_cas(userId, password, logger=logger)
    
    if cas_success:
        # CAS 成功后立即尝试 Portal 入网
        time.sleep(1)
        p_success, p_msg = login_via_portal(userId, password, service_type, logger)
        if p_success:
            return True, f"CAS+Portal: {p_msg}"
        else:
            return True, f"CAS 认证成功但 Portal 入网失败: {p_msg} (网络可能已通)"
    else:
        return False, f"全部方式失败: Portal={msg}, CAS={cas_msg}"


# ============================================================
# 主运行逻辑
# ============================================================

def run_once(config, logger):
    """执行一次检测和登录"""
    logger.info("=" * 50)
    logger.info("开始网络检测...")
    
    # 检查网络
    if is_network_ok(logger):
        logger.info(">>> [OK] 网络正常，无需操作")
        return True
    
    logger.info(">>> [!] 网络不可用，尝试自动登录...")
    
    # 执行登录
    user_id = config.get('userId', config.get('username', ''))
    password = config.get('password', '')
    service_type = str(config.get('service', '3'))
    
    success, message = do_full_login(user_id, password, service_type, logger)
    
    if success:
        time.sleep(2)
        if is_network_ok(logger):
            logger.info(">>> [OK] 🎉 网络恢复正常！")
            return True
        else:
            logger.warning("登录成功但网络仍不通，稍后再次检测")
            return False
    else:
        logger.error(f">>> [ERROR] 登录失败: {message}")
        return False


def run_daemon(config, logger, interval=None):
    """守护模式"""
    if interval is None:
        interval = config.get('check_interval', 300)
    
    user_id = config.get('userId', '(未设置)')
    logger.info("=" * 50)
    logger.info(f"燕山大学校园网自动登录 v2.0 (新版认证)")
    logger.info(f"账号: {user_id}")
    logger.info(f"检测间隔: {interval}秒")
    logger.info(f"按 Ctrl+C 退出")
    logger.info("")
    
    while True:
        try:
            run_once(config, logger)
            logger.info(f"下次检测: {interval}秒后\n")
            time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("收到中断信号，程序退出")
            break
        except Exception as e:
            logger.error(f"运行出错: {e}")
            time.sleep(30)


def main():
    # Windows 编码修复
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    logger = setup_logging(LOG_FILE)
    logger.info(f"燕山大学校园网自动登录工具 v2.0 (新版 CAS/OAuth2)")
    logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 加载配置
    try:
        config = load_config(CONFIG_FILE)
    except FileNotFoundError:
        logger.error(f"配置文件不存在: {CONFIG_FILE}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"配置文件格式错误: {e}")
        sys.exit(1)
    
    # 命令行参数
    if len(sys.argv) >= 2:
        cmd = sys.argv[1].lower()
        
        if cmd in ('once', 'login', 'l'):
            user_id = config.get('userId', config.get('username', ''))
            pwd = config.get('password', '')
            svc = str(config.get('service', '3'))
            
            if cmd == 'login':
                success, msg = do_full_login(user_id, pwd, svc, logger)
            else:
                success, msg = run_once(config, logger)
            
            if success:
                print(f"\n✅ {msg}")
            else:
                print(f"\n❌ {msg}")
                
        elif cmd in ('daemon', 'd'):
            interval = int(sys.argv[2]) if len(sys.argv) >= 3 else None
            run_daemon(config, logger, interval)
            
        elif cmd in ('status', 's'):
            ok = is_network_ok(logger)
            logger.info(f"网络状态: {'✅ 正常' if ok else '❌ 不可用'}")
            print(f"\n网络: {'✅ 已连接' if ok else '❌ 未连接'}")
            
        else:
            print_help()
    else:
        # 默认单次检测
        run_once(config, logger)


def print_help():
    print("""
燕山大学校园网自动登录工具 v2.0 (新版 CAS/OAuth2 适配)

用法:
  python ysu_login.py            单次检测，断网则自动登录
  python ysu_login.py once       同上
  python ysu_login.py login/l    强制登录
  python ysu_login.py daemon/d   守护模式
  python ysu_login.py daemon 60 守护模式, 每60秒检测一次  
  python ysu_login.py status/s   仅检查网络状态

配置文件: config.json
日志文件: login.log
    """)


if __name__ == '__main__':
    main()
