"""「兔子山的小站」内容归档工具链。

模块划分：

* :mod:`config`      —— 站点常量、抓取礼貌参数、路径布局
* :mod:`models`      —— 数据模型与可访问性标记
* :mod:`http_client` —— 限速 + 退避 + 磁盘缓存 + 熔断的 HTTP 客户端
* :mod:`archive`     —— Internet Archive 补足
* :mod:`discover`    —— 站点结构发现与分页枚举
* :mod:`parsers`     —— HTML → 结构化数据
* :mod:`html2md`     —— HTML 片段 → Markdown
* :mod:`index_map`   —— 索引①/② 解析为分类映射
* :mod:`media`       —— 图片下载与完整性校验
* :mod:`emit`        —— 生成 md / manifest / sidebar / 首页
* :mod:`verify`      —— 归档结果校验
* :mod:`cli`         —— 命令行入口
"""

__version__ = "0.1.0"
