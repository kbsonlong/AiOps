BASE_PATTERNS = [
    (r"curl.*\$ENV", "dangerous", "可能泄露环境变量"),
    (r"wget.*\$ENV", "dangerous", "可能泄露环境变量"),
    (r"rm\s+-rf\s+/", "dangerous", "删除根目录"),
    (r"mkfs\.", "dangerous", "格式化文件系统"),
    (r"echo.*>>\s*~/(\.bashrc|\.zshrc)", "dangerous", "修改Shell配置文件"),
]

AIOPS_SPECIFIC_PATTERNS = [
    (
        r"(echo|cat).*(/var/lib/(prometheus|victoriametrics)|/var/log/)",
        "dangerous",
        "可能污染监控数据或日志",
    ),
    (
        r"systemctl\s+(stop|restart)\s+(prometheus|victoriametrics|grafana|alertmanager)",
        "caution",
        "停止关键监控服务",
    ),
    (r"kill\s+-\d+\s+\d+", "caution", "强制终止进程"),
    (r"sed\s+-i.*\.(yaml|yml|json|conf|properties)", "caution", "直接修改配置文件"),
    (r"echo.*>\s*/etc/", "dangerous", "修改系统配置文件"),
    (r"stress(-ng)?\s+--cpu\s+\d+", "caution", "CPU压力测试"),
    (r"dd\s+if=/dev/zero", "caution", "磁盘填充测试"),
    (r"logger.*(crit|alert|emerg|err|warning)", "caution", "写入系统日志"),
    (r"iptables.*DROP", "caution", "修改防火墙规则"),
    (r"tc\s+qdisc.*(delay|loss)", "caution", "修改网络流量"),
    (r"docker\s+(rm\s+-f|stop)\s+", "caution", "强制删除或停止容器"),
    (r"kubectl\s+delete\s+", "caution", "删除Kubernetes资源"),
]

WHITELIST_PATTERNS = [
    r"#\s*ALLOWED:\s*.+",
    r"systemctl\s+status\s+",
    r"kubectl\s+get\s+",
    r"docker\s+ps\s+",
]
