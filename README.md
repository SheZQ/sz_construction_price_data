# sz_construction_price_data
用于爬取：https://zjj.sz.gov.cn/szzjxx/web/pc/index
获取全部信息价，已整理2025年10月份-2018年1月份的数据。

# 深圳市建设工程造价信息爬虫

## 项目介绍

这是一个使用 Playwright 框架开发的网络爬虫，用于抓取深圳市住房和建设局网站的工程造价信息，并将数据存储到 SQLite 数据库中。程序能够自动获取多年度、多期数、多分类的造价数据，为工程造价分析提供数据支持。

## 功能特点

- 自动获取所有可查询年份的造价信息
- 按年份和期数层次化爬取数据
- 支持多分类数据抓取
- 自动分页获取完整数据
- 数据存储到 SQLite 数据库，便于后续分析
- 使用 Playwright 模拟浏览器行为，支持动态内容加载

## 技术栈

- Python 3.7+
- Playwright：用于网页自动化和数据抓取
- SQLite：轻量级数据库，用于数据存储
- asyncio：Python 异步编程框架

## 安装指南

1. 克隆本仓库
   ```bash
   git clone https://github.com/SheZQ/sz_construction_price_data.git
   ```

2. 安装依赖包
   ```bash
   pip install playwright
   ```

3. 安装 Playwright 浏览器
   ```bash
   playwright install chromium
   ```

## 使用方法

1. 直接运行主程序
   ```bash
   python main.py
   ```

2. 程序运行过程中会显示抓取进度，包括：
   - 获取到的年份列表
   - 各年份包含的期数
   - 当前正在处理的期数和分类
   - 数据存储状态

3. 抓取完成后，数据将保存在当前目录的 `sz_price_info.db` 文件中

## 数据库结构

程序会自动创建名为 `price_data` 的数据表，结构如下：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 自增主键 |
| period_id | TEXT | 期数ID |
| period_name | TEXT | 期数名称 |
| category_id | TEXT | 分类ID |
| category_name | TEXT | 分类名称 |
| item_name | TEXT | 项目名称 |
| specification | TEXT | 规格 |
| unit | TEXT | 单位 |
| price | TEXT | 价格 |
| update_time | TIMESTAMP | 数据更新时间 |

## 实现原理

1. **初始化数据库**：程序启动时创建 SQLite 数据库及数据表
2. **启动浏览器**：使用 Playwright 启动 Chromium 浏览器
3. **层级数据抓取**：
   - 第一步：获取所有可查询的年份
   - 第二步：对每个年份，获取所有期数
   - 第三步：对每一期，获取所有分类
   - 第四步：对每个分类，分页获取详细数据
4. **数据存储**：将抓取到的数据实时存入数据库

## 注意事项

1. 程序默认以非无头模式（headless=False）运行，可看到浏览器操作过程，如需后台运行，可修改为 `headless=True`
2. 网站可能有访问频率限制，如遇抓取失败可适当增加延迟
3. 数据抓取时间取决于网络状况和数据量大小，请耐心等待
4. 本程序仅用于学习和研究，使用时请遵守网站的 robots 协议和相关规定

## 维护与扩展

- 若网站结构发生变化，可能需要调整选择器（如 `#ztree`）和 API 端点
- 可根据需要扩展数据库字段，增加更多数据维度
- 可添加代理功能以应对 IP 限制

## 提供checkdata.py供检测爬取数据数量是否对应得上
生成json格式方便转换任意格式使用

## 许可证

[MIT](LICENSE)
