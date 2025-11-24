import asyncio
from playwright.async_api import async_playwright
import json
import datetime
import sqlite3

# 初始化数据库
def init_db():
    conn = sqlite3.connect('sz_price_info.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS price_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        period_id TEXT,
        period_name TEXT,
        category_id TEXT,
        category_name TEXT,
        item_name TEXT,
        specification TEXT,
        unit TEXT,
        price TEXT,
        update_time TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

async def main():
    init_db()
    conn = sqlite3.connect('sz_price_info.db')
    cursor = conn.cursor()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://zjj.sz.gov.cn/szzjxx/web/pc/index")
        
        # 等待页面加载完成（根据目标网站实际实际元素调整）
        await page.wait_for_selector('#ztree')

        # 1. 获取所有年份（从API直接获取）
        years = await page.evaluate('''
            async () => {
                return new Promise((resolve) => {
                    $.ajax({
                        url: "/szzjxx/priceinfo/pc/yearinfo",
                        type: "POST",
                        dataType: "json",
                        async: true,
                        success: (data) => {
                            // 按年份倒序排列
                            resolve(data.sort((a, b) => b.yearNum - a.yearNum).map(item => item.yearNum));
                        }
                    });
                });
            }
        ''')
        print(f"获取到年份列表: {years}")

        # 2. 遍历年份（从最新开始）
        for year in years:
            # 获取该年份的所有期数
            periods = await page.evaluate('''
                async (year) => {
                    return new Promise((resolve) => {
                        $.ajax({
                            url: "/szzjxx/priceinfo/pc/currentyear",
                            type: "POST",
                            dataType: "json",
                            data: {year: year},
                            async: true,
                            success: (data) => {
                                // 按期数倒序（根据期数名称中的月份排序）
                                resolve(data.sort((a, b) => new Date(b.periodName) - new Date(a.periodName)));
                            }
                        });
                    });
                }
            ''', year)  # 通过第二个参数传递year

            print(f"年份 {year} 的期数列表: {[p['periodName'] for p in periods]}")

            # 3. 遍历每期数据（从最新期开始）
            for period in periods:
                period_id = period['id']
                period_name = period['periodName']
                print(f"正在处理: {period_name} (ID: {period_id})")

                # 获取该期的分类列表
                categories = await page.evaluate('''
                    async (period_id) => {
                        return new Promise((resolve) => {
                            $.ajax({
                                url: "/szzjxx/priceinfo/pc/getcategorytreelist",
                                type: "POST",
                                dataType: "json",
                                data: {periodid: period_id},
                                async: true,
                                success: (data) => {
                                    // 收集所有二级分类（跳过顶级分类）
                                    let result = [];
                                    data.forEach(top => {
                                        if (top.children) {
                                            top.children.forEach(child => {
                                                result.push({id: child.id, name: child.name});
                                            });
                                        }
                                    });
                                    resolve(result);
                                }
                            });
                        });
                    }
                ''', period_id)  # 通过第二个参数传递period_id

                # 4. 遍历每个分类获取数据
                for category in categories:
                    category_id = category['id']
                    category_name = category['name']
                    print(f"  正在处理分类: {category_name}")

                    # 分页获取所有数据
                    page_num = 1
                    while True:
                        data = await page.evaluate('''
                            async (params) => {
                                return new Promise((resolve) => {
                                    $.ajax({
                                        url: "/szzjxx/priceinfo/pc/all",
                                        type: "POST",
                                        dataType: "json",
                                        data: {
                                            periodId: params.period_id,
                                            categoryIds: params.category_id,
                                            page: params.page_num,
                                            rows: 100,
                                            order: "asc",
                                            sort: "sequencenum"
                                        },
                                        async: true,
                                        success: (data) => {
                                            resolve(data);
                                        }
                                    });
                                });
                            }
                        ''', {
                            "period_id": period_id,
                            "category_id": category_id,
                            "page_num": page_num
                        })  # 通过参数传递所有需要的变量

                        # 保存数据到数据库
                        if data.get('rows'):
                            for item in data['rows']:
                                cursor.execute('''
                                INSERT INTO price_data 
                                (period_id, period_name, category_id, category_name, 
                                 item_name, specification, unit, price, update_time)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (
                                    period_id,
                                    period_name,
                                    category_id,
                                    category_name,
                                    item.get('mc', ''),  # 修复：使用'mc'字段获取材料名称
                                    item.get('gg', ''),  # 规格
                                    item.get('dw', ''),  # 单位
                                    item.get('djSq', ''),  # 价格
                                    datetime.datetime.now()
                                ))
                            conn.commit()
                            page_num += 1
                        else:
                            break  # 没有更多数据

        await browser.close()
    conn.close()
    

if __name__ == "__main__":
    asyncio.run(main())