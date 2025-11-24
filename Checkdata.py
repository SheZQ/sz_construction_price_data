import asyncio
import re
import json
import datetime
from collections import defaultdict
from playwright.async_api import async_playwright

async def check_data_counts():
    # 数据结构：年份 -> 期数 -> 分类 -> 数据量
    year_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    # 年份总数据量
    year_totals = defaultdict(int)

    async with async_playwright() as p:
        # 启动浏览器（调试时设为False，生产环境设为True）
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://zjj.sz.gov.cn/szzjxx/web/pc/index")
        await page.wait_for_selector('#ztree')  # 等待页面加载完成

        # 1. 获取所有年份
        years = await page.evaluate('''
            () => new Promise(resolve => {
                $.ajax({
                    url: "/szzjxx/priceinfo/pc/yearinfo",
                    type: "POST",
                    dataType: "json",
                    success: (data) => {
                        resolve(data.map(item => item.yearNum).sort((a, b) => b - a));
                    }
                });
            })
        ''')
        print(f"检测到年份: {years}")

        # 2. 遍历每个年份
        for year in years:
            print(f"\n===== 开始处理年份: {year} =====")
            
            # 获取该年份的所有期数
            periods = await page.evaluate('''
                (year) => new Promise(resolve => {
                    $.ajax({
                        url: "/szzjxx/priceinfo/pc/currentyear",
                        type: "POST",
                        data: {year: year},
                        dataType: "json",
                        success: (data) => {
                            resolve(data.map(period => ({
                                id: period.id,
                                name: period.periodName
                            })));
                        }
                    });
                })
            ''', year)

            # 3. 遍历每期数据
            for period in periods:
                period_id = period['id']
                period_name = period['name']
                print(f"\n处理期数: {period_name} (ID: {period_id})")

                # 获取该期的所有分类
                categories = await page.evaluate('''
                    (period_id) => new Promise(resolve => {
                        $.ajax({
                            url: "/szzjxx/priceinfo/pc/getcategorytreelist",
                            type: "POST",
                            data: {periodid: period_id},
                            dataType: "json",
                            success: (data) => {
                                // 提取二级分类
                                const result = [];
                                data.forEach(top => {
                                    if (top.children && top.children.length > 0) {
                                        top.children.forEach(child => {
                                            result.push({
                                                id: child.id,
                                                name: child.name
                                            });
                                        });
                                    }
                                });
                                resolve(result);
                            }
                        });
                    })
                ''', period_id)

                # 4. 遍历每个分类，从AJAX返回值提取真实数据量
                for category in categories:
                    category_id = category['id']
                    category_name = category['name']
                    
                    try:
                        # 关键修改：获取AJAX请求的原始返回值，从中提取total字段
                        ajax_result = await page.evaluate('''
                            (params) => new Promise(resolve => {
                                $.ajax({
                                    url: "/szzjxx/priceinfo/pc/all",
                                    type: "POST",
                                    data: {
                                        periodId: params.period_id,
                                        categoryIds: params.category_id,
                                        page: 1,
                                        rows: 10,  // 仅请求10条，不影响total统计
                                        order: "asc",
                                        sort: "sequencenum"
                                    },
                                    dataType: "json",
                                    success: (data) => {
                                        // 直接返回接口的原始数据（包含total字段）
                                        resolve(data);
                                    },
                                    error: () => resolve(null)
                                });
                            })
                        ''', {
                            "period_id": period_id,
                            "category_id": category_id
                        })

                        # 从AJAX返回值中提取真实总数据量
                        if ajax_result and 'total' in ajax_result and ajax_result['total'] is not None:
                            real_count = int(ajax_result['total'])
                            year_data[year][period_name][category_name] = real_count
                            year_totals[year] += real_count
                            print(f"  分类: {category_name.ljust(35)} 数据量: {real_count}")
                        else:
                            print(f"  分类: {category_name.ljust(35)} 数据量: 0 (接口未返回total字段)")

                    except Exception as e:
                        # 捕获所有异常，标记数据量为0
                        error_msg = str(e)[:30] + "..." if len(str(e)) > 30 else str(e)
                        print(f"  分类: {category_name.ljust(35)} 数据量: 0 (错误: {error_msg})")
                        year_data[year][period_name][category_name] = 0

        await browser.close()

    # 生成并打印原生格式化表格
    print("\n" + "="*120)
    print("深圳市建设工程造价信息 - 真实数据量统计结果（按年份）")
    print("="*120)

    # 1. 年份汇总表
    print("\n【年份汇总统计】")
    if year_totals:
        # 动态计算列宽
        max_year_len = max(len(str(y)) for y in year_totals.keys())
        max_total_len = max(len(str(v)) for v in year_totals.values())
        # 表头
        print(f"{'年份'.ljust(max_year_len + 4)} | {'总数据量'.ljust(max_total_len + 4)} | {'包含期数'}")
        print("-" * (max_year_len + max_total_len + 20))
        # 表内容
        for year in sorted(year_totals.keys(), reverse=True):
            period_count = len(year_data[year])
            print(f"{str(year).ljust(max_year_len + 4)} | {str(year_totals[year]).ljust(max_total_len + 4)} | {period_count}")
    else:
        print("未获取到任何数据")

    # 2. 最新年份期数详情表
    if years:
        latest_year = max(years)
        print(f"\n【{latest_year}年期数详情统计】")
        period_data = year_data[latest_year]
        if period_data:
            # 动态计算期数列宽
            max_period_len = max(len(p) for p in period_data.keys())
            # 表头
            print(f"{'期数名称'.ljust(max_period_len + 4)} | {'数据量'}")
            print("-" * (max_period_len + 10))
            # 表内容
            for period_name, categories in period_data.items():
                period_total = sum(categories.values())
                print(f"{period_name.ljust(max_period_len + 4)} | {period_total}")
        else:
            print(f"{latest_year}年未获取到期数数据")

    # 3. 保存完整结果到JSON文件
    result = {
        "summary": {
            "total_all_years": sum(year_totals.values()),
            "total_by_year": dict(year_totals)
        },
        "detailed_data": {
            year: {
                period: {
                    "period_total": sum(categories.values()),
                    "categories": dict(categories)
                } for period, categories in periods.items()
            } for year, periods in year_data.items()
        },
        "check_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "note": "数据量从AJAX接口的total字段提取，为每个分类的真实数据条数"
    }

    with open("sz_price_real_data_count_verification.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*120)
    print(f"统计完成！所有年份总数据量: {sum(year_totals.values())} 条")
    print(f"完整结果已保存到: sz_price_real_data_count_verification.json")
    print("="*120)

if __name__ == "__main__":
    # 安装依赖：pip install playwright
    # 首次运行需安装浏览器：playwright install chromium
    asyncio.run(check_data_counts())