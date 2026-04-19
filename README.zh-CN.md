# YSU Campus Network Auto Login

[English](https://github.com/Summerandbreeze/Ysu_netlogin/blob/main/README.md) | [Chinese](https://github.com/Summerandbreeze/Ysu_netlogin/blob/main/README.zh-CN.md)

燕山大学校园网自动认证脚本，适用于 Windows 环境下的校园网掉线重连场景，并尽量兼容 Clash Verge 开启时的使用体验。

这个项目的目标很明确：当校园网掉线，或者重新要求认证时，脚本自动检测网络并重新登录，尽量避免为了认证而手动退出 Clash Verge。

## 项目功能

- 检测当前是否真正联网
- 避免把校园网认证页误判成正常外网
- 优先尝试直连 Portal 接口登录
- 必要时回退到旧版 CAS 流程
- 支持单次运行、守护模式和 Windows 计划任务
- 通过 `curl --noproxy '*'` 尽量减少代理和 TUN 干扰

## 环境要求

- Windows 10 或 Windows 11
- Python 3.9 及以上版本
- 系统中可用 `curl.exe`
- 已连接燕山大学校园网 Wi-Fi 或有线网络

## 文件说明

- `ysu_login.py`：主脚本
- `config.example.json`：配置模板
- 普通启动 BAT：以普通窗口启动守护模式
- 静默启动 BAT：以最小化方式启动守护模式
- 定时任务 BAT：安装 Windows 计划任务

## 安装步骤

### 1. 克隆仓库

```powershell
git clone https://github.com/Summerandbreeze/Ysu_netlogin.git
cd Ysu_netlogin
```

### 2. 创建本地配置文件

```powershell
copy config.example.json config.json
```

编辑 `config.json`，填入你的真实账号和密码：

```json
{
    "userId": "2024XXXXXXXX",
    "password": "your_password_here",
    "service": 3,
    "check_interval": 300,
    "log_file": "login.log"
}
```

## 配置说明

`config.json` 中各字段含义如下：

- `userId`：校园网账号或学号
- `password`：校园网密码
- `service`：运营商编号
- `check_interval`：守护模式下的检查间隔，单位为秒
- `log_file`：日志文件名

`service` 取值：

- `0`：校园网
- `1`：中国移动
- `2`：中国联通
- `3`：中国电信

## 首次测试

建议先手动执行一次，不要一开始就直接安装计划任务：

```powershell
python ysu_login.py once
```

强制执行登录：

```powershell
python ysu_login.py login
```

只检查当前网络状态：

```powershell
python ysu_login.py status
```

如果这一步都不能正常运行，先修正配置，再考虑设置自动运行。

## 自动运行方式

### 方式一：守护模式

每 300 秒检查一次：

```powershell
python ysu_login.py daemon 300
```

你也可以直接双击仓库根目录中的以下两类 BAT 文件之一：

- 普通窗口启动的 BAT
- 开机最小化启动的 BAT

如果希望随 Windows 启动，建议把最小化启动的 BAT 放进启动项文件夹。

### 方式二：Windows 计划任务

如果你不想让 Python 常驻运行，可以使用仓库根目录中的定时任务 BAT 文件来安装计划任务。

安装完成后，可以先列出所有计划任务，再查找本项目创建的任务：

```powershell
schtasks /query
```

也可以直接打开任务计划程序，查找安装脚本创建的任务。

## Clash Verge 说明

这个项目的设计目标不是“先退出 Clash 再认证”，而是尽量在 Clash Verge 开启时也能完成认证。

主要思路：

- 使用 `curl --noproxy '*'`
- 尽量直连认证接口
- 降低代理和 TUN 对认证流程的干扰

如果在 Clash Verge 开启时仍然无法登录，建议按顺序检查：

1. 校园网认证域名是否被错误地走了代理
2. 开启 TUN 时，是否需要把认证域名或 IP 加入 `DIRECT`
3. 再次执行 `python ysu_login.py login`
4. 只有在必要时，才临时关闭 TUN 作为兜底方案

## 日志

默认日志文件：

- `login.log`

推荐排查步骤：

1. 运行 `python ysu_login.py status`
2. 运行 `python ysu_login.py login`
3. 打开 `login.log`
4. 检查失败原因是账号、CAS、Portal，还是代理处理问题

## 安全说明

不要公开提交以下文件：

- `config.json`
- `.login_cookies.txt`
- `login.log`
- 任何包含真实账号、密码、Cookie 或会话信息的文件

仓库中只保留 `config.example.json` 作为模板。

## 免责声明

本项目仅用于个人使用和学习研究，请确认你的使用方式符合学校的网络管理要求。

